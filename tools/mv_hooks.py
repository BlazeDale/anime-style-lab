"""🪝 Hooks: export each storyboard scene as a standalone widescreen mp4 (for posting one a day on social media or a song page),
cut from the assembled final cut so it carries the headline lower third and the original song in sync.

  python tools/mv_hooks.py musicvideos/NNN-x [s1 s2 ...] [--cut cut/x.mp4] [--pad 0.0] [--join s27,s28]

- default cut: the newest FULL-quality build (cut/<slug>.mp4), else the draft
- scene times come from that build's resolved timeline (cut/<slug>.json "cuts": t0/t1 in video seconds, `frame` = scene id)
- --join s27,s28: one hook spanning consecutive scenes (a multi-shot gag, or a hook that must reach a platform's minimum length)
- writes export/hooks/NN-sX[-sY].mp4 (+ .txt with the scene's headline / lyric / caption for the post) and prints them
--auto (the page's "🪝 Build for Hooks"): the WHOLE song split into consecutive 10-30 s hooks without cutting interesting scenes or
vocals, same aspect as the cut. Boundaries prefer a scene change that falls between sung lines (lyrics_timing.json, or the quiet moments
of the isolated vocal); a cut inside a scene is only used in a vocal gap; mid-line is the last resort.
-> export/hooks/auto/NN_<m>m<ss>-<m>m<ss>.mp4 + .txt + hooks.json (the folder is replaced on every build).
"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from config import FFMPEG  # noqa: E402

HOOK_MIN, HOOK_MAX, HOOK_AIM = 10.0, 30.0, 20.0
PEN_MIDLINE, PEN_IN_SCENE, GUARD = 10.0, 4.0, 0.15


def in_line(t, lines, guard=GUARD):
    return any(a - guard < t < b + guard for a, b in lines)


def vocal_spans(path, offset=0.0, rel_db=28.0, hop=0.02, bridge=0.10, min_len=0.06):
    """Where the singer is actually making sound: [(t0, t1)] in video seconds (song time + offset), from the isolated vocal track's
    RMS envelope (voiced = within rel_db of the loud frames' level; gaps shorter than `bridge` are joined). Lyric-line timings can't do
    this: the aligner stretches lines end to end (no gaps at all between short sung words)."""
    import numpy as np
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    n = int(16000 * hop)
    if len(x) < n:
        return []
    fr = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    on = db > np.percentile(db, 95) - rel_db
    spans, start = [], None
    for i, v in enumerate(on):
        if v and start is None:
            start = i
        elif not v and start is not None:
            spans.append([start * hop, i * hop]); start = None
    if start is not None:
        spans.append([start * hop, len(on) * hop])
    merged = []
    for a, b in spans:
        if merged and a - merged[-1][1] < bridge:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(a + offset, b + offset) for a, b in merged if b - a >= min_len]


def vocal_dips(path, offset=0.0, hop=0.02, smooth=3, bin_s=1.0):
    """The quietest instant of every `bin_s` window of the vocal track: [(t, level 0..1)] in video seconds (0 = as quiet as the track
    gets, 1 = as loud as its loud frames). For dense vocals with no real pauses (one long sung monologue): cutting at the dip
    between two words is far better than mid-word."""
    import numpy as np
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    n = int(16000 * hop)
    if len(x) < n * 4:
        return []
    fr = x[: len(x) // n * n].reshape(-1, n)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(axis=1)) + 1e-9)
    db = np.convolve(db, np.ones(smooth) / smooth, mode="same")
    hi = np.percentile(db, 95)
    lev = np.clip((db - (hi - 40.0)) / 40.0, 0, 1)  # 0 = 40 dB or more below the loud level, 1 = the loud level
    # a cut needs the moment AROUND it quiet: env = the loudest level within +-60 ms (a 20 ms consonant closure inside a word is not a gap)
    r = 3
    pad = np.pad(lev, r, mode="edge")
    env = np.max(np.stack([pad[i:i + len(lev)] for i in range(2 * r + 1)]), axis=0)
    per = max(1, int(bin_s / hop))
    out = []
    for s in range(0, len(env), per):
        k = s + int(np.argmin(env[s:s + per]))
        out.append((round(k * hop + offset, 3), float(env[k])))

    def level_at(t):
        k = int(round((t - offset) / hop))
        return float(env[k]) if 0 <= k < len(env) else 0.0
    return out, level_at


def plan_hooks(scene_starts, lines, total, lo=HOOK_MIN, hi=HOOK_MAX, aim=HOOK_AIM, guard=GUARD, min_gap=0.6, dips=(), level_at=None):
    """Split [0, total] (video seconds) into consecutive hooks of lo..hi s. scene_starts = where each scene begins; lines = sung spans
    [(t0, t1)] in video seconds (lyric lines, or vocal_spans with a smaller guard / min_gap). Candidates: scene starts (free outside the
    sung spans, PEN_MIDLINE inside one), the middle of every vocal gap >= min_gap that is not near a scene start (PEN_IN_SCENE: it splits
    a scene) and a 2 s last-resort grid. Dynamic programming minimises the penalties plus ((len - aim) / 10)^2 per hook. Relaxes the
    limits if no split fits. Returns [(t0, t1)]."""
    lines = sorted((float(a), float(b)) for a, b in lines if b > a)
    cand = {}
    for t in scene_starts:  # with the vocal envelope (level_at): free when quiet there, scaled up to PEN_MIDLINE at full voice
        if 0 < t < total:
            if not in_line(t, lines, guard):
                cand[round(float(t), 3)] = 0.0
            else:
                lv = level_at(t) if level_at else 1.0
                cand[round(float(t), 3)] = 0.0 if lv < 0.15 else PEN_MIDLINE * lv
    gaps = [(b1, a2) for (_, b1), (a2, _) in zip(lines, lines[1:]) if a2 - b1 >= min_gap]
    if lines:
        gaps = [(0.0, lines[0][0])] + gaps + [(lines[-1][1], total)]
    for a, b in gaps:
        if b - a >= min_gap:
            m = round((a + b) / 2, 3)
            if 0 < m < total and not any(abs(m - s) < 1.0 for s in cand):
                cand[m] = PEN_IN_SCENE
    for t, level in dips:  # the quiet moment between two words (vocal_dips): PEN_IN_SCENE when silent .. PEN_MIDLINE at full voice
        if 0 < t < total and not any(abs(t - s) < 0.5 for s in cand):
            cand[round(t, 3)] = PEN_IN_SCENE + 1 + (PEN_MIDLINE - PEN_IN_SCENE) * level
    t = 2.0  # last resort: a 2 s grid, so a stretch with no scene change or gap can still be split (mid-scene, maybe mid-line)
    while t < total - 1.0:
        if not any(abs(t - s) < 1.0 for s in cand):
            cand[round(t, 3)] = PEN_MIDLINE + 2 if in_line(t, lines, guard) else PEN_IN_SCENE + 2
        t += 2.0
    pts = [0.0] + sorted(cand) + [float(total)]
    pen = [0.0] + [cand[t] for t in sorted(cand)] + [0.0]
    for lo_, hi_ in ((lo, hi), (lo, hi * 1.5), (lo / 2, hi * 2)):
        best, prev = [0.0] + [None] * (len(pts) - 1), [None] * len(pts)
        for j in range(1, len(pts)):
            for i in range(j):
                ln = pts[j] - pts[i]
                if best[i] is None or not lo_ <= ln <= hi_:
                    continue
                c = best[i] + pen[j] + ((ln - aim) / 10) ** 2
                if best[j] is None or c < best[j]:
                    best[j], prev[j] = c, i
        if best[-1] is not None:
            out, j = [], len(pts) - 1
            while j:
                out.append((pts[prev[j]], pts[j]))
                j = prev[j]
            return out[::-1]
    n = max(1, round(total / aim))  # nothing fits (a very short song): even pieces
    return [(total * k / n, total * (k + 1) / n) for k in range(n)]


def mmss(t):
    return f"{int(t // 60)}m{int(t % 60):02d}"


def encode_hook(cut, t0, t1, out):
    dur = t1 - t0
    subprocess.run([FFMPEG, "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", str(cut), "-t", f"{dur:.3f}",
                    "-af", f"afade=t=in:d=0.12,afade=t=out:st={max(0, dur - 0.35):.3f}:d=0.35",
                    "-c:v", "libx264", "-crf", "18", "-maxrate", "16M", "-bufsize", "32M", "-preset", "slow", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(out)], check=True)


def auto_hooks(d, cut, status=None, dry_run=False, rel_db=28.0):
    """🪝 the whole cut as 10-30 s hooks (see the module doc). cut = a full build (its .json timeline gives scene starts + preroll).
    dry_run: print the plan (span, length, why each boundary) and write nothing."""
    d, cut = Path(d), Path(cut)
    tl = json.loads(cut.with_suffix(".json").read_text(encoding="utf-8"))
    P, total = float(tl.get("preroll") or 0), float(tl["duration"])
    starts = [c["t0"] for c in tl["cuts"] if not c.get("label") or c.get("label") == c["frame"]]
    lt = d / "audio" / "lyrics_timing.json"
    lines = [(l["t0"] + P, l["t1"] + P, l.get("text", "")) for l in (json.loads(lt.read_text(encoding="utf-8")).get("lines", []) if lt.exists() else [])
             if l.get("t0") is not None and l.get("t1") is not None]
    mv = json.loads((d / "mv.json").read_text(encoding="utf-8")) if (d / "mv.json").exists() else {}
    voc = ROOT / mv["vocals"] if mv.get("vocals") else None
    if voc and voc.is_file():  # real silences in the isolated vocal (breaths count): a tight guard is enough
        sung, guard, min_gap, src = vocal_spans(voc, P, rel_db=rel_db), 0.06, 0.25, "vocal track"
        dips, level_at = vocal_dips(voc, P)
    else:
        sung, guard, min_gap, src, dips, level_at = [(a, b) for a, b, _ in lines], GUARD, 0.6, "lyric lines", [], None
    plan = plan_hooks(starts, sung, total, guard=guard, min_gap=min_gap, dips=dips, level_at=level_at)
    if dry_run:
        gl = [a2 - b1 for (_, b1), (a2, _) in zip(sung, sung[1:])]
        print(f"vocals from the {src}: {len(sung)} sung spans, gaps >= {min_gap} s: {sum(g >= min_gap for g in gl)}, >= 1 s: {sum(g >= 1 for g in gl)}")
        for n, (t0, t1) in enumerate(plan, 1):
            dl = dict(dips).get(round(t1, 3))
            sc = any(abs(t1 - s) < 1e-3 for s in starts)
            lv = level_at(t1) if level_at else None
            kind = ("end" if t1 >= total - 1e-6 else ("scene change" if sc else "in a scene") + (", in a vocal gap" if not in_line(t1, sung, guard)
                    else f", quietest point there ({40 * (1 - lv):.0f} dB under her voice)" if lv is not None else ", MID-VOCAL"))
            print(f"{n:02d}  {mmss(t0)} -> {mmss(t1)}  {t1 - t0:5.1f}s  ends at: {kind}")
        return [{"n": n, "t0": a, "t1": b} for n, (a, b) in enumerate(plan, 1)]
    ch = {}
    for sbd in sorted(d.glob("sb*/chapter.json")):
        for s in json.loads(sbd.read_text(encoding="utf-8")).get("scenes", []):
            ch[s["id"]] = s
    out_dir = d / "export" / "hooks" / "auto"
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True)
    index = []
    for n, (t0, t1) in enumerate(plan, 1):
        if status:
            status(f"hook {n}/{len(plan)}")
        out = out_dir / f"{n:02d}_{mmss(t0)}-{mmss(t1)}.mp4"
        encode_hook(cut, t0, t1, out)
        frames = [c["frame"] for c in tl["cuts"] if c["t0"] < t1 - 0.05 and c["t1"] > t0 + 0.05]
        heads = list(dict.fromkeys(ch.get(f, {}).get("headline") for f in frames if ch.get(f, {}).get("headline")))
        sung = [x for a, b, x in lines if a < t1 and b > t0 and x]
        out.with_suffix(".txt").write_text("\n".join(filter(None, [" / ".join(heads), "Lyric: " + " / ".join(sung) if sung else "",
                                                                   f"{t0:.2f}-{t1:.2f} s of {cut.name}"])) + "\n", encoding="utf-8")
        index.append({"n": n, "file": out.name, "t0": round(t0, 3), "t1": round(t1, 3), "frames": list(dict.fromkeys(frames)),
                      "headlines": heads, "lyric": sung, "mb": round(out.stat().st_size / 1e6, 1)})
        print(f"{(out.relative_to(ROOT) if out.is_relative_to(ROOT) else out).as_posix()}  {t1 - t0:.1f}s  {out.stat().st_size / 1e6:.1f} MB")
    (out_dir / "hooks.json").write_text(json.dumps({"from": cut.name, "hooks": index}, indent=1, ensure_ascii=False), encoding="utf-8")
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mv")
    ap.add_argument("scenes", nargs="*")
    ap.add_argument("--cut")
    ap.add_argument("--pad", type=float, default=0.0)
    ap.add_argument("--join", action="append", default=[])
    ap.add_argument("--auto", action="store_true", help="the whole song as 10-30 s hooks -> export/hooks/auto/")
    ap.add_argument("--dry-run", action="store_true", help="--auto: print the split, write nothing")
    ap.add_argument("--rel-db", type=float, default=28.0, help="--auto: vocal counts as sung within this many dB of its loud level")
    a = ap.parse_args()
    d = ROOT / a.mv
    cuts = sorted((d / "cut").glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    full = [p for p in cuts if not p.stem.endswith(("-draft", "-suno"))]
    cut = (d / a.cut) if a.cut else (full or cuts)[-1]
    if a.auto:
        auto_hooks(d, cut, dry_run=a.dry_run, rel_db=a.rel_db)
        return
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
        encode_hook(cut, t0, t1, out)
        sc = [ch.get(s, {}) for s in g]
        out.with_suffix(".txt").write_text("\n".join(filter(None, [
            " / ".join(filter(None, (s.get("headline") for s in sc))),
            " / ".join(filter(None, (s.get("caption") for s in sc))),
            "Lyric: " + " / ".join(filter(None, (s.get("lyric") for s in sc))),
            f"{t0:.2f}-{t1:.2f} s of {cut.name}"])) + "\n", encoding="utf-8")
        print(f"{out.relative_to(ROOT).as_posix()}  {dur:.1f}s  {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
