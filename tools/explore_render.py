"""🌌 Render an Explore episode's shots (images only).
  python tools/explore_render.py explore/NNN-slug [--only e3 e4 [--redo]] [--force-timer] [--dry-run [--graph]]
  --redo (with --only): the shots re-render from their CURRENT text with a fresh seed; each old picture stays until its replacement
  is ready, then moves to _rerolled/
  (after fixing a bible look or a shot prompt; a plain 🎲 reroll re-runs the saved graph instead)
Every shot of episode.json that has no eN.png yet is rendered with Qwen Image 2.1 text-to-image (the episode `style` with {subject}
filled by the shot prompt, or "<shot prompt>. <style>" when the style has no slot; the shot's `aspect` (default 16:9) at ~1.2 MP; seed =
shot.seed or 1000+index). Writes eN.png + eN.workflow.json (so 🎲 reroll works: ref_reroll.py), puts `src` on the shot, sets the episode
status (rendering -> done, or paused) and rebuilds the gallery after each image.
The explore state (feedback/explore.json, tools/explore_state.py) is checked BEFORE EVERY SHOT: once the 15 minute timer has run out
or the user pressed Stop, rendering stops after the current shot and the episode is left "paused" (run again after Continue to finish
it). --force-timer ignores the state. --dry-run lists what would render (prompts, sizes) without the GPU; --graph also builds the
first graph (needs ComfyUI up for comfy-cli, still no GPU). Takes the GPU ticket per image.
episode.json is RE-READ BEFORE EVERY SHOT (Apply re-steers the story in flight): the next shot without a png, in list order, is the one
rendered, so a mid-render rewrite of the unrendered tail (tools/explore_edit.py) takes effect at once; shots that already have a png are never touched;
a picture whose shot was rewritten while it rendered is set aside in _discarded/ and the new shot rendered instead.
STEER CUE (hard-wired): after the style's {subject} is filled, ONE short sentence built from the episode's CURRENT presence / emotion / formality (or the
shot's own `steer` override) is appended to the image prompt: composition from presence, mood + palette from the emotion, staging from the formality blend's
picture lines. Never camera movement. The exact sentence is saved as "steer_cue" in eN.json. --no-steer turns it off. Claude still writes captions / story by hand."""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import explore_state  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ASPECTS = {"1:1": "1:1 (Square)", "2:3": "2:3 (Portrait Photo)", "3:2": "3:2 (Photo)", "3:4": "3:4 (Portrait Standard)",
           "4:3": "4:3 (Standard)", "9:16": "9:16 (Portrait Widescreen)", "16:9": "16:9 (Widescreen)", "21:9": "21:9 (Ultrawide)"}
MEGAPIXELS = 1.2
STATE_FILE = explore_state.FILE


def aspect_name(a):
    a = (a or "16:9").strip()
    for k, v in ASPECTS.items():
        if a == k or a == v or a.split(" ")[0] == k:
            return v
    raise ValueError(f"aspect must be one of {list(ASPECTS)}, got {a!r}")



# ---------------------------------------------------------------- the steer cue
EMO_CUE = {  # emotion -> (name, mood + palette words)
    "joy": ("joy", "warm golden light and bright saturated colour"),
    "wonder": ("wonder", "clear luminous light and fresh colour"),
    "awe": ("awe", "luminous and expansive, glowing light"),
    "tension": ("tension", "taut, high contrast and cold edges"),
    "dread": ("dread", "ominous deep shadow and sickly muted colour"),
    "melancholy": ("melancholy", "hushed, cool desaturated blues and grey"),
    "longing": ("longing", "wistful dusk light and faded warm colour"),
    "serenity": ("serenity", "calm, soft diffused light and gentle pastel colour"),
}
STEER_WORDS = 45   # words in the whole cue; the maturity ceiling is never cut to fit


def _words(t):
    return len(str(t).split())


def presence_cue(p):
    """presence knob 0-100 -> a composition cue (never camera movement)"""
    p = 50 if p is None else float(p)
    if p <= 12:
        return "very close, hushed, personal framing with soft light"
    if p <= 30:
        return "close, quiet, personal framing with soft light"
    if p < 40:
        return "fairly close, quiet framing with soft light"
    if p <= 60:
        return "composed classic framing"
    if p < 70:
        return "wide composed framing with dramatic light"
    if p < 88:
        return "vast scale, dramatic light, grand composition"
    return "immense scale, dramatic sky and light, grand composition"


