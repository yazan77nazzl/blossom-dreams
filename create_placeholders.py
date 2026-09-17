import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

IMAGES_DIR = Path(__file__).resolve().parent / "public" / "images"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Aesthetic palette inspired by Blossom Dreams
# Soft blush, luxury rose, champagne gold accents, rich deep magenta
IMAGE_CONFIGS = [
    # Hero & About
    ("hero_bg.jpg", "BLOSSOM DREAMS", "Sanctuary of Luxury Beauty & Glamour", "#FDF2F8", "#BE185D", "#831843"),
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
