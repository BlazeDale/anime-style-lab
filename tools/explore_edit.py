"""🌌 Re-steer the story in flight (Apply: steer the current story toward love, battle, tension...; both the story and the
images follow, wrapping up the current events and moving in the new direction).

  python tools/explore_edit.py current                      the episode in flight = the newest episode whose status is not done, with rendered / unrendered
                                                            counts and the unrendered shots (so you know what to rewrite); "none" when everything is done
  python tools/explore_edit.py explore/NNN-slug [--from eK] --shots new_shots.json [--steer-from-state] [--reason "..."]
        replaces EVERY UNRENDERED shot from eK onward (default: the first unrendered shot) with the list in new_shots.json (a JSON list of
        {prompt, caption, aspect?, hold?, seed?}); the new ids continue from the last kept shot (e7, e8, ...). It REFUSES to touch any shot that already has
        a png (the error lists them). --steer-from-state copies the CURRENT steer from feedback/explore.json (presence / emotion / formality) into
        episode.json and onto each new shot as `steer`, so the renderer's steer cue and the story follow the new direction. Every edit appends
        {ts, steer, from, reason, removed, added} to episode.json `steer_log`.
tools/explore_render.py re-reads episode.json before every shot, so an edit made while a render is running takes effect at the next shot (a shot that was
rendering during the edit is set aside in _discarded/ and rendered again from its new text)."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import explore_state  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
STEER_KEYS = ("presence", "emotion", "formality", "cores", "maturity")


class EditError(Exception):
    pass


def _num(shot_id):
    try:
        return int(str(shot_id).lstrip("e"))
    except ValueError:
        return 0


def _load(edir):
    return json.loads((Path(edir) / "episode.json").read_text(encoding="utf-8"))


def _save(edir, ep):
    edir = Path(edir)
    tmp = edir / "episode.json.tmp"
    tmp.write_text(json.dumps(ep, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(edir / "episode.json")


def rendered(edir, shot):
    return (Path(edir) / f"{shot['id']}.png").is_file()


def current(root=None):
    """the episode in flight: newest (highest NNN) whose status is not done -> {id, dir, status, rendered, unrendered, shots: [unrendered]} or None"""
    d = Path(root or ROOT) / "explore"
    files = list(d.glob("*/episode.json")) if d.exists() else []
    files += list(d.glob("sagas/*/ch*/episode.json")) if d.exists() else []  # 📖 saga chapters are episodes too
    def when(f):
        try:
            return str(json.loads(f.read_text(encoding="utf-8")).get("created", ""))
        except (OSError, ValueError):
            return ""
    for f in sorted(files, key=lambda f: (when(f), str(f)), reverse=True):
        try:
            ep = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if ep.get("status", "draft") == "done":
            continue
        shots = ep.get("shots") or []
        un = [s for s in shots if not (f.parent / f"{s['id']}.png").is_file()]
        return {"id": (f.parent.parent.name + "/" if ep.get("saga") else "") + f.parent.name, "dir": str(f.parent), "title": ep.get("title", ""), "status": ep.get("status", "draft"), "rendered": len(shots) - len(un),
                "unrendered": len(un), "shots": [{"id": s["id"], "caption": s.get("caption", ""), "prompt": s.get("prompt", "")} for s in un]}
    return None


def edit(edir, new_shots, from_id=None, steer_state=None, reason="", ts=None):
    """replace every unrendered shot from `from_id` onward; returns {removed, added, from, steer}. Raises EditError (nothing is written) on any problem"""
    import explore_render as er
    edir = Path(edir)
    ep = _load(edir)
    shots = ep.get("shots") or []
    ids = [s["id"] for s in shots]
    if from_id is None:
        first = next((s for s in shots if not rendered(edir, s)), None)
        from_id = first["id"] if first else None
        if from_id is None:
            raise EditError("every shot already has a picture: there is nothing left to rewrite (start the next episode instead)")
    if from_id not in ids:
        raise EditError(f"unknown shot {from_id!r} (this episode has {', '.join(ids)})")
    k = ids.index(from_id)
    keep, tail = shots[:k], shots[k:]
    done = [s["id"] for s in tail if rendered(edir, s)]
    if done:
        raise EditError(f"refusing to modify shot(s) that already have a picture: {', '.join(done)} (start --from the first unrendered shot, or use 🎲 reroll for those)")
    if not isinstance(new_shots, list) or not new_shots:
        raise EditError("new_shots must be a non-empty JSON list of {prompt, caption, ...}")
    base = max([_num(s["id"]) for s in keep] or [0])
    out = []
    bible = None
    if ep.get("saga"):  # 📖 saga chapter: the same checks as saga.py chapter (cast names, dialogue speakers in frame, 0-4 lines)
        import saga
        bible = saga.load(edir.parent)
        errs = []
        for n, s in enumerate(new_shots, 1):
            errs += saga.validate_shot(bible, s, f"new shot #{n}")[0]
        if errs:
            raise EditError("; ".join(errs))
    for n, s in enumerate(new_shots, 1):
        if not isinstance(s, dict) or not str(s.get("prompt", "")).strip():
            raise EditError(f"new shot #{n} has no prompt")
        if not bible and not str(s.get("caption", "")).strip():
            raise EditError(f"new shot #{n} has no caption")
        try:
            er.aspect_name(s.get("aspect"))
        except ValueError as e:
            raise EditError(f"new shot #{n}: {e}")
        ns = saga.normalize_shot(s, base + n) if bible else {k2: v for k2, v in s.items() if k2 not in ("id", "src", "steer")}
        ns["id"] = f"e{base + n}"
        if "steer" in s:
            ns["steer"] = s["steer"]
        out.append(ns)
    steer = None
    if steer_state is not None:
        steer = {k2: steer_state[k2] for k2 in STEER_KEYS if steer_state.get(k2) is not None}
        for k2, v in steer.items():
            ep[k2] = v
        for ns in out:
            ns["steer"] = {**steer, **(ns.get("steer") or {})}
    removed = [{"id": s["id"], "caption": s.get("caption", "")} for s in tail]
    ep["shots"] = keep + out
    if ep.get("status") == "done":
        ep["status"] = "paused"
    ep.setdefault("steer_log", []).append({"ts": ts or time.strftime("%Y-%m-%d %H:%M:%S"), "steer": steer if steer is not None else {k2: ep.get(k2) for k2 in STEER_KEYS if ep.get(k2) is not None},
                                           "from": from_id, "reason": reason, "removed": [r["id"] for r in removed], "added": [s["id"] for s in out]})
    _save(edir, ep)
    return {"removed": removed, "added": [{"id": s["id"], "caption": s.get("caption", "")} for s in out], "from": from_id, "steer": steer, "kept": [s["id"] for s in keep]}


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = list(argv)
    if not args or args[0] in ("-h", "--help"):
        sys.exit(__doc__)
    if args[0] == "current":
        c = current()
        if not c:
            print("none: every episode is done (start the next one if exploring is still active)")
            return
        print(f"{c['id']}  [{c['status']}]  {c['rendered']} rendered / {c['unrendered']} unrendered  {c['title']}  ({Path(c['dir']).relative_to(ROOT).as_posix() if Path(c['dir']).is_relative_to(ROOT) else c['dir']})")
        for s in c["shots"]:
            print(f"  {s['id']}  {s['caption']}")
        return

    def opt(name):
        if name in args:
            i = args.index(name)
            v = args[i + 1] if i + 1 < len(args) else None
            del args[i:i + 2]
            return v
        return None

    from_id, shots_file, reason = opt("--from"), opt("--shots"), opt("--reason") or ""
    steer_flag = "--steer-from-state" in args
    if steer_flag:
        args.remove("--steer-from-state")
    if len(args) != 1 or not shots_file:
        sys.exit(__doc__)
    edir = Path(args[0])
    edir = edir if edir.is_absolute() else ROOT / edir
    try:
        new = json.loads(Path(shots_file).read_text(encoding="utf-8"))
        st = explore_state.state() if steer_flag else None
        res = edit(edir, new, from_id, st, reason)
    except (EditError, OSError, ValueError) as e:
        sys.exit(f"explore_edit: {e}")
    print(f"{edir.name}: kept {len(res['kept'])} shot(s); removed {len(res['removed'])} unrendered, added {len(res['added'])}" + (" (steer copied from the explore state)" if res["steer"] is not None else ""))
    for r in res["removed"]:
        print(f"  - {r['id']}  {r['caption']}")
    for a in res["added"]:
        print(f"  + {a['id']}  {a['caption']}")


if __name__ == "__main__":
    main(sys.argv[1:])
