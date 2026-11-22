#!/usr/bin/env python3
"""
Turn a portrait photo into the ASCII art the hero card prints, written to
data/portrait.txt. render_cards.py reads that file, so this runs by hand when the
photo changes, not in the daily workflow.

    pip install -r scripts/portrait-requirements.txt
    python scripts/make_portrait.py                # your current GitHub avatar
    python scripts/make_portrait.py photo.jpg      # any photo
    python scripts/make_portrait.py --monogram ZM  # placeholder: big initials

Steps:
  1. cut the person out with MediaPipe's multiclass selfie segmenter (downloaded
     once to ~/.cache), which also says which pixels are hair, skin and clothes
  2. smooth texture but keep edges, flatten the clothes so a pattern doesn't
     turn into noise, and boost local contrast on the face
  3. map brightness to character density for light text on a dark card, with a
     floor so dark hair and beard still print, and darken the line work (eyes,
     brows, mouth) so it survives the small size

Tune the crop with CROP="top,left,size" (pixels in the 460px avatar), and the
detail with COLS.
"""
import os
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "data", "portrait.txt")
PROFILE_USER = "ZiadMD"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/image_segmenter/"
             "selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite")
MODEL = os.path.expanduser("~/.cache/profile-cards/selfie_multiclass_256x256.tflite")

COLS = int(os.environ.get("COLS", 150))
ROWS = round(COLS / 1.9)            # character cells are ~1.9x taller than wide
CROP = os.environ.get("CROP", "80,87,300")  # top,left,size: head and shoulders
RAMP = " .`:-=+*cs#%@"              # sparse -> dense (dense prints brightest on dark)
SIZE = 460                          # photos are scaled to this before cropping


def github_avatar(user):
    import json
    req = urllib.request.Request(f"https://api.github.com/users/{user}", headers={"User-Agent": "profile-cards"})
    url = json.load(urllib.request.urlopen(req, timeout=20))["avatar_url"].split("?")[0] + f"?s={SIZE}"
    path = os.path.expanduser("~/.cache/profile-cards/avatar.jpg")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    urllib.request.urlretrieve(url, path)
    return path


def segment(rgb):
    """Per-pixel class probabilities: background, hair, body skin, face skin, clothes, other."""
    from ai_edge_litert.interpreter import Interpreter
    if not os.path.exists(MODEL):
        os.makedirs(os.path.dirname(MODEL), exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL)
    it = Interpreter(model_path=MODEL)
    it.allocate_tensors()
    inp, out = it.get_input_details()[0], it.get_output_details()[0]
    x = np.asarray(Image.fromarray(rgb).resize((256, 256), Image.BILINEAR), np.float32) / 255
    it.set_tensor(inp["index"], x[None])
    it.invoke()
    logits = it.get_tensor(out["index"])[0]
    e = np.exp(logits - logits.max(-1, keepdims=True))
    p = e / e.sum(-1, keepdims=True)
    h, w = rgb.shape[:2]
    return np.stack([np.asarray(Image.fromarray(p[..., k].astype(np.float32)).resize((w, h), Image.BILINEAR))
                     for k in range(p.shape[-1])], -1)


def ink_from_photo(path):
    import cv2
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    side = min(im.size)  # square, then a fixed size so CROP means the same thing for any photo
    im = im.crop(((im.width - side) // 2, 0, (im.width - side) // 2 + side, side)).resize((SIZE, SIZE), Image.LANCZOS)
    rgb = np.asarray(im)
    probs = segment(rgb)
    fg = np.clip((1 - probs[..., 0] - 0.5) / 0.2, 0, 1)
    clothes = probs.argmax(-1) == 4

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    for _ in range(3):
        gray = cv2.bilateralFilter(gray, 9, 40, 9)
    sm = gray.astype(np.float32)
    if clothes.any():  # flatten patterns (plaid, prints) to a calm texture
        blur = cv2.GaussianBlur(sm, (0, 0), 7)
        sm[clothes] = ((0.35 * blur + 0.65 * np.median(sm[clothes])) * 0.85)[clothes]
    sm = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(6, 6)).apply(np.clip(sm, 0, 255).astype(np.uint8)).astype(np.float32)
    lo, hi = np.percentile(sm[fg > .5], [2, 98])
    tone = np.clip((sm - lo) / max(hi - lo, 1), 0, 1)
    ridges = np.clip((cv2.GaussianBlur(sm, (0, 0), 5) - cv2.GaussianBlur(sm, (0, 0), 1.2)) / 35, 0, 1)

    top, left, size = (int(v) for v in CROP.split(","))
    box = (slice(top, top + size), slice(left, left + size))
    ink = np.clip(0.22 + 0.78 * tone - 0.5 * ridges, 0, 1) * fg
    return ink[box]


def ink_from_monogram(text):
    im = Image.new("L", (1100, 1100), 0)
    try:
        font = ImageFont.truetype(os.path.join(ROOT, "fonts", "serif-italic.woff2"), 760)
    except OSError:
        font = ImageFont.load_default(size=600)
    draw = ImageDraw.Draw(im)
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((im.width - box[2] - box[0]) / 2, (im.height - box[3] - box[1]) / 2), text, font=font, fill=255)
    return np.asarray(im.filter(ImageFilter.GaussianBlur(10)), np.float32) / 255


def to_rows(ink):
    small = np.asarray(Image.fromarray((ink * 255).astype(np.uint8)).resize((COLS, ROWS), Image.LANCZOS), np.float32) / 255
    return ["".join(" " if v < .06 else RAMP[min(len(RAMP) - 1, int(v * (len(RAMP) - 1) + .5))] for v in row)
            for row in small]


if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["--monogram"] and len(args) == 2:
        ink = ink_from_monogram(args[1])
    elif len(args) <= 1:
        ink = ink_from_photo(args[0] if args else github_avatar(PROFILE_USER))
    else:
        sys.exit(__doc__)
    rows = to_rows(ink)
    with open(OUT, "w") as f:  # rows keep their trailing spaces so every line is COLS wide
        f.write("\n".join(rows) + "\n")
    print(f"wrote data/portrait.txt ({len(rows)} rows x {COLS} cols)")
