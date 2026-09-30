"""Render journey chapters: journeys/NNN-slug/chNN/ -> sNN.png scenes of one character exploring their world.

Journeys (the gallery's 🧭 page) follow ONE character from a lab image through their own world, chapter by chapter;
the user directs each next chapter from the gallery. Character consistency comes from Qwen 2.1's reference-image input:
the journey's `refs` (default: the source portrait) are fed to TextEncodeQwenImage21 (vision tokens + VAE reference
latents), and every scene prompt repeats the same character sheet in the source image's own style prompt.

  journey.json   {title, name, source, source_cap, style ("...{subject}..." style prompt of the source version),
                  character (look: face, hair, costume, props), world (setting bible), refs: [png, ...], ref_resolution}
  chNN/chapter.json {title, direction, summary, choices: [next-path suggestions], params: {...},
                  scenes: [{id: "s1", shot, caption, prompt, seed}]}
  chNN/sN.png (+ sN.workflow.json: the exact API graph that was submitted)

Usage:
    .venv/Scripts/python tools/run_journey.py journeys/001-x/ch01 [...more]
    .venv/Scripts/python tools/run_journey.py --reroll journeys/001-x/ch01/s3.png
"""
import importlib
import json
import random
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import build_gallery
import pipeline
import run_version as rv

ROOT = rv.ROOT
DEFAULTS = {**rv.DEFAULTS, "aspect_ratio": "16:9 (Widescreen)", "megapixels": 1.2}

# every scene: the character lives in the world, never poses for the viewer (user 2026-09-25: "They should not be
# posing for the picture but existing in their world", "much more detail given to the world")
CANDID = ("A candid in-world moment, like a still from the film: the character is absorbed in what they are doing and "
          "unaware of the viewer, not posing, not looking at the camera, seen in three-quarter view, profile or from behind, "
          "eyes on their task or on the world around them. The world is the co-star: a richly detailed, "
          "lived-in environment filling the whole frame, with depth, atmosphere and small storytelling details. "
          "Keep the character's face, hair, outfit and colors exactly as in the reference image, but ONLY their appearance: "
          "the pose, action, hands, props and place come from this description, not from the reference image.")
# (the reference image leaks its POSE too: if the source portrait shows a specific action, scenes copy it; CANDID says the
# reference is appearance only, but still check every chapter)
# scenes with a director's `camera` field: the camera leads the prompt and CANDID drops its fixed "three-quarter view,
# profile or from behind", which fights every framing that isn't one of those three
CANDID_DIRECTED = CANDID.replace("seen in three-quarter view, profile or from behind, ", "")


def load(chdir: Path):
    j = json.loads((chdir.parent / "journey.json").read_text(encoding="utf-8"))
    ch = json.loads((chdir / "chapter.json").read_text(encoding="utf-8"))
    params = {**DEFAULTS, **ch.get("params", {})}
    return j, ch, params


def look(v):
    """cast entries: "look text" or {"look": text, "ref": lab png, "from": caption}: a library cameo (user 2026-09-25:
    "remember characters from that person's style ... if a need for one arises it can be someone from our library")"""
    return v["look"] if isinstance(v, dict) else v


def scene_refs(j, sc):
    """-> [(png, who)]: the lead's refs, then the portrait of every cast cameo in this scene that has one.
    Only same-style library characters get a `ref` (a portrait in another style would drag that style in); cross-style
    cameos stay text-only and are redrawn in the journey's style."""
    # scene `refs` override the lead's references (e.g. an in-cockpit scene instead of the standing source portrait,
    # whose pose can keep coming back)
    # scene `noref`: no lead reference at all, for wide shots where the lead is tiny (with the face ref present the
    # model can paste a big portrait of the lead over the action)
    # journey `ref_for` {png: cast member}: a ref that is NOT the lead's face (e.g. a cropped egg) goes only to scenes whose
    # `with` names that member (noref scenes too), and is named in the prompt
    rf = j.get("ref_for") or {}
    lead_all = sc.get("refs") or j.get("refs") or [j["source"]]
    lead = [r for r in lead_all if rf.get(r, j["name"]) == j["name"] or sc.get("refs")] or [j["source"]]
    refs = [] if sc.get("noref") else [(r, j["name"]) for r in lead]
    for r in (j.get("refs") or []):
        who = rf.get(r)
        if who and who != j["name"] and who in sc.get("with", []):
            refs.append((r, who))
    for n in sc.get("with", []):
        v = j.get("cast", {}).get(n)
        if isinstance(v, dict) and v.get("ref"):
            refs.append((v["ref"], n))
    return refs


NOFIG_RE = re.compile(r"NO (person|people|face|faces|woman|man|human|figure)", re.I)


