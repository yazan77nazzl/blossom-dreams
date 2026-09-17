"""PostgreSQL-only database access and idempotent application schema."""
from contextlib import contextmanager
from datetime import date as _date, datetime as _datetime, time as _time
import re
import psycopg
from psycopg.rows import dict_row
from app.config import settings

IS_POSTGRES = True

def _normalise(value):
    if isinstance(value, _time):
        return value.strftime("%H:%M")
    return value.isoformat() if isinstance(value, (_datetime, _date)) else value

def _qmark_to_psycopg(sql: str) -> str:
    """Convert qmark bind placeholders without touching quoted URL/text data."""
    out, quoted, index = [], False, 0
    while index < len(sql):
        char = sql[index]
        if char == "'":
            out.append(char)
            if quoted and index + 1 < len(sql) and sql[index + 1] == "'":
                out.append("'")
                index += 2
                continue
            quoted = not quoted
        elif char == "?" and not quoted:
            out.append("%s")
        else:
            out.append(char)
        index += 1
    return "".join(out)

_TENANT_INSERT_TABLES = {
    "profiles", "admin_users", "categories", "services", "offers", "bookings",
    "availability_settings", "closed_dates", "gallery_images", "salon_settings",
    "locations", "location_availability_settings",
}

def _bind_tenant_on_insert(sql: str) -> str:
    """Add organization_id to legacy INSERTs that do not supply it explicitly."""
    match = re.match(r"(\s*INSERT\s+INTO\s+)([a-z_]+)(\s*\()([^)]*)(\)\s*VALUES\s*\()", sql, re.I | re.S)
    if not match or match.group(2).lower() not in _TENANT_INSERT_TABLES:
        return sql
    if "organization_id" in match.group(4).lower():
        return sql
    prefix = f"{match.group(1)}{match.group(2)}{match.group(3)}organization_id, {match.group(4)}{match.group(5)}current_setting('app.organization_id')::uuid, "
    return prefix + sql[match.end():]

class Cursor:
    """Adapts existing qmark SQL to psycopg; there is intentionally no SQLite path."""
    def __init__(self, cursor): self._cursor, self.lastrowid = cursor, None
    def execute(self, query, params=None):
        insert = bool(re.match(r"^\s*INSERT\s+INTO", query, re.I))
        returning = bool(re.search(r"\bRETURNING\b", query, re.I))
        sql = _bind_tenant_on_insert(_qmark_to_psycopg(query))
        if insert and not returning: sql = sql.rstrip().rstrip(";") + " RETURNING id"
        self._cursor.execute(sql, tuple(params) if params is not None else None)
        if insert and not returning:
            row = self._cursor.fetchone()
            self.lastrowid = row["id"] if row else None
        return self
    def fetchone(self):
        row = self._cursor.fetchone()
        return {k: _normalise(v) for k, v in row.items()} if row else None
    def fetchall(self):
        return [{k: _normalise(v) for k, v in row.items()} for row in self._cursor.fetchall()]

class Connection:
    def __init__(self, connection, organization_id: str | None = None):
        self._connection = connection
        self._organization_id = organization_id

    def cursor(self):
        return Cursor(self._connection.cursor(), self._organization_id)

    def commit(self): self._connection.commit()
    def rollback(self): self._connection.rollback()
    def close(self): self._connection.close()


