#!/usr/bin/env python3
"""
Turn a portrait photo into the rows of ASCII art the hero card prints, written to
data/portrait.txt. render_cards.py reads that file, so this runs once by hand
(not in the daily workflow) and only needs Pillow + NumPy.

    python scripts/make_portrait.py photo.jpg     # from a photo
    python scripts/make_portrait.py --monogram ZM # placeholder: big serif initials

Works best with a head-and-shoulders shot on a plain, light background. The
background is estimated from the photo's border and pushed to blank.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data", "portrait.txt")
COLS, ROWS = 110, 58           # ~1:1.9 character cells -> a roughly square portrait
RAMP = " .`:-=+*cs#%@"         # light -> dark
WHITE_FLOOR = 0.82             # anything lighter than this prints as a space
GAMMA = 1.15


def from_photo(path):
    im = ImageOps.exif_transpose(Image.open(path)).convert("L")
    side = min(im.size)  # centre square crop, biased up toward the face
    left, top = (im.width - side) // 2, max(0, (im.height - side) // 4)
    im = im.crop((left, top, left + side, top + side))
    a = np.asarray(im.filter(ImageFilter.MedianFilter(3)), dtype=np.float32) / 255
    border = np.concatenate([a[:8].ravel(), a[-8:].ravel(), a[:, :8].ravel(), a[:, -8:].ravel()])
    bg = np.median(border)
    lo, hi = np.percentile(a, [2, 98])
    a = np.clip((a - lo) / max(hi - lo, 1e-3), 0, 1)
    if bg > 0.5:  # light background: fade anything close to it out to white
        bgn = np.clip((bg - lo) / max(hi - lo, 1e-3), 0, 1)
        a = np.where(np.abs(a - bgn) < 0.08, 1.0, a)
    return Image.fromarray((a * 255).astype(np.uint8))


def monogram(text):
    font_path = os.path.join(ROOT, "fonts", "serif-italic.woff2")
    im = Image.new("L", (1100, 1100), 255)
    try:
        font = ImageFont.truetype(font_path, 760)
    except OSError:
        font = ImageFont.load_default(size=600)
    draw = ImageDraw.Draw(im)
    box = draw.textbbox((0, 0), text, font=font)
    x = (im.width - (box[2] - box[0])) / 2 - box[0]
    y = (im.height - (box[3] - box[1])) / 2 - box[1]
    draw.text((x, y), text, font=font, fill=0)
    return im.filter(ImageFilter.GaussianBlur(10))  # soft edges give the ramp something to do


def to_rows(im):
    px = np.asarray(im.resize((COLS, ROWS), Image.LANCZOS), dtype=np.float32) / 255
    rows = []
    for line in px ** GAMMA:
        rows.append("".join(" " if v >= WHITE_FLOOR else
                            RAMP[min(len(RAMP) - 1, int((1 - v) * (len(RAMP) - 1) + .5))] for v in line))
    return rows


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--monogram":
        rows = to_rows(monogram(sys.argv[2]))
    elif len(sys.argv) == 2:
        rows = to_rows(from_photo(sys.argv[1]))
    else:
        sys.exit(__doc__)
    with open(OUT, "w") as f:
        f.write("\n".join(r.rstrip() for r in rows) + "\n")
    print(f"wrote data/portrait.txt ({len(rows)} rows)")
