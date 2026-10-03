"""usage: python tools/contact_sheet.py <out.jpg> [--cols N] [--w W --h H] [--frames N] <paths or dirs...>
Numbered contact sheet. Dirs expand to *.png (natural order: s1..s10 for journey chapters).
An .mp4 adds N evenly spaced frames (default 6, ffmpeg), each tile labelled with its time ("3 @4.2s")."""
import sys, re, io, json, subprocess
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow is required (pip install -r requirements.txt, or run this with the project's .venv python)")
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FFMPEG, FFPROBE


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


def video_frames(p, n):
    """[(label, image)] for n evenly spaced frames of a clip (skips the very last frame)."""
    dur = float(json.loads(subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(p)],
        capture_output=True, text=True, check=True).stdout)["format"]["duration"])
    out = []
    for k in range(n):
        t = dur * k / max(1, n - 1) if n > 1 else 0.0
        t = min(t, max(0.0, dur - 0.05))
        png = subprocess.run([FFMPEG, "-v", "error", "-ss", f"{t:.3f}", "-i", str(p), "-frames:v", "1",
                              "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
        out.append((f"@{t:.1f}s", Image.open(io.BytesIO(png)).convert("RGB")))
    return out


def main(argv):
    cols = w = h = None
    frames = 6
    rest, i = [], 0
    while i < len(argv):
        if argv[i] == "--cols": cols = int(argv[i + 1]); i += 2
        elif argv[i] == "--w": w = int(argv[i + 1]); i += 2
        elif argv[i] == "--h": h = int(argv[i + 1]); i += 2
        elif argv[i] == "--frames": frames = int(argv[i + 1]); i += 2
        else: rest.append(argv[i]); i += 1
    if len(rest) < 2:
        sys.exit(__doc__)
    out, files = rest[0], expand(rest[1:])
    if not files:
        sys.exit("no images")
    tiles = []  # (source, label, image)
    for f in files:
        if f.suffix.lower() in (".mp4", ".mov", ".webm"):
            tiles += [(f, lab, im) for lab, im in video_frames(f, frames)]
        else:
            tiles.append((f, "", Image.open(f).convert("RGB")))
    ims = [t[2] for t in tiles]
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
    for n, (_, lab, im) in enumerate(tiles):
        im.thumbnail((w - 4, h - 4))
        x, y = (n % cols) * w, (n // cols) * h
        ox, oy = x + (w - im.width) // 2, y + (h - im.height) // 2
        sheet.paste(im, (ox, oy))
        s = f"{n + 1} {lab}".strip()
        bb = d.textbbox((ox + 6, oy + 4), s, font=font)
        d.rectangle((bb[0] - 4, bb[1] - 2, bb[2] + 4, bb[3] + 2), fill=(0, 0, 0))
        d.text((ox + 6, oy + 4), s, fill=(255, 235, 80), font=font)
    sheet.save(out, quality=88)
    print(f"{out}: {len(ims)} tiles, {cols}x{rows} of {w}x{h}")
    for n, (f, lab, _) in enumerate(tiles):
        print(f"{n + 1}: {f} {lab}".rstrip())


if __name__ == "__main__":
    main(sys.argv[1:])
