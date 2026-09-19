#!/usr/bin/env python3
"""
Migration script to create generic subcategories table,
migrate existing nail_subcategories, add subcategory_id to services,
and backfill relationships.
Run this once after deploying new code (before removing old columns).
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import get_db

def run_migration():
    with get_db() as conn:
        cursor = conn.cursor()
        print("[MIGRATION] Starting subcategories migration...")

        # 1. Create subcategories table (generic)
        cursor.execute("""
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
        print("[MIGRATION] subcategories table ensured.")

        # 2. Enable RLS and policy for subcategories (mirroring other tables)
        cursor.execute("ALTER TABLE subcategories ENABLE ROW LEVEL SECURITY")
        cursor.execute("ALTER TABLE subcategories FORCE ROW LEVEL SECURITY")
        cursor.execute("DROP POLICY IF EXISTS organization_isolation ON subcategories")
        cursor.execute("""
            CREATE POLICY organization_isolation
            ON subcategories
            USING (organization_id::text = current_setting('app.organization_id', true))
            WITH CHECK (organization_id::text = current_setting('app.organization_id', true))
        """)
        print("[MIGRATION] RLS policies applied to subcategories.")

        # 3. Migrate existing nail_subcategories into subcategories linked to Nails category
        cursor.execute("""
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
        print("[MIGRATION] Existing nail subcategories copied to generic table.")

        # 4. Add subcategory_id column to services if not exists
        cursor.execute("""
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
        print("[MIGRATION] subcategory_id column ensured on services.")

        # 5. Add foreign key constraint for subcategory_id (if not exists)
        cursor.execute("""
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
        print("[MIGRATION] FK constraint added for subcategory_id.")

        # 6. Backfill services.subcategory_id from nail_subcategory_id via name+slug match
        cursor.execute("""
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
        print("[MIGRATION] Services backfilled with generic subcategory_id.")

        # 7. Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_subcategories_category_id
            ON subcategories (category_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_services_subcategory_id
            ON services (subcategory_id);
        """)
        print("[MIGRATION] Indexes created.")

        conn.commit()
        print("[MIGRATION] Migration completed successfully.")

if __name__ == "__main__":
    run_migration()