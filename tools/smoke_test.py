"""Prove the render pipeline end to end with ONE image, without touching anything in evolutions/.

    python tools/smoke_test.py [evolutions/001-plain-anime/v02] [--subject f-modern]

Copies that version's prompt.txt + params.json into feedback/smoke/ (gitignored), renders a single subject through
the same code path as run_version.py (comfy-cli conversion, GPU ticket, ComfyUI /prompt), and prints where the PNG
landed and how long it took. Run tools/doctor.py first if anything is missing.
"""
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ROOT = config.ROOT

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to a legacy code page
except AttributeError:
    pass

if __name__ == "__main__":
    # needs comfy-cli from the .venv: hand over to it when started with another Python
    if config.VENV_PYTHON.exists() and Path(sys.executable).resolve() != config.VENV_PYTHON.resolve():
        sys.exit(subprocess.call([str(config.VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]]))
    if not config.COMFY_CLI.exists():
        sys.exit("comfy-cli isn't installed in .venv yet. Run: python tools/doctor.py --fix")

    import run_version  # noqa: E402  (imports comfy-cli paths + ComfyUI config)

    argv = sys.argv[1:]
    subject = argv[argv.index("--subject") + 1] if "--subject" in argv else "f-modern"
    pos = [a for i, a in enumerate(argv) if not a.startswith("--") and not (i and argv[i - 1] == "--subject")]
    src = ROOT / (pos[0] if pos else "evolutions/001-plain-anime/v02")
    out = ROOT / "feedback" / "smoke" / f"{src.parent.name}_{src.name}"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for f in ("prompt.txt", "params.json"):
        shutil.copyfile(src / f, out / f)
    raw = json.loads((out / "params.json").read_text(encoding="utf-8"))
    raw.update(subjects=[subject], seeds=raw.get("seeds", [1001])[:1])
    (out / "params.json").write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")

    params, items = run_version.load_version(out)
    name, prompt, seed = items[0]
    print(f"smoke test: {src.relative_to(ROOT).as_posix()} · {subject} · seed {seed} -> ComfyUI {config.COMFY_URL}",
          flush=True)
    t0 = time.time()
    run_version.render(out, params, name, prompt, seed, force=True)
    png = out / f"{name}.png"
    if not png.exists():
        sys.exit("FAILED: no image came back from ComfyUI")
    print(f"OK: {png.relative_to(ROOT).as_posix()} in {time.time() - t0:.0f}s "
          f"(first run includes model loading). The pipeline works; the gallery was rebuilt.")