def _atlas_items(v, nd, floor=0.2, n=3):
    """the blend's (node, w) pairs that exist in the atlas, heavy first, light ones (< floor) dropped (the top one always stays)"""
    import atlas as fa
    items = [(nd[i], w) for i, w in fa.story_items(v) if i in nd]   # an orbit value folds each sub-link into its parent link
    return ([t for t in items if t[1] >= floor] or items[:1])[:n]


def emotion_cue(e, atlas=None, budget=(9, 5)):
    """Emotion Atlas value -> a mood cue from the blend's picture lines, weighted, scaled by intensity ('' below 0.15 or when neutral): 'Clearly bittersweet, tinged with
    nostalgia: <picture clause>'. The retired 8-emotion wheel object still gives its old phrase."""
    if isinstance(e, dict) and isinstance(e.get("blend"), list):
        if float(e.get("intensity") or 0) < 0.15 or not e["blend"]:
            return ""
        import atlas as fa
        nd = fa.by_id(atlas if atlas is not None and atlas.get("kind") == "emotion" else fa.load(kind="emotion"))
        items = _atlas_items(e, nd)
        if not items:
            return ""
        k = float(e.get("intensity") or 0)
        scale = "a faint" if k < 0.34 else "a clear" if k < 0.67 else "an overwhelming"
        head = f"{scale} mood of {items[0][0]['name'].lower()}"   # a MOOD (atmosphere), not a scene to stage
        if len(items) > 1:
            head += f", tinged with {items[1][0]['name'].lower()}"
        clause = _mood_clause(items[0][0]["picture"], budget[0]) if budget[0] else ""   # mood only (light / colour / tone), never the staging
        if len(items) > 1 and budget[1] and items[1][1] >= 0.3:
            clause = "; ".join(x for x in (clause, _mood_clause(items[1][0]["picture"], budget[1])) if x)
        return head + (": " + clause if clause else "")
    if not isinstance(e, dict) or e.get("primary") not in EMO_CUE:
        return ""
    k = float(e.get("intensity") or 0)
    if k < 0.15:
        return ""
    name, descr = EMO_CUE[e["primary"]]
    scale = "a subtle sense of" if k < 0.34 else "a clear feeling of" if k < 0.67 else "an overwhelming sense of"
    sec, mix = e.get("secondary"), float(e.get("mix") or 0)
    if sec in EMO_CUE and sec != e["primary"] and mix >= 0.15:
        return f"{scale} {name} tinged with {EMO_CUE[sec][0]}, {descr}"
    return f"{scale} {name}, {descr}"


def _clause(picture, n):
    """the first comma-chunks of a picture line, up to n words"""
    out, used = [], 0
    for ch in [c.strip() for c in str(picture).split(",") if c.strip()]:
        w = _words(ch)
        if out and used + w > n:
            break
        out.append(ch)
        used += w
    return ", ".join(out)


MOOD_WORDS = ("light", "lamplight", "glow", "palette", "tone", "haze", "shadow", "blue", "grey", "gray", "gold", "amber", "red", "warm", "cool", "cold", "pale",
              "desaturat", "muted", "hue", "colour", "color", "dim", "bright", "contrast", "saturat", "neon", "silver", "violet", "crimson", "chiaroscuro", "dusk", "glare")
STAGE_WORDS = ("figure", "person", "someone", "adult", "people", "couple", "traveler", "traveller", "man", "woman", "embrace", "kiss", "eye", "face", "hand", "arm",
               "shoulder", "smile", "tear", "head", "expression", "posture", "sitting", "standing", "watching", "holding", "gazing", "touching", "reaching", "running",
               "keepsake", "sea", "water", "window", "room", "hill", "mountain", "petal", "leaves", "scarf", "rain", "street", "crowd", "drenched", "clothed", "body")


