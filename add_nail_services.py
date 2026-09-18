"""Add more nail services with subcategories."""
from app.database import get_db

# Nail services to add (category_id = 184 for nails)
NAIL_SERVICES = [
    {
        "name": "Signature Russian Manicure",
        "slug": "signature-russian-manicure",
        "description": "Meticulous dry cuticle diamond e-file care, precise nail shaping, and flawless single-tone gel polish finish.",
        "duration_minutes": 60,
        "price": 35.00,
        "discount_price": 30.00,
        "image_url": "",
        "is_active": True,
        "is_featured": True,
        "subcategory": "manicure"
    },
    {
        "name": "Full Set Gel Sculpted Extensions",
        "slug": "full-set-gel-sculpted-extensions",
        "description": "Handcrafted custom extensions with luxury French tips or custom Ombré styling, lightweight and durable.",
        "duration_minutes": 90,
        "price": 65.00,
        "discount_price": 55.00,
        "image_url": "",
        "is_active": True,
        "is_featured": False,
        "subcategory": "extensions"
    },
    {
        "name": "Deluxe Spa Pedicure & Foot Bath",
        "slug": "deluxe-spa-pedicure-foot-bath",
        "description": "Rose water soaking bath, organic sugar scrub exfoliation, hot towel wrap, callous removal, and lasting gel polish.",
        "duration_minutes": 60,
        "price": 40.00,
        "discount_price": None,
        "image_url": "",
        "is_active": True,
        "is_featured": False,
        "subcategory": "pedicure"
    },
    {
        "name": "Haute Couture Nail Art (Add-on)",
        "slug": "haute-couture-nail-art-add-on",
        "description": "Intricate hand-painted flowers, 3D chrome swirls, pearl embellishments, and custom luxury designs.",
        "duration_minutes": 30,
        "price": 20.00,
        "discount_price": None,
        "image_url": "",
        "is_active": True,
        "is_featured": False,
        "subcategory": "nail-art"
    },
    {
        "name": "BIAB Builder Gel Overlay",
        "slug": "biab-builder-gel-overlay",
        "description": "Nourishing Builder in a Bottle gel overlay that fortifies weak natural nails while promoting long-term growth and high-gloss beauty.",
        "duration_minutes": 75,
        "price": 45.00,
        "discount_price": None,
        "image_url": "",
        "is_active": True,
        "is_featured": True,
        "subcategory": "gel"
    },
    {
        "name": "Poly Gel Nail Extensions",
        "slug": "poly-gel-nail-extensions",
        "description": "Lightweight, flexible poly gel extensions that combine the strength of acrylic with the flexibility of gel.",
        "duration_minutes": 90,
        "price": 70.00,
        "discount_price": 60.00,
        "image_url": "",
        "is_active": True,
        "is_featured": False,
        "subcategory": "extensions"
    },
    {
        "name": "Acrylic Nail Extensions",
        "slug": "acrylic-nail-extensions",
        "description": "Classic acrylic extensions with custom shaping and length, durable and long-lasting.",
        "duration_minutes": 90,
        "price": 55.00,
        "discount_price": None,
        "image_url": "",
        "is_active": True,
        "is_featured": False,
        "subcategory": "extensions"
    },
    {
        "name": "Gel Polish Removal & Care",
        "slug": "gel-polish-removal-care",
        "description": "Gentle gel polish removal with nail strengthening treatment and cuticle care.",
        "duration_minutes": 30,
        "price": 15.00,
        "discount_price": None,
        "image_url": "",
        "is_active": True,
        "is_featured": False,
        "subcategory": "gel"
    },
]

def add_nail_services():
    with get_db() as conn:
        cur = conn.cursor()
        category_id = 184  # Nails category ID
        
        for svc in NAIL_SERVICES:
            # Check if service already exists
            cur.execute("SELECT id FROM services WHERE slug = ?", (svc["slug"],))
            existing = cur.fetchone()
            
            if existing:
                print(f"Service {svc['name']} already exists, updating...")
                cur.execute("""
                    UPDATE services SET 
                        name = ?, description = ?, duration_minutes = ?, price = ?, 
                        discount_price = ?, image_url = ?, is_active = ?, is_featured = ?, subcategory = ?
                    WHERE slug = ?
                """, (
                    svc["name"], svc["description"], svc["duration_minutes"], svc["price"],
                    svc["discount_price"], svc["image_url"], svc["is_active"], 
                    svc["is_featured"], svc["subcategory"], svc["slug"]
                ))
            else:
                print(f"Adding service: {svc['name']}")
                cur.execute("""
                    INSERT INTO services (
                        category_id, name, slug, description, duration_minutes,
                        price, discount_price, image_url, is_active, is_featured, subcategory
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    category_id, svc["name"], svc["slug"], svc["description"], svc["duration_minutes"],
                    svc["price"], svc["discount_price"], svc["image_url"],
                    svc["is_active"], svc["is_featured"], svc["subcategory"]
                ))
        
        print("Done!")

if __name__ == "__main__":
    from app.database import init_db
    init_db()
    add_nail_services()