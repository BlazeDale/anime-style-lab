"""Render-pipeline status for the gallery's ⚙ Queue panel.

Each render process (run_version.py / run_video.py) registers its planned items in feedback/pipeline/<pid>.json
and marks them running / done / failed as it goes; serve_gallery.py's GET /api/queue merges the files
(dropping ones whose process died) with ComfyUI's own queue.
"""
import atexit
import json
import sys
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "feedback" / "pipeline"


class Job:
    def __init__(self, kind, items):
        """items: [{"label": str, "out": project-relative output path, "kind": "image"|"video"}]"""
        DIR.mkdir(parents=True, exist_ok=True)
        self.path = DIR / f"{os.getpid()}.json"
        self.state = {"pid": os.getpid(), "kind": kind, "started": time.time(),
                      "items": [{**it, "status": "queued"} for it in items]}
        self.save()
        global ACTIVE
        ACTIVE = self
        atexit.register(self.close)

    def save(self):
        # best-effort: on Windows the replace fails while serve_gallery is reading the file, and a status write must
        # never kill a render (2026-09-24 a 96-image job died on this). Retry briefly, then skip this update.
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
        for _ in range(20):
            try:
                tmp.replace(self.path)
                return
            except PermissionError:
                time.sleep(0.05)

    def _item(self, out):
        out = str(out).replace("\\", "/")
        return next((it for it in self.state["items"] if it["out"] == out and it["status"] in ("queued", "running")), None)

    def start(self, out):
        global CURRENT
        it = self._item(out)
        if it:
            it.update(status="running", t0=time.time()); self.save()
            CURRENT = {"lab_pid": os.getpid(), "lab_out": it["out"]}

    def on_gpu(self, out):
        """ComfyUI started executing this item: from here on its time counts as render time"""
        it = self._item(out)
        if it and "g0" not in it:
            it["g0"] = time.time(); self.save()

    def finish(self, out, ok=True):
        it = self._item(out)
        if it:
            now = time.time()
            # secs = time on the GPU when known (g0), else since submit; the ⚙ Queue averages only use gsecs, so a long
            # shared queue doesn't inflate the estimates (2026-09-26: 713 s/image "average" = mostly waiting)
            it.update(status="done" if ok else "failed", secs=round(now - it.get("g0", it.get("t0", now)), 1))
            if "g0" in it:
                it["gsecs"] = it["secs"]
            self.save()

    def close(self):
        # keep finished items visible for a while as "recent"; the server prunes old files
        self.state["ended"] = time.time()
        for it in self.state["items"]:
            if it["status"] in ("queued", "running"):
                it["status"] = "cancelled"
        try:
            self.save()
        except OSError:
            pass


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT)).replace("\\", "/")


# Sharing ComfyUI with other tools/users on the same install (optional). Every lab job is tagged with LAB_CLIENT;
# before each submit, lab scripts can wait while any untagged (= foreign) job is running or pending, so this
# project never queues behind someone else's backlog (at most the one lab job already on the GPU finishes first).
# If you're the only thing using this ComfyUI, this is a harmless no-op.
LAB_CLIENT = "anime-lab"
CURRENT = None  # set by Job.start: the plan item the next lab_body submit belongs to
ACTIVE = None   # this process's Job
_LASTQ = [0.0]


def note_progress(server, pid):
    """call from a submit/wait loop: marks the current item on_gpu once ComfyUI starts executing prompt `pid`
    (checks /queue at most every 3 s)"""
    if not (ACTIVE and CURRENT) or time.time() - _LASTQ[0] < 3:
        return
    _LASTQ[0] = time.time()
    try:
        import json as _j, urllib.request as _u
        with _u.urlopen(f"{server}/queue", timeout=10) as r:
            q = _j.loads(r.read())
        if any(it[1] == pid for it in q.get("queue_running", [])):
            ACTIVE.on_gpu(CURRENT["lab_out"])
    except Exception:
        pass


def lab_body(graph):
    """the POST /prompt body for a lab job: tagged so other lab scripts don't yield to it"""
    body = {"prompt": graph, "client_id": LAB_CLIENT}
    if CURRENT:  # which plan item this is, so the ⚙ Queue can tell the job ComfyUI is executing from ones waiting in it
        body["extra_data"] = {"client_id": LAB_CLIENT, **CURRENT}
    return body