def _mood_clause(picture, n):
    """only the MOOD of a picture line (light, colour, tone, atmosphere), never its staging (who does what, where): emotion drives the
    story, it does not dictate every scene ('two adults in a desperate embrace, ..., deep red and amber light' -> 'deep red and amber light')"""
    keep = []
    for ch in [c.strip() for c in str(picture).split(",") if c.strip()]:
        low = ch.lower()
        if any(w in low for w in MOOD_WORDS) and not any(re.search(r"\b" + w, low) for w in STAGE_WORDS):
            keep.append(ch)
    return _clause(", ".join(keep), n) if keep else ""


def _slug(s):
    import re
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def formality_cue(fo, atlas=None, budget=(10, 6, 4)):
    """formality value (Atlas blend, old stick object, or old number) -> a staging cue from the blend's picture lines, weighted ('' when neutral / faint)"""
    if fo is None:
        return ""
    if isinstance(fo, (int, float)):
        v = float(fo)
        return "casual, candid, unposed staging" if v <= 37 else "formal, ceremonial, ordered staging" if v >= 63 else ""
    if not isinstance(fo, dict):
        return ""
    if float(fo.get("intensity") or 0) < 0.15:
        return ""
    import formality_atlas as fa
    atlas = atlas or fa.load()
    nd = fa.by_id(atlas)
    blend = fo.get("blend")
    if not blend:  # an old stick object: its register (and the partner it blended with) are neurons too
        g, sec, mix = fo.get("genre"), fo.get("secondary"), float(fo.get("mix") or 0)
        blend = [{"id": _slug(g), "w": 1 - mix}] + ([{"id": _slug(sec), "w": mix}] if sec else [])
    import atlas as A
    items = [(i, w) for i, w in A.story_items({**fo, "blend": blend}) if i in nd]   # orbit values: sub-links fold into their parent link
    items = [t for t in items if t[1] >= 0.2] or items[:1]
    if not items or (items[0][0] == "everyday" and items[0][1] >= 0.9):
        return ""
    parts = [_clause(nd[i]["picture"], budget[k]) for k, (i, _) in enumerate(items[:3]) if k < len(budget) and budget[k]]
    parts = [p for p in parts if p]
    return "staged as " + "; ".join(parts) if parts else ""


def core_cue(cores, atlas=None, skip=None, words=6):
    """the TOP active core (heaviest weight, >= 0.25) as an undertone, at its weight: a light one is only 'a hint of X'; '' when none / when it is the mood already named"""
    cs = [c for c in (cores or []) if isinstance(c, dict) and c.get("status", "active") == "active" and c.get("blend") and float(c.get("weight", 0.6)) >= 0.25]
    if not cs:
        return ""
    c = max(cs, key=lambda c: float(c.get("weight", 0.6)))
    import atlas as fa
    nd = fa.by_id(atlas if atlas is not None and atlas.get("kind") == "emotion" else fa.load(kind="emotion"))
    top = nd.get(c["blend"][0].get("id"))
    if not top or top["id"] == skip:
        return ""
    name = (c.get("name") or top["name"]).lower()
    wt = float(c.get("weight", 0.6))
    if wt < 0.5 or not words:
        return f"a hint of {name}"
    mood = _mood_clause(top["picture"], words)   # the core's mood (light / tone), not its staging: the story serves the core, the pictures only lean toward it
    return f"an undertone of {name}: {mood}" if mood else f"an undertone of {name}"


def maturity_cue(m, pic_words=8):
    """the maturity stop's pictures line + its ceiling (the ceiling is NEVER trimmed away); '' when the episode has no maturity"""
    if m is None:
        return ""
    import maturity as mt
    pic, ceil = mt.cue(m)
    return (_clause(pic, pic_words) + "; " if pic_words else "") + ceil


