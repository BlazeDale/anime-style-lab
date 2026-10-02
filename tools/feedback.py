"""Read / answer the user's gallery marks (feedback/state.json).

  python tools/feedback.py list [pending|sent|done]     default: sent
  python tools/feedback.py reply <img-path> "<text>"    marks it done with a reply shown in the gallery
  python tools/feedback.py comments                     threads whose last message is the user's (awaiting reply)
  python tools/feedback.py creply <target> "<text>"     reply in a comment thread (target e.g. general, round:2)
  python tools/feedback.py sets                         submitted 📌 sets (evolve = 1 image, cross = 2+) still waiting
  python tools/feedback.py sreply <set-id> "<text>"     marks a set done; the reply also shows on each of its images
  python tools/feedback.py journeys                     🧭 journey requests still waiting (start = new journey, direct = next chapter, animate = reel of a chapter)
  python tools/feedback.py jreply <req-id> "<text>"     marks a journey request done; the reply shows on the journey page
  python tools/feedback.py mvs                          🎵 music-video submissions still waiting (title, text, refs / lyrics / markers / audio summary)
  python tools/feedback.py mvreply <req-id> "<text>"    marks a music-video request done; the reply shows on the music-video page
  python tools/feedback.py mvgen <mv-id> <req-id> <png> ["reply"]   🖼 closes a reference request with the rendered png (adds it to the mv's refs)
  python tools/feedback.py explore                      🌌 explore state (active / time left) + episodes + the unhandled start/continue request
  python tools/feedback.py explorereply "<text>"        marks the latest 🌌 start/continue request handled (also handled once an episode newer than it exists)
  python tools/feedback.py inbox                        unhandled marks + open threads (run by the prompt hooks)
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "feedback" / "state.json"
COMMENTS = ROOT / "feedback" / "comments.json"
SETS = ROOT / "feedback" / "sets.json"
JOURNEYS = ROOT / "feedback" / "journeys.json"
MVS = ROOT / "feedback" / "mvs.json"
MVD = ROOT / "musicvideos"
LOGF = ROOT / "feedback" / "log.jsonl"
EXPLORE_HANDLED = ROOT / "feedback" / "explore_handled.json"  # {ts: "YYYY-mm-dd HH:MM:SS" of the newest request that was answered, text}


def explore_pending(root=None):
    """🌌 the newest unhandled explore request, or None: a start / continue (plan + render an episode) or, once nothing newer is pending, a TUNE = Apply = "re-steer the
    story in flight". Only while exploring is active (a stopped / timed-out request is moot).
    Handled = explorereply ran after it; a start / continue is also handled once an episode with created >= its ts exists, a tune once an episode's steer_log has an
    entry with ts >= its ts (tools/explore_edit.py wrote one)."""
    root = Path(root or ROOT)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import explore_state
    if not explore_state.state(root / "feedback" / "explore.json")["active"]:
        return None
    lf = root / "feedback" / "log.jsonl"
    if not lf.exists():
        return None
    with open(lf, "rb") as f:  # only the tail: the log is big
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 400000))
        lines = f.read().decode("utf-8", "replace").splitlines()
    ev = tune = None
    for ln in lines:
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if e.get("event") == "explore" and e.get("kind") in ("start", "continue"):
            ev = e
        elif e.get("event") == "explore" and e.get("kind") == "tune":
            tune = e
    h = {}
    try:
        h = json.loads((root / "feedback" / "explore_handled.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass

    def steered(ts):
        for f in [*(root / "explore").glob("*/episode.json"), *(root / "explore").glob("sagas/*/ch*/episode.json")]:
            try:
                if any(str(x.get("ts", "")) >= str(ts) for x in json.loads(f.read_text(encoding="utf-8")).get("steer_log") or []):
                    return True
            except (OSError, ValueError):
                pass
        return False

    if ev and str(h.get("ts", "")) < str(ev.get("ts", "")) and not any(str(e.get("created", "")) >= str(ev.get("ts", "")) for e in explore_state.episodes(root)):
        return ev
    if tune and str(h.get("ts", "")) < str(tune.get("ts", "")) and not steered(tune.get("ts", "")):
        return tune
    return None


def mv_summary(x):
    """one line about the music video a request is for: title, refs, lyric lines, markers, audio/vocals present"""
    try:
        m = json.loads((MVD / x["mv"] / "mv.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "(mv.json missing)"
    lines = [l for l in (m.get("lyrics") or "").splitlines() if l.strip()]
    return (f"\"{m.get('title', '')}\": {len(m.get('refs') or [])} refs, {len(lines)} lyric lines, {len(m.get('markers') or [])} markers, "
            f"audio {'yes' if m.get('audio') else 'no'}, vocals {'yes' if m.get('vocals') else 'no'}"
            + (", idea set" if (m.get("idea") or "").strip() else ", no idea text")
            + (f", {len(m['stems'])} stems (direct with: python tools/mv_stems.py musicvideos/{x['mv']} --summary)" if m.get("stems") else "")
            + (", lyrics timed (audio/lyrics_timing.json)" if (MVD / x["mv"] / "audio" / "lyrics_timing.json").exists() else ""))


def open_gen(only=None):
    """🖼 open reference requests (mv.json gen_requests with status open): [(mv id, request)]"""
    out = []
    for d in sorted(MVD.glob("*/mv.json")) if MVD.exists() else []:
        if only and d.parent.name != only:
            continue
        try:
            m = json.loads(d.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out += [(d.parent.name, g) for g in m.get("gen_requests") or [] if g.get("status") == "open"]
    return out


def gen_line(mv, g):
    return f"🖼 ref request {mv} {g['id']} for {g.get('for') or 'the singer'}: {g['text']}" + (f"  [from {g['src']}: render with --ref {g['src']}]" if g.get("src") else "")


def mvgen(mv, rid, png, reply=""):
    """close a reference request: status done + result png (+ reply), add the png to the mv's refs with note/for, rebuild the gallery"""
    p = MVD / mv / "mv.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    g = next((x for x in m.get("gen_requests") or [] if x["id"] == rid), None)
    if g is None:
        sys.exit(f"no request {rid} in {mv}")
    f = Path(png)
    f = f if f.is_absolute() else ROOT / f
    if not f.is_file():
        sys.exit(f"no such image: {png}")
    rel = f.resolve().relative_to(ROOT).as_posix()
    g.update(status="done", result=rel, reply=reply, done_ts=time.strftime("%Y-%m-%d %H:%M:%S"))
    if rel not in (m.get("refs") or []):
        m["refs"] = (m.get("refs") or []) + [rel]
    m.setdefault("ref_notes", {})[rel] = g["text"]
    if g.get("for") and g["for"] in (m.get("cast") or {}):
        m.setdefault("ref_for", {})[rel] = g["for"]
    write(p, m)
    return rel