def is_lab(item):
    """a /queue item [n, prompt_id, graph, extra_data, ...] is ours if tagged, or (jobs submitted before tagging existed)
    if it saves under ComfyUI's output/anime-style-lab/"""
    if len(item) > 3 and (item[3] or {}).get("client_id") == LAB_CLIENT:
        return True
    graph = item[2] if len(item) > 2 and isinstance(item[2], dict) else {}
    return any(str((n.get("inputs") or {}).get("filename_prefix", "")).startswith("anime-style-lab/") for n in graph.values() if isinstance(n, dict))


def yield_to_other_clients(server="http://127.0.0.1:8188", poll=5, max_wait=4 * 3600):
    """Optional: if this ComfyUI is shared with another tool/session, wait while ITS jobs are running or pending
    so this project doesn't queue behind a backlog it didn't create. A harmless no-op (returns immediately) if
    nothing foreign is ever queued, e.g. when this is the only thing using the install."""
    import urllib.request
    t0, said = time.time(), False
    while time.time() - t0 < max_wait:
        try:
            with urllib.request.urlopen(server + "/queue", timeout=10) as r:
                q = json.loads(r.read())
        except Exception:
            return
        foreign = [it for it in q.get("queue_running", []) + q.get("queue_pending", []) if not is_lab(it)]
        if not foreign:
            if said:
                print(f"foreign jobs done, resuming after {time.time() - t0:.0f}s", flush=True)
            return
        if not said:
            print(f"yielding to {len(foreign)} foreign job(s) on this shared ComfyUI...", flush=True)
            said = True
        time.sleep(poll)


# ---- one lab job in ComfyUI at a time ------------------------------------------------------------------------------
# Submitting several jobs at once makes ComfyUI hold ~20 interleaved image/video jobs: a 16 GB card reloads models on
# almost every switch (a 100 s clip can take 215 s). So a script takes a GPU ticket before submitting and gives it
# back when its job is done. Waiting scripts line up in feedback/pipeline/gpu/; the next one is picked by: the same
# model kind as the last job (fewer model swaps), then oldest.
GPU = DIR / "gpu"


def _alive(pid):
    if sys.platform != "win32":
        try:
            os.kill(int(pid), 0)  # signal 0 = existence check on POSIX
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    import ctypes  # Windows: os.kill(pid, 0) would terminate the process, so ask the kernel instead
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))
    if not h:
        return False
    code = ctypes.c_ulong()
    k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return code.value == 259  # STILL_ACTIVE


def _read(f, d=None):
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return d


def gpu_acquire(kind):
    """block until this process may put ONE job into ComfyUI; kind groups jobs that share a model ('image',
    'video:fasth3', ...)"""
    (GPU / "tickets").mkdir(parents=True, exist_ok=True)
    me = os.getpid()
    ticket = GPU / "tickets" / f"{me}.json"
    ticket.write_text(json.dumps({"pid": me, "kind": kind, "ts": time.time()}), encoding="utf-8")
    holder = GPU / "holder.json"
    try:
        while True:
            h = _read(holder)
            if h and h.get("pid") != me and _alive(h["pid"]):
                time.sleep(1)
                continue
            last = (_read(GPU / "last.json", {}) or {}).get("kind")
            waiting = []
            for t in (GPU / "tickets").glob("*.json"):
                x = _read(t)
                if x and _alive(x["pid"]):
                    waiting.append(x)
                elif x:
                    try:
                        t.unlink(missing_ok=True)  # a dead script's ticket
                    except OSError:
                        pass  # another script is removing/reading it: harmless
            waiting.sort(key=lambda x: (x.get("kind") != last, x.get("ts", 0)))
            if waiting and waiting[0]["pid"] == me:
                holder.write_text(json.dumps({"pid": me, "kind": kind, "ts": time.time()}), encoding="utf-8")
                time.sleep(0.3)  # two scripts that both saw a free GPU: the later write wins, the other re-checks
                if (_read(holder) or {}).get("pid") == me:
                    return
            time.sleep(1)
    finally:
        try:
            ticket.unlink(missing_ok=True)
        except OSError:
            pass


def gpu_release(kind):
    holder = GPU / "holder.json"
    if (_read(holder) or {}).get("pid") == os.getpid():
        try:
            (GPU / "last.json").write_text(json.dumps({"kind": kind, "ts": time.time()}), encoding="utf-8")
            holder.unlink(missing_ok=True)
        except OSError:
            pass