def steer_cue(ep, shot=None, atlas=None):
    """ONE short sentence for the image prompt from the episode's CURRENT steer (shot['steer'] overrides per shot); '' when there is nothing to say.
    Parts: presence composition, the emotion blend's mood (weighted picture lines), the top active core's undertone (at its weight), the formality staging, the maturity
    stop's pictures + ceiling. Kept near STEER_WORDS by shrinking tiers (formality first, then the core, then the mood); the maturity ceiling is always kept."""
    ov = (shot or {}).get("steer") or {}
    g = lambda k: ov[k] if k in ov else ep.get(k)  # noqa: E731
    pres, emo, fo, cores, mat = g("presence"), g("emotion"), g("formality"), g("cores"), g("maturity")
    tiers = [  # emotion budget, core words, formality budget, maturity picture words
        ((9, 5), 6, (10, 6, 4), 8), ((7, 0), 4, (6, 0, 0), 6), ((5, 0), 0, (0, 0, 0), 4), ((3, 0), 0, (0, 0, 0), 3)]
    text = ""
    for eb, cw, fb, mw in tiers:
        parts = []
        if pres is not None:
            parts.append(presence_cue(pres))
        e = emotion_cue(emo, None, eb)
        if e:
            parts.append(e)
        skip = None
        if isinstance(emo, dict) and emo.get("blend") and float(emo.get("intensity") or 0) >= 0.15:
            skip = emo["blend"][0].get("id")
        c = core_cue(cores, None, skip, cw)
        if c:
            parts.append(c)
        f = formality_cue(fo, atlas, fb) if any(fb) else ""
        if f:
            parts.append(f)
        m = maturity_cue(mat, mw)
        if m:
            parts.append(m)
        text = "; ".join(parts)
        if _words(text) <= STEER_WORDS:
            break
    if not text:
        return ""
    return text[0].upper() + text[1:] + "."


def prompt_of(ep, shot, steer=True, atlas=None, edir=None):
    """the style with {subject} filled by the shot prompt (or the shot prompt followed by a free-form style), then the one-sentence steer cue.
    A 📖 saga chapter (episode.json has `saga`, edir given) goes through saga_render.prompt_of: characters, references, place."""
    if edir is not None and ep.get("saga"):
        import saga_render
        return saga_render.prompt_of(ep, shot, edir, steer, atlas)
    style = (ep.get("style") or "").strip()
    subject = (shot.get("prompt") or "").strip()
    base = subject if not style else style.replace("{subject}", subject) if "{subject}" in style else f"{subject}. {style}"
    cue = steer_cue(ep, shot, atlas) if steer else ""
    return f"{base} {cue}" if cue else base


def seed_of(shot, i):
    return int(shot.get("seed") or 1000 + i)


def plan(ep, edir, only=None):
    """-> [(index, shot)] still to render (no png yet), limited to `only` ids"""
    out = []
    for i, s in enumerate(ep.get("shots") or [], 1):
        if only and s.get("id") not in only:
            continue
        if (edir / f"{s['id']}.png").is_file():
            continue
        out.append((i, s))
    return out


def load(edir):
    return json.loads((edir / "episode.json").read_text(encoding="utf-8"))


def retire(edir, ids, stamp=None):
    """--redo: move each shot's png (+ workflow / sidecar json) to _rerolled/<id>__<stamp>.* so the shot re-renders from its CURRENT text
    (bible looks, prompt, steer) and 🕘 past revisions keeps the old picture. -> ids that had a picture"""
    stamp = stamp or time.strftime("%Y%m%d-%H%M%S")
    rr = edir / "_rerolled"
    moved = []
    for sid in ids:
        png = edir / f"{sid}.png"
        if not png.is_file():
            continue
        rr.mkdir(exist_ok=True)
        png.replace(rr / f"{sid}__{stamp}.png")
        for src, dst in ((edir / f"{sid}.workflow.json", rr / f"{sid}.workflow__{stamp}.json"), (edir / f"{sid}.json", rr / f"{sid}.json__{stamp}")):
            if src.is_file():
                src.replace(dst)
        moved.append(sid)
    return moved


