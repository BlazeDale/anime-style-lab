"""🧹 Disk housekeeping: keeps disk use bounded without losing the lessons from bad generations.

Deletes only heavy media, never the lesson: before a file goes, its record is appended to feedback/discards.jsonl
{path, kind, why, bytes, mtime, deleted, meta (the clip's sidecar: prompt/engine/seed... | the image's prompt texts), marks, comments}
and a small preview is kept in feedback/discards/<id>.jpg (320 px image / a 4-frame strip for a clip).

  python tools/housekeeping.py [--dry-run] [--rev-days 30] [--nope-days 7]

- revisions: files in evolutions/journeys/musicvideos **/_rerolled/ older than --rev-days (🕘 compare/restore keeps working for newer ones)
- 👎 clips: .mp4 marked nope in feedback/state.json, the mark older than --nope-days (+ the clip's .json / .genaudio.m4a)
serve_gallery runs it once a day. Never touches ComfyUI's output folder.
"""
import argparse, hashlib, json, subprocess, sys, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
FB = ROOT / "feedback"
LOG, PREV = FB / "discards.jsonl", FB / "discards"
AREAS = ("evolutions", "journeys", "musicvideos")


def load(p, d):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return d


def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def prompts_of(workflow):
    """the human text inside a saved API graph (prompt / text inputs), not the whole graph"""
    g = load(workflow, {})
    out = []
    for n in (g.values() if isinstance(g, dict) else []):
        for k, v in ((n or {}).get("inputs") or {}).items() if isinstance(n, dict) else []:
            if isinstance(v, str) and len(v) > 25 and k in ("text", "prompt", "positive", "value", "string"):
                out.append(v)
    return out


def preview(src, dst):
    from config import FFMPEG
    vf = "thumbnail=12,scale=160:-1,tile=4x1" if src.suffix == ".mp4" else "scale=320:-1"  # a clip: 4 representative frames in a row
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-vf", vf, "-frames:v", "1", "-q:v", "5", str(dst)], capture_output=True)


def comments_for(key, cm, before=None):
    out = [c for c in cm if c.get("target") == "image:" + key]
    return [{"who": c.get("author"), "ts": c.get("ts"), "text": c.get("text")} for c in out if not before or (c.get("ts") or "") <= before]


def record_and_delete(files, kind, why, key, meta, marks, comments, dry):
    main = files[0]
    size = sum(f.stat().st_size for f in files if f.exists())
    if dry:
        return size
    PREV.mkdir(parents=True, exist_ok=True)
    rid = hashlib.sha1(f"{rel(main)}|{main.stat().st_mtime}".encode()).hexdigest()[:12]
    try:
        preview(main, PREV / f"{rid}.jpg")
    except Exception:
        pass
    rec = {"id": rid, "path": rel(main), "key": key, "kind": kind, "why": why, "bytes": size,
           "mtime": datetime.fromtimestamp(main.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"), "deleted": time.strftime("%Y-%m-%d %H:%M:%S"),
           "meta": meta, "marks": marks, "comments": comments, "preview": f"feedback/discards/{rid}.jpg"}
    with LOG.open("a", encoding="utf-8") as fh:  # the lesson is written BEFORE anything is deleted
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    for f in files:
        if f.exists():
            f.unlink()
        th = ROOT / ".thumbs" / rel(f)  # its cached thumbnail too
        for t in (th, th.with_suffix(".webp")):
            if t.exists():
                t.unlink()
    return size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rev-days", type=float, default=30)
    ap.add_argument("--nope-days", type=float, default=7)
    a = ap.parse_args()
    now, state, cm = time.time(), load(FB / "state.json", {}), load(FB / "comments.json", [])
    freed, n = 0, 0
    # 1) old revisions in _rerolled/
    for area in AREAS:
        for d in (ROOT / area).rglob("_rerolled"):
            for f in sorted(d.iterdir()):
                if not f.is_file() or f.suffix not in (".png", ".mp4") or now - f.stat().st_mtime < a.rev_days * 86400:
                    continue
                stem, _, stamp = f.stem.partition("__")  # s22__YYYYMMDD-HHMMSS.png | clip names keep their own name
                orig = d.parent / (f"{stem}{f.suffix}" if stamp and stamp[:8].isdigit() else f.name)
                key = rel(orig) if orig.parent.exists() else rel(f)
                group = [f]
                if f.suffix == ".png":
                    wf = d / f"{stem}.workflow__{stamp}.json"
                    group.append(wf) if wf.exists() else None
                    meta = {"prompts": prompts_of(wf)} if wf.exists() else {}
                else:
                    group += [p for p in (f.with_suffix(".json"), f.with_name(f.stem + ".genaudio.m4a")) if p.exists()]
                    meta = load(f.with_suffix(".json"), {})
                before = f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]} {stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}" if stamp[:8].isdigit() else None
                freed += record_and_delete(group, "revision", f"replaced, older than {a.rev_days:g} days", key, meta,
                                           state.get(key), comments_for(key, cm, before), a.dry_run)
                n += 1
    # 2) 👎 clips
    for key, m in state.items():
        acts = m.get("actions") or [m.get("action")]
        if not key.endswith(".mp4") or "nope" not in acts:
            continue
        f = ROOT / key
        try:
            age = now - time.mktime(time.strptime(m.get("ts", ""), "%Y-%m-%d %H:%M:%S"))
        except ValueError:
            age = now - f.stat().st_mtime if f.exists() else 0
        if not f.exists() or age < a.nope_days * 86400:
            continue
        group = [f] + [p for p in (f.with_suffix(".json"), f.with_name(f.stem + ".genaudio.m4a")) if p.exists()]
        freed += record_and_delete(group, "nope-clip", f"marked 👎 over {a.nope_days:g} days ago", key, load(f.with_suffix(".json"), {}),
                                   m, comments_for(key, cm), a.dry_run)
        n += 1
    print(f"{'would free' if a.dry_run else 'freed'} {freed / 1e6:.1f} MB in {n} item(s)" + ("" if a.dry_run else f"; lessons in {rel(LOG)}"))


if __name__ == "__main__":
    main()
