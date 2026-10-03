"""📖 Saga chapter rendering: explore_render.py with journey-style character consistency.
  python tools/explore_render.py explore/sagas/NNN-slug/chNN [--only e3] [--force-timer] [--dry-run [--graph]] [--no-steer]
explore_render.py hands every episode that has `saga` in its episode.json to this module for the two things that differ:
  prompt_of(ep, shot, edir, ...)  the saga style with {subject} filled by the shot prompt, then (journeys' scene_prompt idea, no lead character):
                                  "In the scene: <name> is <look>; ..." for every cast member in the shot's `with` (looks read from saga.json at render
                                  time, so a bible edit applies at once), "Reference image N shows <name>: appearance only." for each reference,
                                  "Setting: <place look>" (shot `place` = a bible place name -> its look, or free text), one consistency clause, then the
                                  explore steer cue. A `camera` field leads ("Camera: ..."); `nofigure` shots use run_journey.scene_prompt's no-people branch.
  build(ep, shot, i, edir)        the same graph run_journey builds (TextEncodeQwenImage21 `images.image_N` + vae, ref_crop via ImageCrop): every cast member
                                  in `with` that has a `ref` (+ `ref_crop`) is fed as a reference image; `noref` shots get none (wide shots where the figures are tiny).
Everything else (steer cue, per-shot re-read of episode.json, the explore timer, _discarded/, gallery rebuild) is explore_render's own loop.
After a chapter: `saga.py setref <saga> "<name>" chNN/eK.png [--crop ...]` for every new character without a ref."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CONSISTENCY = ("Draw each named character exactly as described here and in their reference image: the same face, hair, outfit and colors, but ONLY their appearance. "
               "The pose, expression, action, hands, props and place come from this description, not from the reference images; "
               "never copy a reference image's facial expression or smile: each face shows what this moment makes them feel.")


def root_of(edir):
    """explore/sagas/NNN-slug/chNN -> the project root (works for a temp tree too)"""
    return Path(edir).resolve().parents[3]


def load_bible(edir):
    return json.loads((Path(edir).parent / "saga.json").read_text(encoding="utf-8"))


def _look(v):
    return v.get("look", "") if isinstance(v, dict) else str(v)


def journey_view(bible, ep=None):
    """the saga bible as the journey dict run_journey's helpers read (no lead: name '' and every ref belongs to a cast member)"""
    cast = {n: ({"look": _look(v), **({"ref": v["ref"]} if isinstance(v, dict) and v.get("ref") else {})}) for n, v in (bible.get("cast") or {}).items()}
    crops = {v["ref"]: v["ref_crop"] for v in (bible.get("cast") or {}).values() if isinstance(v, dict) and v.get("ref") and v.get("ref_crop")}
    return {"name": "", "character": "", "source": "", "refs": [], "style": (ep or {}).get("style") or bible.get("style", ""),
            "world": (bible.get("world") or {}).get("setting", ""), "cast": cast, "ref_crop": crops,
            "ref_resolution": (bible.get("render") or {}).get("ref_resolution") or bible.get("ref_resolution", 512)}


def place_text(bible, shot):
    pl = (shot.get("place") or "").strip()
    if not pl:
        return ""
    for p in bible.get("places") or []:
        if p.get("name", "").strip().lower() == pl.lower():
            return f"{p['name']}, {p.get('look', '')}".strip(", ")
    return pl


def refs_of(bible, shot, root):
    """-> [(project-relative png, cast name)] in `with` order; none for a `noref` shot; a missing file is skipped"""
    import run_journey as rj
    if shot.get("noref"):
        return []
    j = journey_view(bible)
    got = [(r, w) for r, w in rj.scene_refs(j, {"noref": True, "with": shot.get("with") or []}) if (Path(root) / r).is_file()]
    mr = (bible.get("render") or {}).get("max_refs")   # only the first N characters of `with` (the ones the shot is about) get a portrait; the rest stay text-only
    return got[:int(mr)] if mr else got


def faces_text(shot):
    """shot `faces` {cast name: "eyes wide, jaw tight, fighting tears"} -> "Faces: Mara: eyes wide, ...; Rook: ..." (only names in frame; "" when none)"""
    fc = shot.get("faces") if isinstance(shot.get("faces"), dict) else {}
    with_ = shot.get("with") or []
    items = [f"{n}: {str(v).strip().rstrip('.')}" for n, v in fc.items() if n in with_ and str(v).strip()]
    return ("Faces (expressions for this exact moment): " + "; ".join(items) + ".") if items else ""


