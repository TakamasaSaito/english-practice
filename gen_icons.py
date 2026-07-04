"""Generate app icons for Gate English PWA.
Run: python3 gen_icons.py
Outputs: static/icons/icon-{32,180,192,512}.png
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path("static/icons")
OUT.mkdir(parents=True, exist_ok=True)

BG    = (18, 33, 61)      # #12213D
AMBER = (246, 162, 28)    # #F6A21C


def draw_plane(draw: ImageDraw.ImageDraw, size: int):
    """Draw a right-pointing paper-plane dart on a square of `size` pixels."""
    m  = max(3, int(size * 0.13))   # margin
    w  = size - 2 * m
    h  = size - 2 * m
    cy = size // 2

    # --- key points ---------------------------------------------------
    nose         = (m + w,           cy)           # nose (right, center)
    top_wing     = (m,               m)            # upper-left wing tip
    bot_wing     = (m,               m + h)        # lower-left wing tip
    tail         = (m + w // 4,      cy)           # tail notch center

    # --- main silhouette: simple 4-point dart -------------------------
    # polygon order guarantees the interior covers (size//2, size//2)
    draw.polygon([nose, top_wing, tail, bot_wing], fill=AMBER)

    # --- fold crease (visible on larger sizes) -----------------------
    lw = max(1, size // 64)
    draw.line([tail, nose], fill=BG, width=lw)


def make_icon(size: int):
    img  = Image.new("RGBA", (size, size), BG + (255,))
    draw = ImageDraw.Draw(img)
    draw_plane(draw, size)
    out_path = OUT / f"icon-{size}.png"
    img.save(out_path, "PNG", optimize=True)

    # quick sanity: sample a pixel just above center — should be amber
    px = img.getpixel((size // 2, size // 2 - size // 8))
    status = "✓" if px[:3] == AMBER else f"? {px}"
    print(f"  {out_path}  ({size}x{size})  sample={status}")


if __name__ == "__main__":
    print("Generating icons...")
    for s in [32, 180, 192, 512]:
        make_icon(s)
    print("Done.")
