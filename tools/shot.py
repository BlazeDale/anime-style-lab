"""📸 Screenshot the gallery as a browser draws it (headless Edge against the running serve_gallery), optionally after a script.

  python tools/shot.py out.png [--js "sgOpen('001-my-saga')"] [--hash "#/nev"] [--wait 8000] [--size 1600,900]
                       [--store key=json ...]

It copies gallery/index.html to gallery/_shot.html with a <script> that presets localStorage (--store) and runs --js a moment after load,
loads http://127.0.0.1:<gallery_port>/gallery/_shot.html<hash> in headless Edge for --wait ms of virtual time, saves the PNG, and deletes the copy.
(The AGENTS.md visual-check recipe, hard-wired so it needs no one-off shell commands.)
"""
import argparse, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from config import GALLERY_PORT  # noqa: E402
EDGE = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--js", default="")
    ap.add_argument("--hash", default="")
    ap.add_argument("--wait", type=int, default=8000)
    ap.add_argument("--size", default="1600,900")
    ap.add_argument("--store", action="append", default=[], help="localStorage key=json, set before the page script runs")
    a = ap.parse_args()
    edge = next((e for e in EDGE if Path(e).exists()), None)
    if not edge:
        sys.exit("msedge.exe not found")
    src = (ROOT / "gallery" / "index.html").read_text(encoding="utf-8")
    pre = "".join(f"localStorage.setItem({json.dumps(k)}, {json.dumps(v)});" for k, v in (s.split("=", 1) for s in a.store))
    head = f"<script>try{{{pre}}}catch(e){{}}</script>"
    tail = f"<script>window.addEventListener('load',()=>setTimeout(()=>{{try{{{a.js}}}catch(e){{document.title='JS ERROR '+e}}}},2500));</script>" if a.js else ""
    html = src.replace("<head>", "<head>" + head, 1)
    i = html.rfind("</body>")
    html = html[:i] + tail + html[i:] if i >= 0 else html + tail
    shot = ROOT / "gallery" / "_shot.html"
    shot.write_text(html, encoding="utf-8")
    out = Path(a.out).resolve()
    try:
        subprocess.run([edge, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={a.size}", f"--virtual-time-budget={a.wait}",
                        f"--screenshot={out}", f"http://127.0.0.1:{GALLERY_PORT}/gallery/_shot.html{a.hash}"], timeout=120, capture_output=True)
    finally:
        shot.unlink(missing_ok=True)
    print(out if out.exists() else "no screenshot written")


if __name__ == "__main__":
    main()
