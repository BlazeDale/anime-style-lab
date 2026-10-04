"""Serve the project locally so the gallery can live-update: http://127.0.0.1:<gallery_port>/gallery/
(default port 8765, set in config.json / config.example.json).

Also the feedback API behind the gallery's buttons:
  GET  /api/feedback          -> feedback/state.json  {img_path: {actions: [...], action, note, cap, status, reply, ts}}
  POST /api/feedback          {src, action: animate|evolve|cross|cast|love|nope|clear|note, note?, cap?}
                              -> toggles that mark on the image (several can coexist; love/nope exclude each other)
  POST /api/feedback/submit   -> pending marks become "sent"; one "submit" line is appended to feedback/log.jsonl
  GET  /api/comments          -> feedback/comments.json
  POST /api/comments          {target: general|round:N|lineage:ID|version:ID/vNN, text} -> logged as a "comment" event
  GET  /api/pins              -> {pins: [{src, cap}], directions, sets: [...recent submitted sets]}
  POST /api/pins              {op: toggle, src, cap} | {op: clear} | {op: directions, text}   (the 📌 tray, server-side)
  POST /api/pins/submit       -> the tray becomes one set: 1 image = evolve, 2+ = cross; appended to feedback/sets.json
                                 (status "sent") + a "set" event in feedback/log.jsonl; the tray is cleared
  GET  /api/queue             -> the ⚙ Queue panel: render jobs' plans (feedback/pipeline/<pid>.json, written by
                                 tools/pipeline.py from run_version / run_video) + ComfyUI's own queue counts
  POST /api/reroll            {src} -> 🎲 re-render that image in place (same prompt, fresh seed) via run_version.py --reroll;
                                 one at a time in a worker thread; the old image moves to vNN/_rerolled/
  POST /api/reveal            {src} -> opens the file manager with that video clip selected (existing .mp4 under evolutions/, journeys/ or musicvideos/)
  GET  /api/journeys          -> {requests: [...]}: 🧭 journey requests (feedback/journeys.json)
  POST /api/journeys          {op: start, src, cap, text}  -> "🧭 explore their world" on an image: the coding agent writes chapter 1
                              {op: direct, journey, text}  -> the user directs the journey's next chapter
                              {op: ref, journey, src}      -> ⚓ toggle a scene as an extra character reference (journey.json refs)
                              each start/direct = a "journey" event in log.jsonl; the coding agent answers with feedback.py jreply
  GET  /api/mv                -> {mvs: [mv.json + id], requests: [...]}: 🎵 music videos (musicvideos/NNN-slug/mv.json) + feedback/mvs.json
  POST /api/mv                {op: new|from_pins|save|marker_set|marker_del|ref|ref_remove|ref_crop|ref_note|request_done|ref_gen_request|ref_gen_cancel|submit, mv, ...}
                              from_pins = the 📌 tray becomes a new mv's references (mv null) or is added to one; submit = an ACT request
                              for the coding agent (feedback.py mvs / mvreply); every op returns {mv, requests}
  POST /api/mv/upload?mv=ID&kind=audio|vocals|stems&name=song.mp3   raw body -> musicvideos/ID/audio/song.<ext>|vocals.<ext>; audio kicks off
                              tools/mv_analyze.py (waveform/beats/sections -> audio/analysis.json) in a background thread.
                              kind=stems (a .zip, <=1.5 GB): audio files -> audio/stems/, the zip's full mix (or an ffmpeg mixdown) = the song and
                              its LEAD vocal = the vocals unless hand-uploaded (mv.json audio_from/vocals_from), then tools/mv_stems.py -> audio/stems.json
                              (mv op stems_clear removes them)
  POST /api/mv                {op: lyrics_place, mv} -> queues tools/mv_lyrics.py (audio/lyrics_timing.json) on the reroll worker; also queued after a
                              vocals upload / stems zip with a lead vocal and after a lyrics save that changed the text
  POST /api/mv                {op: assemble, mv, draft?} -> queues tools/mv_assemble.py (the 🎞 final cut: clips + the original song -> musicvideos/ID/cut/<slug>.mp4) on the
                              reroll worker; progress in cut/_status.json, the page shows the latest cut + its edit list
  GET  /api/explore           -> {state: {active, left, until, reason: timer|stopped|idle|"", ...}, episodes: [...]}: 🌌 Explore mode (feedback/explore.json,
                              explore/NNN-slug/episode.json; tools/explore_state.py has the logic)
  POST /api/explore           {op: start, seed?, presence?, emotion?, formality?} | {op: continue, ...} | {op: tune, presence?, emotion?, formality?} | {op: stop}: start/continue open a
                              15 minute window and log an ACT "explore" event (kind start|continue, with presence 0-100 + emotion {primary, secondary, mix,
                              intensity}) that wakes the agent to plan episodes; tune changes the knob + wheel mid-run (info); stop logs kind stop (info). The timer needs no thread:
                              once now > until the state reads active=false, reason "timer", and only Continue resumes
  GET  /api/blur              -> {img_path: true}: images the user blurred (feedback/blur.json)
  POST /api/blur              {src} -> toggle the blur on that image (stays until turned off)
Static files: served from the repo root.
"""
import functools
import http.server
import importlib
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
from config import COMFY_URL, COMFY_PYTHON, FFMPEG, GALLERY_PORT, VENV_PYTHON  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PORT = GALLERY_PORT
FB = ROOT / "feedback"
STATE = FB / "state.json"
LOG = FB / "log.jsonl"
COMMENTS = FB / "comments.json"
PINS = FB / "pins.json"  # {pins: [{src, cap}], directions}
EXPLORE_ANIM = FB / "explore_animate.json"  # [{id a<n>, kind animate, saga, chapter, text, ts, status open|done, reply?, done_ts?}]
JOURNEYS = FB / "journeys.json"  # [{id, kind: start|direct|animate, chapter? (animate), image?, cap?, journey?, text, ts, status: sent|done, reply?}]
MVS = FB / "mvs.json"  # [{id, kind: submit, mv, text, ts, status: sent|done, reply?}]  (🎵 music video requests)
MVDIR = ROOT / "musicvideos"
GPY = str(COMFY_PYTHON)  # interpreter with librosa + soundfile (config "comfy_python"; default = this python)
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


