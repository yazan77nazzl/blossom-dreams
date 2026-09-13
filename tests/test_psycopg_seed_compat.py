"""
Regression tests for the Render/Neon startup crash.

Production error (psycopg.ProgrammingError):
    only '%s', '%b', '%t' are allowed as placeholders, got '%0'

Root cause: seed_data.py put a literal `%` into the SQL text of a
parameterized statement (LIKE '%0x151f4096b6ee7923%'). psycopg validates
`%` placeholders whenever a query is bound with parameters, while SQLite
never parses them — so SQLite tests could not catch it.

These tests use psycopg's real placeholder parser (`_queries._split_query`)
and drive seed_database() through the app's PgCursorWrapper in a simulated
PostgreSQL mode with a recording fake connection.
"""
import ast
import re
import types
from pathlib import Path

import pytest

psycopg = pytest.importorskip("psycopg")
from psycopg import _queries  # noqa: E402
from psycopg.errors import ProgrammingError  # noqa: E402

PROJECT = Path(__file__).resolve().parent.parent
SEED_FILE = PROJECT / "app" / "seed_data.py"


def _wrapper_convert(sql: str) -> str:
    """Mirror PgCursorWrapper.execute(): convert '?' placeholders to '%s'."""
    return re.sub(r"\?", "%s", sql)


def _extract_execute_sql(src: str):
    """Return (sql, has_params_flag) for every cursor.execute(...) call."""
    tree = ast.parse(src)
    out = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "execute"
        ):
            arg0 = node.args[0]
            if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                has_params = len(node.args) > 1
                out.append((arg0.value, has_params))
    return out


def _assert_psycopg_parseable(sql: str, params):
    """Run psycopg's real placeholder parsing; must not raise ProgrammingError."""
    converted = _wrapper_convert(sql).encode("utf-8")
    parts = _queries._split_query(converted, encoding="utf-8")
    ph_count = len(parts) - 1  # trailing QueryPart is the static tail
    if params is not None:
        assert ph_count == len(params), (
            f"placeholder count {ph_count} != params {len(params)} for SQL:\n{sql}"
        )


# --------------------------------------------------------------------------
# 1. Static scan of every SQL string in seed_data.py
# --------------------------------------------------------------------------
def test_static_seed_sql_is_psycopg_parseable():
    src = SEED_FILE.read_text(encoding="utf-8-sig")  # tolerate a BOM if present
    statements = _extract_execute_sql(src)
    assert statements, "expected seed_data.py to contain cursor.execute() calls"

    static_sql = [sql for sql, has_params in statements]
    assert all(isinstance(s, str) for s in static_sql)

    for sql, _has_params in statements:
        _assert_psycopg_parseable(sql, None)
        # With no parameters psycopg uses PQexec (no % parsing), but a literal
        # '%' in the statement is still a latent bug the moment it gets bound.
        converted = _wrapper_convert(sql)
        assert "%" not in converted.replace("%s", ""), (
            f"literal '%' remains in SQL text (must be a bound parameter):\n{sql}"
        )


def test_static_versailles_update_binds_like_pattern():
    src = SEED_FILE.read_text(encoding="utf-8-sig")
    statements = _extract_execute_sql(src)
    updates = [sql for sql, _ in statements if "UPDATE locations" in sql]
    assert updates, "Versailles locations UPDATE must exist"
    sql = updates[-1]
    # The LIKE pattern must be a bound parameter, never inlined into the SQL.
    assert "LIKE ?" in sql
    assert "%0x" not in sql
    assert "0x151f4096b6ee7923" not in sql
    assert "slug = ?" in sql


# --------------------------------------------------------------------------
# 2. Whole seed_database() run through the real cursor wrapper in a
#    simulated PostgreSQL mode (recording fake connection).
# --------------------------------------------------------------------------
class _FakeCursor:
    """Records every (sql, params) psycopg would receive; no real storage."""

    def __init__(self):
        self.records = []
        self.locations_exist = False
        self.lastrowid = 0
        self._pending = []

    def execute(self, sql, params=None):
        sql = sql or ""
        params = tuple(params) if params is not None else None
        self.records.append((sql, params))
        self._pending = []
        head = sql.lstrip().upper()
        if head.startswith("SELECT"):
            if "FROM LOCATIONS" in head and self.locations_exist:
                self._pending = [{"id": 1}]
            elif "COUNT(" in head:
                self._pending = [{"count": 0}]
        elif "RETURNING id" in head:
            self.lastrowid += 1
            self._pending = [{"id": self.lastrowid}]
        return self

    def fetchone(self):
        return self._pending.pop(0) if self._pending else None

    def fetchall(self):
        rows, self._pending = self._pending, []
        return rows


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


