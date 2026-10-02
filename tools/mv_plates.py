"""EXPERIMENTAL. Two-plate prep for a lip-synced person (a reporter, a singer) over a moving background: a lip-sync clip (LTX
image+audio) freezes its background, so the person is cut out over green and composited over a separate moving plate
(see mv_composite.py). Needs opencv-python, numpy, Pillow and transparent-background (pip install transparent-background).

    python tools/mv_plates.py musicvideos/NNN/sbNN/sX.png [--x 0.62] [--feather 1.5] [--grow 0.08]

Writes next to the frame, in sbNN/plates/:
  sX_matte.png   soft matte (L) of the person + held mic, cut from the STILL (transparent-background, cached base ckpt)
  sX_green.png   that cutout, same position/scale, over chroma green #00B140 (feed this to LTX ia2v as the start frame)
  sX_box.json    {"box": [x0,y0,x1,y1] fractions grown by --grow (the clean-plate inpaint box), "free_side": "left|right"
                 (the side of the frame AWAY from the person = where background action may happen), "bbox", "x_hint"}
The clean plate (background without the person) is made with tools/fix_area.py on the ORIGINAL frame with --out and --prompt.
"""
import json, sys
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:  # checked in main()
    cv2 = np = None

ROOT = Path(__file__).resolve().parent.parent
GREEN = (0x00, 0xB1, 0x40)  # RGB


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def load_remover():
    ck = Path.home() / ".transparent-background" / "ckpt_base.pth"
    if not ck.exists():
        raise SystemExit(f"transparent-background checkpoint missing ({ck}); not downloading it automatically. Install/copy it there first.")
    from transparent_background import Remover
    return Remover(mode="base", ckpt=str(ck))


def reporter_matte(rgb, x_hint=None, remover=None):
    """soft alpha (float 0..1) of the person nearest x_hint (else the largest salient component)"""
    from PIL import Image
    remover = remover or load_remover()
    soft = np.array(remover.process(Image.fromarray(rgb), type="map").convert("L"), dtype=np.float32) / 255.0
    if soft.shape[:2] != rgb.shape[:2]:
        soft = cv2.resize(soft, (rgb.shape[1], rgb.shape[0]))
    hard = (soft > 0.5).astype(np.uint8)
    hard = cv2.morphologyEx(hard, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(hard, 8)
    if n < 2:
        raise SystemExit("no salient object found")
    h, w = hard.shape
    comps = [i for i in range(1, n) if st[i, cv2.CC_STAT_AREA] > 0.004 * h * w]
    if x_hint is None:
        best = max(comps, key=lambda i: st[i, cv2.CC_STAT_AREA])
    else:
        # the big component whose horizontal span contains / is closest to the hint, biggest wins ties
        def score(i):
            x0, ww = st[i, cv2.CC_STAT_LEFT], st[i, cv2.CC_STAT_WIDTH]
            hx = x_hint * w
            d = 0 if x0 <= hx <= x0 + ww else min(abs(hx - x0), abs(hx - x0 - ww))
            return (-d / w, st[i, cv2.CC_STAT_AREA])
        best = max(comps, key=score)
    keep = (lab == best).astype(np.uint8)
    # include other big blobs that touch/overlap the kept one dilated (a mic or hand split off the body)
    near = cv2.dilate(keep, np.ones((25, 25), np.uint8))
    for i in comps:
        if i != best and (near[lab == i].any()):
            keep |= (lab == i).astype(np.uint8)
    region = cv2.dilate(keep, np.ones((7, 7), np.uint8)).astype(np.float32)
    return soft * region, keep


def main():
    if cv2 is None:
        sys.exit("mv_plates needs opencv + numpy: pip install opencv-python numpy")
    src = Path(sys.argv[1])
    src = src if src.is_absolute() else ROOT / src
    x_hint = float(arg("--x")) if arg("--x") else None
    feather = float(arg("--feather", 1.5))
    grow = float(arg("--grow", 0.08))
    bgr = cv2.imread(str(src), cv2.IMREAD_COLOR)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    alpha, keep = reporter_matte(rgb, x_hint)
    # clean the edge: pull in 1px (kills the background halo), then a 1-2px gaussian feather
    a = cv2.erode(alpha, np.ones((3, 3), np.uint8))
    a = cv2.GaussianBlur(a, (0, 0), feather)
    a = np.clip((a - 0.05) / 0.9, 0, 1)
    ys, xs = np.where(keep > 0)
    x0, x1, y0, y1 = xs.min() / w, (xs.max() + 1) / w, ys.min() / h, (ys.max() + 1) / h
    bw, bh = x1 - x0, y1 - y0
    box = [max(0, x0 - bw * grow), max(0, y0 - bh * grow), min(1, x1 + bw * grow), min(1, y1 + bh * grow)]
    cx = (x0 + x1) / 2
    out = src.parent / "plates"
    out.mkdir(exist_ok=True)
    stem = src.stem
    green = np.zeros_like(rgb, dtype=np.float32)
    green[:] = GREEN
    comp = rgb.astype(np.float32) * a[..., None] + green * (1 - a[..., None])
    cv2.imwrite(str(out / f"{stem}_matte.png"), (a * 255).astype(np.uint8))
    cv2.imwrite(str(out / f"{stem}_green.png"), cv2.cvtColor(comp.astype(np.uint8), cv2.COLOR_RGB2BGR))
    info = {"box": [round(v, 4) for v in box], "bbox": [round(v, 4) for v in (x0, y0, x1, y1)],
            "free_side": "left" if cx > 0.5 else "right", "x_hint": x_hint, "source": src.name}
    (out / f"{stem}_box.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"green": str(out / f"{stem}_green.png"), **info}))


if __name__ == "__main__":
    main()