def mv_lyrics_run(mvid):
    """tools/mv_lyrics.py on one music video (the vocals, else the song): audio/lyrics_timing.json, or audio/lyrics_error.txt"""
    d = mvdir(mvid)
    if not d:
        return
    err = d / "audio" / "lyrics_error.txt"
    try:
        r = subprocess.run([PY, str(ROOT / "tools" / "mv_lyrics.py"), f"musicvideos/{mvid}"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            err.write_text(((r.stderr or r.stdout or "").strip().splitlines() or ["no output"])[-1][:400], encoding="utf-8")
    except Exception as e:
        err.write_text(str(e)[:400], encoding="utf-8")
    (d / "audio" / "lyrics_pending").unlink(missing_ok=True)
    rebuild_bg()


def mv_lyrics_queue(d):
    """🎤 queue the lyric placement for a music video; needs lyrics and
    vocals or a song. audio/lyrics_pending (a time stamp, trusted for 10 min: a restart drops the queue) is what the page shows as Placing lyrics"""
    m = mv_load(d)
    if not (m.get("lyrics") or "").strip() or not (m.get("vocals") or m.get("audio")):
        return False
    (d / "audio").mkdir(exist_ok=True)
    (d / "audio" / "lyrics_error.txt").unlink(missing_ok=True)
    (d / "audio" / "lyrics_pending").write_text(str(int(time.time())), encoding="utf-8")
    k = f"mvlyrics:{d.name}"
    if k not in REROLLS:
        REROLLS.append(k)
    REROLL_WAKE.set()
    log({"event": "mv_lyrics", "mv": d.name, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    rebuild_bg()
    return True


MV_TARGETS = ("draft", "youtube", "suno", "hooks")  # Build for YouTube / Suno / Hooks (+ the draft)


def mv_asm_queue(d, target):
    """🎞 queue a final-cut build (all clips put together over the original full song): cut/_status.json
    says queued until the worker starts tools/mv_assemble.py (which keeps it updated). target: draft | youtube | suno | hooks (True/False = old draft flag)"""
    if target is True or target is False:
        target = "draft" if target else "youtube"
    (d / "cut").mkdir(exist_ok=True)
    (d / "cut" / "_status.json").write_text(json.dumps({"state": "queued", "draft": target == "draft", "target": target, "stage": "waiting in the queue", "ts": int(time.time())}), encoding="utf-8")
    k = f"mvasm:{d.name}|{target}"
    if k not in REROLLS:
        REROLLS.append(k)
    REROLL_WAKE.set()
    log({"event": "mv_assemble", "mv": d.name, "draft": target == "draft", "target": target, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    rebuild_bg()
    return k


def mv_asm_run(key):
    mvid, mode = key[len("mvasm:"):].split("|")
    mode = "youtube" if mode == "full" else mode
    cmd = [PY, str(ROOT / "tools" / "mv_assemble.py"), f"musicvideos/{mvid}"] + (["--draft"] if mode == "draft" else ["--target", mode])
    try:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            sp = ROOT / "musicvideos" / mvid / "cut" / "_status.json"
            st = load_json(sp, {}) or {}
            if st.get("state") != "error":
                st.update(state="error", stage="failed", error=((r.stderr or r.stdout or "").strip().splitlines() or ["no output"])[-1][:400], ts=int(time.time()))
                sp.write_text(json.dumps(st), encoding="utf-8")
    except Exception as e:
        (ROOT / "musicvideos" / mvid / "cut" / "_status.json").write_text(json.dumps({"state": "error", "error": str(e)[:400], "ts": int(time.time())}), encoding="utf-8")
    rebuild_bg()


XASM_TARGETS = ("draft", "youtube", "suno", "hooks")  # 🎞 saga-chapter final cut (tools/saga_assemble.py), same buttons as the music-video one


def xasm_dir(saga, ch):
    if not re.fullmatch(r"[\w.-]+", str(saga)) or not re.fullmatch(r"ch\d\d", str(ch)):
        return None
    d = ROOT / "explore" / "sagas" / str(saga) / str(ch)
    return d if (d / "episode.json").is_file() else None


def xasm_label(k):
    saga, ch, target = (k.split(":", 1)[1].split("|") + ["", "", ""])[:3]
    ch = ("music video " + ch) if k.startswith("xmv:") else ch
    title = (load_json(ROOT / "explore" / "sagas" / saga / "saga.json", {}) or {}).get("title", saga)
    return f"{title} {ch} ({ {'full': 'YouTube', 'youtube': 'YouTube', 'suno': 'Suno', 'hooks': 'hooks', 'draft': 'draft'}.get(target, target)})"


def xmusic_write(d, fn):
    """edit chNN/episode.json reel.music through fn(music dict or None) -> new dict or None (atomic write); returns the new value"""
    f = d / "episode.json"
    ep = load_json(f, {}) or {}
    reel = ep.get("reel") if isinstance(ep.get("reel"), dict) else {}
    new = fn(reel.get("music") if isinstance(reel.get("music"), dict) else None)
    if new is None:
        reel.pop("music", None)
    else:
        reel["music"] = new
    if reel:
        ep["reel"] = reel
    else:
        ep.pop("reel", None)
    save_json(f, ep)
    return new


def xmusic_clean(m, body):
    m = dict(m or {})
    if body.get("clip_sound") in ("off", "low", "full"):
        m["clip_sound"] = body["clip_sound"]
    if body.get("offset") is not None:
        try:
            m["offset"] = round(max(0.0, min(36000.0, float(body["offset"]))), 2)
        except (TypeError, ValueError):
            pass
    return m


def ffprobe_path():
    from config import FFPROBE
    return FFPROBE


def xmv_saga(saga):
    if not re.fullmatch(r"[\w.-]+", str(saga)):
        return None
    d = ROOT / "explore" / "sagas" / str(saga)
    return d if (d / "saga.json").is_file() else None


def xmv_range(spec):
    """'ch01-ch03' | 'ch02' -> the canonical range key, or None"""
    m = re.fullmatch(r"(ch\d\d)(?:-(ch\d\d))?", str(spec or "").strip().lower())
    if not m:
        return None
    a, b = m.group(1), m.group(2) or m.group(1)
    return a if a == b else (f"{a}-{b}" if a < b else f"{b}-{a}")


def xmv_write(d, fn):
    """edit saga.json `mv` through fn(dict) -> dict or None (None removes the key); returns the new value. (saga.json is also edited by tools/saga.py: read-modify-write, quick)"""
    f = d / "saga.json"
    sj = load_json(f, {}) or {}
    cur = sj.get("mv") if isinstance(sj.get("mv"), dict) else {}
    new = fn(dict(cur))
    if new:
        sj["mv"] = new
    else:
        sj.pop("mv", None)
    save_json(f, sj)
    return new


def xmv_clean(m, body):
    m = dict(m or {})
    if body.get("clip_sound") in ("off", "low", "full"):
        m["clip_sound"] = body["clip_sound"]
    if body.get("offset") is not None:
        try:
            m["offset"] = round(max(0.0, min(36000.0, float(body["offset"]))), 2)
        except (TypeError, ValueError):
            pass
    if body.get("chapters") is not None:
        r = xmv_range(body.get("chapters"))
        if r:
            m["chapters"] = r
    if body.get("length") is not None:
        sys.path.insert(0, str(Path(__file__).parent)); import saga_edit as _se
        ln = _se.parse_length(body.get("length"))
        if ln:
            m["length"] = _se.fmt_len(ln) if isinstance(body.get("length"), str) and ":" in body["length"] else ln
        elif str(body.get("length")).strip() == "":
            m.pop("length", None)
    return m


def xmv_queue(d, rng, target):
    """🎞 queue the saga-level music video build (tools/saga_assemble.py <saga> --chapters <rng>)"""
    (d / "cut").mkdir(exist_ok=True)
    (d / "cut" / "_status.json").write_text(json.dumps({"state": "queued", "target": target, "range": rng, "stage": "waiting in the queue", "ts": int(time.time())}), encoding="utf-8")
    k = f"xmv:{d.name}|{rng}|{target}"
    if k not in REROLLS:
        REROLLS.append(k)
    REROLL_WAKE.set()
    log({"event": "explore_assemble", "saga": d.name, "range": rng, "target": target, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    rebuild_bg()
    return k


def xmv_run(key):
    saga, rng, target = key[len("xmv:"):].split("|")
    sp = ROOT / "explore" / "sagas" / saga / "cut" / "_status.json"
    try:
        r = subprocess.run([PY, str(ROOT / "tools" / "saga_assemble.py"), f"explore/sagas/{saga}", "--chapters", rng, "--target", target, "--no-gallery"], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            st = load_json(sp, {}) or {}
            if st.get("state") != "error":
                st.update(state="error", stage="failed", msg=((r.stderr or r.stdout or "").strip().splitlines() or ["no output"])[-1][:400], ts=int(time.time()))
                sp.write_text(json.dumps(st), encoding="utf-8")
    except Exception as e:
        sp.write_text(json.dumps({"state": "error", "target": target, "msg": str(e)[:400], "ts": int(time.time())}), encoding="utf-8")
    rebuild_bg()


def xasm_queue(d, target):
    """🎞 queue a saga-chapter final-cut build: chNN/cut/_status.json says queued until the worker starts tools/saga_assemble.py (which keeps it updated)"""
    (d / "cut").mkdir(exist_ok=True)
    (d / "cut" / "_status.json").write_text(json.dumps({"state": "queued", "target": target, "stage": "waiting in the queue", "ts": int(time.time())}), encoding="utf-8")
    k = f"xasm:{d.parent.name}|{d.name}|{target}"
    if k not in REROLLS:
        REROLLS.append(k)
    REROLL_WAKE.set()
    log({"event": "explore_assemble", "saga": d.parent.name, "chapter": d.name, "target": target, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    rebuild_bg()
    return k


def xasm_run(key):
    saga, ch, target = key[len("xasm:"):].split("|")
    sp = ROOT / "explore" / "sagas" / saga / ch / "cut" / "_status.json"
    try:
        r = subprocess.run([PY, str(ROOT / "tools" / "saga_assemble.py"), f"explore/sagas/{saga}/{ch}", "--target", target, "--no-gallery"], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            st = load_json(sp, {}) or {}
            if st.get("state") != "error":
                st.update(state="error", stage="failed", msg=((r.stderr or r.stdout or "").strip().splitlines() or ["no output"])[-1][:400], ts=int(time.time()))
                sp.write_text(json.dumps(st), encoding="utf-8")
    except Exception as e:
        sp.write_text(json.dumps({"state": "error", "target": target, "msg": str(e)[:400], "ts": int(time.time())}), encoding="utf-8")
    rebuild_bg()


def reroll_worker():
    while True:
        REROLL_WAKE.wait()
        while REROLLS:
            key = REROLLS[0]
            up = key[len("upscale:"):] if key.startswith("upscale:") else None
            fit = key[len("refit:"):].split("|", 1) if key.startswith("refit:") else None
            fix = key[len("fixarea:"):].split("|", 2) if key.startswith("fixarea:") else None  # box@mtime|src|text, see /api/fix_area
            face = key[len("mvface:"):].split("|", 2) if key.startswith("mvface:") else None  # mode|mv|src: 🙂 face close-up
            if key.startswith("xmv:"):  # 🎞 the saga-level music video
                xmv_run(key)
                REROLLS.pop(0)
                continue
            if key.startswith("xasm:"):  # 🎞 tools/saga_assemble.py (NevNovella chapter final cut)
                xasm_run(key)
                REROLLS.pop(0)
                continue
            if key.startswith("mvasm:"):  # 🎞 tools/mv_assemble.py (ffmpeg, minutes)
                mv_asm_run(key)
                REROLLS.pop(0)
                continue
            if key.startswith("mvlyrics:"):  # 🎤 tools/mv_lyrics.py (CPU whisper), error text kept for the page
                mv_lyrics_run(key[len("mvlyrics:"):])
                REROLLS.pop(0)
                continue
            cmd = ([PY, str(ROOT / "tools" / "mv_face.py"), face[1], face[2], face[0]] if face else
                   [PY, str(ROOT / "tools" / "hires_card.py"), up, upscaled_path(up), "--size", "2048", "--denoise", "0.45", "--detail"] if up else
                   [PY, str(ROOT / "tools" / "refit.py"), fit[1], fit[0]] if fit else
                   [PY, str(ROOT / "tools" / "fix_area.py"), fix[1], *fix[0].split("@")[0].split(","), fix[2]]
                   + (["--if-mtime", fix[0].split("@")[1]] if "@" in fix[0] else []) if fix else
                   [PY, str(ROOT / "tools" / "ref_reroll.py"), key] if re.fullmatch(r"(?:musicvideos/[^/]+/refs|explore/[^/]+|explore/sagas/[^/]+/ch\d+)/[^/]+\.png", key) else
                   [PY, str(ROOT / "tools" / "run_journey.py"), "--reroll", key] if key.startswith(("journeys/", "musicvideos/")) else
                   [PY, str(ROOT / "tools" / "run_version.py"), "--reroll", key] + (["--fix"] if wants_fix(key) else []))
            PIPE.mkdir(parents=True, exist_ok=True)
            with open(PIPE / "worker.log", "a", encoding="utf-8") as out:  # failures used to vanish into DEVNULL
                out.write(f"\n== {time.strftime('%Y-%m-%d %H:%M:%S')} {key}\n")
                out.flush()
                try:
                    rc = subprocess.run(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT).returncode
                except OSError as e:  # e.g. no .venv yet: report it instead of killing the worker thread
                    out.write(f"could not start {cmd[0]}: {e}\n")
                    rc = 1
            if rc:
                print(f"worker job failed ({rc}): {key} (see feedback/pipeline/worker.log)", flush=True)
            REROLLS.pop(0)
        REROLL_WAKE.clear()


def render_worker():
    """🖨 the render queue (tools/render_queue.py): one job at a time through run_version.py; a job that was running when the
    server stopped is resumed (run_version skips finished images). Done -> a "render_done" event, the watcher's cue to review that set."""
    sys.path.insert(0, str(Path(__file__).parent)); import render_queue as RQ
    q = RQ.load()
    for j in q["jobs"]:
        if j["status"] == "running":
            j["status"] = "queued"
    RQ.save(q)
    while True:
        try:
            q = RQ.load()
            job = next((j for j in q["jobs"] if j["status"] == "queued"), None)
            if not job:
                time.sleep(5); continue
            job.update(status="running", started=time.strftime("%Y-%m-%d %H:%M:%S")); RQ.save(q)
            rc = subprocess.call([PY, "-u", "tools/run_version.py", *job["dirs"]], cwd=ROOT,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            q = RQ.load()
            for j in q["jobs"]:
                if j["id"] == job["id"]:
                    j.update(status="done" if rc == 0 else "failed", rc=rc, ended=time.strftime("%Y-%m-%d %H:%M:%S"))
            RQ.save(q)
            log({"event": "render_done", "job": job["id"], "label": job["label"], "dirs": job["dirs"], "rc": rc, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
        except Exception as e:
            print("render_worker:", e, flush=True); time.sleep(10)


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
        if not isinstance(j, dict) or "pid" not in j or "items" not in j:
            continue  # not a job plan (e.g. a stray model_times.json)
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
    waiting = REROLLS[1:]  # REROLLS[0] is already running as its own pipeline job (except 🎤 lyrics: no plan of its own, so it is listed)
    if REROLLS and REROLLS[0].startswith(("mvlyrics:", "mvasm:", "xasm:", "xmv:")):
        waiting = REROLLS[:]
    if waiting:
        jobs.append({"pid": 0, "kind": "reroll-queue", "started": now,
                     "items": [{"kind": "image", "out": k, "status": "running" if k == REROLLS[0] and k.startswith(("mvlyrics:", "mvasm:", "xasm:", "xmv:")) else "queued",
                                "label": ("🎞 assembling " + xasm_label(k) if k.startswith(("xasm:", "xmv:")) else ("🎤 placing lyrics · " + k[9:] if k.startswith("mvlyrics:") else "🎞 assembling " + (load_json(ROOT / "musicvideos" / k[6:].split("|")[0] / "mv.json", {}) or {}).get("title", k[6:]) + " (" + {"full": "YouTube", "youtube": "YouTube", "suno": "Suno", "hooks": "hooks"}.get(k.split("|")[-1], k.split("|")[-1]) + ")" if k.startswith("mvasm:") else "✎ " + k.split("|")[1].split("/", 1)[1] if k.startswith("fixarea:") else "🙂 face close-up · " + k.split("|")[1] if k.startswith("mvface:") else "🎲 " + k.split("/", 1)[1])).replace("_seed1001", "")} for k in waiting]})
    # 🖨 sets waiting on the render worker: one queued row per image still to render
    try:
        sys.path.insert(0, str(Path(__file__).parent)); import render_queue as RQ
        rq_items = []
        for j in RQ.load()["jobs"]:
            if j["status"] != "queued":
                continue
            for d in j["dirs"]:
                p = load_json(ROOT / d / "params.json", {}) or {}
                for s in p.get("subjects", []):
                    for seed in p.get("seeds", [1001]):
                        if not (ROOT / d / f"{s}_seed{seed}.png").exists():
                            rq_items.append({"kind": "image", "model": "QI2.1", "status": "queued", "out": f"{d}/{s}_seed{seed}.png",
                                             "label": f"🖨 {j['label']} · {d.split('/')[1]} · {s}"})
        if rq_items:
            jobs.append({"pid": 0, "kind": "render-queue", "started": now, "items": rq_items})
    except Exception as e:
        print("render queue listing:", e, flush=True)
    # averages from GPU time only (gsecs); submit-to-done "secs" include waiting in a shared queue
    done = [it for j in jobs for it in j["items"] if it["status"] == "done" and it.get("gsecs")]
    avg = {k: round(sum(x) / len(x)) if (x := [it["gsecs"] for it in done if it["kind"] == k]) else d
           for k, d in (("image", 25), ("video", 110))}
    sys.path.insert(0, str(Path(__file__).parent)); import pipeline
    avgm = {m: round(sum(x) / len(x)) for m, x in pipeline.model_times().items() if x}  # per model (⚙ Queue chips + ETAs)
    return {"now": now, "jobs": jobs, "comfy": comfy, "avg": avg, "avgm": avgm, "foreign": foreign}


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
    for top in ("evolutions/", "journeys/", "musicvideos/", "explore/"):
        if top in src:
            return top + src.split(top, 1)[1]
    return src


def is_img(key):
    return key.startswith(("evolutions/", "journeys/", "musicvideos/", "explore/"))


def restore_revision(key, rev, root=None, now=None):
    """🕘 restore a past revision: swap <dir>/_rerolled/<stem>__<stamp>.png with the current <stem>.png (+ their workflow json).
    Nothing is deleted: the current picture goes into _rerolled/ under a fresh stamp, so a restore can be undone by restoring again.
    Returns {ok, rev: name of the new archive entry} or raises ValueError. Caller holds LOCK."""
    root = Path(root or ROOT).resolve()
    key, rev = norm(str(key)).replace("\\", "/"), norm(str(rev)).replace("\\", "/")
    cur, old = (root / key).resolve(), (root / rev).resolve()
    top = cur.relative_to(root).parts[0] if cur.is_relative_to(root) else ""
    if top not in ("evolutions", "journeys", "musicvideos") or len(cur.relative_to(root).parts) != 4 or cur.suffix != ".png" or not cur.is_file():
        raise ValueError("bad image")
    arch = cur.parent / "_rerolled"
    m = re.fullmatch(re.escape(cur.stem) + r"__(\d{8}-\d{6})\.png", old.name)
    if old.parent != arch or not m or not old.is_file():
        raise ValueError("bad revision")
    t = int(now if now is not None else time.time())
    while True:  # a fresh stamp that is free (two restores inside one second)
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(t))
        if not (arch / f"{cur.stem}__{stamp}.png").exists():
            break
        t += 1
    cwf, owf = cur.parent / f"{cur.stem}.workflow.json", arch / f"{cur.stem}.workflow__{m.group(1)}.json"
    cur.replace(arch / f"{cur.stem}__{stamp}.png")
    if cwf.exists():
        cwf.replace(arch / f"{cur.stem}.workflow__{stamp}.json")
    old.replace(cur)
    if owf.exists():
        owf.replace(cwf)
    os.utime(cur, None)  # thumbnails and ?v= follow the mtime
    meta = cur.parent / ("params.json" if top == "evolutions" else "chapter.json")
    if meta.exists():
        try:
            raw = json.loads(meta.read_text(encoding="utf-8"))
            raw.setdefault("restores", {}).setdefault(cur.name, []).append({"from": old.name, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
            meta.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        except (OSError, ValueError):
            pass
    return {"ok": True, "archived": f"{cur.stem}__{stamp}.png", "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t)), "mtime": int(cur.stat().st_mtime)}


def scene_png(f):
    """a journey scene (journeys/NNN/chNN/sN.png) or a music-video storyboard frame (musicvideos/NNN/sbNN/sN.png)"""
    return ((f.is_relative_to(ROOT / "journeys") and f.parent.name.startswith("ch")) or
            (f.is_relative_to(MVDIR) and f.parent.name.startswith("sb"))) and f.stem.startswith("s")


def explore_png(f):
    """a 🌌 Explore shot (explore/NNN-slug/eN.png with its saved graph): 🎲 reroll goes through tools/ref_reroll.py"""
    return (f.is_relative_to(ROOT / "explore") and (f.parent.parent == ROOT / "explore" or f.parent.parent.parent.parent == ROOT / "explore" and f.parent.parent.parent.name == "sagas")  # 📖 saga chapter: explore/sagas/NNN/chNN/eN.png
            and f.with_name(f.stem + ".workflow.json").is_file())


ENGAGE_ACTS = {"auto", "next", "skip", "back", "jump", "close"}


def engage_clean(events):
    """the player's engagement rows -> validated dicts (src must be an explore png path; numbers clamped; at most 200 per post)"""
    out = []
    for e in (events if isinstance(events, list) else [])[:200]:
        if not isinstance(e, dict):
            continue
        src = norm(str(e.get("src", "")))
        if not re.fullmatch(r"explore/(sagas/[\w.-]+/ch\d+|[\w.-]+)/e\d+\.png", src) or e.get("act") not in ENGAGE_ACTS:
            continue
        try:
            row = {"src": src, "act": e["act"], "dwell": max(0, min(3_600_000, int(e.get("dwell") or 0))), "read": max(0, min(600_000, int(e.get("read") or 0))),
                   "beats": max(0, min(20, int(e.get("beats") or 0))), "seen": max(0, min(20, int(e.get("seen") or 0))), "paused": max(0, min(3_600_000, int(e.get("paused") or 0)))}
        except (TypeError, ValueError):
            continue
        out.append(row)
    return out


def explore_api(body, ts, by="gallery"):
    """POST /api/explore: start | continue | stop; returns {state, episodes}"""
    sys.path.insert(0, str(Path(__file__).parent)); import explore_state
    path, op = FB / "explore.json", str(body.get("op", ""))
    tune = explore_state.clean_tune(body)  # presence knob, maturity dial, emotion atlas value, stacked cores, formality atlas value
    steer = lambda st: {k: st.get(k) for k in explore_state.STEER_KEYS}  # noqa: E731
    if op == "start":
        st = explore_state.start(path, by, tune=tune)
        log({"event": "explore", "kind": "start", "seed": str(body.get("seed") or "").strip()[:2000], "until": st["until"], **steer(st), "ts": ts})
    elif op == "continue":
        st = explore_state.cont(path, by, tune=tune)
        save_saga_cores(st)
        log({"event": "explore", "kind": "continue", "until": st["until"], **steer(st), "ts": ts})
    elif op == "tune":  # informational: Claude reads it from explore.json / `feedback.py explore` before the next episode
        st = explore_state.tune(path, by, values=tune)
        save_saga_cores(st)
        log({"event": "explore", "kind": "tune", **steer(st), "ts": ts})
    elif op == "stop":
        st = explore_state.stop(path, by)
        log({"event": "explore", "kind": "stop", "ts": ts})
    elif op == "atlas_add":  # the user typed a feeling the Emotion / Formality Atlas has no node for: [ACT] Claude adds the node with atlas.py <kind> add
        import atlas as fa
        text = " ".join(str(body.get("text") or "").split())[:200]
        kind = "emotion" if body.get("atlas") == "emotion" else "formality"
        if len(text) < 2:
            return None
        req = fa.add_request(ROOT, text, ts, kind)
        if req.get("new"):  # a fresh request (an identical open one is not logged twice)
            log({"event": "explore", "kind": "atlas_add", "atlas": kind, "text": text, "id": req["id"], "ts": ts})
        return {"state": explore_state.state(path), "episodes": explore_state.episodes(ROOT), "atlas_request": req}
    elif op == "atlas_reset":  # the gallery's two-click "Factory reset" on an atlas map: backup first, then synapses back to factory (added nodes kept unless remove_added)
        if by != "gallery":    # same-origin browser fetches only (Sec-Fetch-Site: same-origin)
            return None
        import atlas as fa
        kind = "emotion" if body.get("atlas") == "emotion" else "formality"
        path_ = fa.atlas_path(kind, ROOT)
        bk = fa.backup_atlas(kind, ROOT)
        a = fa.load(path_, kind)
        summ = fa.reset_atlas(a, bool(body.get("remove_added")))
        fa.save(a, path_)
        log({"event": "atlas_reset", "atlas": kind, "backup": bk.name, "removed": summ["removed_nodes"], "ts": ts})
        return {"ok": True, "atlas": kind, "backup": bk.name, "summary": summ, "state": explore_state.state(path), "episodes": explore_state.episodes(ROOT)}
    elif op in ("music_set", "music_clear"):  # 🎵 the chapter's song (uploaded by the user): options / remove; the file lives in chNN/cut/
        d = xasm_dir(body.get("saga"), body.get("chapter"))
        if not d:
            return None
        if op == "music_clear":
            cur = xmusic_write(d, lambda m: None)
            for old in (d / "cut").glob("music.*"):
                old.unlink(missing_ok=True)
        else:
            cur = xmusic_write(d, lambda m: xmusic_clean(m, body) if m and m.get("file") else m)
        log({"event": "explore_music", "saga": d.parent.name, "chapter": d.name, "op": op, "ts": ts})
        return {"music": cur, "state": explore_state.state(path), "episodes": explore_state.episodes(ROOT)}
    elif op in ("mv_set", "mv_music_clear"):  # 🎞 the saga-level music video: range / song length / clip sound / offset; remove its song
        d = xmv_saga(body.get("saga"))
        if not d:
            return None
        if op == "mv_music_clear":
            def clr(m):
                m.pop("music", None)
                return m
            cur = xmv_write(d, clr)
            for old in (d / "cut").glob("music.*"):
                old.unlink(missing_ok=True)
        else:
            cur = xmv_write(d, lambda m: xmv_clean(m, body))
        log({"event": "explore_music", "saga": d.name, "op": op, "ts": ts})
        return {"mv": cur, "state": explore_state.state(path), "episodes": explore_state.episodes(ROOT)}
    elif op == "assemble" and body.get("chapters"):  # 🎞 the saga-level music video build (chapters = the range)
        d, rng, target = xmv_saga(body.get("saga")), xmv_range(body.get("chapters")), str(body.get("target") or "")
        if not d or not rng or target not in XASM_TARGETS:
            return None
        k = xmv_queue(d, rng, target)
        return {"queued": REROLLS.index(k) + 1 if k in REROLLS else 0, "state": explore_state.state(path), "episodes": explore_state.episodes(ROOT)}
    elif op == "assemble":  # 🎞 Final cut of a saga chapter: queue tools/saga_assemble.py on the reroll worker (informational event)
        d, target = xasm_dir(body.get("saga"), body.get("chapter")), str(body.get("target") or "")
        if not d or target not in XASM_TARGETS:
            return None
        k = xasm_queue(d, target)
        return {"queued": REROLLS.index(k) + 1 if k in REROLLS else 0, "state": explore_state.state(path), "episodes": explore_state.episodes(ROOT)}
    elif op == "animate":  # 🎬 Animate chapter on a saga chapter: [ACT] write per-shot motion + tools/animate_chapter.py, then feedback.py xanimreply
        sid, ch = str(body.get("saga", "")), str(body.get("chapter", ""))
        if not re.fullmatch(r"[\w.-]+", sid) or not re.fullmatch(r"ch\d\d", ch) or not (ROOT / "explore" / "sagas" / sid / ch / "episode.json").is_file():
            return None
        text = str(body.get("text", "")).strip()[:2000]
        reqs = load_json(EXPLORE_ANIM, [])
        r = {"id": f"a{len(reqs) + 1}", "kind": "animate", "saga": sid, "chapter": ch, "text": text, "ts": ts, "status": "open"}
        reqs.append(r)
        save_json(EXPLORE_ANIM, reqs)
        log({"event": "explore", "kind": "animate", "saga": sid, "chapter": ch, "text": text, "id": r["id"], "ts": ts})
        return {"animate_requests": reqs, "state": explore_state.state(path), "episodes": explore_state.episodes(ROOT)}
    else:
        return None
    return {"state": st, "episodes": explore_state.episodes(ROOT)}


def save_saga_cores(st):
    """the deck's cores + maturity belong to the CURRENT (newest) saga: a Continue / Apply saves them into its saga.json (history kept by core id)"""
    try:
        import saga
        sdir = saga.resolve(None, ROOT)
        saga.cores_set(sdir, st.get("cores") or [], st.get("maturity"), ROOT)
    except Exception as e:  # no saga yet (a new one starts with the deck's cores) or unreadable: nothing to save into
        if "no sagas yet" not in str(e):
            print("saga cores not saved:", e)


def atlas_sig(kind="formality"):
    """changes whenever an Atlas file is rewritten (the page refetches then)"""
    try:
        return str((ROOT / "explore" / ("emotion_atlas.json" if kind == "emotion" else "formality_atlas.json")).stat().st_mtime_ns)
    except OSError:
        return ""


def explore_learn(key, delta):
    """❤ / 👎 on an explore shot: strengthen / weaken the synapses between the nodes of the blends (emotion, its cores, formality) that episode was written with"""
    try:
        import atlas as fa
        n = fa.learn_from_mark(ROOT, key, delta, kind="formality") + fa.learn_from_mark(ROOT, key, delta, kind="emotion")
        if n:
            log({"event": "atlas_learn", "key": key, "delta": delta, "edges": n, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    except Exception as e:  # learning must never break a mark
        print("atlas learn failed:", e)


def ref_png(f):
    """a generated music-video reference (musicvideos/NNN/refs/<name>.png) with its saved graph: gets 🎲 / ✎ / ⤢ / ⬚ like a storyboard frame"""
    return f.is_relative_to(MVDIR) and f.parent.name == "refs" and f.parent.parent.parent == MVDIR and f.with_name(f.stem + ".workflow.json").is_file()


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


def ref_toggle(j, op, key, fallback):
    """⚓ toggle / 🗑 remove a reference in j["refs"] (journey.json or mv.json); `fallback` = what an emptied list becomes
    (a journey never has none: its source portrait; a music video may)"""
    refs = j.get("refs") or list(fallback)
    refs = [r for r in refs if r != key] if key in refs else (refs + [key] if op == "ref" else refs)
    j["refs"] = refs or list(fallback)
    if key not in j["refs"] and isinstance(j.get("ref_crop"), dict):
        j["ref_crop"].pop(key, None)  # un-anchored: its crop goes too
        if not j["ref_crop"]:
            del j["ref_crop"]
    for fld in ("ref_notes", "ref_for"):  # its note + target go too
        if key not in j["refs"] and isinstance(j.get(fld), dict):
            j[fld].pop(key, None)
            if not j[fld]:
                del j[fld]


def ref_set_crop(j, key, crop):
    rc = j.get("ref_crop") if isinstance(j.get("ref_crop"), dict) else {}
    if crop:
        rc[key] = crop
    else:
        rc.pop(key, None)
    if rc:
        j["ref_crop"] = rc
    else:
        j.pop("ref_crop", None)
    return rc


def ref_set_note(j, key, note, who, lead):
    """what a reference IS (ref_notes) + which character it is for (ref_for; the lead is the default)"""
    notes = j.get("ref_notes") if isinstance(j.get("ref_notes"), dict) else {}
    rf = j.get("ref_for") if isinstance(j.get("ref_for"), dict) else {}
    if note:
        notes[key] = note
    else:
        notes.pop(key, None)
    if who != lead:
        rf[key] = who
    else:
        rf.pop(key, None)
    for fld, val in (("ref_notes", notes), ("ref_for", rf)):
        if val:
            j[fld] = val
        else:
            j.pop(fld, None)
    return notes, rf


def mvdir(mv):
    """musicvideos/NNN-slug/ if it exists and has an mv.json (the id can't climb out of musicvideos/)"""
    d = (MVDIR / str(mv)).resolve()
    return d if d.parent == MVDIR.resolve() and (d / "mv.json").exists() else None


def mv_load(d):
    return {**json.loads((d / "mv.json").read_text(encoding="utf-8")), "id": d.name}


def mv_save(d, m):
    m = {k: v for k, v in m.items() if k != "id"}
    tmp = d / "mv.json.tmp"
    tmp.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(d / "mv.json")


def mv_duration(d):
    try:
        return float(json.loads((d / "audio" / "analysis.json").read_text(encoding="utf-8")).get("duration") or 0)
    except (OSError, ValueError, TypeError):
        return 0.0


def mv_new(title, refs, ts):
    """next free musicvideos/NNN-slug/ with a draft mv.json"""
    MVDIR.mkdir(exist_ok=True)
    nums = [int(x.name[:3]) for x in MVDIR.iterdir() if x.is_dir() and re.match(r"\d{3}-", x.name)]
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "music-video"
    d = MVDIR / f"{max(nums, default=0) + 1:03d}-{slug}"
    d.mkdir()
    mv_save(d, {"title": title or "Untitled music video", "idea": "", "lyrics": "", "status": "draft", "created": ts,
                "audio": None, "vocals": None, "refs": refs, "markers": [], "ref_requests": [],
                "name": "", "style": "", "character": "", "world": "", "cast": {}, "ref_resolution": 512})
    return d


REBUILD = threading.Lock()


RB_WAITING = threading.Event()


def rebuild_bg():
    """refresh gallery/data.json (new mv, finished analysis, mv edits) without holding up the request; calls that land while
    one rebuild is already waiting for the lock merge into it"""
    if RB_WAITING.is_set():
        return
    RB_WAITING.set()

    def run():
        with REBUILD:
            RB_WAITING.clear()  # changes from here on start the next rebuild
            try:
                importlib.reload(sys.modules.get("build_gallery") or __import__("build_gallery")).main()
            except Exception:
                pass  # the next render rebuild picks it up anyway
    threading.Thread(target=run, daemon=True).start()


AUDIO_EXT = ("mp3", "wav", "flac", "m4a", "ogg", "opus", "aac")


def _run_err(cmd, err, ok_file):
    """run a tool under ComfyUI's python; its last output line goes to `err` (the page shows it instead of "Analysing…" forever)"""
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode or not ok_file.exists():
        err.write_text(((r.stderr or r.stdout or "").strip().splitlines() or ["no output"])[-1][:400], encoding="utf-8")


def mv_analyze_run(d):
    m, err = mv_load(d), d / "audio" / "analysis_error.txt"
    err.unlink(missing_ok=True)
    if m.get("audio"):
        _run_err([GPY, str(ROOT / "tools" / "mv_analyze.py"), str(ROOT / m["audio"]), str(d / "audio" / "analysis.json")], err, d / "audio" / "analysis.json")


STEMS_RUN = threading.Lock()


def mv_stems_run(d):
    """stems -> audio/stems.json (tools/mv_stems.py); needs the song's analysis.json for sections when there is one"""
    err = d / "audio" / "stems_error.txt"
    with STEMS_RUN:
        err.unlink(missing_ok=True)
        (d / "audio" / "stems.json").unlink(missing_ok=True)
        _run_err([GPY, str(ROOT / "tools" / "mv_stems.py"), str(d)], err, d / "audio" / "stems.json")


def mv_analyze_bg(d):
    """waveform + beats + sections for the timeline (tools/mv_analyze.py under ComfyUI's python), off the request thread;
    stems (if any) are re-checked against the new song afterwards"""
    def run():
        mv_analyze_run(d)
        if mv_load(d).get("stems"):
            mv_stems_run(d)
        rebuild_bg()
    threading.Thread(target=run, daemon=True).start()


def stems_mixdown(d, files):
    """all stems summed (no normalisation, aligned at t=0) -> audio/song.wav, 48 kHz 16-bit stereo, soft-limited against clipping"""
    n = len(files)
    cmd = [FFMPEG, "-y", "-loglevel", "error"]
    for f in files:
        cmd += ["-i", str(f)]
    fmt = "".join(f"[{i}:a]aformat=sample_rates=48000:channel_layouts=stereo:sample_fmts=fltp[a{i}];" for i in range(n))
    cmd += ["-filter_complex", fmt + "".join(f"[a{i}]" for i in range(n)) + f"amix=inputs={n}:normalize=0:duration=longest,alimiter=limit=0.95:level=0",
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(d / "audio" / "song.wav")]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(((r.stderr or "").strip().splitlines() or ["ffmpeg failed"])[-1][:300])


def mv_stems_bg(d, analyze=False, mixdown=False):
    """after a stems zip: [mixdown of the stems ->] [song analysis ->] stems analysis, off the request thread"""
    def run():
        ad = d / "audio"
        try:
            if mixdown:
                stems_mixdown(d, sorted(p for p in (ad / "stems").iterdir() if p.is_file()))
                with LOCK:
                    m = mv_load(d)
                    m["audio"] = f"musicvideos/{d.name}/audio/song.wav"
                    mv_save(d, m)
            if analyze:
                mv_analyze_run(d)
            elif mv_load(d).get("audio"):  # a song kept from before: its analysis may still be running from that upload
                for _ in range(300):
                    if (ad / "analysis.json").exists() or (ad / "analysis_error.txt").exists():
                        break
                    time.sleep(2)
        except Exception as e:
            (ad / "analysis_error.txt").write_text(f"mixdown of the stems failed: {e}"[:400], encoding="utf-8")
            rebuild_bg()
            return
        mv_stems_run(d)
        rebuild_bg()
    threading.Thread(target=run, daemon=True).start()


def mv_stems_ingest(d, zpath):
    """a stems zip is enough on its own: audio files -> audio/stems/, the full-mix file (or a mixdown of all stems)
    becomes the song and the LEAD vocal stem becomes the vocals, unless the user uploaded their own song/vocals by hand
    (audio_from / vocals_from record where a file came from). -> (mv, analyze song?, mixdown?)"""
    import shutil
    import mv_stems
    ad = d / "audio"
    new = ad / "stems.new"
    shutil.rmtree(new, ignore_errors=True)
    try:
        files = sorted(mv_stems.extract_audio_zip(zpath, new), key=str.lower)
    except Exception:
        shutil.rmtree(new, ignore_errors=True)
        raise
    if not files:
        shutil.rmtree(new, ignore_errors=True)
        raise ValueError("no audio files in the zip")
    by = {Path(f).stem: f for f in files}
    with LOCK:
        m = mv_load(d)
        mix = mv_stems.pick_mix(list(by), m.get("title", ""))
        lead = mv_stems.pick_lead([n for n in by if n != mix])
        own_song = bool(m.get("audio")) and not str(m.get("audio_from", "")).startswith("stems")
        own_voc = bool(m.get("vocals")) and m.get("vocals_from") != "stems"
        info, analyze, mixdown = {}, False, False
        if mix:
            mixf = new / by[mix]
            if own_song:
                mixf.unlink()
                info["song"] = "your uploaded song (kept)"
            else:
                for old in ad.glob("song.*"):
                    old.unlink(missing_ok=True)
                dst = ad / ("song" + mixf.suffix.lower())
                shutil.move(str(mixf), str(dst))
                m["audio"], m["audio_from"] = f"musicvideos/{d.name}/audio/{dst.name}", "stems-mix-file"
                info["song"], analyze = f"{by[mix]} (the full mix in the zip)", True
            files.remove(by[mix])
        elif own_song:
            info["song"] = "your uploaded song (kept)"
        else:
            for old in ad.glob("song.*"):
                old.unlink(missing_ok=True)
            m["audio"], m["audio_from"] = None, "stems-mixdown"
            info["song"], analyze, mixdown = f"mixdown of {len(files)} stems", True, True
        if analyze:
            (ad / "analysis.json").unlink(missing_ok=True)
        if lead and not own_voc:
            for old in ad.glob("vocals.*"):
                old.unlink(missing_ok=True)
            dst = ad / ("vocals" + Path(by[lead]).suffix.lower())
            shutil.copy2(new / by[lead], dst)
            m["vocals"], m["vocals_from"] = f"musicvideos/{d.name}/audio/{dst.name}", "stems"
            info["vocals"] = by[lead]
        elif own_voc:
            info["vocals"] = "your uploaded vocals (kept)"
        else:
            if m.get("vocals_from") == "stems":  # the previous zip's lead vocal, and this zip has none
                for old in ad.glob("vocals.*"):
                    old.unlink(missing_ok=True)
            m["vocals"] = None
            m.pop("vocals_from", None)
            info["vocals"] = None
        shutil.rmtree(ad / "stems", ignore_errors=True)
        new.rename(ad / "stems")
        for f in ("stems.json", "stems_error.txt"):
            (ad / f).unlink(missing_ok=True)
        (ad / "analysis_error.txt").unlink(missing_ok=True)
        m["stems"] = [{"name": Path(f).stem, "file": f"musicvideos/{d.name}/audio/stems/{f}"} for f in files]
        m["stems_info"] = info
        mv_save(d, m)
        log({"event": "mv_upload", "mv": d.name, "kind": "stems", "files": len(files), "song": info.get("song"), "vocals": info.get("vocals"),
             "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    return m, analyze, mixdown


MEDIA_EXT = (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".flac", ".wav", ".mp3", ".m4a", ".ogg", ".opus", ".aac")
THUMB = 640  # tile slider tops out at 520 css px



def pinned_cut(f, path):
    """a music-video cut asked for as ?v=<mtime> of an EARLIER build: serve that build from cut/_old/ (mv_assemble keeps the last few),
    so a player that started before a rebuild keeps reading the same bytes (otherwise a draft replaced
    under a playing <video> corrupts playback)."""
    m = re.search(r"[?&]v=(\d+)", path)
    if not m or f.parent.name != "cut" or not f.is_file() or int(f.stat().st_mtime) == int(m.group(1)):
        return f
    old = f.parent / "_old" / f"{f.stem}__{m.group(1)}{f.suffix}"
    return old if old.is_file() else f


def housekeeper():
    """🧹 once a day: tools/housekeeping.py prunes _rerolled revisions > 30 days and 👎 clips > 7 days, keeping each one's lesson
    (prompt, marks, comments, a small preview) in feedback/discards.jsonl first"""
    time.sleep(120)  # let the server settle first
    while True:
        try:
            r = subprocess.run([sys.executable, str(ROOT / "tools" / "housekeeping.py")], cwd=ROOT, capture_output=True, text=True, timeout=1800,
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            with (ROOT / "feedback" / "housekeeping.log").open("a", encoding="utf-8") as fh:
                fh.write(time.strftime("%Y-%m-%d %H:%M:%S ") + (r.stdout or r.stderr).strip()[-500:] + "\n")
        except Exception as e:
            print("housekeeping:", e)
        time.sleep(24 * 3600)

class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, ".flac": "audio/flac", ".wav": "audio/wav",
                      ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".ogg": "audio/ogg", ".opus": "audio/ogg", ".aac": "audio/aac"}

    def log_message(self, *args):
        pass

    def end_headers(self):
        # media keep their bytes in the browser cache and only revalidate (a cheap 304 via Last-Modified; rerolls keep the
        # file name but change the mtime); everything else stays no-store. no-store on every png made each live redraw
        # re-download every visible 2 MB image
        media = self.path.split("?")[0].lower().endswith(MEDIA_EXT)
        self.send_header("Cache-Control", "no-cache" if media else "no-store")
        if media:
            self.send_header("Accept-Ranges", "bytes")
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
        # stamped with the SOURCE mtime and rebuilt on any difference: a restored older file (copy2 keeps its old mtime)
        # kept the newer thumbnail when this compared 'older than'
        if not dst.exists() or abs(dst.stat().st_mtime - mt) > 0.001:
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
            os.utime(dst, (mt, mt))
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
        if self.path.startswith("/api/explore/atlas"):
            sys.path.insert(0, str(Path(__file__).parent)); import atlas as _atlas
            kind = "emotion" if "kind=emotion" in self.path else "formality"   # no kind = the formality atlas (as before)
            return self.send_json(_atlas.load(_atlas.atlas_path(kind, ROOT), kind))
        if self.path.startswith("/api/explore"):
            sys.path.insert(0, str(Path(__file__).parent)); import explore_state, atlas as _atlas
            return self.send_json({"state": explore_state.state(FB / "explore.json"), "episodes": explore_state.episodes(ROOT), "atlas_sig": atlas_sig(),
                                   "emotion_atlas_sig": atlas_sig("emotion"), "atlas_requests": _atlas.open_requests(ROOT),
                                   "animate_requests": load_json(EXPLORE_ANIM, [])})
        if self.path.startswith("/api/mv"):
            with LOCK:
                return self.send_json({"mvs": [mv_load(x.parent) for x in sorted(MVDIR.glob("*/mv.json"), reverse=True)] if MVDIR.exists() else [],
                                       "requests": load_json(MVS, [])})
        if self.path.startswith("/api/blur"):
            with LOCK:
                return self.send_json(load_json(BLUR, {}))
        if self.send_range():  # media (ranged or whole) streamed by us: the file is opened per chunk, never held
            return
        return super().do_GET()

    def send_range(self):
        """HTTP Range for media (206 Partial Content) so <audio>/<video> can seek (Firefox + Chrome need it for the music-video
        timeline). False = not a ranged media file; the static handler answers instead."""
        f = Path(self.translate_path(self.path.split("?")[0]))
        f = pinned_cut(f, self.path)
        if not f.is_file() or f.suffix.lower() not in MEDIA_EXT + (".webm",):
            return False
        size = f.stat().st_size
        if not self.headers.get("Range"):  # whole video/audio file, 200 (a download / a player without ranges); images stay
            if f.suffix.lower() not in (".mp4", ".webm", ".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac"):
                return False  # with the static handler (its 304 revalidation)
            self.send_response(200)
            self.send_header("Content-Type", self.guess_type(str(f)))
            self.send_header("Content-Length", str(size))
            self.send_header("Last-Modified", self.date_time_string(int(f.stat().st_mtime)))
            self.end_headers()
            self.stream(f, 0, size - 1)
            return True
        m = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", "").strip())
        if not m:
            return False
        a, b = m.groups()
        lo, hi = (size - int(b), size - 1) if not a and b else (int(a or 0), int(b) if b else size - 1)
        hi = min(hi, size - 1, lo + 8 * 1024 * 1024 - 1)  # <= 8 MB per response: the file handle is held only briefly, so a rebuild
        # can swap the file on Windows (an open handle blocks os.replace); players simply ask for the next range
        if lo > hi or lo >= size:
            self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers()
            return True
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(f)))
        self.send_header("Content-Range", f"bytes {lo}-{hi}/{size}")
        self.send_header("Content-Length", str(hi - lo + 1))
        self.send_header("Last-Modified", self.date_time_string(int(f.stat().st_mtime)))
        self.end_headers()
        self.stream(f, lo, hi)
        return True

    def stream(self, f, lo, hi, step=1024 * 1024):
        """send bytes lo..hi, reopening the file for every 1 MB: on Windows an open handle blocks os.replace, and a slow client
        (a phone on Wi-Fi) would otherwise keep the final cut locked for the whole transfer"""
        pos = lo
        while pos <= hi:
            try:
                with f.open("rb") as fh:
                    fh.seek(pos)
                    chunk = fh.read(min(step, hi - pos + 1))
            except OSError:
                return
            if not chunk:
                return
            self.wfile.write(chunk)  # the handle is already closed while the client reads
            pos += len(chunk)

    def mv_upload(self):
        """POST /api/mv/upload?mv=ID&kind=audio|vocals&name=song.mp3, raw body: saved as audio/song.<ext> | vocals.<ext>"""
        from urllib.parse import parse_qs, urlparse
        q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        n, d = int(self.headers.get("Content-Length") or 0), mvdir(q.get("mv"))
        ext, kind = os.path.splitext(q.get("name", ""))[1].lower().lstrip("."), q.get("kind")
        stems = kind == "stems"  # a zip of the separate tracks: up to 1.5 GB, streamed to disk
        if not d or kind not in ("audio", "vocals", "stems") or ext not in (("zip",) if stems else AUDIO_EXT) \
                or not 0 < n <= (1536 if stems else 200) * 1024 * 1024:
            return self.send_json({"error": "bad request"}, 400)
        stem = "stems" if stems else "song" if kind == "audio" else "vocals"
        ad = d / "audio"
        ad.mkdir(exist_ok=True)
        tmp = ad / f"{stem}.upload.tmp"
        left = n
        with tmp.open("wb") as fh:
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                fh.write(chunk)
                left -= len(chunk)
        if left:
            tmp.unlink(missing_ok=True)
            return self.send_json({"error": "short body"}, 400)
        if stems:
            try:
                m, analyze, mixdown = mv_stems_ingest(d, tmp)
            except Exception as e:
                return self.send_json({"error": f"couldn't read the zip: {e}"[:300]}, 400)
            finally:
                tmp.unlink(missing_ok=True)
            mv_stems_bg(d, analyze, mixdown)
            if m.get("vocals_from") == "stems":
                mv_lyrics_queue(d)  # the zip's lead vocal is the vocals: time the lyrics against it
            rebuild_bg()
            return self.send_json({"mv": m, "requests": load_json(MVS, [])})
        with LOCK:
            for old in ad.glob(f"{stem}.*"):
                if old != tmp:
                    old.unlink(missing_ok=True)
            dst = ad / f"{stem}.{ext}"
            tmp.replace(dst)
            m = mv_load(d)
            m["audio" if kind == "audio" else "vocals"] = f"musicvideos/{d.name}/audio/{dst.name}"
            m.pop("audio_from" if kind == "audio" else "vocals_from", None)  # hand-uploaded: a later stems zip won't replace it
            (m.get("stems_info") or {}).pop("song" if kind == "audio" else "vocals", None)
            mv_save(d, m)
            if kind == "audio":
                (ad / "analysis.json").unlink(missing_ok=True)  # the old song's waveform
            log({"event": "mv_upload", "mv": d.name, "kind": kind, "file": dst.name, "bytes": n, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
        if kind == "audio":
            mv_analyze_bg(d)
        else:
            mv_lyrics_queue(d)  # vocals uploaded: place the lyrics (no-op without lyrics)
            rebuild_bg()
        return self.send_json({"mv": m, "requests": load_json(MVS, [])})

    def explore_upload(self):
        """POST /api/explore/upload?saga=ID&chapter=chNN&kind=music&name=song.mp3, raw body (<= 200 MB): saved as chNN/cut/music.<ext>, recorded in episode.json reel.music"""
        from urllib.parse import parse_qs, urlparse
        q = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        mvlevel = not q.get("chapter")  # no chapter = the saga-level 🎞 music video's song
        n, d = int(self.headers.get("Content-Length") or 0), (xmv_saga(q.get("saga")) if mvlevel else xasm_dir(q.get("saga"), q.get("chapter")))
        name = os.path.basename(q.get("name", ""))
        ext = os.path.splitext(name)[1].lower().lstrip(".")
        if not d or q.get("kind") != "music" or ext not in AUDIO_EXT or not 0 < n <= 200 * 1024 * 1024:
            return self.send_json({"error": "bad request"}, 400)
        cd = d / "cut"
        cd.mkdir(exist_ok=True)
        tmp = cd / "music.upload.tmp"
        left = n
        with tmp.open("wb") as fh:
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                fh.write(chunk)
                left -= len(chunk)
        if left:
            tmp.unlink(missing_ok=True)
            return self.send_json({"error": "short body"}, 400)
        with LOCK:
            for old in cd.glob("music.*"):
                if old != tmp:
                    old.unlink(missing_ok=True)
            dst = cd / f"music.{ext}"
            tmp.replace(dst)
            if mvlevel:
                dur = 0.0
                try:
                    dur = float(subprocess.run([ffprobe_path(), "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(dst)], capture_output=True, text=True).stdout.strip() or 0)
                except Exception:
                    pass
                cur = xmv_write(d, lambda m: {**m, "music": {"file": dst.name, "name": name[:120], "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "dur": round(dur, 2)}})["music"]
            else:
                cur = xmusic_write(d, lambda m: {**(m or {}), "file": dst.name, "name": name[:120], "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
            log({"event": "explore_music", "saga": q.get("saga"), "chapter": q.get("chapter") or "", "op": "upload", "file": dst.name, "bytes": n, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
        rebuild_bg()
        return self.send_json({"music": cur})

    def do_POST(self):
        if self.path.startswith("/api/explore/upload"):
            return self.explore_upload()
        if self.path.startswith("/api/mv/upload"):
            return self.mv_upload()
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            return self.send_json({"error": "bad json"}, 400)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.path == "/api/explore":
            # 🌌 start / continue / stop exploring: no Sec-Fetch guard (harmless; the timer caps what the agent writes unattended)
            with LOCK:
                res = explore_api(body, ts, "gallery" if self.headers.get("Sec-Fetch-Site") == "same-origin" else "api")
            return self.send_json(res if res else {"error": "bad request"}, 200 if res else 400)
        if self.path == "/api/revision/restore":
            # 🕘 restore a past revision: a swap, nothing is deleted
            try:
                with LOCK:
                    res = restore_revision(body.get("src", ""), body.get("rev", ""))
                    log({"event": "revision_restore", "src": norm(str(body.get("src", ""))), "rev": norm(str(body.get("rev", ""))), "ts": ts})
            except ValueError as e:
                return self.send_json({"error": str(e)}, 400)
            rebuild_bg()
            return self.send_json(res)
        if self.path == "/api/show/seen":
            # 🎞 what the slideshow dealt (a debug log): key + title + the page build, appended to feedback/show.jsonl; no log event
            row = {k: str(body.get(k, ""))[:200] for k in ("key", "title", "ui", "set")}
            if row["key"]:
                with LOCK, (FB / "show.jsonl").open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({**row, "ts": ts}, ensure_ascii=False) + "\n")
            return self.send_json({"ok": True})
        if self.path == "/api/reroll":
            key = norm(str(body.get("src", "")))
            f = (ROOT / key).resolve()
            ok_evo = f.is_relative_to(ROOT / "evolutions") and f.parent.name.startswith("v")
            ok_jrn = scene_png(f) or ref_png(f) or explore_png(f)
            if not ((ok_evo or ok_jrn) and f.suffix == ".png" and f.is_file()):
                return self.send_json({"error": "bad request"}, 400)
            if key not in REROLLS:
                REROLLS.append(key)
                REROLL_WAKE.set()
                log({"event": "reroll", "img": key, "ts": ts, "fix": wants_fix(key)})
            return self.send_json({"ok": True, "position": REROLLS.index(key)})
        if self.path == "/api/upscale":
            # ⤢ upscale: a 2048 px hi-res img2img pass of the image with its own prompt (tools/hires_card.py),
            # saved to _upscaled/; runs on the same one-at-a-time worker
            key = norm(str(body.get("src", "")))
            f = (ROOT / key).resolve()
            ok_evo = f.is_relative_to(ROOT / "evolutions") and f.parent.name.startswith("v")
            ok_jrn = scene_png(f) or ref_png(f)
            if not ((ok_evo or ok_jrn) and f.suffix == ".png" and f.is_file()):
                return self.send_json({"error": "bad request"}, 400)
            k = "upscale:" + key
        if self.path == "/api/explore/engage":
            # 📖 reader engagement from the Nev Novel player (make sure the story is entertaining): per shot left, how long it was on screen vs
            # its reading time, how far the lines got, and how it was left (auto / next / skip / back / pause). Appended to feedback/engage.jsonl; no log event
            rows = engage_clean(body.get("events"))
            if rows:
                with LOCK, (FB / "engage.jsonl").open("a", encoding="utf-8") as fh:
                    for r in rows:
                        fh.write(json.dumps({**r, "ts": ts}, ensure_ascii=False) + "\n")
            return self.send_json({"ok": True, "n": len(rows)})
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
            ok_jrn = scene_png(f) or ref_png(f)
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
            ok_jrn = scene_png(f) or ref_png(f)
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
            if not (any(f.is_relative_to(ROOT / a) for a in ("evolutions", "journeys", "musicvideos", "explore")) and f.suffix == ".mp4" and f.is_file()):
                return self.send_json({"error": "bad request"}, 400)
            if sys.platform == "win32":
                subprocess.Popen(f'explorer /select,"{f}"')
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(f)])
            else:
                subprocess.Popen(["xdg-open", str(f.parent)])
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
                if op in ("ref", "ref_remove"):  # ⚓ toggle / 🗑 remove only (a removed file may already be gone)
                    d, key = jdir(body.get("journey")), norm(str(body.get("src", "")))
                    if not d or not is_img(key) or (op == "ref" and not (ROOT / key).is_file()):
                        return self.send_json({"error": "bad request"}, 400)
                    j = json.loads((d / "journey.json").read_text(encoding="utf-8"))
                    ref_toggle(j, op, key, [j["source"]])  # never empty: the source portrait is the fallback identity
                    (d / "journey.json").write_text(json.dumps(j, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    log({"event": "journey-ref", "journey": d.name, "refs": j["refs"], "op": op, "src": key, "ts": ts})
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
                    rc = ref_set_crop(j, key, crop)
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
                    notes, rf = ref_set_note(j, key, note, who, j["name"])
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
                elif op == "animate":  # 🎬 Animate chapter: the coding agent writes motion + runs one run_video --batch
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
            if self.path == "/api/mv":
                return self.mv_post(body, ts)
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
                elif op == "order":  # drag-to-reorder in the tray: the first pin leads a cross (its subject, the diff base)
                    want = [norm(str(s)) for s in (body.get("srcs") or [])]
                    rank = {s: i for i, s in enumerate(want)}
                    pv["pins"] = sorted(pv["pins"], key=lambda p: rank.get(p["src"], len(want)))
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
                before = set(acts(state.get(key, {}))) & {"love", "nope"}
                if action == "clear":
                    state.pop(key, None)
                else:
                    cur = state.get(key, {})
                    a = acts(cur)
                    if cur.get("status") in ("sent", "done"):
                        # a new mark on an already-sent image: one-shot requests (🎬 🌱 🧬 👥) were already handled,
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
                if key.startswith("explore/") and action in ("love", "nope", "clear"):  # Formality Atlas learning: liked paths thicken, disliked ones thin
                    after = set(acts(state.get(key, {}))) & {"love", "nope"}
                    net = (("love" in after) - ("love" in before)) - (("nope" in after) - ("nope" in before))
                    if net:
                        explore_learn(key, 0.1 * net)
                return self.send_json(state)
        return self.send_json({"error": "not found"}, 404)

    def mv_post(self, body, ts):
        """🎵 music videos (called under LOCK): see the docstring; every op answers {mv, requests}"""
        reqs, op = load_json(MVS, []), body.get("op")
        bad = lambda msg="bad request": self.send_json({"error": msg}, 400)
        if op == "new":  # an empty music video (lyrics / idea first, references later)
            d = mv_new(str(body.get("title") or "").strip()[:80], [], ts)
            log({"event": "mv", "kind": "start", "mv": d.name, "images": [], "ts": ts})
            rebuild_bg()
            return self.send_json({"mv": mv_load(d), "requests": reqs})
        if op == "from_pins":  # the 📌 tray becomes a new mv's references, or is added to an existing one
            pv = load_json(PINS, {"pins": [], "directions": ""})
            imgs = [p["src"] for p in pv["pins"]]
            if not imgs:
                return bad("nothing pinned")
            if body.get("mv"):
                d = mvdir(body.get("mv"))
                if not d:
                    return bad()
                m = mv_load(d)
                m["refs"] = list(dict.fromkeys((m.get("refs") or []) + imgs))
            else:
                d = mv_new(str(body.get("title") or "").strip()[:80], list(dict.fromkeys(imgs)), ts)
                m = mv_load(d)
            mv_save(d, m)
            save_json(PINS, {"pins": [], "directions": ""})
            log({"event": "mv", "kind": "add_refs" if body.get("mv") else "start", "mv": d.name, "images": imgs, "ts": ts})
            rebuild_bg()
            return self.send_json({"mv": m, "requests": reqs})
        d = mvdir(body.get("mv"))
        if not d:
            return bad()
        m, key = mv_load(d), norm(str(body.get("src", "")))
        lyr_before = m.get("lyrics", "")
        if op == "save":
            for fld, cap in (("title", 120), ("idea", 5000), ("lyrics", 20000)):
                if isinstance(body.get(fld), str):
                    m[fld] = body[fld][:cap] if fld != "title" else (body[fld].strip()[:cap] or m.get("title", ""))
        elif op == "marker_set":
            mk, dur = body.get("marker") or {}, mv_duration(d)
            try:
                t0, t1 = round(float(mk.get("t0")), 2), round(float(mk.get("t1")), 2)
                emph = int(mk.get("emph") or 1)
            except (TypeError, ValueError):
                return bad()
            if dur:
                t0, t1 = max(0.0, min(t0, dur)), max(0.0, min(t1, dur))
            if t0 < 0 or t1 - t0 < 0.05:
                return bad("bad range")
            marks = m.get("markers") or []
            mid = str(mk.get("id") or "")
            if not any(x.get("id") == mid for x in marks):
                mid = "m%d" % (max([int(x["id"][1:]) for x in marks if re.fullmatch(r"m\d+", str(x.get("id")))] or [0]) + 1)
            new = {"id": mid, "t0": t0, "t1": t1, "lyric": str(mk.get("lyric") or "").strip()[:500],
                   "note": str(mk.get("note") or "").strip()[:1000], "emph": min(3, max(1, emph))}
            m["markers"] = sorted([x for x in marks if x.get("id") != mid] + [new], key=lambda x: (x["t0"], x["t1"]))
        elif op == "marker_del":
            m["markers"] = [x for x in m.get("markers") or [] if x.get("id") != body.get("id")]
        elif op == "lyrics_place":  # 🎤 (re)run tools/mv_lyrics.py; the answer arrives as audio/lyrics_timing.json
            if not mv_lyrics_queue(d):
                return bad("needs lyrics (Save them first) and the vocals or the song")
            return self.send_json({"mv": m, "requests": reqs})
        elif op == "assemble":  # 🎞 build on the reroll worker: target draft (1280x720, fast) | youtube (master) | suno (size-capped) | hooks (10-30 s pieces)
            if not m.get("audio") or not (d / "sb01" / "chapter.json").exists():
                return bad("needs the song and a storyboard (sb01)")
            target = body.get("target") or ("draft" if body.get("draft") else "youtube")
            if target not in MV_TARGETS:
                return bad("target must be one of " + ", ".join(MV_TARGETS))
            k = mv_asm_queue(d, target)
            return self.send_json({"mv": m, "requests": reqs, "queued": REROLLS.index(k) + 1 if k in REROLLS else 0})
        elif op == "stems_clear":  # 🎚 remove the stems (the song / vocals picked from them stay)
            import shutil
            shutil.rmtree(d / "audio" / "stems", ignore_errors=True)
            for f in ("stems.json", "stems_error.txt"):
                (d / "audio" / f).unlink(missing_ok=True)
            m.pop("stems", None)
            m.pop("stems_info", None)
        elif op in ("ref", "ref_remove"):
            if not is_img(key) or (op == "ref" and not (ROOT / key).is_file()):
                return bad()
            ref_toggle(m, op, key, [])
        elif op in ("ref_crop", "ref_note"):
            if key not in (m.get("refs") or []):
                return bad("not a reference of this music video")
            if op == "ref_crop":
                crop = valid_crop(body.get("crop"))
                if body.get("crop") is not None and crop is None:
                    return bad("bad crop")
                ref_set_crop(m, key, crop)
            else:
                lead = m.get("name") or "the singer"  # (the agent fills `name` before storyboarding)
                note, who = str(body.get("note", "")).strip()[:300], str(body.get("for", "")).strip() or lead
                who = lead if who == "the singer" else who
                if who != lead and who not in (m.get("cast") or {}):
                    return bad("unknown character")
                ref_set_note(m, key, note, who, lead)
        elif op == "face":  # 🙂 face close-up of a reference, rendered on the reroll worker -> added to refs
            mode = body.get("mode")
            if key not in (m.get("refs") or []) or mode not in ("same", "front"):
                return bad()
            if mode == "same" and not (m.get("ref_crop") or {}).get(key):
                return bad("crop the face first (✂), then 🙂 Same face")
            k = f"mvface:{mode}|{d.name}|{key}"
            if k not in REROLLS:
                REROLLS.append(k); REROLL_WAKE.set()
            log({"event": "mv_face", "mv": d.name, "src": key, "mode": mode, "ts": ts})
            return self.send_json({"mv": m, "requests": reqs, "queued": REROLLS.index(k) + 1 if k in REROLLS else 0})
        elif op == "cover":  # 🖼 a storyboard frame (or a reference) as the music video's card image; same again = unset
            if not (key.startswith(f"musicvideos/{d.name}/") or key in (m.get("refs") or [])) or not (ROOT / key).is_file():
                return bad()
            if m.get("cover") == key:
                m.pop("cover", None)
            else:
                m["cover"] = key
        elif op == "request_done":
            for r in m.get("ref_requests") or []:
                if r.get("id") == body.get("id"):
                    r["done"] = bool(body.get("done"))
        elif op == "ref_gen_request":  # 🖼 "request a reference" : the user asks in words, the agent writes the prompt + renders
            text = str(body.get("text", "")).strip()
            if not 1 <= len(text) <= 500:
                return bad("describe the image in 1-500 characters")
            lead = m.get("name") or "the singer"
            who = str(body.get("for", "")).strip()
            who = "" if who in ("", lead, "the singer") else who
            if who and who not in (m.get("cast") or {}):
                return bad("unknown character")
            from_ref = norm(str(body.get("src", ""))) if body.get("src") else ""  # the reference this request starts from (the ref's "Ask" box)
            if from_ref and from_ref not in (m.get("refs") or []):
                return bad("unknown reference")
            gr = m.get("gen_requests") or []
            gid = "g%d" % (max([int(x["id"][1:]) for x in gr if re.fullmatch(r"g\d+", str(x.get("id")))] or [0]) + 1)
            gr.append({"id": gid, "text": text, "for": who, "ts": ts, "status": "open", **({"src": from_ref} if from_ref else {})})
            m["gen_requests"] = gr
            log({"event": "mv", "kind": "ref_request", "mv": d.name, "id": gid, "text": text, "for": who, **({"src": from_ref} if from_ref else {}), "ts": ts})
        elif op == "ref_gen_cancel":
            hit = next((x for x in m.get("gen_requests") or [] if x.get("id") == body.get("id") and x.get("status") == "open"), None)
            if not hit:
                return bad("no such open request")
            hit["status"] = "cancelled"
            log({"event": "mv", "kind": "ref_request_cancel", "mv": d.name, "id": hit["id"], "ts": ts})
        elif op == "submit":
            text = str(body.get("text", "")).strip()
            m["status"] = "submitted"
            r = {"id": f"v{len(reqs) + 1}", "kind": "submit", "mv": d.name, "text": text, "ts": ts, "status": "sent"}
            reqs.append(r)
            save_json(MVS, reqs)
            log({"event": "mv", **{k: v for k, v in r.items() if k != "status"}})
        else:
            return bad()
        mv_save(d, m)
        if op == "save" and m.get("lyrics", "") != lyr_before:
            mv_lyrics_queue(d)  # new words -> new timing (when the vocals / song are there)
        if op.startswith("ref") and not op.startswith("ref_gen"):
            log({"event": "mv-" + op.replace("_", "-"), "mv": d.name, "src": key, "ts": ts})
        rebuild_bg()  # so the phone / another tab sees the change on its next poll
        return self.send_json({"mv": m, "requests": reqs})

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # emoji in log lines crash a cp1252 console
    except Exception:
        pass
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
    threading.Thread(target=render_worker, daemon=True).start()  # 🖨 tools/render_queue.py
    threading.Thread(target=housekeeper, daemon=True).start()
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
