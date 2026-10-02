"""🖼 Generate a requested reference image for a music video (the answer to a "request a reference" from the music-video page).
  python tools/mv_ref_gen.py musicvideos/<id> "<subject text>" [--aspect 1:1|3:4|16:9|...] [--seed N]
                                           [--ref <png>]... [--out name] [--dry-run]
Qwen Image 2.1 text-to-image: the mv's `style` ({subject} slot) filled with the subject text, plus reference images (default: the
lead's face-front ref, refs/*__face_front.png, when there is one; --ref replaces that default, `--ref none` = no reference; the mv's
ref_crop is applied). Writes musicvideos/<id>/refs/gen_<n>.png (+ .json, .workflow.json) and prints its project-relative path.
Does NOT touch mv.json: `tools/feedback.py mvgen <mv> <req-id> <png>` adds the result to refs and closes the request.
--dry-run builds and saves the graph (gen_<n>.workflow.json) without submitting or taking the GPU."""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline  # noqa: E402
import run_journey  # noqa: E402
import run_version as rv  # noqa: E402
import mv_face  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ASPECTS = {"1:1": "1:1 (Square)", "2:3": "2:3 (Portrait Photo)", "3:2": "3:2 (Photo)", "3:4": "3:4 (Portrait Standard)",
           "4:3": "4:3 (Standard)", "9:16": "9:16 (Portrait Widescreen)", "16:9": "16:9 (Widescreen)", "21:9": "21:9 (Ultrawide)"}
MULTI = ("--ref", "--aspect", "--seed", "--out")


def arg(flag, default=None):
    return mv_face.arg(flag, default)


def args_of(flag):
    return [sys.argv[i + 1] for i, a in enumerate(sys.argv[:-1]) if a == flag]


def aspect_name(a):
    a = (a or "3:4").strip()
    for k, v in ASPECTS.items():
        if a == k or a == v or a.split(" ")[0] == k:
            return v
    sys.exit(f"aspect must be one of {list(ASPECTS)}")


def next_out(refs_dir: Path, name=None):
    if name:
        return refs_dir / (name if name.endswith(".png") else name + ".png")
    n = 1
    while (refs_dir / f"gen_{n}.png").exists():
        n += 1
    return refs_dir / f"gen_{n}.png"


def default_refs(mv_dir: Path, m):
    return [r for r in (m.get("refs") or []) if r.endswith("__face_front.png") and (ROOT / r).is_file()][:1]


def prompt_of(m, subject, refs):
    style = (m.get("style") or "").strip()
    body = style.replace("{subject}", subject) if "{subject}" in style else (subject + (". " + style if style else ""))
    notes = m.get("ref_notes") or {}
    pre = ""
    for i, r in enumerate(refs, 1):
        what = notes.get(r) or "a reference"
        pre += (f"Reference image {i} shows {what}: if the picture below is of that same person keep their face, hair and styling exactly, "
                "otherwise take only the art style from it. " if i == 1 else f"Reference image {i} shows {what}. ")
    return pre + body


def build(mv_dir: Path, subject, refs, aspect, seed, out: Path):
    m = json.loads((mv_dir / "mv.json").read_text(encoding="utf-8"))
    refs = refs if refs is not None else default_refs(mv_dir, m)
    params = {**mv_face.params_of(mv_dir / "x" / "y"), "aspect_ratio": aspect, "megapixels": 1.0}
    j = {"ref_crop": m.get("ref_crop") or {}, "ref_resolution": 1024}
    g = run_journey.build_graph(j, params, prompt_of(m, subject, refs), seed, "anime-style-lab/mvgen_" + out.stem, refs=refs)
    return g, refs


def main():
    pos, skip = [], set()
    for i, a in enumerate(sys.argv[1:], 1):
        if a in MULTI:
            skip.add(i + 1)
        if i not in skip and not a.startswith("--"):
            pos.append(a)
    if len(pos) != 2:
        sys.exit(__doc__)
    mv_dir = (ROOT / pos[0]).resolve() if not Path(pos[0]).is_absolute() else Path(pos[0])
    if not (mv_dir / "mv.json").is_file():
        sys.exit(f"no mv.json in {pos[0]}")
    subject = pos[1].strip()
    if not subject:
        sys.exit("empty subject text")
    given = args_of("--ref")
    refs = None if not given else ([] if given == ["none"] else [Path(r).as_posix() for r in given])
    for r in refs or []:
        if not (ROOT / r).is_file():
            sys.exit(f"no such reference: {r}")
    out = next_out(mv_dir / "refs", arg("--out"))
    out.parent.mkdir(parents=True, exist_ok=True)
    seed = int(arg("--seed", 0)) or int.from_bytes(__import__("os").urandom(4), "big") % 2**31
    g, refs = build(mv_dir, subject, refs, aspect_name(arg("--aspect")), seed, out)
    wf = out.parent / (out.stem + ".workflow.json")
    wf.write_text(json.dumps(g, indent=2), encoding="utf-8")
    rel = out.relative_to(ROOT).as_posix()
    if "--dry-run" in sys.argv:
        print("dry-run: graph saved to", wf.relative_to(ROOT).as_posix(), "would write", rel, "refs", refs, flush=True)
        return
    job = pipeline.Job("mvgen", [{"kind": "image", "out": rel, "label": f"🖼 {mv_dir.name} · {out.stem}"}])
    job.start(rel)
    try:
        hist = rv.submit_and_wait(g, timeout=3600)
    except BaseException:
        job.finish(rel, ok=False)
        raise
    job.finish(rel)
    im = [i for o in hist["outputs"].values() for i in o.get("images", [])][0]
    with urllib.request.urlopen(f"{rv.SERVER}/view?" + urllib.parse.urlencode({k: im[k] for k in ("filename", "subfolder", "type")})) as r:
        out.write_bytes(r.read())
    ks = next(k for k, n in g.items() if n["class_type"] == "KSampler")
    out.with_suffix(".json").write_text(json.dumps({"subject": subject, "refs": refs, "aspect": aspect_name(arg("--aspect")),
                                                    "seed": g[ks]["inputs"]["seed"]}, indent=2), encoding="utf-8")
    print(rel, flush=True)


if __name__ == "__main__":
    main()