class Cursor:
    """Adapts existing qmark SQL to psycopg; there is intentionally no SQLite path."""
    def __init__(self, cursor, organization_id: str | None = None):
        self._cursor, self.lastrowid = cursor, None
        self._organization_id = organization_id
        self._skip_org_context = False

    def execute(self, query, params=None, skip_org_context=False):
        # Prepend SET LOCAL for RLS to work with PgBouncer transaction pooling.
        # Each transaction gets a fresh backend connection; SET LOCAL ensures
        # app.organization_id is set for the current transaction only.
        # Skip for DDL (CREATE/ALTER/DROP/etc.) — they don't need RLS context.
        # Execute SET LOCAL as a separate command to avoid multi-command
        # prepared statement issues with PgBouncer/psycopg.
        ddl = bool(re.match(r"^\s*(CREATE|ALTER|DROP|TRUNCATE|COMMENT|GRANT|REVOKE|ANALYZE|VACUUM|REINDEX)\b", query, re.I))
        use_org = self._organization_id and not ddl and not skip_org_context
        if use_org:
            self._cursor.execute(f"SET LOCAL app.organization_id = '{self._organization_id}'")
        sql = query
        insert = bool(re.match(r"^\s*INSERT\s+INTO", sql, re.I))
        returning = bool(re.search(r"\bRETURNING\b", sql, re.I))
        sql = _bind_tenant_on_insert(_qmark_to_psycopg(sql))
        if insert and not returning: sql = sql.rstrip().rstrip(";") + " RETURNING id"
        self._cursor.execute(sql, tuple(params) if params is not None else None)
        if insert and not returning:
            row = self._cursor.fetchone()
            self.lastrowid = row["id"] if row else None
        return self

    def execute_no_org(self, query, params=None):
        """Execute without prepending SET LOCAL app.organization_id.
        For init_db bootstrap operations that run before RLS is fully configured."""
        return self.execute(query, params, skip_org_context=True)

    def fetchone(self):
        row = self._cursor.fetchone()
        return {k: _normalise(v) for k, v in row.items()} if row else None

    def fetchall(self):
        return [{k: _normalise(v) for k, v in row.items()} for row in self._cursor.fetchall()]


