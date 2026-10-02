"""🎵 Put the SONG under a music-video clip (the video model's own audio is no use for a music video): a clip made from a storyboard
frame musicvideos/<id>/sbNN/sN.png plays the song from that frame's t0 for the clip's length, instead of whatever the video
model generated. The model's own audio is kept next to it as <clip>.genaudio.m4a (cheap to keep).
  python tools/mv_audio.py <clip.mp4> [<frame.png>]      (frame defaults to the clip's source image: <clip name before '__'>.png)
Called automatically by run_video.py and lipsync.py for clips of storyboard frames."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FFMPEG, FFPROBE  # noqa: E402


def frame_of(clip: Path):
    return clip.with_name(clip.name.split("__")[0] + ".png")


def song_under(clip, frame=None, at=None):
    """replace clip's audio with the song slice [t0, t0 + clip length]; returns t0 or None when it isn't an mv frame"""
    clip = Path(clip).resolve()
    frame = Path(frame).resolve() if frame else frame_of(clip)
    sb, mvdir = frame.parent, frame.parent.parent
    if not (sb.name.startswith("sb") and (mvdir / "mv.json").exists() and (sb / "chapter.json").exists()):
        return None
    m = json.loads((mvdir / "mv.json").read_text(encoding="utf-8"))
    ch = json.loads((sb / "chapter.json").read_text(encoding="utf-8"))
    sc = next((s for s in ch["scenes"] if s["id"] == frame.stem), None)
    song = ROOT / (m.get("audio") or "")
    if not sc or sc.get("t0") is None or not song.is_file():
        return None
    t0 = float(at) if at is not None else float(sc["t0"])  # `at`: a clip of one line inside a long frame (lip-sync tests)
    dur = float(subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
                               capture_output=True, text=True).stdout.strip() or 0)
    keep = clip.with_suffix(".genaudio.m4a")
    if not keep.exists():  # the model's own sound, once (a re-run must not overwrite it with the song)
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(clip), "-vn", "-c:a", "aac", "-b:a", "160k", str(keep)])
    tmp = clip.with_suffix(".tmp.mp4")
    pre = min(float(sc.get("preroll") or 0), max(0.0, dur - 0.5))
    if pre > 0:  # the video's opening: the model's own sound (needle drop, room tone) for `preroll` s, then the song from t0
        # (e.g. a needle drop or room tone before the song starts)
        fc = (f"[1:a]atrim=0:{pre + 0.3:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo[g];"
              f"[2:a]aresample=48000,aformat=channel_layouts=stereo[s];[g][s]acrossfade=d=0.3:c1=tri:c2=tri,"
              f"atrim=0:{dur:.3f},afade=t=out:st={max(0, dur - 0.08):.3f}:d=0.08[a]")
        cmd = [FFMPEG, "-v", "error", "-y", "-i", str(clip), "-i", str(keep), "-ss", f"{t0:.3f}", "-t", f"{dur - pre + 0.3:.3f}", "-i", str(song),
               "-filter_complex", fc, "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", str(tmp)]
    else:
        cmd = [FFMPEG, "-v", "error", "-y", "-i", str(clip), "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}", "-i", str(song),
               "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
               "-af", "afade=t=in:d=0.04,afade=t=out:st=%.3f:d=0.08" % max(0, dur - 0.08), "-shortest", str(tmp)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("ffmpeg: " + r.stderr[-400:])
    tmp.replace(clip)
    meta = clip.with_suffix(".json")
    if meta.exists():
        d = json.loads(meta.read_text(encoding="utf-8"))
        d.update(song_audio={"from": m["audio"], "t0": t0, "seconds": round(dur, 2), "preroll": pre}, generated_audio=keep.name)
        meta.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
    return t0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    t = song_under(ROOT / sys.argv[1], ROOT / sys.argv[2] if len(sys.argv) > 2 else None)
    print("song under" if t is not None else "not a storyboard clip:", sys.argv[1], "" if t is None else f"from {t:.2f} s")
