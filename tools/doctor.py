"""First-run check: is everything in place to render and browse the gallery?

    python tools/doctor.py          report only (changes nothing)
    python tools/doctor.py --fix    also create what's safe to create: config.json, .venv + requirements, gallery page

Checks Python, the .venv and its packages, config.json, Node (optional), ComfyUI at the configured comfy_url, the
Qwen Image 2.1 nodes, the model files the workflow templates reference, and whether the gallery server is running.
It never installs anything into ComfyUI or downloads models: those are listed for you to fetch.
Runs on the standard library, so any Python 3.10+ can start it.
"""
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ROOT = config.ROOT
FIX = "--fix" in sys.argv
BASE = ROOT / "workflows" / "base"
IMAGE_TEMPLATE = BASE / "qwen_image_2_1_t2i.template.json"
VIDEO_TEMPLATES = {"fasth3": "video_fastvideo_fasth3_i2v.template.json",
                   "h3turbo": "video_minimax_h3_i2v.template.json"}
NODES = ("TextEncodeQwenImage21", "ResolutionSelector")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to a legacy code page
except AttributeError:
    pass

rows = []  # (status, item, detail)   status: ok | missing | optional | info


def row(status, item, detail=""):
    rows.append((status, item, detail))


def get(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read())


def template_models(path):
    """model file names a workflow template loads (every widget value that looks like a weights file)"""
    names, stack = set(), [json.loads(path.read_text(encoding="utf-8"))]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            stack.extend(x.values())
        elif isinstance(x, list):
            stack.extend(x)
        elif isinstance(x, str) and x.endswith((".safetensors", ".pth", ".ckpt", ".gguf")):
            names.add(x.replace("\\", "/").rsplit("/", 1)[-1])
    return names


def run(cmd):
    print("  $ " + " ".join(str(c) for c in cmd), flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=ROOT).returncode == 0


def check_python():
    v = sys.version_info
    if v >= (3, 10):
        row("ok", "Python 3.10+", f"{v.major}.{v.minor}.{v.micro}")
    else:
        row("missing", "Python 3.10+", f"this is {v.major}.{v.minor}; install 3.10 or newer")


def venv_imports():
    """-> list of missing packages inside the .venv (None if there's no .venv)"""
    if not config.VENV_PYTHON.exists():
        return None
    code = ("import importlib.util as u;"
            "print(','.join(m for m in ('PIL','numpy') if not u.find_spec(m)))")
    out = subprocess.run([str(config.VENV_PYTHON), "-c", code], capture_output=True, text=True)
    missing = [m for m in out.stdout.strip().split(",") if m]
    if not config.COMFY_CLI.exists():
        missing.append("comfy-cli")
    return missing


def check_venv():
    missing = venv_imports()
    if (missing is None or missing) and FIX:
        if missing is None:
            run([sys.executable, "-m", "venv", ROOT / ".venv"])
        run([config.VENV_PYTHON, "-m", "pip", "install", "-q", "--upgrade", "pip"])
        run([config.VENV_PYTHON, "-m", "pip", "install", "-q", "-r", ROOT / "requirements.txt"])
        missing = venv_imports()
    if missing is None:
        row("missing", ".venv", "not created. Fix: python tools/doctor.py --fix")
    elif missing:
        row("missing", ".venv packages", f"missing {', '.join(missing)}. Fix: python tools/doctor.py --fix")
    else:
        row("ok", ".venv + requirements", f"{config.VENV_PYTHON.relative_to(ROOT)} has comfy-cli, Pillow, numpy")


def check_config():
    cfg = ROOT / "config.json"
    if not cfg.exists() and FIX:
        shutil.copyfile(ROOT / "config.example.json", cfg)
        row("ok", "config.json", "created from config.example.json")
    elif cfg.exists():
        row("ok", "config.json", f"comfy_url {config.COMFY_URL}, gallery port {config.GALLERY_PORT}")
    else:
        row("missing", "config.json", "not created (defaults apply). Fix: python tools/doctor.py --fix")


def check_node():
    node = shutil.which("node")
    if node:
        v = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
        row("ok", "Node.js (optional)", f"{v}, for tools/test_gallery.js")
    else:
        row("optional", "Node.js (optional)", "not found; only needed for tools/test_gallery.js")


