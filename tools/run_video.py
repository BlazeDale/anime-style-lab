"""Animate a lab image with an image-to-video workflow (ComfyUI templates in workflows/base).

  .venv/Scripts/python tools/run_video.py <image.png> <engine> [--prompt "..."] [--seconds 5] [--seed 1001] [--out DIR]
  engines: fasth3 | h3turbo   (see ENGINES)

The template is converted with comfy-cli, then patched by node class (model/file names that differ on this
install, the start image, prompt, duration, aspect) and POSTed straight to ComfyUI, same as run_version.py.
The source image is uploaded to ComfyUI via POST /upload/image (no direct filesystem path into the ComfyUI install).
Writes <out>/<engine>_seed<seed>.mp4 and a matching .json sidecar (prompt, engine, timings).
"""
import argparse
import json
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
from config import COMFY_CLI, COMFY_URL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
COMFY = str(COMFY_CLI)
SERVER = COMFY_URL

# "vae"/"clip" = {template file: alternative}, "lora" = an optional turbo LoRA. A swap only happens when the
# template's own file isn't installed and the alternative is (see installed()), so a stock install runs the
# templates as shipped.
ENGINES = {
    # FastVideo FastH3: MiniMax H3 distilled to 8 steps (newest, fastest). Only the video VAE name differs here.
    "fasth3": {"template": "video_fastvideo_fasth3_i2v", "family": "h3",
               "vae": {"minimax_h3_video_vae_int8_convrot.safetensors": "minimax_h3_video_vae_fp16.safetensors"}},
    # Full MiniMax H3 fl2va + the installed 4-step lightx2v turbo LoRA (template expects an 8-step LoRA).
    "h3turbo": {"template": "video_minimax_h3_i2v", "family": "h3", "turbo_steps": 4,
                "vae": {"minimax_h3_video_vae_int8_convrot.safetensors": "minimax_h3_video_vae_fp16.safetensors"},
                "lora": "H3\\minimax_h3_fl2v_lightx2v_turbo_4step_v0.1_comfy_resized_avg_rank_21_bf16.safetensors"},
}


def upload_image(path):
    """POST /upload/image (multipart, overwrite=true) -> the name ComfyUI stored it under. No direct filesystem
    access to the ComfyUI install: this works against any ComfyUI reachable at config.comfy_url."""
    path = Path(path).resolve()
    name = ("animestylelab_" + "_".join(path.relative_to(ROOT).with_suffix("").parts[-3:])).replace("@", "_") + path.suffix
    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n".encode(),
        path.read_bytes(), f"\r\n--{boundary}--\r\n".encode()])
    req = urllib.request.Request(SERVER + "/upload/image", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["name"]


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


def patch(g, eng, image_name, prompt, seconds, seed, aspect):
    cfg = ENGINES[eng]
    for n in nodes(g, "VAELoader"):
        n["inputs"]["vae_name"] = pick(n["inputs"]["vae_name"], cfg.get("vae", {}), "vae")
    for n in nodes(g, "CLIPLoader"):
        n["inputs"]["clip_name"] = pick(n["inputs"]["clip_name"], cfg.get("clip", {}), "text_encoders")
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
        if cfg.get("lora") and cfg["lora"].replace("\\", "/") in {f.replace("\\", "/") for f in installed("loras")}:
            for n in nodes(g, "LoraLoaderModelOnly"):
                n["inputs"]["lora_name"] = cfg["lora"]
            for n in nodes(g, "PrimitiveBoolean"):
                n["inputs"]["value"] = True  # turbo on
            ints = sorted(nodes(g, "PrimitiveInt"), key=lambda n: n["inputs"]["value"])
            if ints:
                ints[0]["inputs"]["value"] = cfg["turbo_steps"]  # the turbo step count (the other is the 20-step default)
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
    """ResolutionSelector option matching the source png's shape (portrait 3:4 / landscape 4:3 / square)"""
    import struct
    w, h = struct.unpack(">II", Path(image).read_bytes()[16:24])
    return "4:3 (Standard)" if w > h * 1.1 else "3:4 (Portrait Standard)" if h > w * 1.1 else "1:1 (Square)"


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
    g = patch(comfy_graph(ENGINES[eng]["template"]), eng, staged, prompt, seconds, seed, aspect)
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
            "prompt": prompt, "seconds": seconds, "seed": seed, "render_seconds": round(secs, 1), "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    dest.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"done {dest.relative_to(ROOT)} in {secs:.0f}s", flush=True)
    try:  # show each clip in the gallery as soon as it lands (not only at the end of a batch)
        sys.path.insert(0, str(Path(__file__).parent)); import build_gallery; build_gallery.main()
    except Exception as e:
        print("gallery rebuild failed:", e, flush=True)
    return dest, meta


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
    if a.motion:
        sys.path.insert(0, str(Path(__file__).parent)); import video_prompt
        a.prompt = video_prompt.build(a.image, a.motion, a.camera, a.shot, a.sound, a.music, a.line, a.voice, a.vocal, a.face, a.sfx)
    run(a.image, a.engine, a.prompt, a.seconds, a.seed, a.out, tag=a.tag, note=a.note)


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
    ap.add_argument("--tag", default=""); ap.add_argument("--note", default="")
    ap.add_argument("--allow-repeat", action="store_true", help="skip the check that a re-animated character gets a new line + action")
    ap.add_argument("--seconds", type=float, default=5)
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
                                   "label": f"🎬 {Path(a.image).resolve().parent.parent.name[:3]} {Path(a.image).stem.replace('_seed1001', '')}"
                                            + (f" · {a.tag}" if a.tag else "")} for a in specs])
    for a in specs:  # one bad clip (e.g. a repeated line) doesn't stop the rest of a batch
        try:
            try:
                clip(a)
            except RuntimeError as e:
                # two H3 clips have died on "HostBuffer.read_file_slice failed" (ComfyUI's dynamic loader failing to
                # read model weights while models were swapping); it's transient, so retry once
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
