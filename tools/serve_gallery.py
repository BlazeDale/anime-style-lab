"""Serve the project locally so the gallery can live-update: http://127.0.0.1:<gallery_port>/gallery/
(default port 8765, set in config.json / config.example.json).

Also the feedback API behind the gallery's buttons:
  GET  /api/feedback          -> feedback/state.json  {img_path: {actions: [...], action, note, cap, status, reply, ts}}
  POST /api/feedback          {src, action: animate|evolve|cross|cast|love|nope|clear|note, note?, cap?}
                              -> toggles that mark on the image (several can coexist; love/nope exclude each other)
                              also accepts {src: "style:<lineage id>", action: love|nope} to like/dislike a whole style
                              (a standing taste signal, applied immediately -- no "Send" needed)
  POST /api/feedback/submit   -> pending marks become "sent"; one "submit" line is appended to feedback/log.jsonl
  GET  /api/comments          -> feedback/comments.json
  POST /api/comments          {target: general|round:N|lineage:ID|version:ID/vNN, text} -> logged as a "comment" event
  GET  /api/pins              -> {pins: [{src, cap}], directions, sets: [...recent submitted sets]}
  POST /api/pins              {op: toggle, src, cap} | {op: clear} | {op: directions, text} | {op: count, n}
                              (the 📌 tray, server-side; count = how many variant lineages "Submit" should ask for)
  POST /api/pins/submit       -> the tray becomes one set: 1 image = evolve, 2+ = cross; appended to feedback/sets.json
                                 (status "sent") + a "set" event in feedback/log.jsonl; the tray is cleared
  GET  /api/queue             -> the ⚙ Queue panel: render jobs' plans (feedback/pipeline/<pid>.json, written by
                                 tools/pipeline.py from run_version / run_video) + ComfyUI's own queue counts
  POST /api/reroll            {src} -> 🎲 re-render that image in place (same prompt, fresh seed) via run_version.py --reroll;
                                 one at a time in a worker thread; the old image moves to vNN/_rerolled/
  POST /api/upscale           {src} -> ⤢ hi-res img2img pass of the image with its own prompt (tools/hires_card.py),
                                 saved to <dir>/_upscaled/<name>.png; same one-at-a-time worker as reroll
  POST /api/refit             {src, aspect} -> ⬚ re-render the image's prompt at a new aspect ratio with the image as
                                 reference (tools/refit.py), saved to <dir>/_resized/<name>__<w>x<h>.png
  POST /api/fix_area          {src, box:[x0,y0,x1,y1] fractions, text} -> ✎ inpaint only that box (tools/fix_area.py); same one-at-a-time worker
  POST /api/reveal            {src} -> opens Windows Explorer with that video clip selected (existing .mp4 under evolutions/ or journeys/)
  GET  /api/journeys          -> {requests: [...]}: 🧭 journey requests (feedback/journeys.json)
  POST /api/journeys          {op: start, src, cap, text}  -> "🧭 explore their world" on an image: the coding agent writes chapter 1
                              {op: direct, journey, text}  -> the user directs the journey's next chapter
                              {op: ref, journey, src}      -> ⚓ toggle a scene as an extra character reference (journey.json refs)
                              {op: ref_crop, journey, src, crop:[x0,y0,x1,y1]|null} -> ✂ crop a reference to head and shoulders (journey.json ref_crop)
                              {op: ref_note, journey, src, note, for} -> what a reference shows + which character it is for (ref_notes / ref_for)
                              {op: animate, journey, chapter, text} -> 🎬 "Animate chapter": the coding agent writes per-scene motion
                                 and runs tools/animate_chapter.py (ONE run_video --batch)
                              each start/direct = a "journey" event in log.jsonl; answer with feedback.py jreply
  GET  /api/blur              -> {img_path: true}: images the user blurred (feedback/blur.json)
  POST /api/blur              {src} -> toggle the blur on that image (stays until turned off)
Static files: served from the repo root.
"""
import functools
import http.server
import json
import os
import re
import sys
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import COMFY_URL, GALLERY_PORT, VENV_PYTHON  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PORT = GALLERY_PORT
FB = ROOT / "feedback"
STATE = FB / "state.json"
LOG = FB / "log.jsonl"
COMMENTS = FB / "comments.json"
PINS = FB / "pins.json"  # {pins: [{src, cap}], directions}
JOURNEYS = FB / "journeys.json"  # [{id, kind: start|direct, image?, cap?, journey?, text, ts, status: sent|done, reply?}]
BLUR = FB / "blur.json"  # {img_path: true}
SETS = FB / "sets.json"  # [{id, kind: evolve|cross, images, caps, directions, ts, status: sent|done, reply?}]  # [{id, target, author: you|claude, text, ts}]
LOCK = threading.Lock()


