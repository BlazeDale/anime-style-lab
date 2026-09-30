"""Fix-and-reshoot one journey scene in a single step (edit chapter.json, log the revision, re-render with a new seed).

  .venv/Scripts/python tools/scene_fix.py journeys/015-x/ch01 s4 --why "hands only, no face" \
      [--camera "..."] [--camera-append "..."] [--prompt "..."] [--prompt-append "..."] \
      [--with a,b | --with ""] [--noref | --ref] [--replace OLD NEW] [--sheet-replace OLD NEW] \
      [--no-render] [--dry-run]

Claude writes the creative text; this does the mechanics: edit the scene, append {"scene","date","why"} to the chapter's
`revisions`, then `run_journey.py --reroll <png>` (old png/workflow -> chNN/_rerolled/, new random seed).
--replace applies to camera AND prompt (an error if OLD is in neither). --sheet-replace edits journey.json `character`
(e.g. add "high-necked gown") and is logged in the same revision. Directing rules (every scene has a camera line; a from-behind lead needs noref) show as warnings.
"""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def dump(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def warnings_for(sc):
    w = []
    cam = sc.get("camera", "").lower()
    if not cam:
        w.append("scene has no camera line (every scene should have one)")
    if any(k in cam for k in ("from behind", "back view", "over-the-shoulder", "over the shoulder")) and not sc.get("noref"):
        w.append("camera looks like a from-behind/OTS shot but the scene is not noref: a face ref turns the lead around. "
                 "If the lead faces away use --noref + 'face NOT visible'.")
    if sc.get("noref") and "face" not in (cam + sc.get("prompt", "").lower()):
        w.append("noref scene never says where the face is ('face NOT visible' / 'NO face in frame')")
    return w


def apply(chdir, sid, a):
    """edit chapter.json (+ journey.json) in memory; returns (chapter, scene, changes, journey_edit or None)"""
    chdir = Path(chdir)
    ch = load_json(chdir / "chapter.json")
    sc = next((s for s in ch["scenes"] if s["id"] == sid), None)
    if sc is None:
        raise SystemExit(f"no scene {sid} in {chdir / 'chapter.json'} (has {[s['id'] for s in ch['scenes']]})")
    changes, jedit = [], None
    if a.camera is not None:
        sc["camera"] = a.camera
        changes.append("camera replaced")
    if a.camera_append:
        sc["camera"] = (sc.get("camera", "").rstrip(" .") + "; " + a.camera_append.strip()).lstrip("; ")
        changes.append("camera appended")
    if a.prompt is not None:
        sc["prompt"] = a.prompt
        changes.append("prompt replaced")
    if a.prompt_append:
        sc["prompt"] = sc.get("prompt", "").rstrip() + " " + a.prompt_append.strip()
        changes.append("prompt appended")
    if a.replace:
        old, new = a.replace
        hit = False
        for k in ("camera", "prompt"):
            if old in sc.get(k, ""):
                sc[k] = sc[k].replace(old, new)
                hit = True
                changes.append(f"{k}: replaced {old!r}")
        if not hit:
            raise SystemExit(f"--replace: {old!r} not found in the camera or the prompt of {sid}")
    if a.with_ is not None:
        sc["with"] = [x.strip() for x in a.with_.split(",") if x.strip()]
        changes.append(f"with = {sc['with']}")
    if a.noref:
        sc["noref"] = True
        changes.append("noref on")
    if a.ref:
        sc.pop("noref", None)
        changes.append("noref off (face ref)")
    if a.sheet_replace:
        old, new = a.sheet_replace
        jp = chdir.parent / "journey.json"
        j = load_json(jp)
        if old not in j["character"]:
            raise SystemExit(f"--sheet-replace: {old!r} not found in journey.json character")
        j["character"] = j["character"].replace(old, new)
        changes.append(f"character sheet: {old!r} -> {new!r}")
        jedit = (jp, j)
    if not changes:
        raise SystemExit("nothing to change: give --camera/--prompt/--replace/--with/--noref/--ref/... "
                         "(for a plain reroll use run_journey.py --reroll)")
    why = a.why + (f" [character sheet: {a.sheet_replace[0]!r} -> {a.sheet_replace[1]!r}]" if a.sheet_replace else "")
    ch.setdefault("revisions", []).append({"scene": sid, "date": datetime.date.today().isoformat(), "why": why})
    return ch, sc, changes, jedit


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chapter")
    ap.add_argument("scene")
    ap.add_argument("--why", required=True)
    ap.add_argument("--camera")
    ap.add_argument("--camera-append")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-append")
    ap.add_argument("--with", dest="with_")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--noref", action="store_true")
    g.add_argument("--ref", action="store_true")
    ap.add_argument("--replace", nargs=2, metavar=("OLD", "NEW"))
    ap.add_argument("--sheet-replace", nargs=2, metavar=("OLD", "NEW"))
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    chdir = Path(a.chapter)
    chdir = chdir if chdir.is_absolute() else ROOT / chdir
    ch, sc, changes, jedit = apply(chdir, a.scene, a)
    for c in changes:
        print("  -", c)
    for w in warnings_for(sc):
        print("WARNING:", w)
    print(f"camera: {sc.get('camera', '')}\nprompt: {sc.get('prompt', '')}")
    if a.dry_run:
        print("(dry run: nothing written, nothing rendered)")
        return 0
    dump(chdir / "chapter.json", ch)
    if jedit:
        dump(*jedit)
    if a.no_render:
        print("edited; not rendered (--no-render)")
        return 0
    png = chdir / f"{a.scene}.png"
    try:
        rel = png.resolve().relative_to(ROOT).as_posix()
        chrel = chdir.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        raise SystemExit(f"{png} is outside the project: cannot render")
    cmd = [sys.executable, str(ROOT / "tools" / "run_journey.py")]
    cmd += ["--reroll", rel] if png.exists() else [chrel]
    print("running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