@contextmanager
def get_db():
    raw = psycopg.connect(settings.DATABASE_URL, row_factory=dict_row, prepare_threshold=None)
    # Look up the Blossom Dreams organization ID once per connection.
    # This ID is then passed to each Cursor to emit SET LOCAL at transaction start.
    organization_id = None
    with raw.cursor() as setup_cursor:
        try:
            setup_cursor.execute("SELECT id FROM organizations WHERE slug = %s", ("blossom-dreams",))
            org = setup_cursor.fetchone()
            if org:
                organization_id = str(org["id"])
        except psycopg.errors.UndefinedTable:
            raw.rollback()  # First schema initialization: organizations does not exist yet.
    conn = Connection(raw, organization_id)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS organizations (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS profiles (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, email TEXT NOT NULL, full_name TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (organization_id, email));
CREATE TABLE IF NOT EXISTS admin_users (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, profile_id UUID REFERENCES profiles(id) ON DELETE SET NULL, username TEXT NOT NULL, email TEXT NOT NULL, hashed_password TEXT NOT NULL, full_name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'admin', created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (organization_id, username), UNIQUE (organization_id, email));
CREATE TABLE IF NOT EXISTS categories (id BIGSERIAL PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, name TEXT NOT NULL, slug TEXT NOT NULL, description TEXT, display_order INTEGER NOT NULL DEFAULT 0, icon TEXT NOT NULL DEFAULT 'sparkles', is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (organization_id, slug));
CREATE TABLE IF NOT EXISTS services (id BIGSERIAL PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, category_id BIGINT NOT NULL REFERENCES categories(id) ON DELETE RESTRICT, name TEXT NOT NULL, slug TEXT NOT NULL, description TEXT, duration_minutes INTEGER NOT NULL DEFAULT 60 CHECK (duration_minutes > 0), price NUMERIC(10,2) NOT NULL CHECK (price >= 0), discount_price NUMERIC(10,2) CHECK (discount_price IS NULL OR discount_price >= 0), image_url TEXT, is_active BOOLEAN NOT NULL DEFAULT TRUE, is_featured BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (organization_id, slug));
CREATE TABLE IF NOT EXISTS locations (id BIGSERIAL PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, slug TEXT NOT NULL, name TEXT NOT NULL, address TEXT, google_maps_url TEXT, latitude DOUBLE PRECISION, longitude DOUBLE PRECISION, display_order INTEGER NOT NULL DEFAULT 0, is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (organization_id, slug));
CREATE TABLE IF NOT EXISTS offers (id BIGSERIAL PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, service_id BIGINT REFERENCES services(id) ON DELETE SET NULL, title TEXT NOT NULL, description TEXT, original_price NUMERIC(10,2) NOT NULL CHECK (original_price >= 0), discounted_price NUMERIC(10,2) NOT NULL CHECK (discounted_price >= 0), discount_percent INTEGER, start_date DATE NOT NULL, end_date DATE NOT NULL CHECK (end_date >= start_date), image_url TEXT, is_active BOOLEAN NOT NULL DEFAULT TRUE, is_featured BOOLEAN NOT NULL DEFAULT FALSE, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS bookings (id BIGSERIAL PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, booking_code TEXT NOT NULL, service_id BIGINT NOT NULL REFERENCES services(id) ON DELETE RESTRICT, location_id BIGINT REFERENCES locations(id) ON DELETE SET NULL, customer_name TEXT NOT NULL, customer_phone TEXT NOT NULL, customer_email TEXT, notes TEXT, appointment_date DATE NOT NULL, appointment_time TIME NOT NULL, duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0), status TEXT NOT NULL DEFAULT 'pending', price NUMERIC(10,2) NOT NULL CHECK (price >= 0), created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE (organization_id, booking_code));
CREATE TABLE IF NOT EXISTS availability_settings (id BIGSERIAL PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), day_name TEXT NOT NULL, is_open BOOLEAN NOT NULL DEFAULT TRUE, open_time TIME NOT NULL DEFAULT '09:00', close_time TIME NOT NULL DEFAULT '19:00', slot_interval_minutes INTEGER NOT NULL DEFAULT 30, buffer_minutes INTEGER NOT NULL DEFAULT 0, UNIQUE (organization_id, day_of_week));
CREATE TABLE IF NOT EXISTS closed_dates (id BIGSERIAL PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, closed_date DATE NOT NULL, reason TEXT NOT NULL, UNIQUE (organization_id, closed_date));
CREATE TABLE IF NOT EXISTS gallery_images (id BIGSERIAL PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, title TEXT, caption TEXT, image_url TEXT NOT NULL, category TEXT NOT NULL DEFAULT 'All', is_featured BOOLEAN NOT NULL DEFAULT FALSE, display_order INTEGER NOT NULL DEFAULT 0, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS salon_settings (id BIGSERIAL PRIMARY KEY, organization_id UUID NOT NULL UNIQUE REFERENCES organizations(id) ON DELETE CASCADE, salon_name TEXT NOT NULL, tagline TEXT, description TEXT, phone TEXT, whatsapp_number TEXT, instagram_url TEXT, tiktok_url TEXT, address TEXT, google_maps_url TEXT, opening_hours_text TEXT, currency_symbol TEXT NOT NULL DEFAULT '$', announcement_text TEXT, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS location_availability_settings (id BIGSERIAL PRIMARY KEY, organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, location_id BIGINT NOT NULL REFERENCES locations(id) ON DELETE CASCADE, day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), day_name TEXT NOT NULL, is_open BOOLEAN NOT NULL DEFAULT TRUE, open_time TIME NOT NULL DEFAULT '09:00', close_time TIME NOT NULL DEFAULT '19:00', slot_interval_minutes INTEGER NOT NULL DEFAULT 30, buffer_minutes INTEGER NOT NULL DEFAULT 0, UNIQUE (organization_id, location_id, day_of_week));
"""

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Create/update the schema
        for statement in SCHEMA.split(";\n"):
            statement = statement.strip()
            if not statement:
                continue

            print(f"[DB INIT] Executing: {statement[:300]}", flush=True)

            try:
                cursor.execute(statement)
            except Exception as e:
                print(f"[DB INIT] FAILED: {e}", flush=True)
                print(f"[DB INIT] SQL: {statement}", flush=True)
                raise

        # 2. Make sure the default organization exists
        cursor.execute_no_org(
            """
            INSERT INTO organizations (slug, name)
            VALUES (?, ?)
            ON CONFLICT (slug) DO NOTHING
            """,
            ("blossom-dreams", "Blossom Dreams"),
        )

        cursor.execute_no_org(
            """
            SELECT id
            FROM organizations
            WHERE slug = ?
            """,
            ("blossom-dreams",),
        )

        organization = cursor.fetchone()

        if not organization:
            raise RuntimeError(
                "Could not find or create Blossom Dreams organization"
            )

        organization_id = organization["id"]
        cursor.execute_no_org(
    "SELECT set_config('app.organization_id', %s, false)",
    (str(organization_id),),
)

        # 3. Existing databases may have old tables without organization_id.
        #    Add the column only when it does not already exist.
        tenant_tables = (
            "profiles",
            "admin_users",
            "categories",
            "services",
            "offers",
            "bookings",
            "availability_settings",
            "closed_dates",
            "gallery_images",
            "salon_settings",
            "locations",
            "location_availability_settings",
        )

        for table in tenant_tables:
            cursor.execute(
                f"""
                ALTER TABLE {table}
                ADD COLUMN IF NOT EXISTS organization_id UUID
                """
            )
                    # 6.5. Create indexes only after organization_id exists.
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_categories_org ON categories(organization_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_services_org_category ON services(organization_id, category_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_offers_org_active ON offers(organization_id, is_active, end_date)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_bookings_org_slot ON bookings(organization_id, location_id, appointment_date, appointment_time, status)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_gallery_org_order ON gallery_images(organization_id, display_order)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_locations_org_active ON locations(organization_id, is_active)"
        )

        # 4. Put existing rows into the default Blossom Dreams organization.
        for table in tenant_tables:
            cursor.execute_no_org(
                f"""
                UPDATE {table}
                SET organization_id = ?
                WHERE organization_id IS NULL
                """,
                (organization_id,),
            )

        # 5. Add the foreign-key constraints only where possible.
        #    DO NOT recreate them if they already exist.
        for table in tenant_tables:
            constraint_name = f"{table}_organization_id_fkey"

            cursor.execute(
                f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_constraint
                        WHERE conname = '{constraint_name}'
                    ) THEN
                        ALTER TABLE {table}
                        ADD CONSTRAINT {constraint_name}
                        FOREIGN KEY (organization_id)
                        REFERENCES organizations(id)
                        ON DELETE CASCADE;
                    END IF;
                END
                $$;
                """
            )

        # 6. organization_id must be present for all tenant rows.
        for table in tenant_tables:
            cursor.execute(
                f"""
                ALTER TABLE {table}
                ALTER COLUMN organization_id SET NOT NULL
                """
            )

                    # 6.5. Ensure the composite unique constraints required by seed_data.py.
        # These are required for ON CONFLICT (...) to work on existing databases.

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            ux_locations_org_slug
            ON locations (organization_id, slug)
            """
        )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            ux_availability_settings_org_day
            ON availability_settings (organization_id, day_of_week)
            """
        )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            ux_location_availability_settings_org_location_day
            ON location_availability_settings (
                organization_id,
                location_id,
                day_of_week
            )
            """
        )

        # 7. Enable RLS and isolate every tenant table.

        # 7. Enable RLS and isolate every tenant table.
        for table in tenant_tables:
            cursor.execute(
                f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"
            )

            cursor.execute(
                f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"
            )

            cursor.execute(
                f"DROP POLICY IF EXISTS organization_isolation ON {table}"
            )

            cursor.execute(
                f"""
                CREATE POLICY organization_isolation
                ON {table}
                USING (
                    organization_id::text =
                    current_setting('app.organization_id', true)
                )
                WITH CHECK (
                    organization_id::text =
                    current_setting('app.organization_id', true)
                )
                """
            )

        print("[DB INIT] Database initialization completed successfully.", flush=True)