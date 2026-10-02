"""Tiny project config helper.

Reads config.json at the repo root (falls back to config.example.json if config.json
doesn't exist yet — copy it and edit to override). No dependencies, import-only side effects.

Usage:
    from config import COMFY_URL, COMFY_PYTHON, GALLERY_PORT, FFMPEG, FFPROBE
    # or
    import config
    config.CONFIG["comfy_url"]
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_DEFAULTS = {
    "comfy_url": "http://127.0.0.1:8188",
    "comfy_python": None,
    "gallery_port": 8765,
    "ffmpeg": None,
    "ffprobe": None,
    "font": None,
    "headline_font": None,
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
# comfy_python: the interpreter used for PIL/numpy (and librosa/soundfile for the music-video analysis) helper scripts
# (match_contrast, refit, hires_card, mv_analyze, mv_stems, mv_plates...).
# null in config.json means "use whatever python is running this script" (sys.executable) --
# only set it if you need a *different* interpreter (e.g. ComfyUI's own embedded Python) for those libs.
COMFY_PYTHON = CONFIG["comfy_python"] or sys.executable
GALLERY_PORT = int(CONFIG["gallery_port"])

# ffmpeg / ffprobe (music-video and audio tools): config.json's "ffmpeg"/"ffprobe" (a full path), else whatever is on PATH.
FFMPEG = CONFIG.get("ffmpeg") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = CONFIG.get("ffprobe") or shutil.which("ffprobe") or "ffprobe"


def find_font(kind="font"):
    """A .ttf for burned-in captions: config.json's "font" / "headline_font" if set, else the first common system font found
    (Windows, macOS, Linux). Returns a path string or None (then the caller skips text overlays or uses ffmpeg's default)."""
    want = CONFIG.get("headline_font" if kind == "headline_font" else "font")
    if want and Path(want).exists():
        return str(want)
    bold = kind == "headline_font"
    names = (["arialbd.ttf", "Arial Bold.ttf", "Arial Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"] if bold else
             ["georgiai.ttf", "Georgia Italic.ttf", "arial.ttf", "Arial.ttf", "DejaVuSerif-Italic.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
    dirs = ["C:/Windows/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts", "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/TTF"]
    for d in dirs:
        for n in names:
            if (Path(d) / n).exists():
                return str(Path(d) / n)
    return None


# the project's virtualenv (tools/doctor.py --fix creates it): Windows keeps executables in Scripts/, others in bin/
_BIN = ROOT / ".venv" / ("Scripts" if sys.platform == "win32" else "bin")
_EXE = ".exe" if sys.platform == "win32" else ""
VENV_PYTHON = _BIN / f"python{_EXE}"
COMFY_CLI = _BIN / f"comfy{_EXE}"