BROKEN_URL = "https://maps.google.com/?ftid=0x151f4096b6ee7923:0x1de97506f65318e9"


def _run_seed_in_simulated_postgres(monkeypatch, cursor):
    import app.database as db_mod

    # The PG-only names (PgCursorWrapper/PgConnectionWrapper, psycopg, dict_row)
    # live inside `if IS_POSTGRES:` and don't exist when running against SQLite.
    # Re-execute that branch so the REAL wrapper classes are exercised, then
    # swap in the fake psycopg.connect / dict_row.
    src = Path(db_mod.__file__).read_text(encoding="utf-8-sig")  # database.py has a BOM
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.If) and getattr(node.test, "id", None) == "IS_POSTGRES":
            ns = {
                "__name__": "app.database_pg_simulated",
                # module-level names the PG branch delegates to:
                "re": db_mod.re,
                "normalize_db_value": db_mod.normalize_db_value,
                "normalize_db_row": db_mod.normalize_db_row,
            }
            code = compile(ast.Module(node.body, []), "<app.database pg-sim>", "exec")
            exec(code, ns)
            break
    else:
        raise AssertionError("could not locate 'if IS_POSTGRES:' block in app/database.py")

    for name in ("PgCursorWrapper", "PgConnectionWrapper"):
        monkeypatch.setattr(db_mod, name, ns[name], raising=False)

    fake_psycopg = types.SimpleNamespace(
        connect=lambda *a, **k: _FakeConn(cursor),
    )
    monkeypatch.setattr(db_mod, "IS_POSTGRES", True)
    monkeypatch.setattr(db_mod, "psycopg", fake_psycopg, raising=False)
    monkeypatch.setattr(db_mod, "dict_row", dict, raising=False)

    from app.seed_data import seed_database

    seed_database()  # first pass: INSERT branch (fresh install)
    cursor.locations_exist = True
    cursor.records.clear()
    seed_database()  # second pass: legacy-exists branch runs the UPDATEs


def test_seed_runs_in_simulated_postgres_and_parses(monkeypatch):
    fake = _FakeCursor()
    _run_seed_in_simulated_postgres(monkeypatch, fake)

    assert fake.records, "expected seed_database() to issue SQL in PG mode"
    for sql, params in fake.records:
        _assert_psycopg_parseable(sql, params)


def test_versailles_update_fixes_legacy_url_not_amwaj(monkeypatch):
    fake = _FakeCursor()
    _run_seed_in_simulated_postgres(monkeypatch, fake)

    upserts = [
        (sql, params)
        for sql, params in fake.records
        if "UPDATE locations SET google_maps_url" in sql
    ]
    assert upserts, "Versailles UPDATE must run against a pre-existing location"
    sql, params = upserts[-1]

    # Literal '%' must never land in the SQL text psycopg parses.
    assert "%0x" not in sql
    assert "0x151f4096b6ee7923" not in sql

    # The corrected URL is bound, the slug filter is bound, the LIKE pattern
    # is bound — and the pattern itself (with %) travels in the parameters.
    url, slug, pattern = params
    assert slug == "versailles"
    assert url.startswith("https://www.google.com/maps?")
    assert "ftid=0x151f4096b6ee7923" in url
    assert pattern.startswith("%0x151f4096b6ee7923")

    # Amwaj must never be an UPDATE target in the locations table.
    assert not any(
        "UPDATE locations" in sql.upper() and "amwaj" in " ".join(map(str, params or [])).lower()
        for sql, params in fake.records
    )


def test_repro_old_bug_would_have_raised(monkeypatch):
    """Sanity check: the pre-fix inline LIKE would fail psycopg parsing."""
    buggy = """UPDATE locations SET google_maps_url = ?
               WHERE slug = 'versailles' AND google_maps_url LIKE '%0x151f4096b6ee7923%'"""
    with pytest.raises(ProgrammingError):
        _queries._split_query(_wrapper_convert(buggy).encode("utf-8"), encoding="utf-8")