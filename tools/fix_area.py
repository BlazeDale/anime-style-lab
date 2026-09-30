"""✎ Fix area: INPAINT one user-drawn box of an image; everything outside the box stays pixel-identical.
(Whole-image edits via reference+img2img ignore the instruction: Qwen 2.1 just redraws the picture, so the edit is local.)
  python tools/fix_area.py <evolutions/.../x.png | journeys/.../chNN/sN.png> x0 y0 x1 y1 "<what should be there>"
         [--denoise 1.0] [--feather 24] [--seed N] [--dry-run]        (box = 0-1 fractions of the picture)
Method, core ComfyUI nodes only: VAEEncode the picture, SetLatentNoiseMask with the (grown) box, KSampler at full denoise inside
the mask with the image's own prompt led by "In the marked area: <text>." (style clauses that ask for faces are dropped when the
text says remove / no face / no person), VAEDecode; then the result is pasted back over the ORIGINAL pixels through a feathered
mask locally (PIL), so nothing outside the box (bar the feather ring) changes at all.
The result replaces the image like a reroll (old png + workflow -> <dir>/_rerolled/); params.json (evolutions) / chapter.json
(journeys) get "fixes_area": {<image name>: [{box, text, denoise, feather, seed, ts}]}."""
import importlib
import json
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline  # noqa: E402
import run_version as rv  # noqa: E402
import run_journey  # noqa: E402

ROOT = rv.ROOT
GROW = 0.12  # the sampled mask is the box grown by this fraction of its size on every side, so the fill has room to blend
REMOVE = re.compile(r"\b(remove|removed|removing|no face|no faces|no person|no people|no human|without (a |any )?(face|person|human)|erase|delete)\b", re.I)
FACEY = re.compile(r"\b(faces?|facial|eyes?|eyelids?|heavy-lidded|lifelike|portrait|hair|gaze|stare|staring|looking at the (viewer|camera))\b", re.I)
WRAP = "Description of the original image (apply the edit on top of it): "


def original_graph_and_prompt(png: Path):
    """-> (API graph of the image's own render, its original prompt). Saved workflow first (exact prompt, incl. {subject} filled
    from subjects.json / journey scene_prompt at render time); else rebuilt from prompt.txt+subjects / scene_prompt."""
    wf = png.with_name(png.stem + ".workflow.json")
    if not wf.exists():
        wf = png.parent / "workflow.json"
    raw = json.loads(wf.read_text(encoding="utf-8"))
    g = raw if raw and all(isinstance(v, dict) and "class_type" in v for v in raw.values()) else         rv.comfy("run", "--workflow", str(wf), "--print-prompt")["data"]["prompt"]
    te = next(k for k, n in g.items() if n["class_type"] == "TextEncodeQwenImage21")
    prompt = g[te]["inputs"].get("prompt")
    if not prompt:
        if png.parent.name.startswith("ch"):
            j, ch, _ = run_journey.load(png.parent)
            prompt = run_journey.scene_prompt(j, next(s for s in ch["scenes"] if s["id"] == png.stem))
        else:
            _, items = rv.load_version(png.parent)
            prompt = next(p for n, p, _ in items if n == png.stem)
    return g, prompt


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def clean_prompt(p):
    """the image's real prompt, even if a saved workflow wrapped the original in an edit instruction"""
    return p.split(WRAP, 1)[1] if WRAP in p else p


def strip_faces(prompt):
    """drop the clauses that ask for faces: sentence by sentence, then comma clause by comma clause inside the survivors"""
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", prompt):
        if not FACEY.search(sent):
            out.append(sent)
            continue
        kept = [c for c in sent.split(", ") if not FACEY.search(c)]
        if kept and len(kept) * 2 >= len(sent.split(", ")):  # mostly non-face sentence: keep its other clauses
            out.append(", ".join(kept).rstrip(",") + ("" if kept[-1].rstrip().endswith((".", "!", "?")) else "."))
    return " ".join(out)


def make_prompt(orig, text, box):
    text = text.strip().rstrip(".")
    base = clean_prompt(orig)
    removing = bool(REMOVE.search(text))
    if removing:
        base = strip_faces(base)
    return f"In the marked area: {text}. Everything else stays as it is. " + base, removing


