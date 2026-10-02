"""Where does a clip move? Prints mean frame-to-frame difference per 0.25 s, so still stretches (a model's frozen tail) can be cut.

  python tools/clip_motion.py <clip.mp4> [...]   ->  per clip: time  motion  bar, and the still spans (motion < --still)
"""
import argparse, subprocess, sys
from pathlib import Path

try:
    import numpy as np
except ImportError:  # checked in main()
    np = None

sys.path.insert(0, str(Path(__file__).parent))
from config import FFMPEG  # noqa: E402


def motion(path, w=160, h=90):
    import mv_assemble
    fps = mv_assemble.probe(Path(path))["fps"] or 24  # Wan is 16 fps, LTX/H3 24
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    return np.concatenate([[d[0] if len(d) else 0], d]), fps


def main():
    if np is None:
        sys.exit("clip_motion needs numpy: pip install numpy")
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+")
    ap.add_argument("--still", type=float, default=0.35, help="mean abs diff per frame below this = still")
    ap.add_argument("--step", type=float, default=0.25)
    a = ap.parse_args()
    for c in a.clips:
        d, fps = motion(c)
        n = max(1, int(a.step * fps))
        print(f"== {Path(c).name}  {len(d) / fps:.2f}s")
        spans, start = [], None
        for i in range(0, len(d), n):
            m = float(d[i:i + n].mean()); t = i / fps
            print(f"  {t:6.2f}  {m:5.2f}  {'#' * min(60, int(m * 10))}")
            if m < a.still and start is None:
                start = t
            elif m >= a.still and start is not None:
                spans.append((start, t)); start = None
        if start is not None:
            spans.append((start, len(d) / fps))
        print("  still:", ", ".join(f"{s:.2f}-{e:.2f}" for s, e in spans if e - s >= 0.5) or "none")


if __name__ == "__main__":
    main()