def check_comfy():
    url = config.COMFY_URL
    try:
        stats = get(url + "/system_stats")
    except (urllib.error.URLError, OSError, ValueError) as e:
        row("missing", "ComfyUI", f"not reachable at {url} ({e}). Start ComfyUI, or set comfy_url in config.json")
        return
    ver = stats.get("system", {}).get("comfyui_version", "?")
    gpu = ", ".join(d.get("name", "?").split(" : ")[0].split(" ", 1)[-1] for d in stats.get("devices", []))
    row("ok", "ComfyUI", f"{url}, version {ver}" + (f", {gpu}" if gpu else ""))

    missing = []
    for n in NODES:
        try:
            if n not in get(f"{url}/object_info/{n}"):
                missing.append(n)
        except (urllib.error.URLError, OSError, ValueError):
            missing.append(n)
    if missing:
        row("missing", "Qwen Image 2.1 nodes", f"{', '.join(missing)} not found: update ComfyUI")
    else:
        row("ok", "Qwen Image 2.1 nodes", ", ".join(NODES))

    have, ups = set(), []
    try:
        for folder in get(url + "/models"):
            try:
                files = [f.replace("\\", "/").rsplit("/", 1)[-1] for f in get(f"{url}/models/{folder}", timeout=15)]
            except (urllib.error.URLError, OSError, ValueError):
                continue
            have.update(files)
            if folder == "upscale_models":
                ups = sorted(files)
    except (urllib.error.URLError, OSError, ValueError):
        row("info", "Models", "couldn't list ComfyUI's model folders; check the README's model list by hand")
        return
    need = template_models(IMAGE_TEMPLATE)
    lacking = sorted(need - have)
    if lacking:
        row("missing", "Image models", "not in ComfyUI's model folders: " + ", ".join(lacking))
    else:
        row("ok", "Image models", ", ".join(sorted(need)))
    row("ok" if ups else "optional", "Upscale model (optional)",
        ", ".join(ups[:3]) if ups else "none; only for hires_card.py/refit.py --model (e.g. 4x-AnimeSharp.pth)")
    try:
        from run_video import ENGINES  # its per-engine alternative file names count as present too
    except Exception:  # noqa: BLE001 -- the video check is optional; never let it break the report
        ENGINES = {}
    for engine, name in VIDEO_TEMPLATES.items():
        alts = {**ENGINES.get(engine, {}).get("vae", {}), **ENGINES.get(engine, {}).get("clip", {})}
        lora = ENGINES.get(engine, {}).get("lora", "").replace("\\", "/").rsplit("/", 1)[-1]

        def present(f):
            if f in have or alts.get(f) in have:
                return True
            return bool(lora) and lora in have and "turbo" in f.lower()  # run_video swaps in its own turbo LoRA

        lack = sorted(f for f in template_models(BASE / name) if not present(f))
        row("ok" if not lack else "optional", f"Video engine {engine} (optional)",
            "ready" if not lack else f"not found in ComfyUI's model folders: {', '.join(lack)}")


def check_gallery():
    page = ROOT / "gallery" / "index.html"
    if not page.exists() and FIX and config.VENV_PYTHON.exists():
        run([config.VENV_PYTHON, ROOT / "tools" / "build_gallery.py"])
    row("ok" if page.exists() else "missing", "Gallery page",
        "gallery/index.html built" if page.exists() else "not built. Fix: python tools/build_gallery.py")
    url = f"http://127.0.0.1:{config.GALLERY_PORT}"
    try:
        get(url + "/api/queue", timeout=3)
        row("ok", "Gallery server", f"running: {url}/gallery/")
    except (urllib.error.URLError, OSError, ValueError):
        py = config.VENV_PYTHON.relative_to(ROOT).as_posix()
        row("info", "Gallery server", f"not running. Start it in the background: {py} tools/serve_gallery.py")


def main():
    check_python()
    check_config()
    check_venv()
    check_node()
    check_comfy()
    check_gallery()
    icon = {"ok": "✅", "missing": "❌", "optional": "➖", "info": "ℹ️ "}
    w = max(len(r[1]) for r in rows)
    print()
    for status, item, detail in rows:
        print(f"{icon[status]} {item.ljust(w)}  {detail}")
    bad = [r for r in rows if r[0] == "missing"]
    print()
    if bad:
        fixable = any(r[1] in (".venv", ".venv packages", "config.json", "Gallery page") for r in bad)
        print(f"{len(bad)} thing(s) missing." + (" Run: python tools/doctor.py --fix" if fixable and not FIX else ""))
    else:
        py = config.VENV_PYTHON.relative_to(ROOT).as_posix()
        print("Ready. Prove the pipeline with one render: " + f"{py} tools/smoke_test.py")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