def scene_text(bible, ep, shot, root):
    import run_journey as rj
    j = journey_view(bible, ep)
    sc = {"id": shot.get("id"), "prompt": (shot.get("prompt") or "").strip(), "with": shot.get("with") or [], "noref": True,
          "nofigure": bool(shot.get("nofigure")), "camera": shot.get("camera") or "", "place": place_text(bible, shot)}
    if rj.is_nofigure(sc):  # nobody in frame (an insert, a landscape, a creature / an egg): run_journey's no-people branch
        if shot.get("noref"):
            j = {**j, "cast": {n: {"look": v["look"]} for n, v in j["cast"].items()}}
        return rj.scene_prompt(j, sc)
    style = j["style"]
    subject = sc["prompt"]
    body = style.replace("{subject}", subject) if "{subject}" in style else f"{subject}. {style}"
    cam = sc["camera"].strip().rstrip(".")
    parts = [f"Camera: {cam}. {body}" if cam else body]
    fc = faces_text(shot)   # 🎭 the emotion ON the faces, from what is happening in this moment
    if fc:
        parts.append(fc)
    people = [f"{n} ({rj.look(j['cast'][n]).rstrip('. ')})" for n in sc["with"] if n in j["cast"]]
    if people:
        parts.append("In the scene: " + "; ".join(people) + ".")
    refs = refs_of(bible, shot, root)
    if refs:
        parts.append(" ".join(f"Reference image {i} shows {w}: appearance only." for i, (_, w) in enumerate(refs, 1)))
    if sc["place"]:
        parts.append(f"Setting: {sc['place']}.")
    if people:
        parts.append(CONSISTENCY)
    return " ".join(parts)


def render_bible(edir, over=None):
    """saga.json with its `render` knobs {steps, ref_resolution, max_refs, megapixels, upscaler, up_scale} (+ overrides, e.g. from a bake-off)"""
    bible = load_bible(edir)
    return {**bible, "render": {**(bible.get("render") or {}), **(over or {})}} if over else bible


def prompt_of(ep, shot, edir, steer=True, atlas=None, over=None):
    import explore_render as er
    bible = render_bible(edir, over)
    base = scene_text(bible, ep, shot, root_of(edir))
    cue = er.steer_cue(ep, shot, atlas) if steer else ""
    return f"{base} {cue}" if cue else base


def build(ep, shot, i, edir, steer=True, over=None):
    import run_journey
    import explore_render as er
    edir = Path(edir)
    bible = render_bible(edir, over)
    root = root_of(edir)
    refs = refs_of(bible, shot, root)
    j = journey_view(bible, ep)
    params = {**er.params_of(edir), "aspect_ratio": er.aspect_name(shot.get("aspect")), "megapixels": er.MEGAPIXELS}
    rk = bible.get("render") or {}
    if rk.get("steps"):
        params["steps"] = int(rk["steps"])
    if rk.get("megapixels"):
        params["megapixels"] = float(rk["megapixels"])
    g = run_journey.build_graph(j, params, prompt_of(ep, shot, edir, steer, over=over), er.seed_of(shot, i),
                                f"anime-style-lab/saga_{edir.parent.name}_{edir.name}_{shot['id']}", refs=[r for r, _ in refs])
    return add_upscale(g, rk.get("upscaler"), float(rk.get("up_scale") or 0.5))


def add_upscale(g, model, scale=0.5):
    """an optional upscale step before saving (per saga: `render.upscaler` = a file in ComfyUI/models/upscale_models, e.g. 4x-AnimeSharp.pth for clean
    anime line art; textured styles may want none or a general model). The 4x model output is scaled by `scale` (0.5 -> 2x the render). Unchanged without a model."""
    if not model:
        return g
    save = next(k for k, v in g.items() if v.get("class_type", "").startswith("SaveImage"))
    src = g[save]["inputs"]["images"]
    if model == "plain":   # no model: a plain lanczos resize to the same 2x size (the baseline an upscaler has to beat)
        g["up_fit"] = {"class_type": "ImageScaleBy", "inputs": {"image": src, "upscale_method": "lanczos", "scale_by": scale * 4}}
        g[save]["inputs"]["images"] = ["up_fit", 0]
        return g
    g["up_load"] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": model}}
    g["up_rgb"] = {"class_type": "SplitImageWithAlpha", "inputs": {"image": src}}   # the Qwen 2.1 VAE decodes 4 channels; ESRGAN models take RGB
    g["up_run"] = {"class_type": "ImageUpscaleWithModel", "inputs": {"upscale_model": ["up_load", 0], "image": ["up_rgb", 0]}}
    g["up_fit"] = {"class_type": "ImageScaleBy", "inputs": {"image": ["up_run", 0], "upscale_method": "lanczos", "scale_by": scale}}
    g[save]["inputs"]["images"] = ["up_fit", 0]
    return g


def extra_json(ep, shot, edir):
    """what eN.json records besides prompt / seed / steer_cue: which references were fed"""
    bible = load_bible(edir)
    return {"saga": ep.get("saga"), "chapter": ep.get("chapter"), "with": shot.get("with") or [], "place": shot.get("place") or "",
            "refs": [{"image": r, "who": w} for r, w in refs_of(bible, shot, root_of(edir))]}
