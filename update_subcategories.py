"""Update existing nail services with subcategories based on their names."""
from app.database import get_db

# Mapping of service slugs to subcategories
SUBCATEGORY_MAP = {
    # Nail services
    "signature-manicure": "manicure",
    "russian-manicure": "manicure",
    "gel-polish": "gel",
    "biab-builder-gel": "gel",
    "full-set-gel-sculpted-extensions": "extensions",
    "gel-sculpted-extensions": "extensions",
    "deluxe-spa-pedicure": "pedicure",
    "deluxe-spa-pedicure-foot-bath": "pedicure",
    "haute-nail-art": "nail-art",
    "haute-couture-nail-art-add-on": "nail-art",
    # Lash services
    "classic-silk-lashes": "classic",
    "russian-mega-volume-lashes": "volume",
    "russian-volume-lashes": "volume",
    "keratin-lash-lift-tint": "lift-tint",
    "keratin-lash-lift": "lift-tint",
    # Brow services
    "brow-lamination-tint": "lamination",
    "hd-brow-sculpt": "sculpting",
    "hd-precision-brow-sculpt-mapping": "sculpting",
    # Skin services
    "hydrafacial-glow": "hydrafacial",
    "hydrafacial-radiance": "hydrafacial",
    "dermaplaning-glass-skin": "dermaplaning",
    "24k-gold-luxury-facial": "luxury-facial",
    # Laser services
    "laser-full-body": "full-body",
    "laser-underarms-bikini": "targeted",
    # Makeup services
    "evening-glam-makeup": "glam",
    "bridal-trial-makeup": "bridal",
    # Piercing/Tattoo services
    "curated-ear-piercing": "piercing",
    "fine-line-tattoo": "tattoo",
}

def update_subcategories():
    with get_db() as conn:
        cur = conn.cursor()
        # Get all services
        cur.execute("SELECT id, slug, name, category_id FROM services")
        services = cur.fetchall()
        
        updated = 0
        for svc in services:
            slug = svc["slug"]
            if slug in SUBCATEGORY_MAP:
                subcategory = SUBCATEGORY_MAP[slug]
                cur.execute("UPDATE services SET subcategory = ? WHERE id = ?", (subcategory, svc["id"]))
                updated += 1
                print(f"Updated {svc['name']} ({slug}) -> {subcategory}")
        
        print(f"\nTotal updated: {updated}")

if __name__ == "__main__":
    from app.database import init_db
    init_db()
    update_subcategories()