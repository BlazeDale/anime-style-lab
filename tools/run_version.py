"""Render one prompt version: evolutions/NNN-slug/vNN/ -> workflow.json + PNGs.

The version dir must contain prompt.txt and params.json. Usage:
    .venv/Scripts/python tools/run_version.py evolutions/001-plain/v01 [...more]
        [--only f-modern,m-scifi]   just these subjects (default: every subject in params.json)
        [--force]                   re-render existing images (old ones move to vNN/_rerolled/)
        [--by-subject]              render one subject across all given versions before the next
Existing images are skipped unless --force, so re-running a version only fills in what's missing.
"""
import importlib
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import build_gallery
import pipeline
from config import COMFY_CLI, COMFY_URL

ROOT = Path(__file__).resolve().parent.parent
COMFY = str(COMFY_CLI)
SERVER = COMFY_URL
BASE = ROOT / "workflows" / "base" / "qwen_image_2_1_t2i.template.json"

DEFAULTS = {
    "seeds": [1001],
    "steps": 25,
    "cfg": 1,
    "aspect_ratio": "3:4 (Portrait Standard)",
    "megapixels": 1,
    "model": "qwen_image_2.1_int8_convrot.safetensors",
    "sampler": "euler",
    "scheduler": "simple",
}


def comfy(*args):
    out = subprocess.run([COMFY, "--json", *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    try:
        env = json.loads(out.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        raise RuntimeError(f"comfy {args[0]} failed:\n{out.stdout}\n{out.stderr}")
    if not env.get("ok", True):
        raise RuntimeError(f"comfy {args[0]} error: {json.dumps(env)[:2000]}")
    return env


def http_json(path, body=None):
    req = urllib.request.Request(SERVER + path, method="POST" if body else "GET",
                                 data=json.dumps(body).encode() if body else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def submit_and_wait(graph, timeout=1800, kind="image"):
    pipeline.gpu_acquire(kind)  # one lab job in ComfyUI at a time, grouped by model
    try:
        return _submit_and_wait(graph, timeout)
    finally:
        pipeline.gpu_release(kind)


def _submit_and_wait(graph, timeout=1800):
    # comfy-cli's client-side validator wrongly rejects the empty autogrow 'images'
    # input on TextEncodeQwenImage21 (server min is 0), so we convert with comfy-cli
    # but submit straight to the server.
    try:
        pipeline.yield_to_other_clients(SERVER)
        pid = http_json("/prompt", pipeline.lab_body(graph))["prompt_id"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"server rejected prompt: {e.read().decode()[:2000]}")
    # the timeout only counts time the job is actually RUNNING (or missing): waiting behind a long shared queue is fine
    # (2026-09-26: with ~20 jobs queued, a 30 min wall-clock timeout killed a whole batch before its first image started)
    t0, last_q = time.time(), 0.0
    while True:
        h = http_json(f"/history/{pid}").get(pid)
        if h and h.get("status", {}).get("completed"):
            return h
        if h and h.get("status", {}).get("status_str") == "error":
            raise RuntimeError(f"run failed: {json.dumps(h['status'])[:2000]}")
        pipeline.note_progress(SERVER, pid)
        if time.time() - last_q > 20:
            last_q = time.time()
            q = http_json("/queue")
            if any(it[1] == pid for it in q.get("queue_pending", [])):
                t0 = time.time()  # still waiting its turn
            elif not any(it[1] == pid for it in q.get("queue_running", [])) and not h and time.time() - t0 > 120:
                raise RuntimeError(f"prompt {pid} vanished from the queue (deleted or ComfyUI restarted)")
        if time.time() - t0 > timeout:
            raise TimeoutError(pid)
        time.sleep(2)


SUBJECTS = json.loads((ROOT / "subjects.json").read_text(encoding="utf-8"))


def load_version(vdir: Path):
    """-> (params, [(image_name, prompt, seed)]). A prompt with {subject} fans out over params['subjects']."""
    template = (vdir / "prompt.txt").read_text(encoding="utf-8").strip()
    params = {**DEFAULTS, **json.loads((vdir / "params.json").read_text(encoding="utf-8"))}
    (vdir / "params.json").write_text(json.dumps(params, indent=2) + "\n", encoding="utf-8")
    if "{subject}" not in template:
        return params, [(f"seed{s}", template, s) for s in params["seeds"]]
    return params, [(f"{k}_seed{s}", template.replace("{subject}", SUBJECTS[k]["text"]), s)
                    for k in params.get("subjects", list(SUBJECTS)) for s in params["seeds"]]


JOB = None  # pipeline.Job: shows this run's plan in the gallery's ⚙ Queue panel


def render(vdir: Path, params, name, prompt, seed, force=False):
    out_png = vdir / f"{name}.png"
    if out_png.exists() and not force:  # a reroll always writes (2026-09-27: a stale batch re-filled the moved-away file
        return                          # first, and the reroll then skipped its own new image)
    if JOB:
        JOB.start(pipeline.rel(out_png))
    try:
        _render(vdir, params, name, prompt, seed, out_png)
    except BaseException:
        if JOB:
            JOB.finish(pipeline.rel(out_png), ok=False)
        raise
    if JOB:
        JOB.finish(pipeline.rel(out_png))
    # reload: long render jobs must pick up builder edits made while they run (else they rewrite a stale gallery)
    importlib.reload(build_gallery).main()


def _render(vdir, params, name, prompt, seed, out_png):
    # single-image versions keep the original workflow.json name
    wf = vdir / ("workflow.json" if name.startswith("seed") else f"{name}.workflow.json")
    shutil.copyfile(BASE, wf)
    sets = {
        "459.prompt": prompt,
        "459.seed": seed,
        "459.steps": params["steps"],
        "459.cfg": params["cfg"],
        "459.scheduler": params["sampler"],      # template's sampler widget is named 'scheduler'
        "459.scheduler_1": params["scheduler"],
        "459.unet_name": params["model"],
        "13.aspect_ratio": params["aspect_ratio"],
        "13.megapixels": params["megapixels"],
        "461.filename_prefix": f"anime-style-lab/{vdir.parent.name}_{vdir.name}_{name}",
    }
    comfy("workflow", "set-slot", str(wf), *[f"{k}={json.dumps(v)}" for k, v in sets.items()])
    graph = comfy("run", "--workflow", str(wf), "--print-prompt")["data"]["prompt"]
    if params.get("negative"):  # only takes effect with cfg > 1 (at cfg 1 the sampler skips the negative branch)
        for n in graph.values():
            if n["class_type"] == "TextEncodeQwenImage21" and "negative_prompt" in n["inputs"]:
                n["inputs"]["negative_prompt"] = params["negative"]
    if params.get("refs"):  # reference images (Qwen 2.1 TextEncodeQwenImage21 images.image_N), e.g. matching turnaround
        import run_journey  # views of one character: same reference-image upload/wiring as journeys
        te = next(k for k, n in graph.items() if n["class_type"] == "TextEncodeQwenImage21")
        vae = next(k for k, n in graph.items() if n["class_type"] == "VAELoader")
        for i, ref in enumerate(params["refs"], 1):
            graph[f"ref{i}"] = {"class_type": "LoadImage", "inputs": {"image": run_journey.upload(ROOT / ref)}}
            graph[te]["inputs"][f"images.image_{i}"] = [f"ref{i}", 0]
        graph[te]["inputs"]["vae"] = [vae, 0]
        graph[te]["inputs"]["resolution"] = params.get("ref_resolution", 768)
    t0 = time.time()
    hist = submit_and_wait(graph)
    imgs = [i for o in hist["outputs"].values() for i in o.get("images", [])]
    if not imgs:
        raise RuntimeError(f"no image output for {vdir} {name}")
    q = urllib.parse.urlencode({k: imgs[0][k] for k in ("filename", "subfolder", "type")})
    with urllib.request.urlopen(f"{SERVER}/view?{q}") as r:
        out_png.write_bytes(r.read())
    print(f"done {out_png.relative_to(ROOT)} in {time.time() - t0:.0f}s", flush=True)


# "fix" rerolls (user 2026-09-24): negatives stay off by default; a 🎲 on an image whose latest comment reports bad
# hands/anatomy re-renders with this negative prompt and CFG 2.5 (at CFG 1 a negative prompt has no effect)
FIX_NEG = ("bad anatomy, bad hands, extra fingers, missing fingers, fused fingers, deformed hands, extra limbs, "
           "malformed limbs, twisted torso, text, logo, lettering, watermark, signage")
FIX_CFG = 2.5


def reroll(png: Path, fix=False):
    """🎲 from the gallery: same prompt + params, a fresh random seed, rendered in place under the same file name.
    The old image (and its workflow) moves to vNN/_rerolled/; params.json "rerolls" records {image name: [seeds used]}.
    fix=True adds FIX_NEG at FIX_CFG and records it under params.json "fixes" {image name: {seed, cfg, negative}}."""
    import random
    png = png.resolve()
    vdir, name = png.parent, png.stem
    params, items = load_version(vdir)
    _, prompt, _ = next(it for it in items if it[0] == name)
    seed = random.randint(1, 2**31 - 1)
    arch = vdir / "_rerolled"
    arch.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    wf = vdir / ("workflow.json" if name.startswith("seed") else f"{name}.workflow.json")
    for f in (png, wf):
        if f.exists():
            f.replace(arch / f"{f.stem}__{stamp}{f.suffix}")
    raw = json.loads((vdir / "params.json").read_text(encoding="utf-8"))
    raw.setdefault("rerolls", {}).setdefault(name, []).append(seed)
    if fix:
        raw.setdefault("fixes", {})[name] = {"seed": seed, "cfg": FIX_CFG, "negative": FIX_NEG}
        params = {**params, "cfg": FIX_CFG, "negative": FIX_NEG}
    elif name in raw.get("fixes", {}):
        del raw["fixes"][name]  # a plain reroll replaces a fixed image
    (vdir / "params.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    print(f"reroll {png.relative_to(ROOT)} seed {seed}{' (fix: negative + cfg %g)' % FIX_CFG if fix else ''}", flush=True)
    render(vdir, params, name, prompt, seed, force=True)


if __name__ == "__main__":
    if "--reroll" in sys.argv:  # --reroll <evolutions/.../name.png>
        png = ROOT / sys.argv[sys.argv.index("--reroll") + 1]
        fix = "--fix" in sys.argv
        JOB = pipeline.Job("reroll", [{"kind": "image", "out": pipeline.rel(png), "label": f"🎲{'🩹' if fix else ''} {png.parent.parent.name} {png.parent.name} · {png.stem.replace('_seed1001', '')}"}])
        reroll(png, fix)
        sys.exit()
    # --by-subject: render one subject across all given versions before moving to the next
    # --only k1,k2: just these subject keys (or image names); --force: re-render images that already exist
    #   (the old png + workflow move to vNN/_rerolled/ first, like a 🎲 reroll, so nothing is lost)
    argv = sys.argv[1:]
    only = set(argv[argv.index("--only") + 1].split(",")) if "--only" in argv else None
    force = "--force" in argv
    args = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i and argv[i - 1] == "--only")]
    jobs = []
    for arg in args:
        vdir = (ROOT / arg).resolve() if not Path(arg).is_absolute() else Path(arg)
        params, items = load_version(vdir)
        if only:
            items = [it for it in items if it[0] in only or it[0].rsplit("_seed", 1)[0] in only]
        jobs += [(i, vdir, params, *it) for i, it in enumerate(items)]
    if only and not jobs:
        sys.exit(f"--only {','.join(sorted(only))}: no matching subject/image in {', '.join(args)}")
    if "--by-subject" in sys.argv:
        jobs.sort(key=lambda j: j[0])  # stable: keeps version order within each subject
    if force:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for _, vdir, params, name, prompt, seed in jobs:
            wf = vdir / ("workflow.json" if name.startswith("seed") else f"{name}.workflow.json")
            for f in (vdir / f"{name}.png", wf):
                if f.exists():
                    (vdir / "_rerolled").mkdir(exist_ok=True)
                    f.replace(vdir / "_rerolled" / f"{f.stem}__{stamp}{f.suffix}")
    todo = [(vdir, name) for _, vdir, params, name, prompt, seed in jobs if not (vdir / f"{name}.png").exists()]
    if todo:
        JOB = pipeline.Job("images", [{"kind": "image", "out": pipeline.rel(vdir / f"{name}.png"),
                                       "label": f"{vdir.parent.name} {vdir.name} · {name.replace('_seed1001', '')}"} for vdir, name in todo])
    for _, vdir, params, name, prompt, seed in jobs:
        render(vdir, params, name, prompt, seed)
