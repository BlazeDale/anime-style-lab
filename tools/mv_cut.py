"""✂🎤 Cut the vocals for one lip-sync clip (a lip-sync model needs a moment to settle the character before the singing starts, and the
clip must never open mid-word):
  python tools/mv_cut.py musicvideos/NNN-x <start s> <end s> <out.wav> [--lead-in 2.0] [--with-backing] [--exact]
- start snaps to the quietest breath (lowest vocal loudness) in the 0.8 s before the nearest placed lyric line's start, so the clip
  never opens mid-word; end snaps to the quietest point within +-0.6 s of the asked end (or of the line end it falls in);
- the cut is padded with --lead-in seconds of SILENCE in front (the video model gets time to settle into the shot; run_video
  --lead-in trims that much off the finished clip again).
Prints JSON {start, end, lead_in, seconds, out} so the caller can pass --song-at <start>."""
import json
import subprocess
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError:  # checked in main()
    np = None

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
from config import FFMPEG  # noqa: E402
SR, HOP = 16000, 160  # 10 ms loudness frames


def loudness(wav):
    pcm = np.frombuffer(subprocess.run([FFMPEG, "-v", "error", "-i", str(wav), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                       capture_output=True, check=True).stdout, np.float32)
    n = len(pcm) // HOP
    return np.sqrt((pcm[:n * HOP].reshape(n, HOP) ** 2).mean(1))


def quietest(rms, a, b):
    i0, i1 = max(0, int(a * SR / HOP)), min(len(rms), max(int(a * SR / HOP) + 1, int(b * SR / HOP)))
    return (i0 + int(np.argmin(rms[i0:i1]))) * HOP / SR if i1 > i0 else a


def snap(rms, lines, start, end):
    starts = [ln["t0"] for ln in lines]
    s0 = min(starts, key=lambda t: abs(t - start)) if starts else start  # the lyric line that begins nearest the asked start
    s = quietest(rms, s0 - 0.8, s0 + 0.02)
    ends = [ln["t1"] for ln in lines if ln["t1"] > s + 1.0]
    e0 = min(ends, key=lambda t: abs(t - end)) if ends else end
    e = quietest(rms, e0 - 0.3, e0 + 0.6)
    return round(s, 3), round(max(e, s + 1.0), 3)


def main():
    if np is None:
        sys.exit("mv_cut needs numpy: pip install numpy")
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--lead-in"]
    if len(args) != 4:
        sys.exit(__doc__)
    d, start, end, out = ROOT / args[0], float(args[1]), float(args[2]), ROOT / args[3]
    lead = float(sys.argv[sys.argv.index("--lead-in") + 1]) if "--lead-in" in sys.argv else 2.0
    m = json.loads((d / "mv.json").read_text(encoding="utf-8"))
    vox = ROOT / (m.get("vocals") or m.get("audio"))
    if "--with-backing" in sys.argv:  # the singer sings along with the backing vocals: lead + backing stems mixed
        bv = sorted((d / "audio" / "stems").glob("*acking*"))
        if bv:
            mix = d / "audio" / "vocals_with_backing.wav"
            if not mix.exists():
                subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(vox), "-i", str(bv[0]), "-filter_complex",
                                "amix=inputs=2:normalize=0,alimiter=limit=0.95", "-ar", "48000", str(mix)], check=True)
            vox = mix
    lt = d / "audio" / "lyrics_timing.json"
    lines = json.loads(lt.read_text(encoding="utf-8"))["lines"] if lt.exists() else []
    # --exact: keep the asked window (vocals the lyric timing never placed, e.g. a sung intro before the first timed line)
    s, e = (round(start, 3), round(end, 3)) if "--exact" in sys.argv else snap(loudness(vox), lines, start, end)
    out.parent.mkdir(parents=True, exist_ok=True)
    ms = int(lead * 1000)
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{s:.3f}", "-to", f"{e:.3f}", "-i", str(vox), "-ac", "1", "-ar", "48000",
                    "-af", f"afade=t=in:d=0.03,adelay={ms}|{ms},afade=t=out:st={lead + e - s - 0.05:.3f}:d=0.05", str(out)], check=True)
    print(json.dumps({"start": s, "end": e, "lead_in": lead, "seconds": round(lead + e - s, 3), "out": out.relative_to(ROOT).as_posix()}))


if __name__ == "__main__":
    main()
