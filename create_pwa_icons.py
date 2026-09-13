"""Generate the Blossom Dreams PWA icon set (Brand: bubblegum + rose gold).

Output (all PNG):
  public/images/icons/icon-192.png            (192x192, any)
  public/images/icons/icon-512.png            (512x512, any)
  public/images/icons/icon-maskable-512.png   (512x512, maskable - motif kept in safe zone)
  public/images/icons/apple-touch-icon.png    (180x180, no transparency)
  public/images/icons/favicon-32.png          (32x32)
  public/images/icons/favicon-48.png          (48x48)

Run:  python create_pwa_icons.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent / "public" / "images" / "icons"

GRAD_TOP = (247, 161, 179)   # #F7A1B3 bubblegum
GRAD_BOTTOM = (139, 42, 92)   # #8B2A5C deep rose velvet
GOLD_TOP = (247, 224, 146)    # #F7E092
GOLD_BOTTOM = (212, 164, 74)  # #D4A44A
PETAL_EDGE = (162, 73, 45)    # #A2492D copper
CREAM = (255, 247, 240)       # #FFF7F0
SPARKLE = (208, 104, 72)      # #D06848 copper


def _vertical_gradient(size, top, bottom):
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        t = y / (size - 1)
        color = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(size):
            px[x, y] = color
    return img


def _petal(w, h):
    layer = Image.new("RGBA", (w, h + 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    px = layer.load()
    for x in range(w):
        for y in range(h + 1):
            nx = (x - w / 2) / (w / 2)
            ny = (y - h / 2) / (h / 2)
            if nx * nx + ny * ny <= 1:
                t = y / h
                base = tuple(
                    round(GOLD_TOP[i] + (GOLD_BOTTOM[i] - GOLD_TOP[i]) * t)
                    for i in range(3)
                )
                px[x, y] = base + (255,)
    d.ellipse([0, 0, w, h], fill=None, outline=PETAL_EDGE + (255,), width=max(3, w // 40))
    return layer


def _star(size, color):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size / 2
    r = size / 2
    d.polygon(
        [(c, 0), (c + r * 0.28, c - r * 0.28), (size, c), (c + r * 0.28, c + r * 0.28),
         (c, size), (c - r * 0.28, c + r * 0.28), (0, c), (c - r * 0.28, c - r * 0.28)],
        fill=color + (255,),
    )
    return img


def make_art(size=1024, motif_scale=1.0):
    base = _vertical_gradient(size, GRAD_TOP, GRAD_BOTTOM).convert("RGBA")
    motif = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cx = cy = size / 2
    petal_w = int(size * 0.17 * motif_scale)
    petal_h = int(size * 0.34 * motif_scale)
    petal = _petal(petal_w, petal_h)
    for i in range(5):
        angle = i * 72 - 90
        rotated = petal.rotate(angle, resample=Image.BICUBIC, center=(petal_w / 2, petal_h / 2))
        rw, rh = rotated.size
        motif.alpha_composite(rotated, (int(cx - rw / 2), int(cy - rh / 2)))

    ring_r = int(size * 0.115 * motif_scale)
    d = ImageDraw.Draw(motif)
    d.ellipse(
        [cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
        fill=None,
        outline=GOLD_TOP + (255,),
        width=max(3, size // 250),
    )
    center_r = int(size * 0.10 * motif_scale)
    d.ellipse([cx - center_r, cy - center_r, cx + center_r, cy + center_r], fill=CREAM + (255,))

    spark = _star(int(size * 0.09), SPARKLE)
    for angle, dist in ((18, 0.26), (126, 0.30), (252, 0.27)):
        a = math.radians(angle)
        x = cx + math.cos(a) * size * dist * motif_scale - spark.width / 2
        y = cy + math.sin(a) * size * dist * motif_scale - spark.height / 2
        motif.alpha_composite(spark, (int(x), int(y)))

    return Image.alpha_composite(base, motif)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    art_any = make_art(1024, motif_scale=1.0)
    art_maskable = make_art(1024, motif_scale=0.80)

    jobs = {
        "icon-192.png": (art_any, 192),
        "icon-512.png": (art_any, 512),
        "icon-maskable-512.png": (art_maskable, 512),
        "apple-touch-icon.png": (art_any, 180),
        "favicon-32.png": (art_any, 32),
        "favicon-48.png": (art_any, 48),
    }
    for name, (art, size) in jobs.items():
        out = art.resize((size, size), Image.LANCZOS)
        if name == "apple-touch-icon.png":
            out = out.convert("RGB")
        out.save(OUT_DIR / name, "PNG")
        print(f"wrote {OUT_DIR / name} ({size}x{size})")


if __name__ == "__main__":
    main()