def patch(edir, shot_id=None, **fields):
    """re-read episode.json (Claude may be editing it) and set fields on the episode, or on one shot when shot_id is given"""
    ep = load(edir)
    if shot_id:
        for s in ep.get("shots") or []:
            if s.get("id") == shot_id:
                s.update(fields)
    else:
        ep.update(fields)
    tmp = edir / "episode.json.tmp"
    tmp.write_text(json.dumps(ep, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(edir / "episode.json")
    return ep


def next_shot(edir, only=None):
    """re-read episode.json and return (ep, index, shot) for the first shot in list order without a png (limited to `only`), or (ep, None, None)"""
    ep = load(edir)
    for i, s in enumerate(ep.get("shots") or [], 1):
        if only and s.get("id") not in only:
            continue
        if not (edir / f"{s['id']}.png").is_file():
            return ep, i, s
    return ep, None, None


def same_shot(a, b):
    """did the shot keep its picture-defining fields (prompt, aspect, seed) between two reads?"""
    return bool(a and b) and all(a.get(k) == b.get(k) for k in ("prompt", "aspect", "seed", "with", "place", "camera", "noref", "nofigure"))


def set_aside(edir, shot_id):
    """a rendered picture whose shot was rewritten while it rendered: move it (and its sidecars) to _discarded/ so the id can render again"""
    d = edir / "_discarded"
    d.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    for suf in (".png", ".json", ".workflow.json"):
        f = edir / f"{shot_id}{suf}"
        if f.is_file():
            f.replace(d / f"{shot_id}__{stamp}{suf}")


def final_status(ep, edir):
    return "done" if all((edir / f"{s['id']}.png").is_file() for s in ep.get("shots") or []) else "paused"


def params_of(edir):
    """default Qwen Image 2.1 sampler settings; a params.json next to the pictures may override them"""
    base = {"steps": 25, "cfg": 1, "sampler": "euler", "scheduler": "simple", "model": "qwen_image_2.1_int8_convrot.safetensors"}
    p = Path(edir) / "params.json"
    if p.exists():
        base.update({k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items() if k in base})
    return {**base, "aspect_ratio": "1:1 (Square)", "megapixels": 1.0}


def build(ep, shot, i, edir, steer=True):
    if ep.get("saga"):  # 📖 saga chapter: reference images of the cast in frame
        import saga_render
        return saga_render.build(ep, shot, i, edir, steer)
    import run_journey
    params = {**params_of(edir), "aspect_ratio": aspect_name(shot.get("aspect")), "megapixels": MEGAPIXELS}
    return run_journey.build_graph({"ref_resolution": 1024}, params, prompt_of(ep, shot, steer), seed_of(shot, i),
                                   f"anime-style-lab/explore_{edir.name}_{shot['id']}", refs=[])


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    only, pos, i = [], [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--only":
            i += 1
            while i < len(argv) and not argv[i].startswith("--"):
                only.append(argv[i])
                i += 1
            continue
        if not a.startswith("--"):
            pos.append(a)
        i += 1
    if len(pos) != 1:
        sys.exit(__doc__)
    edir = Path(pos[0])
    edir = edir if edir.is_absolute() else ROOT / edir
    if not (edir / "episode.json").is_file():
        sys.exit(f"no episode.json in {pos[0]}")
    ep = load(edir)
    dry = "--dry-run" in argv
    redo = set()
    if "--redo" in argv:  # the old picture stays on the page until its replacement is ready
        if not only:
            sys.exit("--redo needs --only <ids> (it re-renders shots that already have a picture)")
        redo = set(only)
        seeds = {s["id"]: int(time.time()) % 100000 + k for k, s in enumerate(ep.get("shots") or []) if s.get("id") in only}
        for sid, sd in seeds.items() if not dry else ():  # a fresh seed, so a redo with unchanged text still gives a new picture
            patch(edir, sid, seed=sd)
        ep = load(edir)
    todo = [(i, s) for i, s in enumerate(ep.get("shots") or [], 1) if s.get("id") in redo] if redo else plan(ep, edir, only)
    steer = "--no-steer" not in argv
    for i, s in todo:
        print(f"{'would render' if dry else 'queued'} {s['id']} ({aspect_name(s.get('aspect'))}, seed {seed_of(s, i)}): {prompt_of(ep, s, steer, edir=edir)[:400]}", flush=True)
        if steer and dry:
            print(f"    steer cue: {steer_cue(ep, s) or '(none)'}", flush=True)
        if ep.get("saga"):
            import saga_render
            print(f"    refs: {[(r, w) for r, w in saga_render.refs_of(saga_render.load_bible(edir), s, saga_render.root_of(edir))] or '(none)'}", flush=True)
    if dry:
        print(f"dry-run: {len(todo)} shot(s) to render, {len(ep.get('shots') or []) - len(todo)} already have a png", flush=True)
        if "--graph" in argv and todo:
            g = build(ep, todo[0][1], todo[0][0], edir, steer)
            print("graph built:", len(g), "nodes", flush=True)
        return
    if not todo:
        patch(edir, status=final_status(ep, edir))
        print("nothing to render", flush=True)
        return
    import pipeline
    import run_version as rv
    import build_gallery
    import importlib

    def rebuild():
        try:
            importlib.reload(build_gallery).main()
        except Exception as e:
            print("gallery rebuild failed:", e, flush=True)

    lbl = f"📖 {edir.parent.name} {edir.name}" if ep.get("saga") else f"🌌 {edir.name}"
    job = pipeline.Job("explore", [{"kind": "image", "out": f"{edir.relative_to(ROOT).as_posix()}/{s['id']}.png",
                                    "label": f"{lbl} · {s['id']}"} for _, s in todo])
    patch(edir, status="rendering")
    rebuild()
    stopped = False
    while True:
        if "--force-timer" not in argv and not explore_state.is_active(STATE_FILE):
            stopped = True
            print("explore state is not active (timer ran out or stopped): pausing", flush=True)
            break
        if redo:
            ep = load(edir)
            i, s = next(((k, x) for k, x in enumerate(ep.get("shots") or [], 1) if x.get("id") in redo), (None, None))
        else:
            ep, i, s = next_shot(edir, only)  # re-read EVERY time: Claude may have rewritten the unrendered rest of the story
        if s is None:
            break
        out = edir / f"{s['id']}.png"
        rel = out.relative_to(ROOT).as_posix()
        queued = {it["out"] for it in job.state["items"]}
        if rel not in queued:
            job.state["items"].append({"model": getattr(pipeline, "MODEL_DEFAULT", {}).get("image", "QI2.1"), "kind": "image", "out": rel, "label": f"{lbl} · {s['id']}", "status": "queued"})
        ids = {x.get("id") for x in ep.get("shots") or []}
        job.state["items"] = [it for it in job.state["items"] if it["status"] != "queued" or Path(it["out"]).stem in ids or it["out"] == rel]
        job.start(rel)
        try:
            cue = steer_cue(ep, s) if steer else ""
            g = build(ep, s, i, edir, steer)
            wf = edir / (f"{s['id']}.workflow.redo.json" if redo else f"{s['id']}.workflow.json")
            wf.write_text(json.dumps(g, indent=1, ensure_ascii=False), encoding="utf-8")
            t0 = time.time()
            hist = rv.submit_and_wait(g, timeout=3600)
            ims = [im for o in hist["outputs"].values() for im in o.get("images", [])]
            if not ims:
                raise RuntimeError(f"no image output for {rel}")
            q = urllib.parse.urlencode({k: ims[0][k] for k in ("filename", "subfolder", "type")})
            with urllib.request.urlopen(f"{rv.SERVER}/view?{q}") as r:
                data = r.read()
            if redo:  # swap: the old picture goes to _rerolled/ only now that the new one exists
                retire(edir, [s["id"]])
                wf.replace(edir / f"{s['id']}.workflow.json")
                redo.discard(s["id"])
            out.write_bytes(data)
            out.with_suffix(".json").write_text(json.dumps({"seed": seed_of(s, i), "aspect": aspect_name(s.get("aspect")), "prompt": prompt_of(ep, s, steer, edir=edir), "steer_cue": cue,
                                                            **(__import__("saga_render").extra_json(ep, s, edir) if ep.get("saga") else {})},
                                                           indent=2, ensure_ascii=False), encoding="utf-8")
        except BaseException:
            job.finish(rel, ok=False)
            patch(edir, status="paused")
            raise
        job.finish(rel)
        now_ep = load(edir)
        cur = next((x for x in now_ep.get("shots") or [] if x.get("id") == s["id"]), None)
        if not same_shot(s, cur):  # the story was rewritten while this picture rendered: it no longer belongs to the episode
            set_aside(edir, s["id"])
            print(f"{s['id']} was rewritten while it rendered: picture set aside in _discarded/, rendering the new shot", flush=True)
            continue
        patch(edir, s["id"], src=rel)
        print(f"done {rel} in {time.time() - t0:.0f}s", flush=True)
        rebuild()
    st = final_status(load(edir), edir)
    patch(edir, status=st)
    rebuild()
    print(f"episode {edir.name}: {st}" + (" (stopped by the explore timer; press Continue and run again)" if stopped else ""), flush=True)


if __name__ == "__main__":
    main()