def upload_mask(img, name):
    buf = BytesIO()
    img.save(buf, "PNG")
    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n".encode(),
        buf.getvalue(), f"\r\n--{boundary}--\r\n".encode()])
    req = urllib.request.Request(rv.SERVER + "/upload/image", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["name"]


def build(png: Path, box, text, denoise, seed, dry=False):
    from PIL import Image
    g, orig = original_graph_and_prompt(png)
    te = next(k for k, n in g.items() if n["class_type"] == "TextEncodeQwenImage21")
    ks = next(k for k, n in g.items() if n["class_type"] == "KSampler")
    vae = next(k for k, n in g.items() if n["class_type"] == "VAELoader")
    prompt, removing = make_prompt(orig, text, box)
    for k in [k for k, n in g.items() if k.startswith("edit_") or k.startswith("fix_")]:  # leftovers of a previous edit graph
        del g[k]
    for a in [a for a in g[te]["inputs"] if a.startswith("images.")]:
        del g[te]["inputs"][a]
    g[te]["inputs"]["prompt"] = prompt
    g[te]["inputs"]["resolution"] = 1024 if "resolution" not in g[te]["inputs"] else g[te]["inputs"]["resolution"]
    src = Image.open(png).convert("RGB")
    w, h = src.size
    W, H = w // 16 * 16, h // 16 * 16
    stem = "fix_" + "_".join(png.relative_to(ROOT).with_suffix("").parts[-3:]).replace("@", "-").replace("~", "-")
    # sampled mask: the box grown by GROW, binary, at the encode size
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    gx0, gy0, gx1, gy1 = max(0, x0 - bw * GROW), max(0, y0 - bh * GROW), min(1, x1 + bw * GROW), min(1, y1 + bh * GROW)
    m = Image.new("L", (W, H), 0)
    m.paste(255, (round(gx0 * W), round(gy0 * H), round(gx1 * W), round(gy1 * H)))
    if dry:
        return g, prompt, (w, h), (gx0, gy0, gx1, gy1), removing, m
    g["fix_src"] = {"class_type": "LoadImage", "inputs": {"image": _upload_png(src, stem + ".png")}}
    g["fix_mask_img"] = {"class_type": "LoadImage", "inputs": {"image": upload_mask(m.convert("RGB"), stem + "_mask.png")}}
    g["fix_mask"] = {"class_type": "ImageToMask", "inputs": {"image": ["fix_mask_img", 0], "channel": "red"}}
    img = ["fix_src", 0]
    if (W, H) != (w, h):
        g["fix_fit"] = {"class_type": "ImageScale", "inputs": {"image": img, "upscale_method": "lanczos", "width": W, "height": H, "crop": "disabled"}}
        img = ["fix_fit", 0]
    g["fix_enc"] = {"class_type": "VAEEncode", "inputs": {"pixels": img, "vae": [vae, 0]}}
    g["fix_nm"] = {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["fix_enc", 0], "mask": ["fix_mask", 0]}}
    g[ks]["inputs"].update(latent_image=["fix_nm", 0], denoise=denoise, seed=seed)
    save = next(k for k, n in g.items() if n["class_type"].startswith("SaveImage"))
    g[save]["inputs"]["filename_prefix"] = f"anime-style-lab/{stem}"[:120]
    return g, prompt, (w, h), (gx0, gy0, gx1, gy1), removing, m


def _upload_png(img, name):
    return upload_mask(img, name)  # same multipart upload; not a mask, just a picture


def composite(orig_png: Path, result_bytes, box, feather):
    """paste the generated pixels over the ORIGINAL through a feathered version of the grown box; outside it is untouched"""
    from PIL import Image, ImageFilter
    orig = Image.open(orig_png).convert("RGB")
    w, h = orig.size
    new = Image.open(BytesIO(result_bytes)).convert("RGB")
    if new.size != (w, h):
        new = new.resize((w, h), Image.LANCZOS)
    x0, y0, x1, y1 = box
    inner = Image.new("L", (w, h), 0)
    f = max(1, int(feather))
    # the feather ring lies inside the grown box (edges fade over `feather` px), so the mask never reaches outside it
    inner.paste(255, (round(x0 * w) + f, round(y0 * h) + f, round(x1 * w) - f, round(y1 * h) - f) if (x1 - x0) * w > 4 * f and (y1 - y0) * h > 4 * f
                else (round(x0 * w), round(y0 * h), round(x1 * w), round(y1 * h)))
    mask = inner.filter(ImageFilter.GaussianBlur(f / 2))
    out = Image.composite(new, orig, mask)
    buf = BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue()


