"""Pull a reference-edited image's contrast/saturation back to its source image (Qwen ref edits tend to come back
harder than the source). Matches the subject's luminance std and mean saturation to the source's; the flat
background stays as is. Writes in place, keeps the original in <version>/_before_contrast/.
Needs Pillow + numpy: run with config.json's comfy_python if that's a different interpreter than this one.
  python tools/match_contrast.py <edited.png> <source.png>"""
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def stats(a, bg):
    m = np.abs(a - bg).max(axis=2) > 28
    lum = a.mean(axis=2)
    mx, mn = a.max(axis=2), a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    return m, lum[m].mean(), lum[m].std(), sat[m].mean()


def main(edited, source):
    e = np.asarray(Image.open(edited).convert("RGB")).astype(np.float32)
    s = np.asarray(Image.open(source).convert("RGB").resize((e.shape[1], e.shape[0]))).astype(np.float32)
    bg_e = np.median(e[:8].reshape(-1, 3), axis=0); bg_s = np.median(s[:8].reshape(-1, 3), axis=0)
    me, lm_e, ls_e, sat_e = stats(e, bg_e)
    _, lm_s, ls_s, sat_s = stats(s, bg_s)
    lum = e.mean(axis=2, keepdims=True)
    out = e.copy()
    k = ls_s / max(ls_e, 1e-3)
    new_lum = (lum - lm_e) * k + lm_s                      # contrast + brightness to the source's
    chroma = (e - lum) * (sat_s / max(sat_e, 1e-3))        # saturation to the source's
    out[me] = (new_lum + chroma)[me]
    p = Path(edited)
    keep = p.parent / "_before_contrast"; keep.mkdir(exist_ok=True)  # a subfolder: the gallery would list a sibling .png as a render
    shutil.copy(p, keep / p.name)
    Image.fromarray(out.clip(0, 255).astype(np.uint8)).save(p)
    print(f"{p.name}: contrast x{k:.2f}, saturation x{sat_s / max(sat_e, 1e-3):.2f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