def rebuild():
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_gallery.py")], cwd=ROOT, check=False)


def expand_refs(text):
    """gallery '@095/v02/f-scifi@azeroth2~1' references -> '@095/v02/f-scifi@azeroth2~1 [evolutions/.../file.png]'"""
    import re

    def one(m):
        lin, ver, name = m.group(1), m.group(2), m.group(3)
        hits = sorted(ROOT.glob(f"evolutions/{lin}-*/{ver}/{name}.png")) + sorted(ROOT.glob(f"evolutions/{lin}-*/{ver}/{name}_seed*.png"))
        return m.group(0) + (f" [{hits[0].relative_to(ROOT).as_posix()}]" if hits else " [not found]")
    return re.sub(r"@(\d{3})/(v\d\d)/([^\s\[\]]+)", one, text or "")


def write(path, obj):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def load():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    state = load()
    if cmd == "list":
        want = sys.argv[2] if len(sys.argv) > 2 else "sent"
        for k, v in state.items():
            if v.get("status") == want:
                print(f"{'+'.join(v.get('actions') or [v.get('action', '')]):12} {k}  {v.get('cap', '')}" + (f"\n        note: {v['note']}" if v.get("note") else ""))
    elif cmd == "reply":
        key, text = sys.argv[2], sys.argv[3]
        # handled: drop the one-shot requests (🎬 🌱 🧬 👥) so a later mark doesn't resend them; ❤/👎 stay
        keep = [x for x in state[key].get("actions", []) if x in ("love", "nope")]
        state[key].update(status="done", reply=text, replied=time.strftime("%Y-%m-%d %H:%M:%S"), actions=keep,
                          action=keep[0] if keep else "note")
        tmp = STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(STATE)
        print("ok")
    elif cmd == "comments":
        comments = json.loads(COMMENTS.read_text(encoding="utf-8")) if COMMENTS.exists() else []
        last = {}
        for c in comments:
            last[c["target"]] = c
        for target, c in last.items():
            if c["author"] == "you":
                print(f"[{target}]")
                for m in [m for m in comments if m["target"] == target][-4:]:
                    print(f"  {m['author']:6} {m['text']}")
    elif cmd == "inbox":  # hook output: everything still waiting on Claude; silent when empty
        sys.stdout.reconfigure(encoding="utf-8")
        comments = json.loads(COMMENTS.read_text(encoding="utf-8")) if COMMENTS.exists() else []
        last = {}
        for c in comments:
            last[c["target"]] = c
        marks = [(k, v) for k, v in state.items() if v.get("status") == "sent"]
        open_c = [c for c in last.values() if c["author"] == "you"]
        open_s = [x for x in (json.loads(SETS.read_text(encoding="utf-8")) if SETS.exists() else []) if x["status"] == "sent"]
        open_j = [x for x in (json.loads(JOURNEYS.read_text(encoding="utf-8")) if JOURNEYS.exists() else []) if x["status"] == "sent"]
        open_m = [x for x in (json.loads(MVS.read_text(encoding="utf-8")) if MVS.exists() else []) if x["status"] == "sent"]
        open_g = open_gen()
        try:
            xp = explore_pending()
        except ImportError:
            xp = None
        try:
            import atlas as fatl
            atl = fatl.open_requests(ROOT)
        except ImportError:  # the Nev Novel tools are optional
            atl = []
        if not marks and not open_c and not open_s and not open_j and not open_m and not open_g and not xp and not atl:
            return
        for r in atl:
            kd = r.get("atlas", "formality")
            extra = " --beats \"...\"" if kd == "emotion" else ""
            print(f"🧠 atlas_add {r['id']} ({r['ts']}): the user typed the {kd} \"{r['text']}\" and the {kd} atlas has no node for it -> `python tools/atlas.py {kd} near \"{r['text']}\"` "
                  f"first (never duplicate), else `atlas.py {kd} add \"<name>\" --family F --features k=v,... --picture \"...\" --voice \"...\"{extra} --for {r['id']}` (CLAUDE.md 'Nev Novel' → Atlases).")
        if xp:
            if xp["kind"] == "tune":
                print(f"📖 Nev Novel re-steer requested at {xp['ts']} [{__import__('explore_state').describe(xp, True)}]: `python tools/explore_edit.py current`; if a chapter/episode is still in flight, rewrite its "
                      "UNRENDERED shots so the story wraps up the current thread in 1-3 shots and turns toward the new steer (explore_edit.py ... --steer-from-state); if nothing is "
                      "running it steers the next chapter (CLAUDE.md 'Nev Novel'), then `feedback.py explorereply \"...\"`.")
            else:
                print(f"📖 Nev Novel {xp['kind']} requested at {xp['ts']}" + (f" (seed: {xp['seed']})" if xp.get("seed") else "") + f" [{__import__('explore_state').describe(xp, True)}]"
                      + ": a start with a seed = `python tools/saga.py new ...` (invent the world, lore, cast), a continue = `saga.py bible --brief` then the next chapter; ONE chapter at a time while `python tools/explore_state.py active` exits 0 (CLAUDE.md 'Nev Novel'), then `feedback.py explorereply \"...\"`.")
        print(f"GALLERY INBOX: {len(open_j)} 🧭 journey request(s), {len(open_m)} 🎵 music-video request(s), {len(open_g)} 🖼 reference request(s), {len(open_s)} 📌 set(s), {len(marks)} sent mark(s) and {len(open_c)} comment thread(s) "
              "are waiting on you. Act on them (see CLAUDE.md 'User feedback' / 'Journeys' / 'Music videos'), then reply with tools/feedback.py reply / creply / sreply / jreply / mvreply / mvgen.")
        for x in open_m:
            print(f"  music video {x['id']} {x['mv']}: {mv_summary(x)}" + (f"  text: {x['text']}" if x.get("text") else ""))
        for mv, g in open_g:
            print("  " + gen_line(mv, g))
        for x in open_j:
            print(f"  journey {x['id']} {x['kind']}: {x.get('image') or x.get('journey')}" + (f" {x['chapter']}" if x.get("chapter") else "") + (f"  text: {expand_refs(x['text'])}" if x["text"] else ""))
        for x in open_s:
            print(f"  set {x['id']} {x['kind']} ({x.get('count', 3)} variations): {' × '.join(x['images'])}" + (f"  directions: {expand_refs(x['directions'])}" if x["directions"] else ""))
        for k, v in marks:
            print(f"  mark {'+'.join(v.get('actions') or [v.get('action', '')])}: {k}" + (f"  note: {v['note']}" if v.get("note") else ""))
        for c in open_c:
            print(f"  comment [{c['target']}] {c['ts']}: {c['text']}")
    elif cmd == "explore":
        sys.stdout.reconfigure(encoding="utf-8")
        import explore_state
        st = explore_state.state()
        print(f"steer: {explore_state.describe(st, True)}")
        print(f"explore: {'ACTIVE, ' + str(int(st['left'] // 60)) + 'm' + str(int(st['left'] % 60)).zfill(2) + 's left' if st['active'] else 'not active (' + st['reason'] + ')'}")
        xp = explore_pending()
        if xp:
            print(("  📖 re-steer requested " if xp["kind"] == "tune" else f"  unhandled {xp['kind']} request ") + xp["ts"] + (f"  seed: {xp['seed']}" if xp.get("seed") else ""))
        import atlas as fatl
        for r in fatl.open_requests(ROOT):
            print(f"  atlas_add {r['id']} [{r.get('atlas', 'formality')}]: \"{r['text']}\" (add the node: atlas.py {r.get('atlas', 'formality')} add ... --for {r['id']})")
        if st.get("cores"):
            print("  cores (the story's through-lines): " + explore_state.cores_words(st["cores"], detail=True))
        print("  maturity: " + explore_state.maturity_words(st.get("maturity")))
        for e in explore_state.episodes():
            print(f"  {e['id']}  [{e['status']}] {e['rendered']}/{e['shots']} shots  {e['title']}  (topic: {e['topic']})")
    elif cmd == "explorereply":
        xp_ts = time.strftime("%Y-%m-%d %H:%M:%S")
        write(EXPLORE_HANDLED, {"ts": xp_ts, "text": sys.argv[2] if len(sys.argv) > 2 else ""})
        print("ok")
    elif cmd in ("sets", "sreply"):
        sets = json.loads(SETS.read_text(encoding="utf-8")) if SETS.exists() else []
        if cmd == "sets":
            for x in sets:
                if x["status"] == "sent":
                    print(f"{x['id']} {x['kind']} {x['ts']} · {x.get('count', 3)} variations\n  " + "\n  ".join(x["images"])
                          + (f"\n  directions: {x['directions']}" if x["directions"] else ""))
            return
        sid, text = sys.argv[2], sys.argv[3]
        x = next(x for x in sets if x["id"] == sid)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        x.update(status="done", reply=text, replied=now)
        write(SETS, sets)
        for img, cap in zip(x["images"], x.get("caps", [])):
            cur = state.get(img, {"actions": [], "action": "note", "cap": cap, "ts": now})
            keep = [x for x in cur.get("actions", []) if x in ("love", "nope")]
            cur.update(status="done", reply=text, replied=now, actions=keep, action=keep[0] if keep else "note")
            state[img] = cur
        write(STATE, state)
        print("ok")
    elif cmd in ("journeys", "jreply"):
        reqs = json.loads(JOURNEYS.read_text(encoding="utf-8")) if JOURNEYS.exists() else []
        if cmd == "journeys":
            for x in reqs:
                if x["status"] == "sent":
                    print(f"{x['id']} {x['kind']} {x['ts']}  {x.get('image') or x.get('journey')}" + (f" {x['chapter']}" if x.get("chapter") else "") + (f"\n  text: {expand_refs(x['text'])}" if x["text"] else ""))
            return
        x = next(x for x in reqs if x["id"] == sys.argv[2])
        x.update(status="done", reply=sys.argv[3], replied=time.strftime("%Y-%m-%d %H:%M:%S"))
        if len(sys.argv) > 4:
            x["journey"] = sys.argv[4]  # a start request learns which journey it became
        write(JOURNEYS, reqs)
        print("ok")
    elif cmd in ("mvs", "mvreply"):
        reqs = json.loads(MVS.read_text(encoding="utf-8")) if MVS.exists() else []
        if cmd == "mvs":
            for x in reqs:
                if x["status"] == "sent":
                    print(f"{x['id']} {x['kind']} {x['ts']}  {x['mv']}  {mv_summary(x)}" + (f"\n  text: {x['text']}" if x.get("text") else ""))
            for mv, g in open_gen():
                print(gen_line(mv, g) + f"   (render: tools/mv_ref_gen.py musicvideos/{mv} \"<subject>\"; close: feedback.py mvgen {mv} {g['id']} <png>)")
            return
        x = next(x for x in reqs if x["id"] == sys.argv[2])
        x.update(status="done", reply=sys.argv[3], replied=time.strftime("%Y-%m-%d %H:%M:%S"))
        write(MVS, reqs)
        print("ok")
    elif cmd == "mvgen":
        mv, rid, png = sys.argv[2:5]
        rel = mvgen(mv, rid, png, sys.argv[5] if len(sys.argv) > 5 else "")
        rebuild()
        print("ok", rel)
    elif cmd == "creply":
        comments = json.loads(COMMENTS.read_text(encoding="utf-8")) if COMMENTS.exists() else []
        comments.append({"id": f"c{len(comments) + 1}", "target": sys.argv[2], "author": "claude",
                         "text": sys.argv[3], "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
        tmp = COMMENTS.with_suffix(".tmp")
        tmp.write_text(json.dumps(comments, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(COMMENTS)
        print("ok")


if __name__ == "__main__":
    main()