def main():
    png = (ROOT / sys.argv[1]).resolve()
    box = [float(v) for v in sys.argv[2:6]]
    text = sys.argv[6]
    assert 0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1 and box[2] - box[0] >= 0.02 and box[3] - box[1] >= 0.02, f"bad box {box}"
    # full denoise erases what was there (shape, colours), which suits removals; a fix ("purple boot to match the
    # others") needs the old content as a guide -> 0.65 unless the text removes something
    removal = re.search(r"\b(remove|removing|delete|erase|get rid|no \w+|without|take out|nothing)\b", text, re.I)
    denoise = float(arg("--denoise", 1.0 if removal else 0.65))
    # stale guard: the box was drawn on a specific version of the picture; if a reroll replaced it since, the box no longer fits
    want_mtime = arg("--if-mtime", None)
    if want_mtime is not None and abs(png.stat().st_mtime - float(want_mtime)) > 1:
        rel = png.relative_to(ROOT).as_posix()
        subprocess.run([sys.executable, str(ROOT / "tools" / "feedback.py"), "creply", "image:" + rel,
                        f"✎ Fix area skipped: the picture changed (a 🎲 reroll replaced it) after you drew the box for \"{text}\", "
                        "so the box would land on something else. Draw it again on the current picture."])
        print(f"skipped {rel}: image changed since the box was drawn", flush=True)
        return
    feather = int(arg("--feather", 24))
    seed = int(arg("--seed", random.randint(1, 2**31 - 1)))
    dry = "--dry-run" in sys.argv
    g, prompt, size, grown, removing, mask = build(png, box, text, denoise, seed, dry)
    if dry:
        dbg = ROOT / ".thumbs" / "fix_area_dryrun_mask.png"
        dbg.parent.mkdir(exist_ok=True)
        mask.save(dbg)
        print(f"image: {png.relative_to(ROOT)} {size[0]}x{size[1]}  box {box}  sampled (grown) box {[round(v, 3) for v in grown]}  "
              f"denoise {denoise}  feather {feather}px  seed {seed}  face-clauses-stripped {removing}\nmask preview: {dbg}\n--- prompt ---\n{prompt}")
        return
    is_jrn = png.parent.name.startswith("ch")
    vdir, name = png.parent, png.stem
    wf = vdir / (f"{name}.workflow.json" if is_jrn or not name.startswith("seed") else "workflow.json")
    key = pipeline.rel(png)
    job = pipeline.Job("fix_area", [{"kind": "image", "out": key, "label": f"✎ {vdir.parent.name} {vdir.name} · {name.replace('_seed1001', '')}"}])
    job.start(key)
    try:
        t0 = time.time()
        hist = rv.submit_and_wait(g, timeout=3600)
        ims = [i for o in hist["outputs"].values() for i in o.get("images", [])]
        if not ims:
            raise RuntimeError(f"no image output for {key}")
        q = urllib.parse.urlencode({k: ims[0][k] for k in ("filename", "subfolder", "type")})
        with urllib.request.urlopen(f"{rv.SERVER}/view?{q}") as r:
            data = composite(png, r.read(), grown, feather)
    except BaseException:
        job.finish(key, ok=False)
        raise
    arch = vdir / "_rerolled"
    arch.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for f in (png, wf):
        if f.exists():
            f.replace(arch / f"{f.stem}__{stamp}{f.suffix}")
    png.write_bytes(data)
    wf.write_text(json.dumps(g, indent=1, ensure_ascii=False), encoding="utf-8")
    entry = {"box": box, "text": text, "denoise": denoise, "feather": feather, "seed": seed, "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    meta = vdir / ("chapter.json" if is_jrn else "params.json")
    raw = json.loads(meta.read_text(encoding="utf-8"))
    raw.setdefault("fixes_area", {}).setdefault(name, []).append(entry)
    meta.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    job.finish(key)
    print(f"done {key} in {time.time() - t0:.0f}s (fix area, denoise {denoise})", flush=True)
    try:
        import build_gallery
        importlib.reload(build_gallery).main()
    except Exception as e:
        print("gallery rebuild failed:", e, flush=True)


if __name__ == "__main__":
    main()
