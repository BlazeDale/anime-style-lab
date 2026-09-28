"""Tiny project config helper.

Reads config.json at the repo root (falls back to config.example.json if config.json
doesn't exist yet — copy it and edit to override). No dependencies, import-only side effects.

Usage:
    from config import COMFY_URL, COMFY_PYTHON, GALLERY_PORT
    # or
    import config
    config.CONFIG["comfy_url"]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_DEFAULTS = {
    "comfy_url": "http://127.0.0.1:8188",
    "comfy_python": None,
    "gallery_port": 8765,
}


def load():
    cfg = dict(_DEFAULTS)
    for name in ("config.json", "config.example.json"):
        p = ROOT / name
        if p.exists():
            cfg.update(json.loads(p.read_text(encoding="utf-8")))
            break
    return cfg


CONFIG = load()
COMFY_URL = CONFIG["comfy_url"].rstrip("/")
# comfy_python: the interpreter used for PIL/numpy-only helper scripts (match_contrast, refit, hires_card).
# null in config.json means "use whatever python is running this script" (sys.executable) --
# only set it if you need a *different* interpreter (e.g. ComfyUI's own embedded Python) for those libs.
COMFY_PYTHON = CONFIG["comfy_python"] or sys.executable
GALLERY_PORT = int(CONFIG["gallery_port"])

# the project's virtualenv (tools/doctor.py --fix creates it): Windows keeps executables in Scripts/, others in bin/
_BIN = ROOT / ".venv" / ("Scripts" if sys.platform == "win32" else "bin")
_EXE = ".exe" if sys.platform == "win32" else ""
VENV_PYTHON = _BIN / f"python{_EXE}"
COMFY_CLI = _BIN / f"comfy{_EXE}"
