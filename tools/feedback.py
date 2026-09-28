"""Read / answer the user's gallery marks (feedback/state.json).

  python tools/feedback.py list [pending|sent|done]     default: sent
  python tools/feedback.py reply <img-path> "<text>"    marks it done with a reply shown in the gallery
  python tools/feedback.py comments                     threads whose last message is the user's (awaiting reply)
  python tools/feedback.py creply <target> "<text>"     reply in a comment thread (target e.g. general, round:2)
  python tools/feedback.py sets                         submitted 📌 sets (evolve = 1 image, cross = 2+) still waiting
  python tools/feedback.py sreply <set-id> "<text>"     marks a set done; the reply also shows on each of its images
  python tools/feedback.py journeys                     🧭 journey requests still waiting (start = new journey, direct = next chapter)
  python tools/feedback.py jreply <req-id> "<text>"     marks a journey request done; the reply shows on the journey page
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
        if not marks and not open_c and not open_s and not open_j:
            return
        print(f"GALLERY INBOX: {len(open_j)} 🧭 journey request(s), {len(open_s)} 📌 set(s), {len(marks)} sent mark(s) and {len(open_c)} comment thread(s) "
              "are waiting on you. Act on them (see CLAUDE.md 'User feedback' / 'Journeys'), then reply with tools/feedback.py reply / creply / sreply / jreply.")
        for x in open_j:
            print(f"  journey {x['id']} {x['kind']}: {x.get('image') or x.get('journey')}" + (f"  text: {expand_refs(x['text'])}" if x["text"] else ""))
        for x in open_s:
            print(f"  set {x['id']} {x['kind']} ({x.get('count', 3)} variations): {' × '.join(x['images'])}" + (f"  directions: {expand_refs(x['directions'])}" if x["directions"] else ""))
        for k, v in marks:
            print(f"  mark {'+'.join(v.get('actions') or [v.get('action', '')])}: {k}" + (f"  note: {v['note']}" if v.get("note") else ""))
        for c in open_c:
            print(f"  comment [{c['target']}] {c['ts']}: {c['text']}")
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
                    print(f"{x['id']} {x['kind']} {x['ts']}  {x.get('image') or x.get('journey')}" + (f"\n  text: {expand_refs(x['text'])}" if x["text"] else ""))
            return
        x = next(x for x in reqs if x["id"] == sys.argv[2])
        x.update(status="done", reply=sys.argv[3], replied=time.strftime("%Y-%m-%d %H:%M:%S"))
        if len(sys.argv) > 4:
            x["journey"] = sys.argv[4]  # a start request learns which journey it became
        write(JOURNEYS, reqs)
        print("ok")
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
