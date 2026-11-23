"""Draws the app icon from scratch at every size Windows uses, so it is sharp everywhere.

Each size is drawn at 8x and shrunk with a high-quality filter (no upscaling of a
small picture, which is what made the old icon blurry). Small sizes (16-24 px) use a
simpler drawing with thicker shapes so they stay readable.

Run:  python tools/make_icon.py      (writes icon.ico, icon.png, icon_48.png, icon_256.png)
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BLURPLE = (88, 101, 242, 255)
BLURPLE_DARK = (71, 82, 196, 255)
WHITE = (255, 255, 255, 255)
LINES = (88, 101, 242, 255)
RED = (237, 66, 69, 255)
SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]


def draw(size):
    s = 8
    W = size * s
    small = size <= 24
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # background: rounded square with a soft vertical gradient
    pad = 0 if small else W * 0.02
    radius = W * (0.22 if small else 0.24)
    grad = Image.new("RGBA", (W, W))
    gd = ImageDraw.Draw(grad)
    for y in range(W):
        t = y / W
        c = tuple(int(BLURPLE[i] * (1 - t) + BLURPLE_DARK[i] * t) for i in range(3)) + (255,)
        gd.line([(0, y), (W, y)], fill=c)
    mask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mask).rounded_rectangle([pad, pad, W - pad, W - pad], radius, fill=255)
    img.paste(grad, (0, 0), mask)

    # speech bubble
    bx0, by0 = W * (0.20 if small else 0.21), W * (0.25 if small else 0.26)
    bx1, by1 = W * (0.80 if small else 0.79), W * (0.68 if small else 0.66)
    d.rounded_rectangle([bx0, by0, bx1, by1], W * 0.08, fill=WHITE)
    # tail
    d.polygon([(bx0 + W * 0.10, by1 - W * 0.02), (bx0 + W * 0.06, by1 + W * 0.14),
               (bx0 + W * 0.26, by1 - W * 0.02)], fill=WHITE)
    # text lines inside the bubble (only on bigger sizes)
    if not small:
        lh = W * 0.045
        for i, frac in enumerate((0.70, 0.52)):
            y = by0 + W * 0.10 + i * W * 0.12
            d.rounded_rectangle([bx0 + W * 0.08, y, bx0 + W * 0.08 + (bx1 - bx0 - W * 0.16) * frac,
                                 y + lh], lh / 2, fill=LINES)
    # red "erase" slash with a thin outline so it stands out on white and blurple
    stroke = W * (0.13 if small else 0.085)
    a, b = (W * 0.18, W * 0.80), (W * 0.84, W * 0.18)
    d.line([a, b], fill=BLURPLE_DARK, width=int(stroke + W * 0.05))
    d.line([a, b], fill=RED, width=int(stroke))
    for p in (a, b):          # round caps
        r = stroke / 2
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=RED)
    out = img.resize((size, size), Image.LANCZOS)
    if size <= 32:
        out = out.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60, threshold=0))
    return out


def main(dest=ROOT):
    imgs = {s: draw(s) for s in SIZES}
    big = draw(512)
    write_ico(os.path.join(dest, "icon.ico"), [imgs[s] for s in SIZES])
    imgs[96].save(os.path.join(dest, "icon.png"))
    imgs[48].save(os.path.join(dest, "icon_48.png"))
    imgs[256].save(os.path.join(dest, "icon_256.png"))
    for s in (16, 32, 64):
        imgs[s].save(os.path.join(dest, f"icon_{s}.png"))
    big.save(os.path.join(dest, "icon_512.png"))
    print("icons written to", dest)


def write_ico(path, images):
    """Write a .ico that holds exactly these pictures (all stored as PNG)."""
    import io
    import struct
    blobs = []
    for im in images:
        buf = io.BytesIO()
        im.save(buf, "PNG")
        blobs.append(buf.getvalue())
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries = b""
    for im, blob in zip(images, blobs):
        w, h = im.size
        entries += struct.pack("<BBBBHHII", w % 256, h % 256, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    with open(path, "wb") as f:
        f.write(head + entries + b"".join(blobs))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT)
