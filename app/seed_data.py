"""Intentional fresh data for a new Blossom Dreams PostgreSQL installation.

This file never reads, imports, or transforms SQLite data.
"""
from app.auth import get_password_hash
from app.config import settings
from app.database import get_db

ORG_SLUG = "blossom-dreams"

def seed_database():
    with get_db() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO organizations (slug, name) VALUES (?, ?) ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id", (ORG_SLUG, "Blossom Dreams"))
        org_id = c.fetchone()["id"]
        # The first seed run creates the tenant before get_db() can discover
        # it, so establish the RLS context explicitly for this transaction.
        c.execute("SELECT set_config('app.organization_id', ?, false)", (str(org_id),))

        c.execute("SELECT id FROM profiles WHERE organization_id = ? AND email = ?", (org_id, settings.ADMIN_EMAIL))
        profile = c.fetchone()
        if not profile:
            c.execute("INSERT INTO profiles (organization_id, email, full_name) VALUES (?, ?, ?)", (org_id, settings.ADMIN_EMAIL, settings.ADMIN_FULL_NAME))
            profile_id = c.lastrowid
        else:
            profile_id = profile["id"]
        # Upsert admin user so password/hash stays in sync with settings.ADMIN_PASSWORD
        c.execute(
            "SELECT id FROM admin_users WHERE organization_id = ? AND username = ?",
            (org_id, settings.ADMIN_USERNAME)
        )
        admin_row = c.fetchone()
        hashed_pw = get_password_hash(settings.ADMIN_PASSWORD)
        import logging
        logger = logging.getLogger(__name__)
        # Diagnostics: confirm password env var present and hash verifies in-memory
        logger.info("ADMIN_PASSWORD configured: length=%d", len(settings.ADMIN_PASSWORD))
        from app.auth import verify_password
        in_mem_ok = verify_password(settings.ADMIN_PASSWORD, hashed_pw)
        logger.info("In-memory verify_password(ADMIN_PASSWORD, new_hash) = %s", in_mem_ok)
        logger.info("Seeding admin user: org_id=%s username=%s email=%s hash_len=%d", org_id, settings.ADMIN_USERNAME, settings.ADMIN_EMAIL, len(hashed_pw))
        if admin_row:
            c.execute(
                """
                UPDATE admin_users
                SET hashed_password = ?, profile_id = ?, email = ?, full_name = ?, role = ?
                WHERE id = ?
                """,
                (hashed_pw, profile_id, settings.ADMIN_EMAIL, settings.ADMIN_FULL_NAME, 'admin', admin_row["id"])
            )
            logger.info("Updated existing admin user id=%s", admin_row["id"])
        else:
            c.execute(
                """
                INSERT INTO admin_users (organization_id, profile_id, username, email, hashed_password, full_name, role)
                VALUES (?, ?, ?, ?, ?, ?, 'admin')
                """,
                (org_id, profile_id, settings.ADMIN_USERNAME, settings.ADMIN_EMAIL, hashed_pw, settings.ADMIN_FULL_NAME)
            )
            logger.info("Inserted new admin user")

        c.execute("SELECT id FROM salon_settings WHERE organization_id = ?", (org_id,))
        if not c.fetchone():
            c.execute("""INSERT INTO salon_settings (organization_id, salon_name, tagline, description, phone, whatsapp_number, instagram_url, tiktok_url, address, google_maps_url, opening_hours_text, currency_symbol, announcement_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (org_id, "BLOSSOM DREAMS", "Your sanctuary of elegance, radiance, and luxury beauty.", "Luxury beauty treatments tailored to you.", "+961 70 882 194", "+96170882194", "https://www.instagram.com/blossomdreams.lb/", "https://www.tiktok.com/@blossomdreams.lb", "Amwaj Center, Jounieh, Lebanon", "https://maps.google.com/?q=Amwaj+Center+Jounieh+Lebanon", "Monday - Saturday: 9:00 AM - 7:00 PM | Sunday: Closed", "$", "Welcome to Blossom Dreams. Book your appointment online today!"))

        for day, name, is_open in ((0,"Monday",True),(1,"Tuesday",True),(2,"Wednesday",True),(3,"Thursday",True),(4,"Friday",True),(5,"Saturday",True),(6,"Sunday",False)):
            c.execute("""INSERT INTO availability_settings (organization_id, day_of_week, day_name, is_open, open_time, close_time, slot_interval_minutes, buffer_minutes)
                VALUES (?, ?, ?, ?, '09:00', '19:00', 30, 0) ON CONFLICT (organization_id, day_of_week) DO NOTHING""", (org_id, day, name, is_open))

        c.execute("""INSERT INTO locations (organization_id, slug, name, address, google_maps_url, display_order, is_active)
            VALUES (?, 'amwaj', 'Amwaj Center', 'Amwaj Center, Jounieh, Lebanon', 'https://maps.google.com/?q=Amwaj+Center+Jounieh+Lebanon', 1, TRUE)
            ON CONFLICT (organization_id, slug) DO NOTHING""", (org_id,))

        categories = [("Nails", "nails", "Luxury manicure and nail care.", 1, "hand"), ("Lashes & Brows", "lashes-brows", "Custom lash and brow treatments.", 2, "eye"), ("Skin & Facial", "skin-facial", "Radiance and skin treatments.", 3, "sparkles")]
        category_ids = {}
        for name, slug, description, order, icon in categories:
            c.execute("""INSERT INTO categories (organization_id, name, slug, description, display_order, icon) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (organization_id, slug) DO UPDATE SET name = EXCLUDED.name RETURNING id""", (org_id, name, slug, description, order, icon))
            category_ids[slug] = c.fetchone()["id"]
        # Seed services only if none exist for this organization
        # DEBUG: this guard prevents re-seeding on every deploy
        c.execute("SELECT COUNT(*) as cnt FROM services WHERE organization_id = ?", (org_id,))
        if c.fetchone()["cnt"] == 0:
            services = [("nails", "Signature Manicure", "signature-manicure", "Detailed manicure with a polished finish.", 60, 35, True), ("lashes-brows", "Keratin Lash Lift", "keratin-lash-lift", "Lift and tint for naturally defined lashes.", 60, 40, True), ("skin-facial", "Hydrafacial Radiance", "hydrafacial-radiance", "A deeply cleansing hydration facial.", 60, 85, True)]
            service_ids = {}
            for cat, name, slug, description, duration, price, featured in services:
                c.execute("""INSERT INTO services (organization_id, category_id, name, slug, description, duration_minutes, price, is_featured)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT (organization_id, slug) DO UPDATE SET name = EXCLUDED.name RETURNING id""", (org_id, category_ids[cat], name, slug, description, duration, price, featured))
                service_ids[slug] = c.fetchone()["id"]
            c.execute("SELECT id FROM offers WHERE organization_id = ? AND title = ?", (org_id, "Radiance Duo"))
            if not c.fetchone():
                c.execute("""INSERT INTO offers (organization_id, service_id, title, description, original_price, discounted_price, discount_percent, start_date, end_date, is_active, is_featured)
                    VALUES (?, ?, 'Radiance Duo', 'Hydrafacial and lash lift seasonal package.', 125, 89, 29, CURRENT_DATE, CURRENT_DATE + 365, TRUE, TRUE)""", (org_id, service_ids["hydrafacial-radiance"]))
        for title, caption, category, order in (("Signature Manicure", "A polished manicure finish.", "Nails", 1), ("Radiant Skin", "Fresh facial results.", "Skin & Facial", 2)):
            c.execute("SELECT id FROM gallery_images WHERE organization_id = ? AND title = ?", (org_id, title))
            if not c.fetchone(): c.execute("INSERT INTO gallery_images (organization_id, title, caption, image_url, category, is_featured, display_order) VALUES (?, ?, ?, '/static/images/hero_bg.jpg', ?, TRUE, ?)", (org_id, title, caption, category, order))
