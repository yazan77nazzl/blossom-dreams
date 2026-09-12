import os
from app.database import get_db
from app.auth import get_password_hash
from app.config import settings

def seed_database():
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Admin User
        admin_user = settings.ADMIN_USERNAME
        cursor.execute("SELECT id FROM admin_users WHERE username = ?", (admin_user,))
        if not cursor.fetchone():
            hashed_pwd = get_password_hash(settings.ADMIN_PASSWORD)
            cursor.execute("""
            INSERT INTO admin_users (username, email, hashed_password, full_name, role)
            VALUES (?, ?, ?, ?, ?)
            """, (admin_user, settings.ADMIN_EMAIL, hashed_pwd, settings.ADMIN_FULL_NAME, "admin"))
            print(f"[Seed] Created default admin user: {admin_user}")

        # 2. Salon Settings
        cursor.execute("SELECT id FROM salon_settings WHERE id = 1")
        if not cursor.fetchone():
            cursor.execute("""
            INSERT INTO salon_settings (
                id, salon_name, tagline, description, phone, whatsapp_number,
                instagram_url, tiktok_url, address, google_maps_url,
                opening_hours_text, currency_symbol, announcement_text
            ) VALUES (
                1,
                'BLOSSOM DREAMS',
                'Your sanctuary of elegance, radiance, and luxury beauty.',
                'Blossom Dreams is Lebanon''s premier destination for high-end aesthetic nail artistry, bespoke lash & brow styling, rejuvenating clinical facials, and luxury beauty pampering.',
                '+961 70 882 194',
                '+96170882194',
                'https://www.instagram.com/blossomdreams.lb/',
                'https://www.tiktok.com/@blossomdreams.lb',
                'Verdun, Luxury Fashion District, Beirut, Lebanon',
                'https://maps.google.com/?q=Verdun+Beirut',
                'Monday - Saturday: 9:30 AM - 7:00 PM | Sunday: Closed',
                '$',
                '🌸 Spring Glamour at Blossom Dreams: Enjoy exclusive pampering packages. Book your appointment online today!'
            )
            """)
            print("[Seed] Created default salon settings.")

        # Upgrade any legacy "Blossom Dreams LB" branding on existing installations
        cursor.execute("UPDATE salon_settings SET salon_name = 'BLOSSOM DREAMS' WHERE salon_name = 'BLOSSOM DREAMS LB'")
        cursor.execute("UPDATE salon_settings SET description = REPLACE(description, 'Blossom Dreams LB', 'Blossom Dreams') WHERE description LIKE '%Blossom Dreams LB%'")
        cursor.execute("UPDATE salon_settings SET tagline = REPLACE(tagline, 'Blossom Dreams LB', 'Blossom Dreams') WHERE tagline LIKE '%Blossom Dreams LB%'")
        cursor.execute("UPDATE salon_settings SET announcement_text = REPLACE(announcement_text, 'Blossom Dreams LB', 'Blossom Dreams') WHERE announcement_text LIKE '%Blossom Dreams LB%'")

        # 3. Weekly Availability Settings (0 = Monday, 6 = Sunday)
        days = [
            (0, "Monday", 1, "09:30", "19:00", 30),
            (1, "Tuesday", 1, "09:30", "19:00", 30),
            (2, "Wednesday", 1, "09:30", "19:00", 30),
            (3, "Thursday", 1, "09:30", "19:00", 30),
            (4, "Friday", 1, "09:30", "19:00", 30),
            (5, "Saturday", 1, "09:30", "19:00", 30),
            (6, "Sunday", 0, "09:30", "19:00", 30),
        ]
        for day in days:
            cursor.execute("SELECT id FROM availability_settings WHERE day_of_week = ?", (day[0],))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO availability_settings (day_of_week, day_name, is_open, open_time, close_time, slot_interval_minutes)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (day[0], day[1], bool(day[2]), day[3], day[4], day[5]))

        # 4. Break times (Monday - Saturday 13:30 to 14:30)
        cursor.execute("SELECT COUNT(*) as count FROM break_times")
        if cursor.fetchone()["count"] == 0:
            for day_idx in range(6): # Mon to Sat
                cursor.execute("""
                INSERT INTO break_times (day_of_week, label, start_time, end_time)
                VALUES (?, 'Salon Midday Break', '13:30', '14:30')
                """, (day_idx,))

        # 5. Categories
        categories_data = [
            ("Nails", "nails", "Luxury Russian manicures, BIAB overlays, gel enhancements, and bespoke nail couture.", 1, "hand"),
            ("Lashes", "lashes", "Custom lash extensions, mega volume, classic sets, and lifting infusions.", 2, "eye"),
            ("Brows", "brows", "Micro-sculpting, lamination, tinting, and high-definition shaping.", 3, "sparkles"),
            ("Skin & Facial", "skin-facial", "Advanced clinical glow facials, dermaplaning, and hydration therapies.", 4, "flower"),
            ("Laser Hair Removal", "laser", "Painless medical-grade diode laser hair removal for silky smooth skin.", 5, "zap"),
            ("Glam & Makeup", "makeup", "Red carpet glam, evening elegance, and bridal bespoke makeup.", 6, "heart"),
            ("Piercing & Tattoo", "piercing-tattoo", "Hygienic curated ear styling and delicate fine-line aesthetic tattoos.", 7, "star"),
        ]
        
        category_id_map = {}
        for cat in categories_data:
            cursor.execute("SELECT id FROM categories WHERE slug = ?", (cat[1],))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                INSERT INTO categories (name, slug, description, display_order, icon, is_active)
                VALUES (?, ?, ?, ?, ?, TRUE)
                """, cat)
                category_id_map[cat[1]] = cursor.lastrowid
            else:
                category_id_map[cat[1]] = row["id"]

        # 6. Services
        services_data = [
            # Nails
            (
                "nails", "Signature Russian Manicure", "russian-manicure",
                "Meticulous dry cuticle diamond e-file care, precise nail shaping, and flawless single-tone gel polish finish.",
                60, 35.0, 30.0, "/static/images/nails_manicure.jpg", 1, 1
            ),
            (
                "nails", "BIAB Builder Gel Overlay", "biab-builder-gel",
                "Nourishing Builder in a Bottle gel overlay that fortifies weak natural nails while promoting long-term growth and high-gloss beauty.",
                75, 45.0, None, "/static/images/nails_biab.jpg", 1, 1
            ),
            (
                "nails", "Full Set Gel Sculpted Extensions", "gel-sculpted-extensions",
                "Handcrafted custom extensions with luxury French tips or custom Ombré styling, lightweight and durable.",
                90, 65.0, 55.0, "/static/images/nails_extensions.jpg", 1, 0
            ),
            (
                "nails", "Deluxe Spa Pedicure & Foot Bath", "deluxe-spa-pedicure",
                "Rose water soaking bath, organic sugar scrub exfoliation, hot towel wrap, callous removal, and lasting gel polish.",
                60, 40.0, None, "/static/images/nails_pedicure.jpg", 1, 0
            ),
            (
                "nails", "Haute Couture Nail Art (Add-on)", "haute-nail-art",
                "Intricate hand-painted flowers, 3D chrome swirls, pearl embellishments, and custom luxury designs.",
                30, 20.0, None, "/static/images/nails_art.jpg", 1, 0
            ),

            # Lashes
            (
                "lashes", "Classic Silk Individual Lashes", "classic-silk-lashes",
                "Natural 1:1 application of premium lightweight silk lashes that enhance your natural eye shape.",
                90, 50.0, None, "/static/images/lashes_classic.jpg", 1, 0
            ),
            (
                "lashes", "Russian Mega Volume Lashes", "russian-volume-lashes",
                "Ultra-dense, fluffy 4D-6D handmade fans creating a dramatic, sultry gaze with featherweight softness.",
                120, 75.0, 65.0, "/static/images/lashes_volume.jpg", 1, 1
            ),
            (
                "lashes", "Keratin Lash Lift & Deep Tint", "keratin-lash-lift-tint",
                "Lifts and curls your natural lashes from root to tip infused with nourishing keratin and jet-black tint.",
                60, 40.0, 35.0, "/static/images/lashes_lift.jpg", 1, 1
            ),

            # Brows
            (
                "brows", "Signature Brow Lamination & Tint", "brow-lamination-tint",
                "Restructures brow hairs into full, feathered perfection; includes organic castor oil treatment and custom tint.",
                45, 45.0, 38.0, "/static/images/brows_lamination.jpg", 1, 1
            ),
            (
                "brows", "HD Precision Brow Sculpt & Mapping", "hd-brow-sculpt",
                "Golden-ratio brow mapping, waxing, micro-tweezing, and long-lasting henna/hybrid tinting.",
                30, 25.0, None, "/static/images/brows_sculpt.jpg", 1, 0
            ),

            # Skin & Facial
            (
                "skin-facial", "Hydrafacial Radiance Glow", "hydrafacial-glow",
                "Non-invasive multi-step treatment combining vortex extraction, chemical peeling, and hyaluronic acid hydration infusion.",
                60, 85.0, 70.0, "/static/images/facial_hydra.jpg", 1, 1
            ),
            (
                "skin-facial", "Dermaplaning & Glass Skin Treatment", "dermaplaning-glass-skin",
                "Gentle surgical blade exfoliation removing dead skin cells and peach fuzz, followed by collagen-infusion sheet mask.",
                45, 55.0, None, "/static/images/facial_dermaplane.jpg", 1, 0
            ),
            (
                "skin-facial", "24K Gold Luxury Anti-Aging Facial", "24k-gold-luxury-facial",
                "Pure 24K gold foil sheets, lymphatic face massage, peptide serums, and LED light therapy to boost firmness and elasticity.",
                75, 110.0, 95.0, "/static/images/facial_gold.jpg", 1, 1
            ),

            # Laser
            (
                "laser", "Full Body Laser Hair Removal", "laser-full-body",
                "Full body medical triple-wavelength diode laser with ice-cooling technology for virtually painless, permanent hair reduction.",
                90, 150.0, 125.0, "/static/images/laser_full_body.jpg", 1, 1
            ),
            (
                "laser", "Underarms & Bikini Line Laser", "laser-underarms-bikini",
                "Fast, targeted, cooling-assisted laser session for silky underarms and clean bikini contours.",
                30, 45.0, None, "/static/images/laser_bikini.jpg", 1, 0
            ),

            # Glam & Makeup
            (
                "makeup", "Evening Red Carpet Glam", "evening-glam-makeup",
                "Full professional makeup application including skin prep, contouring, dramatic or soft smokey eyes, and luxury mink lashes.",
                75, 70.0, 60.0, "/static/images/makeup_glam.jpg", 1, 1
            ),
            (
                "makeup", "Bridal Consultation & Trial Makeup", "bridal-trial-makeup",
                "Dedicated bridal session to design and customize your dream wedding look, skin tone matching, and veil placement preview.",
                90, 90.0, None, "/static/images/makeup_bridal.jpg", 1, 0
            ),

            # Piercing & Tattoo
            (
                "piercing-tattoo", "Curated Ear Piercing (Single/Pair)", "curated-ear-piercing",
                "Sterile needle piercing with titanium/14k gold jewelry selection, anatomic placement consultation, and aftercare kit.",
                30, 30.0, None, "/static/images/piercing.jpg", 1, 0
            ),
            (
                "piercing-tattoo", "Fine Line Delicate Tattoo (Micro)", "fine-line-tattoo",
                "Single-needle minimalist floral, script, or geometric tattoo design by our certified tattoo artist.",
                60, 60.0, None, "/static/images/tattoo.jpg", 1, 0
            ),
        ]

        service_id_map = {}
        for item in services_data:
            cat_slug, name, slug, desc, duration, price, disc_price, img, active, feat = item
            cat_id = category_id_map.get(cat_slug)
            if not cat_id:
                continue

            cursor.execute("SELECT id FROM services WHERE slug = ?", (slug,))
            row = cursor.fetchone()
            if not row:
                cursor.execute("""
                INSERT INTO services (category_id, name, slug, description, duration_minutes, price, discount_price, image_url, is_active, is_featured)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (cat_id, name, slug, desc, duration, price, disc_price, img, bool(active), bool(feat)))
                service_id_map[slug] = cursor.lastrowid
            else:
                service_id_map[slug] = row["id"]

        # 7. Special Offers
        offers_data = [
            (
                "Blossom Bridal Glow Duo",
                "Indulge in our signature Hydrafacial Radiance treatment paired with Keratin Lash Lift & Tint for the ultimate luminous glow.",
                125.0, 89.0, 29, "2025-01-01", "2027-12-31",
                "/static/images/offer_glow_duo.jpg", 1, 1,
                service_id_map.get("hydrafacial-glow")
            ),
            (
                "Russian Mega Volume + Brow Lamination Glam",
                "Get runway-ready with dramatic fluffy Russian volume lashes combined with full featherweight brow lamination and custom tint.",
                120.0, 85.0, 29, "2025-01-01", "2027-12-31",
                "/static/images/offer_lash_brow.jpg", 1, 1,
                service_id_map.get("russian-volume-lashes")
            ),
            (
                "BIAB Manicure & Deluxe Pedicure Pamper",
                "Treat yourself to flawless BIAB gel strength overlay and a soothing rose petal spa pedicure.",
                85.0, 59.0, 31, "2025-01-01", "2027-12-31",
                "/static/images/offer_mani_pedi.jpg", 1, 1,
                service_id_map.get("biab-builder-gel")
            ),
            (
                "Summer Full Body Laser Transformation",
                "Medical-grade ice diode laser session for complete silky-smooth confidence with zero downtime.",
                150.0, 115.0, 23, "2025-01-01", "2027-12-31",
                "/static/images/offer_laser.jpg", 1, 0,
                service_id_map.get("laser-full-body")
            )
        ]

        for offer in offers_data:
            cursor.execute("SELECT id FROM offers WHERE title = ?", (offer[0],))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO offers (
                    title, description, original_price, discounted_price, discount_percent,
                    start_date, end_date, image_url, is_active, is_featured, service_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, offer[:8] + (bool(offer[8]), bool(offer[9])) + offer[10:])

        # 8. Gallery Images
        gallery_data = [
            ("French Ombre Almond Nails", "Hand-sculpted Russian manicure with delicate chrome pearl powder", "/static/images/gallery_1.jpg", "Nails", 1, 1),
            ("Fluffy Russian Volume Fans", "Bespoke eye styling with silk volume lashes", "/static/images/gallery_2.jpg", "Lashes", 1, 2),
            ("Feathered Brow Lamination", "Naturally lifted brows with custom organic tint", "/static/images/gallery_3.jpg", "Brows", 1, 3),
            ("Hydrafacial Glass Skin Glow", "Deep pore vortex extraction and peptide hydration", "/static/images/gallery_4.jpg", "Skin & Facial", 1, 4),
            ("Bridal Makeup & Veil Artistry", "Timeless romantic bridal glam with luminous base", "/static/images/gallery_5.jpg", "Glam & Makeup", 1, 5),
            ("Curated Gold Ear Piercings", "14K solid gold huggies and diamond studs styling", "/static/images/gallery_6.jpg", "Piercing & Tattoo", 1, 6),
        ]

        cursor.execute("SELECT COUNT(*) as count FROM gallery_images")
        if cursor.fetchone()["count"] == 0:
            for item in gallery_data:
                cursor.execute("""
                INSERT INTO gallery_images (title, caption, image_url, category, is_featured, display_order)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (item[0], item[1], item[2], item[3], bool(item[4]), item[5]))

        print("[Seed] Seed data successfully applied!")
