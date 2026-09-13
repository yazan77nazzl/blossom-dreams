import os
import re
import sqlite3
from datetime import date as _date, datetime as _datetime, time as _time
from pathlib import Path
from contextlib import contextmanager
from app.config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "blossom_dreams.db"

IS_POSTGRES = settings.DATABASE_URL.startswith("postgresql://") or settings.DATABASE_URL.startswith("postgres://")


def normalize_db_value(value):
    """PostgreSQL returns TIMESTAMP/DATE/TIME columns as datetime/date/time
    objects, but the API layer (pydantic models like BookingResponse) and the
    SQLite path both expect plain strings. Normalize at the cursor boundary so
    every response works identically on SQLite and Postgres."""
    if isinstance(value, (_datetime, _date, _time)):
        return value.isoformat()
    return value


def normalize_db_row(row):
    if row is None:
        return row
    if isinstance(row, dict):
        return {key: normalize_db_value(value) for key, value in row.items()}
    return tuple(normalize_db_value(value) for value in row)

if IS_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row

    class PgCursorWrapper:
        def __init__(self, raw_cursor):
            self._cursor = raw_cursor
            self.lastrowid = None

        def execute(self, query, params=None):
            sql = query
            is_insert = bool(re.match(r'^\s*INSERT\s+INTO', sql, re.IGNORECASE))
            has_returning = bool(re.search(r'\bRETURNING\b', sql, re.IGNORECASE))
            
            if is_insert and not has_returning:
                sql = sql.rstrip().rstrip(';') + " RETURNING id;"
            
            # Convert ? placeholders to %s
            sql = re.sub(r'\?', '%s', sql)
            
            if params is not None:
                self._cursor.execute(sql, tuple(params))
            else:
                self._cursor.execute(sql)
                
            if is_insert and not has_returning:
                res = self._cursor.fetchone()
                if res:
                    self.lastrowid = res["id"] if isinstance(res, dict) else res[0]
            return self

        def fetchone(self):
            return normalize_db_row(self._cursor.fetchone())

        def fetchall(self):
            rows = self._cursor.fetchall()
            return [normalize_db_row(row) for row in rows]

        def fetchmany(self, size=None):
            rows = self._cursor.fetchmany(size) if size else self._cursor.fetchmany()
            return [normalize_db_row(row) for row in rows]

        def __iter__(self):
            return iter(self._cursor)

    class PgConnectionWrapper:
        def __init__(self, raw_conn):
            self._conn = raw_conn

        def cursor(self):
            return PgCursorWrapper(self._conn.cursor())

        def commit(self):
            self._conn.commit()

        def rollback(self):
            self._conn.rollback()

        def close(self):
            self._conn.close()