def is_nofigure(sc):
    """an insert / empty landscape with nobody in frame: explicit `nofigure`, or a noref scene whose camera says NO person/face.
    Without this, inserts (hands, an egg, a shackle) grow a stranger's face, because every prompt would still end with
    CANDID ('the character is absorbed ... keep the character's face, hair ...') and '<lead> is the only person in the scene'."""
    return bool(sc.get("nofigure")) or (bool(sc.get("noref")) and bool(NOFIG_RE.search(sc.get("camera", ""))))


def scene_prompt(j, sc):
    """journey `cast` {name: look} + scene `with` [names]: only the people actually in the scene are described
    (with every NPC and every location in the shared world text, characters blend together and props leak between
    places). Journeys without a cast keep the old behavior (everything in `world`)."""
    # noref wide shots: the scene is the subject; the lead is only mentioned inside the scene prompt (with the
    # character sheet leading the prompt, the lead is still drawn big in the foreground even without a reference)
    subject = sc["prompt"] if sc.get("noref") else f"{j['name']}, {j['character']}, {sc['prompt']}"
    style = j["style"]
    body = style.replace("{subject}", subject) if "{subject}" in style else f"{style} {subject}."
    cam = sc.get("camera", "").strip().rstrip(".")
    if cam:  # the frame first: shot size, angle, lens, where each figure sits, what is cropped
        body = f"Camera: {cam}. {body}"
    candid = CANDID_DIRECTED if cam else CANDID
    if is_nofigure(sc):  # no character to be candid about: say so, and describe only non-human cast (a beast, an egg)
        idx = {w: i for i, (_, w) in enumerate(scene_refs(j, sc), 1) if w != j["name"]}
        things = [f"{n} is {look(j.get('cast', {})[n])}" + (f" (reference image {idx[n]})" if n in idx else "")
                  for n in sc.get("with", []) if n in j.get("cast", {})]
        return (f"{body} {'In the frame: ' + '; '.join(things) + '. ' if things else ''}"
                f"There are no people in this image: no faces, no heads, no bodies except what the camera line names. "
                f"Setting: {sc.get('place') or j.get('world', '')}")
    if "cast" not in j:
        return f"{body} World: {j['world']} {candid}"
    people = [f"{n} is {look(j['cast'][n])}" for n in sc.get("with", [])]
    who = ("Also in the scene: " + "; ".join(people) + ".") if people else f"{j['name']} is the only person in the scene."
    refs = scene_refs(j, sc)
    notes = j.get("ref_notes") or {}
    if any(w != j["name"] or notes.get(r) for r, w in refs):  # cameos / targeted / noted refs: say which image is whom
        who += " " + " ".join(
            f"Reference image {i} shows {w}: {notes[r]}." if w == j["name"] and notes.get(r)
            else f"Reference image {i} shows {notes[r] if notes.get(r) else w}." for i, (r, w) in enumerate(refs, 1))
    return f"{body} {who} Setting: {sc.get('place') or j['world']} {candid}"


