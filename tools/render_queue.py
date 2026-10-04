"""🖨 render queue: the lowest-overhead way to keep renders flowing.

One job list, one worker: tools add version dirs here (new_set.py / new_cast.py --render, or this CLI) and serve_gallery's
render_worker runs them one job at a time with run_version.py, so nothing depends on an agent's background shell (those hit a
30 min limit and one hung for 16 min). A finished job appends a "render_done" event to feedback/log.jsonl ([ACT] in the
watcher): review that set then. A server restart resumes a job that was running (run_version skips finished images).

  render_queue.py add <version dir>... [--label "s91 Moebius x dragons"]
  render_queue.py list          (queued / running / last finished)
  render_queue.py clear         (drop finished jobs from the file)
"""
import json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "feedback" / "render_queue.json"


def load():
    try:
        return json.loads(QUEUE.read_text(encoding="utf-8"))
    except Exception:
        return {"jobs": []}


def save(q):
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE.with_suffix(".tmp")
    tmp.write_text(json.dumps(q, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, QUEUE)


def add(dirs, label=""):
    dirs = [Path(d).as_posix().rstrip("/") for d in dirs]
    q = load()
    n = max([int(j["id"][1:]) for j in q["jobs"]] + [0]) + 1
    job = {"id": f"r{n}", "dirs": dirs, "label": label or ", ".join(d.split("/")[1] for d in dirs), "status": "queued",
           "added": time.strftime("%Y-%m-%d %H:%M:%S")}
    q["jobs"].append(job)
    save(q)
    return job


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return
    cmd, rest = argv[0], argv[1:]
    if cmd == "add":
        label = ""
        if "--label" in rest:
            i = rest.index("--label"); label = rest[i + 1]; rest = rest[:i] + rest[i + 2:]
        missing = [d for d in rest if not (ROOT / d / "prompt.txt").exists()]
        if missing:
            sys.exit(f"not version dirs: {missing}")
        j = add(rest, label)
        print(f"queued {j['id']}: {j['label']} ({len(j['dirs'])} version dirs)")
    elif cmd == "list":
        for j in load()["jobs"]:
            if j["status"] in ("queued", "running") or j.get("ended", "") >= time.strftime("%Y-%m-%d"):
                print(f"{j['id']:>5} {j['status']:<8} {j['label']}  {j.get('ended', j.get('started', j['added']))}")
    elif cmd == "clear":
        q = load(); q["jobs"] = [j for j in q["jobs"] if j["status"] in ("queued", "running")]; save(q)
        print(f"{len(q['jobs'])} open jobs kept")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
