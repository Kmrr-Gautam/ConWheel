"""Generates app/resources/icons/conWheel.ico (+ png) with Pillow: a segmented ring."""
import math
from pathlib import Path
from PIL import Image, ImageDraw

def make(size=512):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse((8, 8, size - 8, size - 8), fill=(23, 24, 28, 255))
    cx = cy = size / 2; R, r = size * .42, size * .17
    for i in range(6):
        a0 = -90 + i * 60 + 3; a1 = a0 + 54
        col = (77, 124, 255, 255) if i == 0 else (52, 56, 68, 255)
        d.pieslice((cx - R, cy - R, cx + R, cy + R), a0, a1, fill=col)
    d.ellipse((cx - r * 1.35, cy - r * 1.35, cx + r * 1.35, cy + r * 1.35), fill=(23, 24, 28, 255))
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(77, 124, 255, 255))
    return im

if __name__ == "__main__":
    out = Path(__file__).parent / "app" / "resources" / "icons"; out.mkdir(parents=True, exist_ok=True)
    im = make(); im.save(out / "conWheel.png")
    im.save(out / "conWheel.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icon written")
