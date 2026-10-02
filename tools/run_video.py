"""Animate a lab image with an image-to-video workflow (ComfyUI templates in workflows/base).

  .venv/Scripts/python tools/run_video.py <image.png> <engine> [--prompt "..."] [--seconds 5] [--seed 1001] [--out DIR]
  engines: fasth3 | h3turbo | ltx25 | wan22 | s2v | s2vfull | ltxia2v   (see ENGINES)
  more flags: --audio FILE (audio-driven engines), --reverse, --as-frame PNG, --song-at S, --lead-in S, --batch clips.json

fasth3 and h3turbo are the supported engines. ltx25, wan22, s2v, s2vfull and ltxia2v are OPTIONAL / EXPERIMENTAL: they need
extra (large) model files that a stock install does not have, and the run stops up front listing which ones are missing.
Model files: the templates name the stock files. When a stock name is not installed but a file with the same basename sits
in some sub-folder of that model folder, that path is used (see resolve_model()).

The template is converted with comfy-cli, then patched by node class (model/file names that differ on this
install, the start image, prompt, duration, aspect) and POSTed straight to ComfyUI, same as run_version.py.
The source image (and the audio of the audio-driven engines) is uploaded to ComfyUI via POST /upload/image
(no direct filesystem path into the ComfyUI install).
Writes <out>/<engine>_seed<seed>.mp4 and a matching .json sidecar (prompt, engine, timings).
"""
import argparse
import json
import mimetypes
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pipeline  # noqa: E402
from config import COMFY_CLI, COMFY_URL, FFMPEG, FFPROBE  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
COMFY = str(COMFY_CLI)
SERVER = COMFY_URL

# "vae"/"clip" = {template file: alternative}, "lora" = an optional turbo LoRA (file name, found by basename). A swap only
# happens when the template's own file isn't installed and the alternative is (see pick() / resolve_model()), so a stock
# install runs the templates as shipped.
ENGINES = {
    # FastVideo FastH3: MiniMax H3 distilled to 8 steps (newest, fastest). Only the video VAE name differs here.
    "fasth3": {"template": "video_fastvideo_fasth3_i2v", "family": "h3",
               "vae": {"minimax_h3_video_vae_int8_convrot.safetensors": "minimax_h3_video_vae_fp16.safetensors"}},
    # Full MiniMax H3 fl2va + the 4-step lightx2v turbo LoRA (the template expects an 8-step LoRA).
    "h3turbo": {"template": "video_minimax_h3_i2v", "family": "h3", "turbo_steps": 4,
                "vae": {"minimax_h3_video_vae_int8_convrot.safetensors": "minimax_h3_video_vae_fp16.safetensors"},
                "lora": "minimax_h3_fl2v_lightx2v_turbo_4step_v0.1_comfy_resized_avg_rank_21_bf16.safetensors"},
    # --- optional / experimental engines (extra models; the run lists what is missing) ---
    # LTX-2.5 22B distilled (int8) with its 2x latent upscaler.
    "ltx25": {"template": "video_ltx2_5_i2v", "family": "ltx",
              "vae": {"ltx-2.5-video-vae-bf16.safetensors": "ltx-2.5-video-vae-conv-bf16.safetensors"},
              "clip": {"gemma4_e2b_it_int8_convrot.safetensors": "gemma4-12b-with-proj-ltx-2.5-comfy-int8-convrot.safetensors"}},
    # AUDIO-DRIVEN engines need --audio: the clip lasts as long as the audio, the prompt is plain prose
    # (H3's structured format doesn't apply).
    # Wan2.2 S2V 14B + 4-step lightx2v LoRA: image + speech -> lip-synced talking/gesturing clip, 16 fps, 3 chained chunks.
    "s2v": {"template": "video_wan2_2_14B_s2v", "family": "s2v", "fps": 16},
    # the same S2V at full quality for singing: speed LoRA off (strength 0), the template's own no-LoRA settings
    # (20 steps, CFG 6), bigger frames. The 4-step run barely moves the mouth.
    "s2vfull": {"template": "video_wan2_2_14B_s2v", "family": "s2v", "fps": 16, "full": True},
    # Wan 2.2 14B image-to-video (high + low noise fp8) with the lightx2v 4-step LoRAs: 16 fps, plain-prose prompt,
    # no audio of its own (storyboard clips get the song).
    "wan22": {"template": "video_wan2_2_14B_i2v", "family": "wan", "fps": 16},
    # LTX-2.3 22B dev fp8 image+audio -> video (lip sync), distilled LoRA, 2x latent upscale; prompt enhancer off.
    "ltxia2v": {"template": "video_ltx2_3_ia2v", "family": "ia2v", "fps": 24},
}
AUDIO_FAMILIES = ("s2v", "ia2v")
SIZES = {"3:4 (Portrait Standard)": (480, 640), "4:3 (Standard)": (640, 480), "1:1 (Square)": (576, 576), "16:9 (Widescreen)": (704, 400)}
LTX_STRENGTH = None  # --ltx-strength / batch "ltx_strength"
AUDIO = {}  # set per clip: {"path": source file, "name": uploaded name, "seconds": duration}
MISSING = []  # (folder, file) pairs of the last patched graph that are not installed