def upload(png: Path):
    """copy a reference image into ComfyUI's input folder (multipart POST /upload/image); returns its input name"""
    name = "journey_" + "_".join(png.relative_to(ROOT).with_suffix("").parts[-3:]).replace("@", "-").replace("~", "-") + ".png"
    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: image/png\r\n\r\n".encode(),
        png.read_bytes(), f"\r\n--{boundary}--\r\n".encode()])
    req = urllib.request.Request(rv.SERVER + "/upload/image", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["name"]


def png_size(png: Path):
    import struct
    w, h = struct.unpack(">II", png.read_bytes()[16:24])  # IHDR width/height
    return w, h


def build_graph(j, params, prompt, seed, prefix, refs=None):
    tmp = ROOT / "journeys" / "_tmp_workflow.json"
    tmp.write_bytes(rv.BASE.read_bytes())
    sets = {"459.prompt": prompt, "459.seed": seed, "459.steps": params["steps"], "459.cfg": params["cfg"],
            "459.scheduler": params["sampler"], "459.scheduler_1": params["scheduler"], "459.unet_name": params["model"],
            "13.aspect_ratio": params["aspect_ratio"], "13.megapixels": params["megapixels"], "461.filename_prefix": prefix}
    rv.comfy("workflow", "set-slot", str(tmp), *[f"{k}={json.dumps(v)}" for k, v in sets.items()])
    graph = rv.comfy("run", "--workflow", str(tmp), "--print-prompt")["data"]["prompt"]
    tmp.unlink(missing_ok=True)
    te = next(k for k, n in graph.items() if n["class_type"] == "TextEncodeQwenImage21")
    vae = next(k for k, n in graph.items() if n["class_type"] == "VAELoader")
    crops = j.get("ref_crop", {})  # {png: [x0, y0, x1, y1] fractions}: e.g. head-and-shoulders only
    for i, ref in enumerate(refs if refs is not None else (j.get("refs") or [j["source"]]), 1):
        graph[f"ref{i}"] = {"class_type": "LoadImage", "inputs": {"image": upload(ROOT / ref)}}
        src = [f"ref{i}", 0]
        if ref in crops:
            w, h = png_size(ROOT / ref)
            x0, y0, x1, y1 = crops[ref]
            graph[f"crop{i}"] = {"class_type": "ImageCrop", "inputs": {"image": src, "x": int(x0 * w), "y": int(y0 * h),
                                                                        "width": int((x1 - x0) * w), "height": int((y1 - y0) * h)}}
            src = [f"crop{i}", 0]
        graph[te]["inputs"][f"images.image_{i}"] = src
    graph[te]["inputs"]["vae"] = [vae, 0]
    graph[te]["inputs"]["resolution"] = j.get("ref_resolution", 768)  # smaller refs = fewer tokens = faster scenes
    if params.get("negative"):
        graph[te]["inputs"]["negative_prompt"] = params["negative"]
    return graph


JOB = None


def render(chdir: Path, j, params, sc, seed=None):
    out = chdir / f"{sc['id']}.png"
    if out.exists():
        return
    seed = seed or sc.get("seed") or params["seeds"][0]
    if JOB:
        JOB.start(pipeline.rel(out))
    try:
        graph = build_graph(j, params, scene_prompt(j, sc), seed, f"anime-style-lab/journey_{chdir.parent.name}_{chdir.name}_{sc['id']}",
                            [r for r, _ in scene_refs(j, sc)])
        (chdir / f"{sc['id']}.workflow.json").write_text(json.dumps(graph, indent=1, ensure_ascii=False), encoding="utf-8")
        t0 = time.time()
        hist = rv.submit_and_wait(graph)
        imgs = [i for o in hist["outputs"].values() for i in o.get("images", [])]
        if not imgs:
            raise RuntimeError(f"no image output for {out}")
        q = urllib.parse.urlencode({k: imgs[0][k] for k in ("filename", "subfolder", "type")})
        with urllib.request.urlopen(f"{rv.SERVER}/view?{q}") as r:
            out.write_bytes(r.read())
        print(f"done {pipeline.rel(out)} in {time.time() - t0:.0f}s", flush=True)
    except BaseException:
        if JOB:
            JOB.finish(pipeline.rel(out), ok=False)
        raise
    if JOB:
        JOB.finish(pipeline.rel(out))
    # reload: long render jobs must pick up builder edits made while they run (else they rewrite a stale gallery)
    importlib.reload(build_gallery).main()


def label(chdir, sc):
    return f"🧭 {chdir.parent.name} {chdir.name} · {sc['id']} {sc.get('shot', '')}".strip()


def reroll(png: Path):
    """🎲 on a scene: same prompt, fresh seed, same file name; the old png moves to chNN/_rerolled/"""
    png = png.resolve()
    chdir = png.parent
    j, ch, params = load(chdir)
    sc = next(s for s in ch["scenes"] if s["id"] == png.stem)
    seed = random.randint(1, 2**31 - 1)
    arch = chdir / "_rerolled"
    arch.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for f in (png, chdir / f"{png.stem}.workflow.json"):
        if f.exists():
            f.replace(arch / f"{f.stem}__{stamp}{f.suffix}")
    ch.setdefault("rerolls", {}).setdefault(sc["id"], []).append(seed)
    sc["seed"] = seed
    (chdir / "chapter.json").write_text(json.dumps(ch, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    render(chdir, j, params, sc, seed)


if __name__ == "__main__":
    if "--reroll" in sys.argv:
        png = ROOT / sys.argv[sys.argv.index("--reroll") + 1]
        JOB = pipeline.Job("reroll", [{"kind": "image", "out": pipeline.rel(png), "label": "🎲 " + label(png.parent, {"id": png.stem})}])
        reroll(png)
        sys.exit()
    jobs = []
    for arg in (a for a in sys.argv[1:] if not a.startswith("--")):
        chdir = (ROOT / arg).resolve()
        j, ch, params = load(chdir)
        jobs += [(chdir, j, params, sc) for sc in ch["scenes"]]
    todo = [(c, sc) for c, j, p, sc in jobs if not (c / f"{sc['id']}.png").exists()]
    if todo:
        JOB = pipeline.Job("journey", [{"kind": "image", "out": pipeline.rel(c / f"{sc['id']}.png"), "label": label(c, sc)} for c, sc in todo])
    for chdir, j, params, sc in jobs:
        render(chdir, j, params, sc)
