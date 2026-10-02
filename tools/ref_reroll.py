"""🎲 Reroll a generated reference picture (music-video reference, Nev Novel shot) like any other image:
  .venv/Scripts/python tools/ref_reroll.py musicvideos/<id>/refs/<name>.png [--seed N] [--dry-run]
Re-submits the reference's own saved graph (<stem>.workflow.json: gen_N.png from mv_ref_gen.py, *__face_front.png from mv_face.py, or a
hires_card output) with a fresh seed, and replaces the file in place. The old picture + workflow move to refs/_rerolled/
(<stem>__YYYYMMDD-HHMMSS.png, <stem>.workflow__<stamp>.json) so 🕘 past revisions works. The sidecar <stem>.json gets
"seed" updated and "rerolls": [{seed, ts}]. A ✎-fixed ref's saved graph is its inpaint pass, so plain_t2i() runs first.
--dry-run builds the graph with the new seed and prints it; nothing is written, no GPU. Takes the GPU ticket."""
import json
import os
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline  # noqa: E402
import run_version as rv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def is_ref(png: Path):
    return png.suffix == ".png" and ((png.parent.name == "refs" and png.parent.parent.parent.name == "musicvideos")
                                     or png.parent.parent.name == "explore"  # 🌌 explore/NNN-slug/eN.png
                                     or png.parent.parent.parent.name == "sagas")  # 📖 explore/sagas/NNN-slug/chNN/eN.png


def build(png: Path, seed: int):
    """-> the saved graph with a new seed on every KSampler / noise node and a unique SaveImage prefix"""
    wf = png.with_name(png.stem + ".workflow.json")
    g = json.loads(wf.read_text(encoding="utf-8"))
    if not (g and all(isinstance(v, dict) and "class_type" in v for v in g.values())):
        sys.exit(f"{wf.name} is not an API graph")
    rv.plain_t2i(g)
    n = 0
    for node in g.values():
        ins = node["inputs"]
        if node["class_type"] in ("KSampler", "KSamplerAdvanced", "RandomNoise") and ("seed" in ins or "noise_seed" in ins):
            ins["noise_seed" if "noise_seed" in ins else "seed"] = seed
            n += 1
        if node["class_type"].startswith("SaveImage"):
            ins["filename_prefix"] = "anime-style-lab/mvreroll_" + png.stem
    if not n:
        sys.exit("no sampler with a seed in the saved graph")
    return g


def main():
    pos = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and sys.argv[i - 1] != "--seed"]
    if len(pos) != 1:
        sys.exit(__doc__)
    png = (ROOT / pos[0]).resolve()
    if not is_ref(png) or not png.is_file():
        sys.exit(f"not a music-video reference png: {pos[0]}")
    if not png.with_name(png.stem + ".workflow.json").is_file():
        sys.exit(f"no {png.stem}.workflow.json next to it: this reference was not generated here, nothing to re-run")
    seed = int(arg("--seed", 0)) or random.randint(1, 2**31 - 1)
    g = build(png, seed)
    rel = png.relative_to(ROOT).as_posix()
    if "--dry-run" in sys.argv:
        print(f"dry-run: would reroll {rel} with seed {seed}; graph nodes {len(g)}; old files would move to refs/_rerolled/", flush=True)
        return
    job = pipeline.Job("reroll", [{"kind": "image", "out": rel, "label": f"🎲 {png.parent.name if png.parent.parent.name == 'explore' else png.parent.parent.name} · {png.stem}"}])
    job.start(rel)
    try:
        hist = rv.submit_and_wait(g, timeout=3600)
        ims = [i for o in hist["outputs"].values() for i in o.get("images", [])]
        if not ims:
            raise RuntimeError(f"no image output for {rel}")
        with urllib.request.urlopen(f"{rv.SERVER}/view?" + urllib.parse.urlencode({k: ims[0][k] for k in ("filename", "subfolder", "type")})) as r:
            data = r.read()
    except BaseException:
        job.finish(rel, ok=False)
        raise
    arch = png.parent / "_rerolled"
    arch.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    wf = png.with_name(png.stem + ".workflow.json")
    for f in (png, wf):
        if f.exists():
            f.replace(arch / f"{f.stem}__{stamp}{f.suffix}")
    png.write_bytes(data)
    wf.write_text(json.dumps(g, indent=2), encoding="utf-8")
    side = png.with_suffix(".json")
    try:
        meta = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
    except ValueError:
        meta = {}
    if "seed" in meta or not meta:
        meta["seed"] = seed
    meta.setdefault("rerolls", []).append({"seed": seed, "ts": time.strftime("%Y-%m-%d %H:%M:%S")})
    side.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    job.finish(rel)
    print("wrote", rel, "seed", seed, flush=True)
    try:
        import importlib
        import build_gallery
        importlib.reload(build_gallery).main()
    except Exception as e:
        print("gallery rebuild failed:", e, flush=True)


if __name__ == "__main__":
    main()
