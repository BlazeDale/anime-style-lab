"""🪝 Hooks: export each storyboard scene as a standalone widescreen mp4 (for posting one a day on social media or a song page),
cut from the assembled final cut so it carries the headline lower third and the original song in sync.

  python tools/mv_hooks.py musicvideos/NNN-x [s1 s2 ...] [--cut cut/x.mp4] [--pad 0.0] [--join s27,s28]

- default cut: the newest FULL-quality build (cut/<slug>.mp4), else the draft
- scene times come from that build's resolved timeline (cut/<slug>.json "cuts": t0/t1 in video seconds, `frame` = scene id)
- --join s27,s28: one hook spanning consecutive scenes (a multi-shot gag, or a hook that must reach a platform's minimum length)
- writes export/hooks/NN-sX[-sY].mp4 (+ .txt with the scene's headline / lyric / caption for the post) and prints them
"""
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from config import FFMPEG  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mv")
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--cut")
    ap.add_argument("--pad", type=float, default=0.0)
    ap.add_argument("--join", action="append", default=[])
    a = ap.parse_args()
    d = ROOT / a.mv
    cuts = sorted((d / "cut").glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    full = [p for p in cuts if not p.stem.endswith("-draft")]
    cut = (d / a.cut) if a.cut else (full or cuts)[-1]
    tl = json.loads(cut.with_suffix(".json").read_text(encoding="utf-8"))
    pieces = tl["cuts"]
    by = {}
    for p in pieces:
        by.setdefault(p["frame"], p)  # the scene's own (first) piece; borrowed re-uses carry a label
    ch = {}
    for sbd in sorted(d.glob("sb*/chapter.json")):
        for s in json.loads(sbd.read_text(encoding="utf-8")).get("scenes", []):
            ch[s["id"]] = s
    order = [p["frame"] for p in pieces if not p.get("label") or p.get("label") == p["frame"]]
    singles = a.scenes or ([] if a.join else order)  # --join alone exports just those runs
    groups = [g.split(",") for g in a.join] + [[s] for s in singles if not any(s in g.split(",") for g in a.join)]
    out_dir = d / "export" / "hooks"
    out_dir.mkdir(parents=True, exist_ok=True)
    for g in groups:
        g = [s for s in g if s in by]
        if not g:
            continue
        t0, t1 = by[g[0]]["t0"] - a.pad, by[g[-1]]["t1"] + a.pad
        t0, t1 = max(0.0, t0), min(tl["duration"], t1)
        n = order.index(g[0]) + 1 if g[0] in order else 0
        out = out_dir / f"{n:02d}-{'-'.join(g)}.mp4"
        dur = t1 - t0
        subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", str(cut), "-t", f"{dur:.3f}",
                        "-af", f"afade=t=in:d=0.12,afade=t=out:st={max(0, dur - 0.35):.3f}:d=0.35",
                        "-c:v", "libx264", "-crf", "18", "-maxrate", "16M", "-bufsize", "32M", "-preset", "slow", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(out)], check=True)
        sc = [ch.get(s, {}) for s in g]
        out.with_suffix(".txt").write_text("\n".join(filter(None, [
            " / ".join(filter(None, (s.get("headline") for s in sc))),
            " / ".join(filter(None, (s.get("caption") for s in sc))),
            "Lyric: " + " / ".join(filter(None, (s.get("lyric") for s in sc))),
            f"{t0:.2f}-{t1:.2f} s of {cut.name}"])) + "\n", encoding="utf-8")
        print(f"{out.relative_to(ROOT).as_posix()}  {dur:.1f}s  {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