def load_state():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(state):
    FB.mkdir(exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE)


def load_comments():
    return json.loads(COMMENTS.read_text(encoding="utf-8")) if COMMENTS.exists() else []


def save_comments(comments):
    FB.mkdir(exist_ok=True)
    tmp = COMMENTS.with_suffix(".tmp")
    tmp.write_text(json.dumps(comments, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(COMMENTS)


def load_json(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def save_json(path, obj):
    FB.mkdir(exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def pins_view():
    return {**load_json(PINS, {"pins": [], "directions": ""}), "sets": load_json(SETS, [])[-10:]}


PIPE = FB / "pipeline"
PY = str(VENV_PYTHON)
WARNED = set()


def warn_once(msg):
    if msg not in WARNED:
        WARNED.add(msg)
        print("WARNING: " + msg, flush=True)


REROLLS = []  # waiting keys (project-relative png paths), consumed by reroll_worker
REROLL_WAKE = threading.Event()


FIX_WORDS = ("hand", "finger", "anatomy", "limb", "arm", "leg", "feet", "foot", "thumb", "wrist")


def wants_fix(key):
    """a 🎲 becomes a 'fix' reroll (negative prompt + higher CFG) when the image's latest comment from the user
    reports bad hands / anatomy"""
    mine = [c for c in load_comments() if c["target"] == "image:" + key and c["author"] == "you"]
    return bool(mine) and any(w in mine[-1]["text"].lower() for w in FIX_WORDS)


def upscaled_path(key):
    """⤢ upscale output: <image dir>/_upscaled/<name>.png (underscore dirs stay out of the gallery grid)"""
    from pathlib import PurePosixPath
    p = PurePosixPath(key)
    return str(p.parent / "_upscaled" / p.name)


def reroll_worker():
    while True:
        REROLL_WAKE.wait()
        while REROLLS:
            key = REROLLS[0]
            up = key[len("upscale:"):] if key.startswith("upscale:") else None
            fit = key[len("refit:"):].split("|", 1) if key.startswith("refit:") else None
            fix = key[len("fixarea:"):].split("|", 2) if key.startswith("fixarea:") else None  # box@mtime|src|text, see /api/fix_area
            cmd = ([PY, str(ROOT / "tools" / "hires_card.py"), up, upscaled_path(up), "--size", "2048", "--denoise", "0.45", "--detail"] if up else
                   [PY, str(ROOT / "tools" / "refit.py"), fit[1], fit[0]] if fit else
                   [PY, str(ROOT / "tools" / "fix_area.py"), fix[1], *fix[0].split("@")[0].split(","), fix[2]]
                   + (["--if-mtime", fix[0].split("@")[1]] if "@" in fix[0] else []) if fix else
                   [PY, str(ROOT / "tools" / "run_journey.py"), "--reroll", key] if key.startswith("journeys/") else
                   [PY, str(ROOT / "tools" / "run_version.py"), "--reroll", key] + (["--fix"] if wants_fix(key) else []))
            PIPE.mkdir(parents=True, exist_ok=True)
            with open(PIPE / "worker.log", "a", encoding="utf-8") as out:  # failures used to vanish into DEVNULL
                out.write(f"\n== {time.strftime('%Y-%m-%d %H:%M:%S')} {key}\n")
                out.flush()
                r = subprocess.run(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
            if r.returncode:
                print(f"worker job failed ({r.returncode}): {key} (see feedback/pipeline/worker.log)", flush=True)
            REROLLS.pop(0)
        REROLL_WAKE.clear()


def pid_alive(pid):
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
    h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return code.value == 259  # STILL_ACTIVE


def mark_on_gpu(jobs, pid, out, prefix):
    """set on_gpu on the plan item ComfyUI is executing: by the tag lab_body adds, else (jobs submitted before the tag)
    by matching the SaveImage prefix anime-style-lab/<lineage>_<vNN>_<name> / journey_... against the item's output path"""
    running = [(j, it) for j in jobs for it in j["items"] if it["status"] == "running"]
    hit = [it for j, it in running if pid and j["pid"] == pid and it["out"] == out]
    if not hit and prefix.startswith("anime-style-lab/"):
        tail = prefix[len("anime-style-lab/"):]
        flat = lambda o: o.split("/", 1)[-1].replace("/", "_")
        hit = [it for j, it in running if flat(it["out"]).startswith(tail) or ("journey_" + flat(it["out"])).startswith(tail)]
        if not hit:
            kind = "video" if tail.startswith("video/") else None
            same = [it for j, it in running if kind and it["kind"] == kind]
            hit = same if len(same) == 1 else []
    for it in hit[:1]:
        # first time we saw it on the GPU = start of the progress estimate (t0 is submit time, often long before)
        it.update(on_gpu=True, gpu_t0=it.get("g0") or GPU_SINCE.setdefault(f'{pid}:{it["out"]}', time.time()))


GPU_SINCE = {}


def queue_view():
    now, jobs = time.time(), []
    for f in sorted(PIPE.glob("*.json")) if PIPE.exists() else []:
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "ended" not in j and not pid_alive(j["pid"]):
            j["ended"] = f.stat().st_mtime  # the process died without closing its plan
            for it in j["items"]:
                if it["status"] in ("queued", "running"):
                    it["status"] = "cancelled"
        if "ended" in j and now - j["ended"] > 1800:
            f.unlink(missing_ok=True)  # keep finished jobs visible as "recent" for 30 min
            continue
        jobs.append(j)
    comfy, foreign = None, []
    try:
        with urllib.request.urlopen(COMFY_URL + "/queue", timeout=1) as r:
            q = json.loads(r.read())
        comfy = {"running": len(q.get("queue_running", [])), "pending": len(q.get("queue_pending", []))}
        # ComfyUI executes ONE job at a time; every lab script marks its item "running" once submitted, so flag the
        # item actually on the GPU (multiple progress bars otherwise look like they're all running at once)
        for it in q.get("queue_running", []):
            ex = it[3] if len(it) > 3 and isinstance(it[3], dict) else {}
            graph = it[2] if len(it) > 2 and isinstance(it[2], dict) else {}
            pre = next((str(n["inputs"]["filename_prefix"]) for n in graph.values() if isinstance(n, dict)
                        and isinstance((n.get("inputs") or {}).get("filename_prefix"), str)), "")
            mark_on_gpu(jobs, ex.get("lab_pid"), ex.get("lab_out"), pre)
        # jobs from other sessions/tools sharing this ComfyUI (optional): own rows, so the panel doesn't pass a
        # waiting lab clip off as the thing on the GPU
        sys.path.insert(0, str(Path(__file__).parent)); import pipeline
        for st, key in (("running", "queue_running"), ("queued", "queue_pending")):
            for it in q.get(key, []):
                if pipeline.is_lab(it):
                    continue
                graph = it[2] if len(it) > 2 and isinstance(it[2], dict) else {}
                prefixes = [str(n["inputs"]["filename_prefix"]) for n in graph.values()
                            if isinstance(n, dict) and "filename_prefix" in (n.get("inputs") or {}) and isinstance(n["inputs"]["filename_prefix"], str)]
                pre = prefixes[0] if prefixes else ""
                name = pre.rstrip("/").split("/")[-1].replace("_", " ") if pre else it[1][:8]
                is3d = pre.startswith("3d/") or any("3D" in n.get("class_type", "") or "Trellis" in n.get("class_type", "") for n in graph.values() if isinstance(n, dict))
                foreign.append({"kind": "3d" if is3d else "foreign", "status": st, "out": pre or it[1],
                                "label": ("🧊 3D asset · " if is3d else "⚙ external job · ") + name, "foreign": True})
    except Exception:
        pass
    waiting = REROLLS[1:]  # REROLLS[0] is already running as its own pipeline job
    if waiting:
        jobs.append({"pid": 0, "kind": "reroll-queue", "started": now,
                     "items": [{"kind": "image", "out": k, "status": "queued", "label": ("✎ " + k.split("|")[1].split("/", 1)[1] if k.startswith("fixarea:") else "🎲 " + k.split("/", 1)[1]).replace("_seed1001", "")} for k in waiting]})
    # averages from GPU time only (gsecs); submit-to-done "secs" include waiting in a shared queue
    done = [it for j in jobs for it in j["items"] if it["status"] == "done" and it.get("gsecs")]
    avg = {k: round(sum(x) / len(x)) if (x := [it["gsecs"] for it in done if it["kind"] == k]) else d
           for k, d in (("image", 25), ("video", 110))}
    return {"now": now, "jobs": jobs, "comfy": comfy, "avg": avg, "foreign": foreign}


def log(event):
    FB.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


EXCLUSIVE = {"love": "nope", "nope": "love"}


def acts(v):
    """marks on an image; older entries stored a single 'action'"""
    if "actions" in v:
        return list(v["actions"])
    return [v["action"]] if v.get("action") and v["action"] != "note" else []


def norm(src):
    # gallery uses "../evolutions/..." or "../journeys/..."; store project-relative paths, without a ?v= cache-buster
    src = src.split("?", 1)[0]
    for top in ("evolutions/", "journeys/"):
        if top in src:
            return top + src.split(top, 1)[1]
    return src


def is_img(key):
    return key.startswith(("evolutions/", "journeys/"))


def jdir(journey):
    d = (ROOT / "journeys" / str(journey)).resolve()
    return d if d.parent == (ROOT / "journeys") and (d / "journey.json").exists() else None


def valid_crop(c):
    """[x0,y0,x1,y1] fractions in [0,1] with at least 2% each way -> rounded list, else None (also None for null)."""
    if not isinstance(c, (list, tuple)) or len(c) != 4 or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in c):
        return None
    x0, y0, x1, y1 = (float(v) for v in c)
    if not all(0 <= v <= 1 for v in (x0, y0, x1, y1)) or x1 <= x0 + 0.02 or y1 <= y0 + 0.02:
        return None
    return [round(v, 4) for v in (x0, y0, x1, y1)]


MEDIA_EXT = (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".flac", ".wav", ".mp3")
THUMB = 640  # tile slider tops out at 520 css px


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".flac": "audio/flac", ".wav": "audio/wav"}

    def log_message(self, *args):
        pass

    def end_headers(self):
        # media keep their bytes in the browser cache and only revalidate (a cheap 304 via Last-Modified; rerolls keep the
        # file name but change the mtime); everything else stays no-store. no-store on every png made each live redraw
        # re-download every visible 2 MB image
        media = self.path.split("?")[0].lower().endswith(MEDIA_EXT)
        self.send_header("Cache-Control", "no-cache" if media else "no-store")
        super().end_headers()

    def send_thumb(self):
        """/thumb/<project-relative image>: a 640px WebP of it, cached in .thumbs/ and rebuilt when the source changes"""
        from urllib.parse import unquote
        rel = unquote(self.path.split("?")[0][len("/thumb/"):])
        src = (ROOT / rel).resolve()
        if ROOT not in src.parents or src.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp") or not src.is_file():
            return self.send_json({"error": "not found"}, 404)
        dst = ROOT / ".thumbs" / (rel + ".webp")
        mt = src.stat().st_mtime
        if not dst.exists() or dst.stat().st_mtime < mt:
            try:
                from PIL import Image
            except ImportError:  # no Pillow in this interpreter: send the full image rather than a broken tile
                warn_once("Pillow is missing, so tiles load full-size images (slower). Fix: python tools/doctor.py --fix")
                self.send_response(302)
                self.send_header("Location", "/" + rel)
                self.end_headers()
                return
            dst.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src) as im:
                im.thumbnail((THUMB, THUMB))
                tmp = dst.with_suffix(f".{threading.get_ident()}.tmp")
                im.convert("RGB").save(tmp, "WEBP", quality=82, method=4)
            tmp.replace(dst)
        stamp = self.date_time_string(int(mt))
        if self.headers.get("If-Modified-Since") == stamp:
            self.send_response(304); self.end_headers(); return
        data = dst.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "image/webp")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Last-Modified", stamp)
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/thumb/"):
            return self.send_thumb()
        if self.path.startswith("/api/feedback"):
            with LOCK:
                return self.send_json(load_state())
        if self.path.startswith("/api/comments"):
            with LOCK:
                return self.send_json(load_comments())
        if self.path.startswith("/api/queue"):
            return self.send_json(queue_view())
        if self.path.startswith("/api/pins"):
            with LOCK:
                return self.send_json(pins_view())
        if self.path.startswith("/api/journeys"):
            with LOCK:
                return self.send_json({"requests": load_json(JOURNEYS, [])})
        if self.path.startswith("/api/blur"):
            with LOCK:
                return self.send_json(load_json(BLUR, {}))
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self.send_json({"error": "bad json"}, 400)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.path == "/api/reroll":
            key = norm(str(body.get("src", "")))
            f = (ROOT / key).resolve()
            ok_evo = f.is_relative_to(ROOT / "evolutions") and f.parent.name.startswith("v")
            ok_jrn = f.is_relative_to(ROOT / "journeys") and f.parent.name.startswith("ch") and f.stem.startswith("s")
            if not ((ok_evo or ok_jrn) and f.suffix == ".png" and f.is_file()):
                return self.send_json({"error": "bad request"}, 400)
            if key not in REROLLS:
                REROLLS.append(key)
                REROLL_WAKE.set()
                log({"event": "reroll", "img": key, "ts": ts, "fix": wants_fix(key)})
            return self.send_json({"ok": True, "position": REROLLS.index(key)})
        if self.path == "/api/upscale":
            # ⤢ upscale: a 2048 px hi-res img2img pass of the image with its own prompt (tools/hires_card.py, denoise 0.35),
            # saved to _upscaled/; runs on the same one-at-a-time worker as reroll
            key = norm(str(body.get("src", "")))
            f = (ROOT / key).resolve()
            ok_evo = f.is_relative_to(ROOT / "evolutions") and f.parent.name.startswith("v")
            ok_jrn = f.is_relative_to(ROOT / "journeys") and f.parent.name.startswith("ch") and f.stem.startswith("s")
            if not ((ok_evo or ok_jrn) and f.suffix == ".png" and f.is_file()):
                return self.send_json({"error": "bad request"}, 400)
            k = "upscale:" + key
            if k not in REROLLS:
                REROLLS.append(k)
                REROLL_WAKE.set()
                log({"event": "upscale", "img": key, "ts": ts})
            return self.send_json({"ok": True, "position": REROLLS.index(k), "out": upscaled_path(key)})
        if self.path == "/api/refit":
            # ⬚ refit to another aspect ratio: tools/refit.py re-renders with the image as reference, output in _resized/
            key, aspect = norm(str(body.get("src", ""))), str(body.get("aspect", ""))
            f = (ROOT / key).resolve()
            ok_evo = f.is_relative_to(ROOT / "evolutions") and f.parent.name.startswith("v")
            ok_jrn = f.is_relative_to(ROOT / "journeys") and f.parent.name.startswith("ch") and f.stem.startswith("s")
            aspects = ("1:1 (Square)", "2:3 (Portrait Photo)", "3:2 (Photo)", "3:4 (Portrait Standard)", "4:3 (Standard)",
                       "9:16 (Portrait Widescreen)", "16:9 (Widescreen)", "21:9 (Ultrawide)")
            if not ((ok_evo or ok_jrn) and f.suffix == ".png" and f.is_file()) or aspect not in aspects:
                return self.send_json({"error": "bad request"}, 400)
            k = f"refit:{aspect}|{key}"
            if k not in REROLLS:
                REROLLS.append(k)
                REROLL_WAKE.set()
                log({"event": "refit", "img": key, "aspect": aspect, "ts": ts})
            return self.send_json({"ok": True, "position": REROLLS.index(k)})
        if self.path == "/api/fix_area":
            # ✎ fix area: inpaint a user-drawn box only (tools/fix_area.py); same one-at-a-time worker as rerolls
            key, text, box = norm(str(body.get("src", ""))), str(body.get("text", "")).strip().replace("|", "/"), body.get("box")
            f = (ROOT / key).resolve()
            ok_evo = f.is_relative_to(ROOT / "evolutions") and f.parent.name.startswith("v")
            ok_jrn = f.is_relative_to(ROOT / "journeys") and f.parent.name.startswith("ch") and f.stem.startswith("s")
            try:
                b = [float(v) for v in box]
                good = len(b) == 4 and all(0 <= v <= 1 for v in b) and b[2] - b[0] >= 0.02 and b[3] - b[1] >= 0.02
            except (TypeError, ValueError):
                good = False
            if not ((ok_evo or ok_jrn) and f.suffix == ".png" and f.is_file() and good and 0 < len(text) <= 300):
                return self.send_json({"error": "bad request"}, 400)
            # "@mtime": the picture version the box was drawn on (fix_area.py --if-mtime skips it if a reroll replaced the file meanwhile)
            k = "fixarea:" + ",".join(f"{v:.4f}" for v in b) + f"@{f.stat().st_mtime:.3f}" + "|" + key + "|" + text
            if k not in REROLLS:
                REROLLS.append(k)
                REROLL_WAKE.set()
                log({"event": "fix_area", "img": key, "box": b, "text": text, "ts": ts})
            return self.send_json({"ok": True, "position": REROLLS.index(k)})
        if self.path == "/api/reveal":
            f = (ROOT / norm(str(body.get("src", "")))).resolve()
            if not ((f.is_relative_to(ROOT / "evolutions") or f.is_relative_to(ROOT / "journeys")) and f.suffix == ".mp4" and f.is_file()):
                return self.send_json({"error": "bad request"}, 400)
            subprocess.Popen(f'explorer /select,"{f}"')
            return self.send_json({"ok": True})
        with LOCK:
            if self.path == "/api/blur":
                key = norm(str(body.get("src", "")))
                if not is_img(key):
                    return self.send_json({"error": "bad request"}, 400)
                bl = load_json(BLUR, {})
                if bl.pop(key, None) is None:
                    bl[key] = True
                save_json(BLUR, bl)
                return self.send_json(bl)
            if self.path == "/api/journeys":
                reqs, op, text = load_json(JOURNEYS, []), body.get("op"), str(body.get("text", "")).strip()
                if op == "ref":
                    d, key = jdir(body.get("journey")), norm(str(body.get("src", "")))
                    if not d or not is_img(key) or not (ROOT / key).is_file():
                        return self.send_json({"error": "bad request"}, 400)
                    j = json.loads((d / "journey.json").read_text(encoding="utf-8"))
                    refs = j.get("refs") or [j["source"]]
                    refs = [r for r in refs if r != key] if key in refs else refs + [key]
                    j["refs"] = refs or [j["source"]]  # never empty: the source portrait is the fallback identity
                    if key not in j["refs"] and isinstance(j.get("ref_crop"), dict):
                        j["ref_crop"].pop(key, None)  # un-anchored: its crop goes too
                        if not j["ref_crop"]:
                            del j["ref_crop"]
                    for fld in ("ref_notes", "ref_for"):  # its note + target go too
                        if key not in j["refs"] and isinstance(j.get(fld), dict):
                            j[fld].pop(key, None)
                            if not j[fld]:
                                del j[fld]
                    (d / "journey.json").write_text(json.dumps(j, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    log({"event": "journey-ref", "journey": d.name, "refs": j["refs"], "ts": ts})
                    return self.send_json({"requests": reqs, "refs": j["refs"], "ref_crop": j.get("ref_crop", {}),
                                           "ref_notes": j.get("ref_notes", {}), "ref_for": j.get("ref_for", {})})
                if op == "ref_crop":  # ✂ click-drag crop of a reference: fractions of width/height, or null to clear
                    d, key = jdir(body.get("journey")), norm(str(body.get("src", "")))
                    if not d:
                        return self.send_json({"error": "bad request"}, 400)
                    j = json.loads((d / "journey.json").read_text(encoding="utf-8"))
                    if key not in (j.get("refs") or [j["source"]]):
                        return self.send_json({"error": "not a reference of this journey"}, 400)
                    crop = valid_crop(body.get("crop"))
                    if body.get("crop") is not None and crop is None:
                        return self.send_json({"error": "bad crop"}, 400)
                    rc = j.get("ref_crop") if isinstance(j.get("ref_crop"), dict) else {}
                    if crop:
                        rc[key] = crop
                    else:
                        rc.pop(key, None)
                    if rc:
                        j["ref_crop"] = rc
                    else:
                        j.pop("ref_crop", None)
                    (d / "journey.json").write_text(json.dumps(j, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    log({"event": "journey-ref-crop", "journey": d.name, "src": key, "crop": crop, "ts": ts})
                    return self.send_json({"requests": reqs, "refs": j.get("refs") or [j["source"]], "ref_crop": rc})
                if op == "ref_note":  # what an anchored reference IS + which character it is for (default: the lead)
                    d, key = jdir(body.get("journey")), norm(str(body.get("src", "")))
                    if not d:
                        return self.send_json({"error": "bad request"}, 400)
                    j = json.loads((d / "journey.json").read_text(encoding="utf-8"))
                    if key not in (j.get("refs") or [j["source"]]):
                        return self.send_json({"error": "not a reference of this journey"}, 400)
                    note, who = str(body.get("note", "")).strip()[:300], str(body.get("for", "")).strip() or j["name"]
                    if who != j["name"] and who not in (j.get("cast") or {}):
                        return self.send_json({"error": "unknown character"}, 400)
                    notes = j.get("ref_notes") if isinstance(j.get("ref_notes"), dict) else {}
                    rf = j.get("ref_for") if isinstance(j.get("ref_for"), dict) else {}
                    if note:
                        notes[key] = note
                    else:
                        notes.pop(key, None)
                    if who != j["name"]:
                        rf[key] = who
                    else:
                        rf.pop(key, None)  # the lead is the default
                    for fld, val in (("ref_notes", notes), ("ref_for", rf)):
                        if val:
                            j[fld] = val
                        else:
                            j.pop(fld, None)
                    (d / "journey.json").write_text(json.dumps(j, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    log({"event": "journey-ref-note", "journey": d.name, "src": key, "note": note, "for": who, "ts": ts})
                    return self.send_json({"requests": reqs, "refs": j.get("refs") or [j["source"]], "ref_crop": j.get("ref_crop", {}),
                                           "ref_notes": notes, "ref_for": rf})
                if op == "start":
                    key = norm(str(body.get("src", "")))
                    if not is_img(key) or not key.endswith(".png"):
                        return self.send_json({"error": "bad request"}, 400)
                    r = {"kind": "start", "image": key, "cap": str(body.get("cap", ""))}
                elif op == "direct":
                    d = jdir(body.get("journey"))
                    if not d or not text:
                        return self.send_json({"error": "bad request"}, 400)
                    r = {"kind": "direct", "journey": d.name}
                elif op == "animate":  # 🎬 Animate chapter: the coding agent writes per-scene motion and runs one run_video --batch
                    d, ch = jdir(body.get("journey")), str(body.get("chapter", ""))
                    if not d or not re.fullmatch(r"ch\d\d", ch) or not (d / ch / "chapter.json").is_file():
                        return self.send_json({"error": "bad request"}, 400)
                    r = {"kind": "animate", "journey": d.name, "chapter": ch}
                else:
                    return self.send_json({"error": "bad request"}, 400)
                r = {"id": f"j{len(reqs) + 1}", **r, "text": text, "ts": ts, "status": "sent"}
                reqs.append(r)
                save_json(JOURNEYS, reqs)
                log({"event": "journey", **{k: v for k, v in r.items() if k != "status"}})
                return self.send_json({"requests": reqs})
            if self.path == "/api/comments":
                target, text = str(body.get("target", "")), str(body.get("text", "")).strip()
                if not text or not target:
                    return self.send_json({"error": "bad request"}, 400)
                comments = load_comments()
                c = {"id": f"c{len(comments) + 1}", "target": target, "author": "you", "text": text, "ts": ts}
                comments.append(c)
                save_comments(comments)
                log({"event": "comment", **c})
                return self.send_json(comments)
            if self.path == "/api/pins":
                pv = load_json(PINS, {"pins": [], "directions": ""})
                op = body.get("op")
                if op == "toggle":
                    key = norm(str(body.get("src", "")))
                    if not is_img(key) or not key.endswith(".png"):
                        return self.send_json({"error": "bad request"}, 400)
                    had = [p for p in pv["pins"] if p["src"] == key]
                    pv["pins"] = [p for p in pv["pins"] if p["src"] != key] if had else pv["pins"] + [{"src": key, "cap": str(body.get("cap", ""))}]
                elif op == "clear":
                    pv = {"pins": [], "directions": ""}
                elif op == "directions":
                    pv["directions"] = str(body.get("text", ""))
                elif op == "count":  # how many variant styles to make (tray "Variations")
                    pv["count"] = max(1, min(9, int(body.get("n") or 3)))
                else:
                    return self.send_json({"error": "bad request"}, 400)
                save_json(PINS, pv)
                return self.send_json(pins_view())
            if self.path == "/api/pins/submit":
                pv = load_json(PINS, {"pins": [], "directions": ""})
                if not pv["pins"]:
                    return self.send_json({"error": "nothing pinned"}, 400)
                sets = load_json(SETS, [])
                st = {"id": f"s{len(sets) + 1}", "kind": "cross" if len(pv["pins"]) > 1 else "evolve",
                      "images": [p["src"] for p in pv["pins"]], "caps": [p["cap"] for p in pv["pins"]],
                      "directions": pv["directions"].strip(), "count": pv.get("count", 3), "ts": ts, "status": "sent"}
                sets.append(st)
                save_json(SETS, sets)
                save_json(PINS, {"pins": [], "directions": ""})
                log({"event": "set", **{k: v for k, v in st.items() if k != "status"}})
                return self.send_json(pins_view())
            state = load_state()
            if self.path == "/api/feedback/submit":
                sent = {k: v for k, v in state.items() if v.get("status") == "pending"}
                for v in sent.values():
                    v["status"] = "sent"
                save_state(state)
                if sent:
                    log({"event": "submit", "ts": ts, "count": len(sent),
                         "marks": [{"img": k, "action": "+".join(acts(v)) or "note", "actions": acts(v), "note": v.get("note", ""), "cap": v.get("cap", "")}
                                   for k, v in sent.items()]})
                return self.send_json({"sent": len(sent), "state": state})
            if self.path == "/api/feedback":
                key = norm(body.get("src", ""))
                action = body.get("action")
                if key.startswith("style:") and re.fullmatch(r"style:\d{3}-[\w-]+", key) and action in ("love", "nope"):
                    # ❤/👎 on a whole style: a standing taste signal, not a request, so it never waits for "Send"
                    cur = state.get(key, {"actions": []})
                    a = [x for x in cur.get("actions", []) if x != action and x != EXCLUSIVE.get(action)]
                    if action not in cur.get("actions", []):
                        a.append(action)
                    if a:
                        state[key] = {"actions": a, "action": a[0], "cap": body.get("cap", ""), "status": "done", "reply": "", "ts": ts}
                    else:
                        state.pop(key, None)
                    save_state(state)
                    log({"event": "style_mark", "lineage": key[6:], "actions": a, "ts": ts})
                    return self.send_json(state)
                if not is_img(key) or action not in ("animate", "evolve", "cross", "cast", "love", "nope", "clear", "note"):
                    return self.send_json({"error": "bad request"}, 400)
                if action == "clear":
                    state.pop(key, None)
                else:
                    cur = state.get(key, {})
                    a = acts(cur)
                    if cur.get("status") in ("sent", "done"):
                        # a new mark on an already-sent image: one-shot requests were already handled,
                        # so they must not ride along again; only the ❤/👎 state carries over
                        a = [x for x in a if x in ("love", "nope")]
                    if action != "note":
                        if action in a:
                            a.remove(action)
                        else:
                            a.append(action)
                            if EXCLUSIVE.get(action) in a:
                                a.remove(EXCLUSIVE[action])
                    if "note" in body:
                        cur["note"] = body["note"]
                    if not a and not cur.get("note"):
                        state.pop(key, None)  # nothing left on this image
                    else:
                        cur["actions"] = a
                        cur["action"] = a[0] if a else "note"  # legacy field
                        cur.update(cap=body.get("cap", cur.get("cap", "")), status="pending", ts=ts)
                        state[key] = cur
                save_state(state)
                return self.send_json(state)
        return self.send_json({"error": "not found"}, 404)


if __name__ == "__main__":
    # started with some other Python (e.g. a bare `python tools/serve_gallery.py`)? hand over to the project's .venv,
    # which has Pillow for thumbnails; without a .venv, keep going and say what won't work
    if Path(PY).exists() and Path(sys.executable).resolve() != Path(PY).resolve():
        print(f"re-launching with {Path(PY).relative_to(ROOT)}", flush=True)
        try:
            sys.exit(subprocess.call([PY, str(Path(__file__).resolve()), *sys.argv[1:]]))
        except KeyboardInterrupt:
            sys.exit(0)
    if not Path(PY).exists():
        warn_once("no .venv found: 🎲 reroll / ⤢ upscale / ⬚ refit won't run. Fix: python tools/doctor.py --fix")
    threading.Thread(target=reroll_worker, daemon=True).start()
    handler = functools.partial(Handler, directory=str(ROOT))
    # home-network access: listen on all interfaces but only answer loopback and private LAN addresses (no auth here,
    # and the API can queue GPU jobs, so never the internet: don't port-forward it or put it behind a public tunnel)
    import ipaddress

    class LanOnlyServer(http.server.ThreadingHTTPServer):
        def verify_request(self, request, client_address):
            try:
                ip = ipaddress.ip_address(client_address[0])
                return ip.is_loopback or ip.is_private
            except ValueError:
                return False

    with LanOnlyServer(("0.0.0.0", PORT), handler) as srv:
        print(f"gallery: http://127.0.0.1:{PORT}/gallery/ (and http://<this PC's LAN IP>:{PORT}/gallery/ on the home network)", flush=True)
        srv.serve_forever()
