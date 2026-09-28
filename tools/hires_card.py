"""Hi-res pass of a rendered card: face detail matters most for a character portrait, so
upscale the image (optionally a crop of it) and re-sample it img2img at a low denoise with a prompt, so it stays the SAME
picture but gains real detail. A crop of the head = a face close-up that matches the card exactly.
  python tools/hires_card.py <card.png> <out.png> [--size 2048] [--denoise 0.35] [--crop x0,y0,x1,y1 (fractions)]
                             [--prompt "..."] [--seed N] [--detail] [--model 4x-AnimeSharp.pth] [--post 4x-AnimeSharp.pth --final 4096]
Default prompt = the card's own prompt (read from its .workflow.json). Built-in nodes only; takes the GPU ticket."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_version as rv  # noqa: E402
import run_journey  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main():
    src, out = ROOT / sys.argv[1], ROOT / sys.argv[2]
    size, denoise = int(arg("--size", 2048)), float(arg("--denoise", 0.35))
    wf = src.with_name(src.stem + ".workflow.json")
    if not wf.exists():  # single-image versions keep the version's workflow.json
        wf = src.parent / "workflow.json"
    raw = json.loads(wf.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and raw and all(isinstance(v, dict) and "class_type" in v for v in raw.values()):
        g = raw  # journeys save the exact API graph already
    else:
        g = rv.comfy("run", "--workflow", str(wf), "--print-prompt")["data"]["prompt"]
    te = next(k for k, n in g.items() if n["class_type"] == "TextEncodeQwenImage21")
    ks = next(k for k, n in g.items() if n["class_type"] == "KSampler")
    vae = next(k for k, n in g.items() if n["class_type"] == "VAELoader")
    lat = next(k for k, n in g.items() if n["class_type"] == "EmptyLatentImage")
    if arg("--prompt"):
        g[te]["inputs"]["prompt"] = arg("--prompt")
    if "--detail" in sys.argv:  # ⤢ upscale: nudge the model to add a little real detail, not change the picture
        g[te]["inputs"]["prompt"] += (" Crisp high-resolution detail: fine texture in fabric, hair strands, skin and materials, clean "
                                      "sharp edges and small highlights, the same composition, colours and style.")
    for k in [k for k, n in g.items() if n["class_type"] == "TextEncodeQwenImage21"]:  # no reference images in a hi-res pass
        for a in [a for a in g[k]["inputs"] if a.startswith("images.")]:
            del g[k]["inputs"][a]
    g["src"] = {"class_type": "LoadImage", "inputs": {"image": run_journey.upload(src)}}
    img = ["src", 0]
    if arg("--crop"):
        from PIL import Image
        w, h = Image.open(src).size
        x0, y0, x1, y1 = [float(v) for v in arg("--crop").split(",")]
        g["crop"] = {"class_type": "ImageCrop", "inputs": {"image": img, "x": int(x0 * w), "y": int(y0 * h),
                                                          "width": int((x1 - x0) * w), "height": int((y1 - y0) * h)}}
        img = ["crop", 0]
        cw, ch = (x1 - x0) * w, (y1 - y0) * h
        W, H = (size, int(size * ch / cw) // 16 * 16) if cw >= ch else (int(size * cw / ch) // 16 * 16, size)
    else:
        from PIL import Image
        w, h = Image.open(src).size
        W, H = (size, int(size * h / w) // 16 * 16) if w >= h else (int(size * w / h) // 16 * 16, size)
    if arg("--model"):  # ESRGAN-type pixel upscale first (built-in nodes), then down to the working size: crisper base than lanczos
        g["upm"] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": arg("--model")}}
        g["upx"] = {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["upm", 0], "image": img}}
        img = ["upx", 0]
    g["up"] = {"class_type": "ImageScale", "inputs": {"image": img, "upscale_method": "lanczos", "width": W, "height": H, "crop": "disabled"}}
    g["enc"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["up", 0], "vae": [vae, 0]}}
    del g[lat]
    g[ks]["inputs"].update(latent_image=["enc", 0], denoise=denoise, seed=int(arg("--seed", g[ks]["inputs"]["seed"])))
    save = next(k for k, n in g.items() if n["class_type"].startswith("SaveImage"))
    if arg("--post"):  # after the detail pass: one more model upscale to --final px on the long side (default 4096)
        fin = int(arg("--final", 4096)); FW, FH = (fin, int(fin * H / W) // 8 * 8) if W >= H else (int(fin * W / H) // 8 * 8, fin)
        dec = g[save]["inputs"]["images"]
        g["postm"] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": arg("--post")}}
        g["rgb"] = {"class_type": "SplitImageWithAlpha", "inputs": {"image": dec}}  # decoded image can be RGBA; ESRGAN wants RGB
        g["postx"] = {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["postm", 0], "image": ["rgb", 0]}}
        g["posts"] = {"class_type": "ImageScale", "inputs": {"image": ["postx", 0], "upscale_method": "lanczos", "width": FW, "height": FH, "crop": "disabled"}}
        g[save]["inputs"]["images"] = ["posts", 0]
    g[save]["inputs"]["filename_prefix"] = "anime-style-lab/hires_" + out.stem
    # show in the ⚙ Queue like any lab render (2026-09-27: hires jobs were invisible there, so the panel looked idle)
    import pipeline
    rel = out.relative_to(ROOT).as_posix()
    job = pipeline.Job("hires", [{"kind": "image", "out": rel, "label": f"🔍 {out.parent.name} · {out.stem}"}])
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
    out.with_suffix(".json").write_text(json.dumps({"source": sys.argv[1], "size": [W, H], "denoise": denoise,
                                                    "crop": arg("--crop"), "prompt": g[te]["inputs"]["prompt"]}, indent=2), encoding="utf-8")
    shutil.copyfile(wf, out.with_name(out.stem + ".workflow.json"))  # so the output can itself be a hires_card input (face crops)
    print("wrote", out.relative_to(ROOT), W, H, flush=True)
    try:  # rebuild so the result shows up in the gallery right away (link next to the button)
        import importlib, build_gallery
        importlib.reload(build_gallery).main()
    except Exception as e:
        print("gallery rebuild failed:", e, flush=True)


if __name__ == "__main__":
    main()
