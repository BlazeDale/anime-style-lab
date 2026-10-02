"""⬚ Refit an image to another aspect ratio (a resize where the subject is reposed to fit the chosen aspect ratio): re-render the image's own prompt at the new aspect ratio with the image itself as Qwen 2.1 reference
image 1, so the same character/outfit/style/colours come back, re-posed and recomposed to fill the new frame (not cropped or
stretched). Reference edits harden contrast, so the result is matched back to the source afterwards (match_contrast.py).
  python tools/refit.py <image.png> "<aspect ratio as ResolutionSelector names it, e.g. 16:9 (Widescreen)>" [--seed N]
Output: <image dir>/_resized/<name>__<w>x<h>.png (+ .json). Built-in nodes only; takes the GPU ticket."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline  # noqa: E402
import run_journey  # noqa: E402
import run_version as rv  # noqa: E402
from config import COMFY_PYTHON  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ASPECTS = ["1:1 (Square)", "2:3 (Portrait Photo)", "3:2 (Photo)", "3:4 (Portrait Standard)", "4:3 (Standard)",
           "9:16 (Portrait Widescreen)", "16:9 (Widescreen)", "21:9 (Ultrawide)"]
REF = ("Reference image 1 shows exactly this character and scene. Keep the same character, face, hair, outfit, props, art style, "
       "colours and lighting as reference image 1, but recompose the picture for a {shape} frame: re-pose the character naturally "
       "and extend the scene so the new frame is filled edge to edge, nothing cropped off awkwardly, no borders. ")


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main():
    src, aspect = ROOT / sys.argv[1], sys.argv[2]
    if aspect not in ASPECTS:
        sys.exit(f"aspect must be one of {ASPECTS}")
    wf = src.with_name(src.stem + ".workflow.json")
    if not wf.exists():
        wf = src.parent / "workflow.json"
    raw = json.loads(wf.read_text(encoding="utf-8"))
    g = raw if raw and all(isinstance(v, dict) and "class_type" in v for v in raw.values()) else \
        rv.comfy("run", "--workflow", str(wf), "--print-prompt")["data"]["prompt"]
    rv.plain_t2i(g)  # a fix-area image saved its inpaint graph: without this, refit would re-make the old picture
    te = next(k for k, n in g.items() if n["class_type"] == "TextEncodeQwenImage21")
    ks = next(k for k, n in g.items() if n["class_type"] == "KSampler")
    vae = next(k for k, n in g.items() if n["class_type"] == "VAELoader")
    res = next(k for k, n in g.items() if n["class_type"] == "ResolutionSelector")
    w, h = [int(x) for x in aspect.split(" ")[0].split(":")]
    shape = "wide landscape" if w > h else "tall portrait" if h > w else "square"
    # drop any earlier reference images (journeys), then the image itself becomes reference image 1
    for a in [a for a in g[te]["inputs"] if a.startswith("images.")]:
        del g[te]["inputs"][a]
    g["refit_src"] = {"class_type": "LoadImage", "inputs": {"image": run_journey.upload(src)}}
    g[te]["inputs"].update({"images.image_1": ["refit_src", 0], "vae": [vae, 0], "resolution": 1024,
                            "prompt": REF.format(shape=shape) + g[te]["inputs"]["prompt"]})
    g[res]["inputs"]["aspect_ratio"] = aspect
    g[res]["inputs"]["megapixels"] = max(1.0, float(g[res]["inputs"].get("megapixels", 1)))
    if arg("--seed"):
        g[ks]["inputs"]["seed"] = int(arg("--seed"))
    out = src.parent / "_resized" / f"{src.stem}__{w}x{h}.png"
    save = next(k for k, n in g.items() if n["class_type"].startswith("SaveImage"))
    g[save]["inputs"]["filename_prefix"] = "anime-style-lab/refit_" + out.stem
    rel = out.relative_to(ROOT).as_posix()
    job = pipeline.Job("refit", [{"kind": "image", "out": rel, "label": f"⬚ {src.parent.parent.name} {src.stem} → {w}:{h}"}])
    job.start(rel)
    try:
        hist = rv.submit_and_wait(g, timeout=3600)
    except BaseException:
        job.finish(rel, ok=False)
        raise
    job.finish(rel)
    ims = [i for o in hist["outputs"].values() for i in o.get("images", [])]
    import urllib.parse
    import urllib.request
    q = urllib.parse.urlencode({k: ims[0][k] for k in ("filename", "subfolder", "type")})
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{rv.SERVER}/view?{q}") as r:
        out.write_bytes(r.read())
    subprocess.run([COMFY_PYTHON, str(ROOT / "tools" / "match_contrast.py"), str(out), str(src)], cwd=ROOT)
    out.with_suffix(".json").write_text(json.dumps({"source": sys.argv[1], "aspect": aspect, "seed": g[ks]["inputs"]["seed"]}, indent=2),
                                        encoding="utf-8")
    print("wrote", rel, flush=True)
    try:  # rebuild so the result shows up in the gallery right away (link next to the button)
        import importlib, build_gallery
        importlib.reload(build_gallery).main()
    except Exception as e:
        print("gallery rebuild failed:", e, flush=True)


if __name__ == "__main__":
    main()
