#!/usr/bin/env python3
"""
Idempotent startup migration for generic subcategories.
Runs automatically on application startup (before uvicorn serves requests).
Safe to run multiple times.
Uses the project's existing database layer (psycopg v3) via app.database.get_db().
"""

def run_startup_migration() -> None:
    """Create subcategories table, add column, migrate data, backfill services."""
    from app.database import get_db

    print("[STARTUP MIGRATION] Running migration via app database layer...")
    with get_db() as conn:
        cur = conn.cursor()

        print("[STARTUP MIGRATION] Ensuring subcategories table exists...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subcategories (
                id              SERIAL PRIMARY KEY,
                organization_id UUID NOT NULL,
                category_id     INT NOT NULL,
                name            VARCHAR(120) NOT NULL,
                slug            VARCHAR(140) NOT NULL,
                description     TEXT,
                display_order   INT NOT NULL DEFAULT 0,
                is_active       BOOLEAN NOT NULL DEFAULT TRUE,
                created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (organization_id, category_id, slug)
            );
        """)
        # Enable RLS (idempotent)
        cur.execute("ALTER TABLE subcategories ENABLE ROW LEVEL SECURITY")
        cur.execute("ALTER TABLE subcategories FORCE ROW LEVEL SECURITY")
        cur.execute("DROP POLICY IF EXISTS organization_isolation ON subcategories")
        cur.execute("""
            CREATE POLICY organization_isolation
            ON subcategories
            USING (organization_id::text = current_setting('app.organization_id', true))
            WITH CHECK (organization_id::text = current_setting('app.organization_id', true))
        """)
        print("[STARTUP MIGRATION] subcategories table and RLS ready.")

        # Migrate existing nail_subcategories into subcategories linked to Nails category
        cur.execute("""
            INSERT INTO subcategories (organization_id, category_id, name, slug, description, display_order, is_active, created_at, updated_at)
            SELECT nsc.organization_id,
                   c.id,
                   nsc.name,
                   nsc.slug,
                   NULL::text,
                   nsc.display_order,
                   nsc.is_active,
                   nsc.created_at,
                   nsc.updated_at
            FROM nail_subcategories nsc
            JOIN categories c
              ON c.organization_id = nsc.organization_id
             AND c.slug = 'nails'
            ON CONFLICT (organization_id, category_id, slug) DO NOTHING;
        """)
        print("[STARTUP MIGRATION] Existing nail subcategories copied to generic table.")

        # Add subcategory_id column to services if not exists
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='services' AND column_name='subcategory_id'
                ) THEN
                    ALTER TABLE services ADD COLUMN subcategory_id INT;
                END IF;
            END $$;
        """)
        print("[STARTUP MIGRATION] subcategory_id column ensured on services.")

        # Add foreign key constraint for subcategory_id (if not exists)
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = 'services_subcategory_id_fkey'
                ) THEN
                    ALTER TABLE services
                    ADD CONSTRAINT services_subcategory_id_fkey
                    FOREIGN KEY (subcategory_id)
                    REFERENCES subcategories(id)
                    ON DELETE SET NULL;
                END IF;
            END $$;
        """)
        print("[STARTUP MIGRATION] FK constraint added for subcategory_id.")

        # Backfill services.subcategory_id from nail_subcategory_id via name+slug match
        cur.execute("""
            UPDATE services s
            SET subcategory_id = sub.id
            FROM subcategories sub
            JOIN nail_subcategories nsc
              ON sub.organization_id = nsc.organization_id
             AND sub.name = nsc.name
             AND sub.slug = nsc.slug
            WHERE s.nail_subcategory_id = nsc.id
              AND s.subcategory_id IS NULL;
        """)
        print("[STARTUP MIGRATION] Services backfilled with generic subcategory_id.")

        # Create indexes for faster lookups
        cur.execute("CREATE INDEX IF NOT EXISTS idx_subcategories_category_id ON subcategories (category_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_services_subcategory_id ON services (subcategory_id);")
        print("[STARTUP MIGRATION] Indexes created.")

        # Ensure bookings table has is_manual column
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name='bookings' AND column_name='is_manual'
                ) THEN
                    ALTER TABLE bookings ADD COLUMN is_manual BOOLEAN NOT NULL DEFAULT FALSE;
                END IF;
            END $$;
        """)
        print("[STARTUP MIGRATION] is_manual column ensured on bookings.")
# Ensure salon_settings has welcome_text column
        cur.execute(\"\"\"\n            DO $$\n            BEGIN\n                IF NOT EXISTS (\n                    SELECT 1 FROM information_schema.columns\n                    WHERE table_name='salon_settings' AND column_name='welcome_text'\n                ) THEN\n                    ALTER TABLE salon_settings ADD COLUMN welcome_text TEXT;\n                END IF;\n            END $$;\n        \"\"\")
        print(\"[STARTUP MIGRATION] welcome_text column ensured on salon_settings.\")

        # commit handled by get_db context manager
        print("[STARTUP MIGRATION] Migration completed successfully.")


if __name__ == "__main__":
    # Allow running manually for testing
    run_startup_migration()