def get_sqlite_connection():
    db_file = str(DB_PATH)
    if settings.DATABASE_URL.startswith("sqlite:///"):
        parsed = settings.DATABASE_URL.replace("sqlite:///", "")
        if parsed:
            db_file = parsed
    conn = sqlite3.connect(db_file, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

@contextmanager
def get_db():
    if IS_POSTGRES:
        raw_conn = psycopg.connect(settings.DATABASE_URL, row_factory=dict_row)
        conn = PgConnectionWrapper(raw_conn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    else:
        conn = get_sqlite_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

def init_db():
    TABLES_DDL = [
        # 1. Admin Users
        """
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # 2. Categories
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            description TEXT,
            display_order INTEGER DEFAULT 0,
            icon TEXT DEFAULT 'sparkles',
            is_active BOOLEAN DEFAULT 1
        );
        """,
        # 3. Services
        """
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL,
            description TEXT,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            price REAL NOT NULL,
            discount_price REAL,
            image_url TEXT,
            is_active BOOLEAN DEFAULT 1,
            is_featured BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
        );
        """,
        # 4. Offers
        """
        CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            original_price REAL NOT NULL,
            discounted_price REAL NOT NULL,
            discount_percent INTEGER,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            image_url TEXT,
            is_active BOOLEAN DEFAULT 1,
            is_featured BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (service_id) REFERENCES services (id) ON DELETE SET NULL
        );
        """,
        # 5. Bookings
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_code TEXT UNIQUE NOT NULL,
            service_id INTEGER NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_email TEXT,
            notes TEXT,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (service_id) REFERENCES services (id) ON DELETE RESTRICT
        );
        """,
        # 6. Availability Settings
        """
        CREATE TABLE IF NOT EXISTS availability_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day_of_week INTEGER NOT NULL UNIQUE,
            day_name TEXT NOT NULL,
            is_open BOOLEAN DEFAULT 1,
            open_time TEXT NOT NULL DEFAULT '09:30',
            close_time TEXT NOT NULL DEFAULT '19:00',
            slot_interval_minutes INTEGER DEFAULT 30
        );
        """,
        # 7. Closed Dates
        """
        CREATE TABLE IF NOT EXISTS closed_dates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            closed_date TEXT UNIQUE NOT NULL,
            reason TEXT NOT NULL
        );
        """,
        # 8. Gallery Images
        """
        CREATE TABLE IF NOT EXISTS gallery_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            caption TEXT,
            image_url TEXT NOT NULL,
            category TEXT DEFAULT 'All',
            is_featured BOOLEAN DEFAULT 0,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # 9. Salon Settings
        """
        CREATE TABLE IF NOT EXISTS salon_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            salon_name TEXT NOT NULL DEFAULT 'BLOSSOM DREAMS',
            tagline TEXT DEFAULT 'Your sanctuary of elegance, radiance, and luxury beauty.',
            description TEXT,
            phone TEXT DEFAULT '+961 70 000 000',
            whatsapp_number TEXT DEFAULT '+96170000000',
            instagram_url TEXT DEFAULT 'https://www.instagram.com/blossomdreams.lb/',
            tiktok_url TEXT,
            address TEXT DEFAULT 'Amwaj Center, Jounieh, Lebanon',
            google_maps_url TEXT,
            opening_hours_text TEXT DEFAULT 'Monday - Saturday: 9:30 AM - 7:00 PM | Sunday: Closed',
            currency_symbol TEXT DEFAULT '$',
            announcement_text TEXT DEFAULT '✨ Welcome to Blossom Dreams. Pamper yourself with our signature treatments. Book online today!'
        );
        """,
        # 10. Business Locations
        """
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            address TEXT,
            google_maps_url TEXT,
            latitude REAL,
            longitude REAL,
            display_order INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """,
        # 11. Per-Location Availability Overrides (NULL/absent = use global
        #     availability_settings). Separate table because the global settings
        #     table carries a UNIQUE constraint on day_of_week that cannot be
        #     dropped cheaply in SQLite.
        """
        CREATE TABLE IF NOT EXISTS location_availability_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_id INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,
            day_name TEXT NOT NULL,
            is_open BOOLEAN DEFAULT 1,
            open_time TEXT NOT NULL DEFAULT '09:00',
            close_time TEXT NOT NULL DEFAULT '19:00',
            slot_interval_minutes INTEGER DEFAULT 30,
            buffer_minutes INTEGER DEFAULT 0,
            UNIQUE (location_id, day_of_week),
            FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE CASCADE
        );
        """
]

    with get_db() as conn:
        cursor = conn.cursor()
        for ddl in TABLES_DDL:
            statement = ddl
            if IS_POSTGRES:
                statement = re.sub(r'INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT', 'SERIAL PRIMARY KEY', statement, flags=re.IGNORECASE)
                # PostgreSQL requires TRUE/FALSE boolean defaults; SQLite keeps
                # its valid INTEGER (1/0) equivalents untouched.
                statement = re.sub(r'\bBOOLEAN\s+DEFAULT\s+1\b', 'BOOLEAN DEFAULT TRUE', statement, flags=re.IGNORECASE)
                statement = re.sub(r'\bBOOLEAN\s+DEFAULT\s+0\b', 'BOOLEAN DEFAULT FALSE', statement, flags=re.IGNORECASE)
            cursor.execute(statement)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_bookings_date_time 
        ON bookings (appointment_date, appointment_time, status);
        """)

        _apply_column_migrations(cursor)


def _column_exists(cursor, table: str, column: str) -> bool:
    """Guarded column-existence check that works on both SQLite and Postgres."""
    if IS_POSTGRES:
        cursor.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
            (table, column),
        )
        return cursor.fetchone() is not None
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row["name"] == column for row in cursor.fetchall())


def _apply_column_migrations(cursor) -> None:
    """Idempotent ALTER TABLE migrations for features added after the base schema."""
    migrations = [
        ("bookings", "location_id", "INTEGER"),
        ("availability_settings", "buffer_minutes", "INTEGER DEFAULT 0"),
    ]
    for table, column, column_ddl in migrations:
        if _column_exists(cursor, table, column):
            continue
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_ddl}")
