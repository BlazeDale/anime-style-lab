"""🙂 Face close-up reference for a music video:
  python tools/mv_face.py <mv id> <ref png> same|front [--seed N]
same  = hi-res re-render of the reference's ✂ face crop (hires_card.py img2img, denoise 0.45 + detail): exactly that face,
        same expression, just big and detailed.
front = a new square close-up drawn with the (cropped) reference as Qwen 2.1 reference image 1: front view, eyes open, calm,
        plain background. A neutral face is the better identity + lip-sync reference than a mid-note one.
Output: musicvideos/<id>/refs/<ref stem>__face_<mode>.png (+ .json), added to the music video's refs with a note.
Built-in nodes only; takes the GPU ticket."""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import COMFY_PYTHON, GALLERY_PORT  # noqa: E402
import pipeline  # noqa: E402
import run_journey  # noqa: E402
import run_version as rv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PY = str(COMFY_PYTHON)  # hires_card.py needs PIL
FRONT = ("Reference image 1 shows this person's face. A close-up portrait of exactly the same person: head and shoulders filling the "
         "frame, facing the viewer straight on, eyes open and looking just past the camera, mouth gently closed, calm neutral "
         "expression, soft even light on the face, plain softly blurred dark background. Keep the same face shape, eyes, eyebrows, "
         "nose, lips, makeup, skin tone, hair, accessories and art style as reference image 1. ")
NOTES = {"same": "face close-up (same expression, hi-res)", "front": "face close-up, front view, eyes open"}


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def out_path(mv, src, mode):
    return ROOT / "musicvideos" / mv / "refs" / f"{Path(src).stem}__face_{mode}.png"


def style_of(src: Path):
    """the lab version's style prompt with the subject swapped for the face close-up (evolutions keep prompt.txt with {subject})"""
    p = src.parent / "prompt.txt"
    if p.exists() and "{subject}" in p.read_text(encoding="utf-8"):
        return p.read_text(encoding="utf-8").replace("{subject}", "a close-up face portrait of the person from reference image 1")
    return ""


def params_of(src: Path):
    p = src.parent / "params.json"
    base = {"steps": 25, "cfg": 1, "sampler": "euler", "scheduler": "simple", "model": "qwen_image_2.1_int8_convrot.safetensors"}
    if p.exists():
        base.update({k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if k in base})
    return {**base, "aspect_ratio": "1:1 (Square)", "megapixels": 1.0}


def front(src: Path, box, out: Path):
    """built from the clean text-to-image template (never the image's own saved graph: after a ✎ fix that is an inpaint
    pass that re-makes the same picture), the (cropped) reference as image 1"""
    rel_src = src.relative_to(ROOT).as_posix()
    seed = int(arg("--seed", 0)) or int.from_bytes(__import__("os").urandom(4), "big") % 2**31
    g = run_journey.build_graph({"ref_crop": {rel_src: box} if box else {}, "ref_resolution": 1024}, params_of(src),
                                FRONT + style_of(src), seed, "anime-style-lab/mvface_" + out.stem, refs=[rel_src])
    ks = next(k for k, n in g.items() if n["class_type"] == "KSampler")
    rel = out.relative_to(ROOT).as_posix()
    job = pipeline.Job("mvface", [{"kind": "image", "out": rel, "label": f"🙂 {out.parent.parent.name} · {out.stem}"}])
    job.start(rel)
    try:
        hist = rv.submit_and_wait(g, timeout=3600)
    except BaseException:
        job.finish(rel, ok=False)
        raise
    job.finish(rel)
    im = [i for o in hist["outputs"].values() for i in o.get("images", [])][0]
    import urllib.parse
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{rv.SERVER}/view?" + urllib.parse.urlencode({k: im[k] for k in ("filename", "subfolder", "type")})) as r:
        out.write_bytes(r.read())
    # (no match_contrast: matching a soft-lit close-up to a dark full-body scene over-saturates the skin)
    (out.parent / (out.stem + ".workflow.json")).write_text(json.dumps(g, indent=2), encoding="utf-8")  # usable as a hires input
    return g[ks]["inputs"]["seed"]


def add_ref(mv, out: Path, note):
    """add the close-up to the music video's refs + its note, through the running gallery server (it owns mv.json);
    straight into mv.json when the server is down"""
    rel = out.relative_to(ROOT).as_posix()
    have = rel in (json.loads((ROOT / "musicvideos" / mv / "mv.json").read_text(encoding="utf-8")).get("refs") or [])
    try:  # (op "ref" TOGGLES, so a redone close-up that's already a reference only gets its note refreshed)
        for body in ([] if have else [{"op": "ref", "mv": mv, "src": rel}]) + [{"op": "ref_note", "mv": mv, "src": rel, "note": note, "for": ""}]:
            req = urllib.request.Request(f"http" + f"://127.0.0.1:{GALLERY_PORT}/api/mv", data=json.dumps(body).encode(), method="POST",
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=20).read()
        return
    except OSError:
        pass
    p = ROOT / "musicvideos" / mv / "mv.json"
    m = json.loads(p.read_text(encoding="utf-8"))
    if rel not in (m.get("refs") or []):
        m["refs"] = (m.get("refs") or []) + [rel]
    m.setdefault("ref_notes", {})[rel] = note
    p.write_text(json.dumps(m, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--") and a != arg("--seed")]
    if len(args) != 3 or args[2] not in NOTES:
        sys.exit(__doc__)
    mv, src_rel, mode = args
    m = json.loads((ROOT / "musicvideos" / mv / "mv.json").read_text(encoding="utf-8"))
    src, box = ROOT / src_rel, (m.get("ref_crop") or {}).get(src_rel)
    if not src.is_file():
        sys.exit(f"no such image: {src_rel}")
    if mode == "same" and not box:
        sys.exit("'same' needs a ✂ face crop on this reference first")
    out = out_path(mv, src_rel, mode)
    if mode == "same":
        face = style_of(src).replace("from reference image 1", "")  # the style + a face subject (the crop IS the picture)
        r = subprocess.run([PY, str(ROOT / "tools" / "hires_card.py"), src_rel, out.relative_to(ROOT).as_posix(), "--size", "1536",
                            "--denoise", "0.45", "--detail", "--crop", ",".join(str(v) for v in box)] + (["--prompt", face] if face else []) + (["--seed", arg("--seed")] if arg("--seed") else []),
                           cwd=ROOT)
        if r.returncode:
            sys.exit(r.returncode)
        seed = None
    else:
        seed = front(src, box, out)
    out.with_suffix(".json").write_text(json.dumps({"source": src_rel, "mode": mode, "crop": box, "seed": seed}, indent=2), encoding="utf-8")
    add_ref(mv, out, NOTES[mode])
    print("wrote", out.relative_to(ROOT).as_posix(), flush=True)


if __name__ == "__main__":
    main()
