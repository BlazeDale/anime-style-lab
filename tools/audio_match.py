"""🔊 How alike are two audio tracks? (e.g. a lip-sync check: did the video model keep our vocal FROZEN, or generate its own audio?)
  python tools/audio_match.py <a> <b> [--skip-a S] [--skip-b S] [--seconds N]
Compares 10 ms loudness envelopes: prints the correlation at the best lag (searched within +-1 s) and that lag.
~0.9+ = the same performance (a frozen vocal comes back near-identical); < 0.5 = different audio.
--skip-a / --skip-b drop leading seconds (e.g. the 2 s silent lead-in of an mv_cut.py vocal)."""
import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FFMPEG  # noqa: E402
SR, HOP = 16000, 160


def envelope(path, skip=0.0, seconds=None):
    cmd = [FFMPEG, "-v", "error", "-ss", f"{skip:.3f}", "-i", str(path)] + (["-t", f"{seconds:.3f}"] if seconds else []) + ["-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    pcm = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)
    n = len(pcm) // HOP
    return np.sqrt((pcm[:n * HOP].reshape(n, HOP) ** 2).mean(axis=1) + 1e-12)


def best_match(a, b, max_lag=100):
    """-> (correlation, lag in frames: b is shifted by lag relative to a)"""
    best = (-1.0, 0)
    for lag in range(-max_lag, max_lag + 1):
        x, y = (a[lag:], b) if lag >= 0 else (a, b[-lag:])
        n = min(len(x), len(y))
        if n < 50:
            continue
        c = float(np.corrcoef(x[:n], y[:n])[0, 1])
        if c > best[0]:
            best = (c, lag)
    return best


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")  # the docstring's emoji crashed --help on a cp1252 console
    ap =argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a"); ap.add_argument("b")
    ap.add_argument("--skip-a", type=float, default=0.0); ap.add_argument("--skip-b", type=float, default=0.0)
    ap.add_argument("--seconds", type=float)
    o = ap.parse_args()
    a, b = envelope(o.a, o.skip_a, o.seconds), envelope(o.b, o.skip_b, o.seconds)
    c, lag = best_match(a, b)
    print(f"correlation {c:.3f} at lag {lag * HOP / SR:+.2f} s ({len(a) * HOP / SR:.1f} s vs {len(b) * HOP / SR:.1f} s)")


if __name__ == "__main__":
    main()
