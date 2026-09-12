import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

IMAGES_DIR = Path(__file__).resolve().parent / "public" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Aesthetic palette inspired by Blossom Dreams
# Soft blush, luxury rose, champagne gold accents, rich deep magenta
IMAGE_CONFIGS = [
    # Nails
    ("nails_manicure.jpg", "RUSSIAN MANICURE", "Precision E-file Cuticle Care & Gel Finish", "#FFF0F5", "#E6739F", "#9D174D"),
    ("nails_biab.jpg", "BIAB BUILDER GEL", "Natural Strengthening & High-Gloss Overlay", "#FDF2F8", "#DB2777", "#831843"),
    ("nails_extensions.jpg", "SCULPTED EXTENSIONS", "French Ombre & Bespoke Length", "#FFF1F2", "#E11D48", "#881337"),
    ("nails_pedicure.jpg", "DELUXE SPA PEDICURE", "Rose Petal Soak, Scrub & Gel Polish", "#FDF4FF", "#C026D3", "#701A75"),
    ("nails_art.jpg", "HAUTE COUTURE NAIL ART", "3D Pearls, Chrome & Hand-Painted Florals", "#FFF0F3", "#F43F5E", "#9F1239"),

    # Lashes
    ("lashes_classic.jpg", "CLASSIC SILK LASHES", "Individual 1:1 Featherweight Natural Set", "#FAF5FF", "#9333EA", "#581C87"),
    ("lashes_volume.jpg", "RUSSIAN MEGA VOLUME", "Fluffy 4D-6D Handmade Fans & Sultry Gaze", "#FDF2F8", "#BE185D", "#831843"),
    ("lashes_lift.jpg", "KERATIN LASH LIFT & TINT", "Root-to-Tip Infusion & Deep Jet Tint", "#FFF1F5", "#FB7185", "#9F1239"),

    # Brows
    ("brows_lamination.jpg", "BROW LAMINATION & TINT", "Full Feathered Restructuring & Castor Care", "#FDF4F5", "#E11D48", "#881337"),
    ("brows_sculpt.jpg", "HD PRECISION BROW SCULPT", "Golden-Ratio Mapping, Wax & Hybrid Tint", "#FFF0F5", "#DB2777", "#9D174D"),

    # Skin & Facial
    ("facial_hydra.jpg", "HYDRAFACIAL RADIANCE", "Vortex Extraction & Hyaluronic Infusion", "#F0FDFA", "#0D9488", "#115E59"),
    ("facial_dermaplane.jpg", "DERMAPLANING RADIANCE", "Glass Skin Exfoliation & Collagen Mask", "#FFF7ED", "#EA580C", "#9A3412"),
    ("facial_gold.jpg", "24K GOLD LUXURY FACIAL", "Pure Gold Foil & Lymphatic LED Therapy", "#FEFCE8", "#CA8A04", "#713F12"),

    # Laser
    ("laser_full_body.jpg", "TRIPLE-WAVELENGTH LASER", "Ice-Cooling Full Body Permanent Smoothness", "#F0FDF4", "#16A34A", "#14532D"),
    ("laser_bikini.jpg", "UNDERARMS & BIKINI LASER", "Targeted Ice-Diode Precision Comfort", "#FDF2F8", "#DB2777", "#831843"),

    # Makeup
    ("makeup_glam.jpg", "EVENING RED CARPET GLAM", "Sculpted Glow, Smokey Eyes & Mink Lashes", "#FAF5FF", "#A855F7", "#6B21A8"),
    ("makeup_bridal.jpg", "BRIDAL BESPOKE ARTISTRY", "Timeless Luminous Luxury for Your Dream Day", "#FFF1F2", "#BE185D", "#831843"),

    # Piercing & Tattoo
    ("piercing.jpg", "CURATED EAR PIERCING", "Solid 14K Gold & Titanium Fine Ear Styling", "#FEFCE8", "#EAB308", "#854D0E"),
    ("tattoo.jpg", "FINE LINE AESTHETIC TATTOO", "Minimalist Floral & Delicate Single Needle", "#F3F4F6", "#4B5563", "#1F2937"),

    # Offers
    ("offer_glow_duo.jpg", "BLOSSOM BRIDAL GLOW DUO", "Hydrafacial + Lash Lift Special Package", "#FDF2F8", "#BE185D", "#831843"),
    ("offer_lash_brow.jpg", "VOLUME LASH & BROW DUO", "Russian Mega Volume + Brow Lamination", "#FFF1F5", "#E11D48", "#881337"),
    ("offer_mani_pedi.jpg", "BIAB & SPA PEDICURE DUO", "Flawless Builder Nails & Rose Spa Care", "#FDF4FF", "#C026D3", "#701A75"),
    ("offer_laser.jpg", "FULL BODY LASER PACKAGE", "Complete 3-Session Summer Radiance", "#F0FDF4", "#059669", "#064E3B"),

    # Gallery
    ("gallery_1.jpg", "FRENCH OMBRE ALMOND NAILS", "Blossom Dreams Signature Art", "#FFF0F5", "#DB2777", "#831843"),
    ("gallery_2.jpg", "FLUFFY RUSSIAN VOLUME FANS", "Custom Lash Curation", "#FAF5FF", "#9333EA", "#581C87"),
    ("gallery_3.jpg", "FEATHERED BROW LAMINATION", "Organic Nourishing Lift", "#FDF4F5", "#E11D48", "#881337"),
    ("gallery_4.jpg", "HYDRAFACIAL GLASS SKIN", "Vortex Deep Pore Extraction", "#F0FDFA", "#0D9488", "#115E59"),
    ("gallery_5.jpg", "BRIDAL MAKEUP & VEIL ART", "Timeless Elegance & Glow", "#FFF1F2", "#BE185D", "#831843"),
    ("gallery_6.jpg", "CURATED GOLD PIERCINGS", "14K Gold Ear Constellation", "#FEFCE8", "#CA8A04", "#713F12"),

    # Hero & About
    ("hero_bg.jpg", "BLOSSOM DREAMS", "Sanctuary of Luxury Beauty & Glamour", "#FDF2F8", "#BE185D", "#831843"),
    ("about_salon.jpg", "OUR ATELIER & PHILOSOPHY", "Bespoke Excellence in Beirut", "#FFF1F2", "#E11D48", "#881337"),
]

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_aesthetic_card(filename, title, subtitle, bg_hex, accent_hex, dark_hex, width=800, height=600):
    bg_rgb = hex_to_rgb(bg_hex)
    accent_rgb = hex_to_rgb(accent_hex)
    dark_rgb = hex_to_rgb(dark_hex)

    img = Image.new("RGB", (width, height), bg_rgb)
    draw = ImageDraw.Draw(img)

    # Soft gradient background simulation
    for y in range(height):
        ratio = y / height
        r = int(bg_rgb[0] * (1 - ratio * 0.15) + accent_rgb[0] * (ratio * 0.15))
        g = int(bg_rgb[1] * (1 - ratio * 0.15) + accent_rgb[1] * (ratio * 0.15))
        b = int(bg_rgb[2] * (1 - ratio * 0.15) + accent_rgb[2] * (ratio * 0.15))
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Decorative circles/floral ambient glow
    draw.ellipse([width - 300, -100, width + 100, 300], fill=None, outline=accent_rgb, width=2)
    draw.ellipse([width - 270, -70, width + 70, 270], fill=None, outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2]), width=1)
    draw.ellipse([-100, height - 300, 300, height + 100], fill=None, outline=accent_rgb, width=2)
    draw.ellipse([-70, height - 270, 270, height + 70], fill=None, outline=(accent_rgb[0], accent_rgb[1], accent_rgb[2]), width=1)

    # Central luxury badge card
    pad = 40
    card_box = [pad, pad, width - pad, height - pad]
    draw.rounded_rectangle(card_box, radius=24, outline=accent_rgb, width=2)

    # Gold corner accents
    corner_len = 30
    gold_rgb = (212, 175, 55)
    # top-left
    draw.line([(pad, pad), (pad + corner_len, pad)], fill=gold_rgb, width=4)
    draw.line([(pad, pad), (pad, pad + corner_len)], fill=gold_rgb, width=4)
    # top-right
    draw.line([(width - pad - corner_len, pad), (width - pad, pad)], fill=gold_rgb, width=4)
    draw.line([(width - pad, pad), (width - pad, pad + corner_len)], fill=gold_rgb, width=4)
    # bottom-left
    draw.line([(pad, height - pad), (pad + corner_len, height - pad)], fill=gold_rgb, width=4)
    draw.line([(pad, height - pad - corner_len), (pad, height - pad)], fill=gold_rgb, width=4)
    # bottom-right
    draw.line([(width - pad - corner_len, height - pad), (width - pad, height - pad)], fill=gold_rgb, width=4)
    draw.line([(width - pad, height - pad - corner_len), (width - pad, height - pad)], fill=gold_rgb, width=4)

    # Blossom brand watermark
    brand_text = "🌸 BLOSSOM DREAMS • BEIRUT"
    draw.text((width // 2, pad + 50), brand_text, fill=dark_rgb, anchor="mm")

    # Title & Subtitle
    draw.text((width // 2, height // 2 - 20), title, fill=dark_rgb, anchor="mm")
    draw.text((width // 2, height // 2 + 40), subtitle, fill=accent_rgb, anchor="mm")

    # Ribbon/Star motif
    motif_text = "✦  LUXURY BEAUTY ATELIER  ✦"
    draw.text((width // 2, height - pad - 60), motif_text, fill=gold_rgb, anchor="mm")

    out_path = IMAGES_DIR / filename
    img.save(out_path, "JPEG", quality=92)
    print(f"Generated {filename}")

def main():
    for config in IMAGE_CONFIGS:
        create_aesthetic_card(*config)
    print("All aesthetic placeholder cards generated successfully!")

if __name__ == "__main__":
    main()
