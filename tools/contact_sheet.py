"""usage: contact_sheet.py <out.jpg> [--cols N] [--w W --h H] <paths or dirs...>
Numbered contact sheet. Dirs expand to *.png (natural order: s1..s10 for journey chapters)."""
import sys, re
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is required (pip install -r requirements.txt, or run this with the project's .venv python)")
from pathlib import Path


def nat(p):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def expand(items):
    out = []
    for it in items:
        p = Path(it)
        if p.is_dir():
            out += sorted(p.glob("*.png"), key=nat)
        elif p.exists():
            out.append(p)
        else:
            sys.exit(f"not found: {it}")
    return out


def main(argv):
    cols = w = h = None
    rest, i = [], 0
    while i < len(argv):
        if argv[i] == "--cols": cols = int(argv[i + 1]); i += 2
        elif argv[i] == "--w": w = int(argv[i + 1]); i += 2
        elif argv[i] == "--h": h = int(argv[i + 1]); i += 2
        else: rest.append(argv[i]); i += 1
    if len(rest) < 2:
        sys.exit(__doc__)
    out, files = rest[0], expand(rest[1:])
    if not files:
        sys.exit("no images")
    ims = [Image.open(f).convert("RGB") for f in files]
    if not (w and h):
        r = ims[0].width / ims[0].height
        w, h = (800, 450) if r > 1.3 else (300, 400) if r < 0.9 else (300, 300)
    cols = cols or (2 if w >= 800 else min(6, len(ims)))
    rows = -(-len(ims) // cols)
    sheet = Image.new("RGB", (cols * w, rows * h), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arialbd.ttf", max(14, h // 14))
    except Exception:
        font = ImageFont.load_default()
    for n, im in enumerate(ims):
        im.thumbnail((w - 4, h - 4))
        x, y = (n % cols) * w, (n // cols) * h
        ox, oy = x + (w - im.width) // 2, y + (h - im.height) // 2
        sheet.paste(im, (ox, oy))
        s = str(n + 1)
        bb = d.textbbox((ox + 6, oy + 4), s, font=font)
        d.rectangle((bb[0] - 4, bb[1] - 2, bb[2] + 4, bb[3] + 2), fill=(0, 0, 0))
        d.text((ox + 6, oy + 4), s, fill=(255, 235, 80), font=font)
    sheet.save(out, quality=88)
    print(f"{out}: {len(ims)} tiles, {cols}x{rows} of {w}x{h}")
    for n, f in enumerate(files):
        print(f"{n + 1}: {f}")


if __name__ == "__main__":
    main(sys.argv[1:])