def _upload(path, name, ctype):
    """POST /upload/image (multipart, overwrite=true) -> the name ComfyUI stored the file under. The endpoint takes any
    file, not just images. No direct filesystem access to the ComfyUI install: works against any ComfyUI at config.comfy_url."""
    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: {ctype}\r\n\r\n".encode(),
        Path(path).read_bytes(), f"\r\n--{boundary}--\r\n".encode()])
    req = urllib.request.Request(SERVER + "/upload/image", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())["name"]


def _stage_name(path, prefix):
    path = Path(path).resolve()
    try:
        parts = path.relative_to(ROOT).with_suffix("").parts[-3:]
    except ValueError:
        parts = (path.stem,)
    return (prefix + "_".join(parts)).replace("@", "_") + path.suffix


def upload_image(path):
    return _upload(path, _stage_name(path, "animestylelab_"), "image/png")


def stage_audio(path):
    """upload the driving audio like the image (ComfyUI's LoadAudio then finds it in its input folder)"""
    ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    return _upload(path, _stage_name(path, "animestylelab_audio_"), ctype)


def audio_seconds(path):
    out = subprocess.run([str(FFPROBE), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True)
    return float(out.stdout.strip())


def comfy_graph(template):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    out = subprocess.run([COMFY, "--json", "run", "--workflow", str(ROOT / "workflows" / "base" / f"{template}.template.json"),
                          "--print-prompt"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    s = out.stdout.strip()
    data = json.loads(s[s.index("{"):])
    if not data.get("ok", True) or not data.get("data"):
        raise RuntimeError(f"convert failed: {json.dumps(data.get('error'))[:500]}")
    return data["data"]["prompt"]


def nodes(g, cls):
    return [n for n in g.values() if n["class_type"] == cls]


_INSTALLED = {}


def installed(folder):
    """file names in one of ComfyUI's model folders (GET /models/<folder>); empty set if it can't be listed"""
    if folder not in _INSTALLED:
        try:
            _INSTALLED[folder] = set(http_json(f"/models/{folder}"))
        except (urllib.error.URLError, OSError, ValueError):
            _INSTALLED[folder] = set()
    return _INSTALLED[folder]


def pick(name, alternates, folder):
    """the template's file if it's installed (or we can't tell), else its alternative when that one is installed"""
    alt = alternates.get(name)
    have = installed(folder)
    return alt if alt and have and name not in have and alt in have else name


def _norm(p):
    return p.replace("\\", "/")


def resolve_model(name, folder):
    """-> (file name to use, found). The stock name if installed (or the folder can't be listed); else an installed file
    with the same basename in some sub-folder (e.g. "video/x.safetensors"); else the stock name, found=False."""
    have = installed(folder)
    if not have or name in have:
        return name, True
    base = _norm(name).rsplit("/", 1)[-1]
    same = sorted(f for f in have if _norm(f).rsplit("/", 1)[-1] == base)
    return (same[0], True) if same else (name, False)


# loader input -> ComfyUI model folder (a few loader classes override the generic key)
KEY_FOLDER = {"ckpt_name": "checkpoints", "unet_name": "diffusion_models", "lora_name": "loras", "vae_name": "vae",
              "clip_name": "text_encoders", "text_encoder": "text_encoders", "audio_encoder_name": "audio_encoders"}
CLASS_FOLDER = {"LatentUpscaleModelLoader": {"model_name": "latent_upscale_models"},
                "UpscaleModelLoader": {"model_name": "upscale_models"}}
ALT_KEYS = {"vae_name": "vae", "clip_name": "clip"}  # inputs that ENGINES[..]["vae" | "clip"] alternatives apply to


def resolve_models(g, cfg):
    """point every model-file input at what is installed (alternates, then basename match) and note what is missing"""
    MISSING.clear()
    for n in g.values():
        for key, val in n["inputs"].items():
            folder = CLASS_FOLDER.get(n["class_type"], {}).get(key) or KEY_FOLDER.get(key)
            if not folder or not isinstance(val, str):
                continue
            if key in ALT_KEYS:
                val = pick(val, cfg.get(ALT_KEYS[key], {}), folder)
            val, found = resolve_model(val, folder)
            n["inputs"][key] = val
            if not found and (folder, val) not in MISSING:
                MISSING.append((folder, val))
    return g


def missing_message(eng):
    lines = ", ".join(f"{f}/{n}" for f, n in MISSING)
    return (f"engine {eng} needs model files that are not installed: {lines}. "
            f"(ltx25, wan22, s2v, s2vfull and ltxia2v are optional engines; fasth3 / h3turbo are the supported ones.)")


def patch(g, eng, image_name, prompt, seconds, seed, aspect):
    cfg = ENGINES[eng]
    resolve_models(g, cfg)
    for n in nodes(g, "LoadImage"):
        n["inputs"]["image"] = image_name
    for n in nodes(g, "ResolutionSelector"):
        n["inputs"]["aspect_ratio"] = aspect
    for n in nodes(g, "SaveVideo"):
        n["inputs"]["filename_prefix"] = f"anime-style-lab/video/{eng}"
    if cfg["family"] == "h3":
        for n in nodes(g, "MiniMaxH3ImageToVideo"):
            n["inputs"]["prompt"] = prompt
        for n in nodes(g, "RandomNoise"):
            n["inputs"]["noise_seed"] = seed
        # duration: the PrimitiveFloat feeding the seconds->frames math expression
        for n in nodes(g, "PrimitiveFloat"):
            n["inputs"]["value"] = float(seconds)
        if cfg.get("lora"):
            lora, found = resolve_model(cfg["lora"], "loras")
            if found and installed("loras"):  # turbo only when the LoRA is really there
                for n in nodes(g, "LoraLoaderModelOnly"):
                    n["inputs"]["lora_name"] = lora
                for n in nodes(g, "PrimitiveBoolean"):
                    n["inputs"]["value"] = True  # turbo on
                ints = sorted(nodes(g, "PrimitiveInt"), key=lambda n: n["inputs"]["value"])
                if ints:
                    ints[0]["inputs"]["value"] = cfg["turbo_steps"]  # the turbo step count (the other is the 20-step default)
                MISSING[:] = [m for m in MISSING if m[0] != "loras"]
    elif cfg["family"] == "s2v":
        w, h = SIZES.get(aspect, (480, 640))
        if cfg.get("full"):
            w, h = {"16:9 (Widescreen)": (832, 480), "4:3 (Standard)": (768, 576), "1:1 (Square)": (640, 640)}.get(aspect, (576, 768))
        for n in nodes(g, "LoadAudio"):
            n["inputs"]["audio"] = AUDIO["name"]
        if cfg.get("full"):
            for n in nodes(g, "LoraLoaderModelOnly"):
                n["inputs"]["strength_model"] = 0.0
            # the template's "without lightning LoRA" row: 20 steps, CFG 6
            for n in nodes(g, "PrimitiveInt"):
                if n["inputs"].get("value") == 4:
                    n["inputs"]["value"] = 20
            for n in nodes(g, "PrimitiveFloat"):
                if n["inputs"].get("value") == 1:
                    n["inputs"]["value"] = 6.0
        for n in nodes(g, "WanSoundImageToVideo"):
            n["inputs"]["width"], n["inputs"]["height"] = w, h
        pos = next(k for k, n in g.items() if n["class_type"] == "WanSoundImageToVideo")
        g[g[pos]["inputs"]["positive"][0]]["inputs"]["text"] = prompt
        # base chunk + 2 extend chunks, each `length` frames: cover the whole line (length must be 4k+1)
        import math
        per = max(33, 4 * math.ceil(AUDIO["seconds"] * cfg["fps"] / 3 / 4) + 1)
        g[g[pos]["inputs"]["length"][0]]["inputs"]["value"] = per
        for n in nodes(g, "KSampler"):
            n["inputs"]["seed"] = seed
    elif cfg["family"] == "ia2v":
        w, h = SIZES.get(aspect, (480, 640))
        for n in nodes(g, "LoadAudio"):
            n["inputs"]["audio"] = AUDIO["name"]
        for n in nodes(g, "PrimitiveStringMultiline"):
            n["inputs"]["value"] = prompt
        for n in nodes(g, "PrimitiveBoolean"):
            if n["inputs"]["value"] is True:  # the prompt-enhancer switch: use our prompt as written
                n["inputs"]["value"] = False
        for n in nodes(g, "PrimitiveFloat"):
            if n["inputs"]["value"] == 9:  # clip duration (s): also trims the audio
                n["inputs"]["value"] = round(AUDIO["seconds"] + 0.3, 2)
        for n in nodes(g, "PrimitiveInt"):  # output size: the 1280 node is WIDTH, 720 is HEIGHT (renders at half, upscales 2x)
            if n["inputs"]["value"] == 1280:
                n["inputs"]["value"] = w * 2
            elif n["inputs"]["value"] == 720:
                n["inputs"]["value"] = h * 2
        for n in nodes(g, "RandomNoise"):
            n["inputs"]["noise_seed"] = seed
        if LTX_STRENGTH is not None:  # first-pass image pin (template 0.7): lower = the scene may move more
            for n in nodes(g, "LTXVImgToVideoInplace"):
                if isinstance(n["inputs"].get("strength"), (int, float)) and n["inputs"]["strength"] < 1:
                    n["inputs"]["strength"] = LTX_STRENGTH
    elif cfg["family"] == "wan":
        w, h = {"16:9 (Widescreen)": (832, 480), "4:3 (Standard)": (768, 576), "1:1 (Square)": (640, 640)}.get(aspect, (480, 640) if aspect.startswith("3:4") else (832, 480))
        for n in nodes(g, "PrimitiveBoolean"):
            n["inputs"]["value"] = True  # the template's 4-step lightning switch (off = 20 steps, CFG 3.5)
        for n in nodes(g, "PrimitiveFloat"):
            if n["inputs"]["value"] == 5:  # clip length (s); x 16 fps + 1 = frames
                n["inputs"]["value"] = float(seconds)
        for n in nodes(g, "WanImageToVideo"):
            n["inputs"]["width"], n["inputs"]["height"] = w, h
        pos = next(k for k, n in g.items() if n["class_type"] == "WanImageToVideo")
        g[g[pos]["inputs"]["positive"][0]]["inputs"]["text"] = prompt
        for n in nodes(g, "KSamplerAdvanced"):
            if n["inputs"].get("add_noise") == "enable":
                n["inputs"]["noise_seed"] = seed
    else:  # ltx
        for n in nodes(g, "PrimitiveStringMultiline"):
            n["inputs"]["value"] = prompt
        for n in nodes(g, "CLIPTextEncode"):  # negative prompt: drop "cartoon/childish", which fights anime styles
            n["inputs"]["text"] = "blurry, distorted face, deformed hands, flicker, text, watermark, ugly"
        for n in nodes(g, "PrimitiveInt"):
            if n["inputs"]["value"] == 5:
                n["inputs"]["value"] = int(seconds)
        for n in nodes(g, "RandomNoise"):
            n["inputs"]["noise_seed"] = seed
    return g


def http_json(path, body=None):
    req = urllib.request.Request(SERVER + path, method="POST" if body else "GET",
                                 data=json.dumps(body).encode() if body else None, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


JOB = None  # pipeline.Job: shows the plan in the gallery's ⚙ Queue panel


def dest_for(image, eng, seed=1001, tag="", out_dir=None, suffix=".mp4"):
    """default: next to the source image as <image>__<engine>[-tag]_seed<N>.mp4 (the gallery indexes these)"""
    image = Path(image).resolve()
    out_dir = Path(out_dir).resolve() if out_dir else image.parent
    etag = eng + (f"-{tag}" if tag else "")
    stem = f"{etag}_seed{seed}" if out_dir != image.parent else f"{image.stem}__{etag}_seed{seed}"
    return out_dir / f"{stem}{suffix}"


def aspect_of(image):
    """ResolutionSelector option matching the source png's shape (16:9 / landscape 4:3 / portrait 3:4 / square)"""
    import struct
    w, h = struct.unpack(">II", Path(image).read_bytes()[16:24])
    # a 16:9 frame read as 4:3 made the audio-driven engines render 1280x960. H3 ignores this (it follows the image);
    # the audio-driven engines size from it
    return ("16:9 (Widescreen)" if w > h * 1.55 else "4:3 (Standard)" if w > h * 1.1 else
            "3:4 (Portrait Standard)" if h > w * 1.1 else "1:1 (Square)")


def run(image, eng, prompt, seconds=5, seed=1001, out_dir=None, aspect=None, tag="", note=""):
    aspect = aspect or aspect_of(image)
    planned = pipeline.rel(dest_for(image, eng, seed, tag, out_dir))
    if JOB:
        JOB.start(planned)
    try:
        res = _run(image, eng, prompt, seconds, seed, out_dir, aspect, tag, note)
    except BaseException:
        if JOB:
            JOB.finish(planned, ok=False)
        raise
    if JOB:
        JOB.finish(planned)
    return res


def _run(image, eng, prompt, seconds, seed, out_dir, aspect, tag, note):
    image = Path(image).resolve()
    staged = upload_image(image)
    if ENGINES[eng]["family"] in AUDIO_FAMILIES:
        if not AUDIO.get("path"):
            raise RuntimeError(f"engine {eng} needs --audio")
        AUDIO.update(name=stage_audio(AUDIO["path"]), seconds=audio_seconds(AUDIO["path"]))
        seconds = round(AUDIO["seconds"], 2)
    g = patch(comfy_graph(ENGINES[eng]["template"]), eng, staged, prompt, seconds, seed, aspect)
    if MISSING:
        raise RuntimeError(missing_message(eng))
    pipeline.gpu_acquire(f"video:{eng}")  # one lab job in ComfyUI at a time, grouped by model
    t0 = time.time()  # render time = from getting the GPU ticket, not from queueing behind other lab jobs
    try:
        try:
            pipeline.yield_to_other_clients(SERVER)
            pid = http_json("/prompt", pipeline.lab_body(g))["prompt_id"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"server rejected: {e.read().decode()[:1500]}")
        while True:
            h = http_json(f"/history/{pid}").get(pid)
            if h and h.get("status", {}).get("status_str") == "error":
                raise RuntimeError(json.dumps(h["status"])[:1500])
            if h and h.get("status", {}).get("completed"):
                break
            pipeline.note_progress(SERVER, pid)
            time.sleep(3)
    finally:
        pipeline.gpu_release(f"video:{eng}")
    secs = time.time() - t0
    files = [f for o in h["outputs"].values() for key in ("images", "videos", "gifs") for f in o.get(key, [])]
    vid = next(f for f in files if f["filename"].endswith((".mp4", ".webm", ".mkv")))
    dest = dest_for(image, eng, seed, tag, out_dir, Path(vid["filename"]).suffix)
    dest.parent.mkdir(parents=True, exist_ok=True)
    q = urllib.parse.urlencode({k: vid[k] for k in ("filename", "subfolder", "type")})
    with urllib.request.urlopen(f"{SERVER}/view?{q}") as r:
        dest.write_bytes(r.read())
    meta = {"engine": eng, "tag": tag, "note": note, "template": ENGINES[eng]["template"], "source_image": str(image.relative_to(ROOT)).replace("\\", "/"),
            "prompt": prompt, "seconds": seconds, "seed": seed, "audio_in": AUDIO.get("path", ""), "render_seconds": round(secs, 1),
            "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    dest.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    try:  # 🎵 storyboard frames: the song plays under the clip
        sys.path.insert(0, str(Path(__file__).parent)); import mv_audio
        if mv_audio.song_under(dest, image) is not None:
            meta = json.loads(dest.with_suffix(".json").read_text(encoding="utf-8"))
    except Exception as e:
        print("song-under failed:", e, flush=True)
    print(f"done {dest.relative_to(ROOT)} in {secs:.0f}s", flush=True)
    try:  # show each clip in the gallery as soon as it lands (not only at the end of a batch)
        sys.path.insert(0, str(Path(__file__).parent)); import build_gallery; build_gallery.main()
    except Exception as e:
        print("gallery rebuild failed:", e, flush=True)
    return dest, meta


def _update_sidecar(dest, **fields):
    p = dest.with_suffix(".json")
    m = json.loads(p.read_text(encoding="utf-8"))
    m.update(fields)
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")


def clip(a):
    if not a.prompt and not a.motion:
        raise SystemExit("give --prompt or --motion")
    # a re-animated character should get a new NPC line + action, not a repeat
    img = Path(a.image).resolve()
    prev = [json.loads(j.read_text(encoding="utf-8")).get("prompt", "") for j in img.parent.glob(f"{img.stem}__*.json")]
    if prev and not a.allow_repeat:
        import re
        said = {x.strip().lower() for q in prev for x in re.findall(r'says: "([^"]+)"', q)}
        if a.line and a.line.strip().lower() in said:
            raise SystemExit(f"this character already said {a.line!r} in an earlier clip: write a new line (or --allow-repeat)")
        if a.motion and any(a.motion.rstrip(". ").lower() in q.lower() for q in prev):
            raise SystemExit("this character already did that action in an earlier clip: pick a new action (or --allow-repeat)")
    AUDIO.clear()
    global LTX_STRENGTH
    LTX_STRENGTH = getattr(a, "ltx_strength", None)
    if getattr(a, "audio", None):
        AUDIO["path"] = a.audio
    if a.motion and ENGINES[a.engine]["family"] not in AUDIO_FAMILIES:
        sys.path.insert(0, str(Path(__file__).parent)); import video_prompt
        a.prompt = video_prompt.build(a.image, a.motion, a.camera, a.shot, a.sound, a.music, a.line, a.voice, a.vocal, a.face, a.sfx,
                                      getattr(a, "speaker", ""), getattr(a, "soundscape", ""))
    dest, meta = run(a.image, a.engine, a.prompt, a.seconds, a.seed, a.out, tag=a.tag, note=a.note)
    if getattr(a, "lead_in", 0):  # the audio had lead_in s of silence in front (tools/mv_cut.py): the model settles into the shot,
        # then the clip starts on the first sung word
        tmp = dest.with_suffix(".trim.mp4")
        r = subprocess.run([str(FFMPEG), "-v", "error", "-y", "-ss", f"{float(a.lead_in):.3f}", "-i", str(dest), "-map", "0:v:0", "-map", "0:a?",
                            "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", str(tmp)],
                           capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("lead-in trim failed: " + r.stderr[-300:])
        tmp.replace(dest)
        _update_sidecar(dest, lead_in_trimmed=float(a.lead_in))
    if getattr(a, "song_at", None) is not None:  # the clip is one line inside a longer frame: song from that line's time
        sys.path.insert(0, str(Path(__file__).parent)); import mv_audio
        mv_audio.song_under(dest, a.image, at=float(a.song_at))
    if getattr(a, "reverse", False):  # animate the LEAVING, play it backwards = a clean ENTRANCE
        # (the start frame already shows the character, so the face stays theirs the whole way in). Picture only: the
        # audio (the song for storyboard frames) keeps playing forwards.
        tmp = dest.with_suffix(".rev.mp4")
        r = subprocess.run([str(FFMPEG), "-v", "error", "-y", "-i", str(dest), "-vf", "reverse", "-map", "0:v:0", "-map", "0:a?",
                            "-c:a", "copy", str(tmp)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("reverse failed: " + r.stderr[-300:])
        tmp.replace(dest)
        _update_sidecar(dest, reversed=True)
        print("reversed", dest.relative_to(ROOT), flush=True)
    if getattr(a, "as_frame", ""):  # rendered from one frame, but it's THIS frame's clip (named + timed + song-under as that frame)
        # e.g. an entrance = the next frame (lips at the mic) animated pulling away, reversed: it ends exactly on that frame's first frame
        frame = (ROOT / a.as_frame).resolve()
        new = dest.with_name(frame.stem + "__" + dest.name.split("__", 1)[1])
        for src, dst in ((dest, new), (dest.with_suffix(".json"), new.with_suffix(".json")),
                         (dest.with_suffix(".genaudio.m4a"), new.with_suffix(".genaudio.m4a"))):
            if src.exists():
                src.replace(dst)
        _update_sidecar(new, frame=frame.relative_to(ROOT).as_posix())
        sys.path.insert(0, str(Path(__file__).parent)); import mv_audio
        mv_audio.song_under(new, frame)
        print("as frame", new.relative_to(ROOT), flush=True)
        try:
            import build_gallery; build_gallery.main()
        except Exception as e:
            print("gallery rebuild failed:", e, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("image", nargs="?"); ap.add_argument("engine", nargs="?", choices=ENGINES)
    ap.add_argument("--batch", help="JSON file: a list of clips, each {image, engine, motion, camera, sfx, line, voice, face, tag, note, ...} "
                                    "(same names as these flags); all of them show in the gallery Queue panel up front")
    ap.add_argument("--prompt", help="raw prompt; or build one with --motion (tools/video_prompt.py)")
    ap.add_argument("--motion"); ap.add_argument("--camera", default="the camera slowly pushes in")
    ap.add_argument("--shot", action="append"); ap.add_argument("--sound", default=""); ap.add_argument("--music", default="")
    ap.add_argument("--line", default="", help="short spoken NPC line"); ap.add_argument("--voice", default="")
    ap.add_argument("--vocal", default="", help="expressed non-word sound: sigh, giggle, gasp"); ap.add_argument("--face", default="", help="micro-expressions")
    ap.add_argument("--sfx", default="", help="action sounds in order, each tied to a visible action (play before the line)")
    ap.add_argument("--soundscape", default="", help="silent clips: 'Only the sounds of <this> can be heard' (e.g. battle, a burning city)")
    ap.add_argument("--speaker", default="", help="who says --line in a multi-character frame (journeys): no look to camera, others silent")
    ap.add_argument("--tag", default=""); ap.add_argument("--note", default="")
    ap.add_argument("--as-frame", default="", help="file + time the clip as this storyboard frame (render from another)")
    ap.add_argument("--lead-in", type=float, default=0, help="seconds of silent lead-in on --audio to trim off the finished clip")
    ap.add_argument("--song-at", type=float, default=None, help="storyboard clips: the song time (s) this clip starts at (default: the frame t0)")
    ap.add_argument("--reverse", action="store_true", help="play the finished clip backwards (animate a character leaving = an entrance)")
    ap.add_argument("--allow-repeat", action="store_true", help="skip the check that a re-animated character gets a new line + action")
    ap.add_argument("--seconds", type=float, default=5)
    ap.add_argument("--ltx-strength", type=float, help="ltxia2v first-pass image pin (template 0.7); lower lets the scene move more")
    ap.add_argument("--audio", help="speech/audio file that drives the audio-driven engines (s2v, s2vfull, ltxia2v)")
    ap.add_argument("--seed", type=int, default=1001); ap.add_argument("--out")
    cli = ap.parse_args()
    if cli.batch:
        specs = []
        for d in json.loads(Path(cli.batch).read_text(encoding="utf-8")):
            ns = ap.parse_args([d["image"], d["engine"]])
            for k, v in d.items():
                setattr(ns, k.replace("-", "_"), v)
            specs.append(ns)
    else:
        if not cli.image or not cli.engine:
            raise SystemExit("give <image> <engine> or --batch")
        specs = [cli]
    JOB = pipeline.Job("videos", [{"kind": "video", "out": pipeline.rel(dest_for(a.image, a.engine, a.seed, a.tag, a.out)),
                                   "model": pipeline.ENGINE_ABBR.get(a.engine, a.engine),
                                   "label": f"🎬 {Path(a.image).resolve().parent.parent.name[:3]} {Path(a.image).stem.replace('_seed1001', '')}"
                                            + (f" · {a.tag}" if a.tag else "")} for a in specs])
    for a in specs:  # one bad clip (e.g. a repeated line) doesn't stop the rest of a batch
        try:
            try:
                clip(a)
            except RuntimeError as e:
                # a transient "HostBuffer.read_file_slice failed" (ComfyUI's dynamic loader failing to read model weights
                # while models were swapping) is worth one retry
                if "read_file_slice" not in str(e):
                    raise
                print(f"retrying {a.image} once after a transient model-load error", flush=True)
                time.sleep(10)
                a.allow_repeat = True  # the failed attempt left no clip, but don't let the repeat check block the retry
                clip(a)
        except (SystemExit, RuntimeError) as e:
            print(f"FAILED {a.image}: {e}", flush=True)
            JOB.finish(pipeline.rel(dest_for(a.image, a.engine, a.seed, a.tag, a.out)), ok=False)
            if len(specs) == 1:
                raise
