"""Scan evolutions/ and write gallery/index.html (+ regenerate each lineage README.md).

Per lineage:  lineage.json  {title, goal, parent: "NNN-slug/vNN"|null, round, tags}
Per version:  prompt.txt, params.json, notes.json {change, why, verdict}, seed*.png
"""
import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVO = ROOT / "evolutions"
JRN = ROOT / "journeys"
MVD = ROOT / "musicvideos"
OUT = ROOT / "gallery" / "index.html"
SUBJECTS = json.loads((ROOT / "subjects.json").read_text(encoding="utf-8"))


def read_json(p, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def collect():
    lineages = []
    for d in sorted(p for p in EVO.iterdir() if p.is_dir()):
        meta = read_json(d / "lineage.json", {})
        versions = []
        for v in sorted(p for p in d.iterdir() if p.is_dir() and p.name.startswith("v")):
            prompt = (v / "prompt.txt").read_text(encoding="utf-8").strip() if (v / "prompt.txt").exists() else ""
            params = read_json(v / "params.json", {})
            seeds = params.get("seeds", [])
            # expected outputs, in display order; rendered ones get a src
            if "{subject}" in prompt:
                expected = [(f"{k}_seed{sd}", f"{SUBJECTS[k]['label']} · {sd}", k)
                            for k in params.get("subjects", list(SUBJECTS)) for sd in seeds]
            else:
                # pre-template versions all used the female-modern subject
                expected = [(f"seed{sd}", f"{SUBJECTS['f-modern']['label']} · {sd}", "f-modern") for sd in seeds]
            names = {e[0] for e in expected}
            expected += [(p.stem, p.stem, "") for p in sorted(v.glob("*.png")) if p.stem not in names]
            slots = [{"name": n, "key": f"{subj}_seed{n.rsplit('seed', 1)[-1]}" if subj else n, "label": lab, "subject": subj,
                      "src": f"../evolutions/{d.name}/{v.name}/{n}.png" if (v / f"{n}.png").exists() else None,
                      "ts": int((v / f"{n}.png").stat().st_mtime) if (v / f"{n}.png").exists() else 0}
                     for n, lab, subj in expected]
            versions.append({
                "id": v.name, "prompt": prompt, "params": params,
                "notes": read_json(v / "notes.json", {}),
                "slots": slots,
                "images": [{"src": x["src"], "name": x["label"]} for x in slots if x["src"]],
            })
        lineages.append({"id": d.name, "title": meta.get("title", d.name), "goal": meta.get("goal", ""),
                         "parent": meta.get("parent"),
                         # evolution parents: list (a crossbreed has 2+); legacy single parent_image still read
                         "parent_images": meta.get("parent_images") or ([meta["parent_image"]] if meta.get("parent_image") else []),
                         "round": meta.get("round", 0), "tags": meta.get("tags", []), "versions": versions,
                         # epoch seconds: when the style was created, and when its newest image finished
                         "created": int((d / "lineage.json").stat().st_ctime) if (d / "lineage.json").exists() else 0,
                         "rendered": int(max((p.stat().st_mtime for p in d.glob("v*/*.png")), default=0))})
    # evolution layer: survey lineages are 0; an evolution set sits one layer below its deepest parent image
    by_id = {l["id"]: l for l in lineages}

    def depth(l, seen=()):
        if not l["parent_images"] or l["id"] in seen:
            return 0
        parents = [by_id.get(p.split("/")[1]) for p in l["parent_images"]]
        return 1 + max((depth(p, seen + (l["id"],)) for p in parents if p), default=0)
    for l in lineages:
        l["depth"] = depth(l)
    return lineages


def collect_journeys():
    """journeys/NNN-slug/journey.json + chNN/chapter.json (see tools/run_journey.py): one character exploring their world"""
    out = []
    for d in sorted(p for p in JRN.iterdir() if p.is_dir() and (p / "journey.json").exists()) if JRN.exists() else []:
        j = read_json(d / "journey.json", {})
        chapters = []
        for c in sorted(p for p in d.iterdir() if p.is_dir() and p.name.startswith("ch") and (p / "chapter.json").exists()):
            ch = read_json(c / "chapter.json", {})
            # dialogue: [{who, text, pos: [x%, y%] bubble top-left, tail: bl|br|b|tl|tr|none, radio?}] -> speech bubbles
            scenes = [{"id": sc["id"], "shot": sc.get("shot", ""), "caption": sc.get("caption", ""), "prompt": sc.get("prompt", ""),
                       "dialogue": sc.get("dialogue", []),
                       "src": f"../journeys/{d.name}/{c.name}/{sc['id']}.png" if (c / f"{sc['id']}.png").exists() else None,
                       "ts": int((c / f"{sc['id']}.png").stat().st_mtime) if (c / f"{sc['id']}.png").exists() else 0}
                      for sc in ch.get("scenes", [])]
            chapters.append({"id": c.name, "title": ch.get("title", c.name), "direction": ch.get("direction"),
                             "summary": ch.get("summary", ""), "choices": ch.get("choices", []), "scenes": scenes})
        out.append({"id": d.name, "title": j.get("title", d.name), "name": j.get("name", ""), "source": j.get("source", ""),
                    "source_cap": j.get("source_cap", ""), "character": j.get("character", ""), "world": j.get("world", ""),
                    "refs": j.get("refs") or [j.get("source", "")], "ref_crop": j.get("ref_crop", {}),
                    "ref_notes": j.get("ref_notes", {}), "ref_for": j.get("ref_for", {}), "style": j.get("style", ""), "chapters": chapters,
                    # cast: [{name, look, ref (library cameo portrait), from}]
                    "cast": [{"name": n, **(v if isinstance(v, dict) else {"look": v})} for n, v in j.get("cast", {}).items()],
                    "created": int((d / "journey.json").stat().st_ctime),
                    "rendered": int(max((p.stat().st_mtime for p in d.glob("ch*/s*.png")), default=0))})
    return out


def mv_lyrics_timing(d):
    t = read_json(d / "audio" / "lyrics_timing.json", None)
    if not t:
        return None
    return {"model": t.get("model"), "source": t.get("source"), "lines": [{k: ln[k] for k in ("i", "text", "t0", "t1", "conf", "spread") if k in ln} for ln in t.get("lines", [])]}


def mv_cut(d):
    """🎞 the latest final cut (musicvideos/<id>/cut/*.mp4 by mtime) + its resolved timeline (.json), the build status (_status.json; a running /
    queued build older than 2 h is shown as stale) and the edit list's rows (edit.json) for the page"""
    cd = d / "cut"
    mp4s = sorted(cd.glob("*.mp4"), key=lambda p: p.stat().st_mtime) if cd.is_dir() else []
    st = read_json(cd / "_status.json", None)
    if st and st.get("state") in ("queued", "running") and time.time() - st.get("ts", 0) > 7200:
        st["state"] = "stale"
    ed = read_json(d / "edit.json", None)
    if not (mp4s or st or ed):
        return None
    def target(q, j):  # draft | youtube | suno (older builds have no "target": draft flag / file name decide)
        if j.get("target"):
            return j["target"]
        return "draft" if j.get("draft", "draft" in q.stem) else "suno" if q.stem.endswith("-suno") else "youtube"
    cut = None
    if mp4s:
        p = mp4s[-1]
        j = read_json(p.with_suffix(".json"), {}) or {}
        strip = p.with_name(p.stem + "_strip.jpg")
        cut = {"src": f"../musicvideos/{d.name}/cut/{p.name}", "mtime": int(p.stat().st_mtime), "draft": bool(j.get("draft", "draft" in p.stem)), "target": target(p, j),
               "duration": j.get("duration"), "w": j.get("w"), "h": j.get("h"), "counts": j.get("counts", {}), "build_seconds": j.get("build_seconds"),
               "strip": f"../musicvideos/{d.name}/cut/{strip.name}" if strip.exists() else None, "cuts": j.get("cuts", []), "all": []}
        for q in reversed(mp4s):
            qj = read_json(q.with_suffix(".json"), {}) or {}
            cut["all"].append({"src": f"../musicvideos/{d.name}/cut/{q.name}", "mtime": int(q.stat().st_mtime), "mb": round(q.stat().st_size / 1e6),
                               "draft": bool(qj.get("draft", "draft" in q.stem)), "target": target(q, qj), "w": qj.get("w"), "h": qj.get("h")})
    hj = read_json(d / "export" / "hooks" / "auto" / "hooks.json", None)  # 🪝 Build for Hooks (tools/mv_hooks.auto_hooks)
    hooks = [{**h, "src": f"../musicvideos/{d.name}/export/hooks/auto/{h['file']}"} for h in (hj or {}).get("hooks", [])
             if (d / "export" / "hooks" / "auto" / h["file"]).exists()]
    if not (mp4s or st or ed or hooks):
        return None
    return {"latest": cut, "status": st, "hooks": hooks, "hooks_from": (hj or {}).get("from"),
            "edit": [{k: c.get(k) for k in ("frame", "t0", "t1", "clip", "look", "in", "fx", "why")} for c in (ed or {}).get("cuts", [])]}


def collect_atlas(root=None, kind="formality"):
    """the Formality / Emotion Atlas (explore/formality_atlas.json, explore/emotion_atlas.json) rides in the payload so the deck can draw it before any fetch"""
    p = Path(root or ROOT) / "explore" / ("emotion_atlas.json" if kind == "emotion" else "formality_atlas.json")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def collect_maturity():
    """the maturity dial's 7 stops + the hard ceiling text (tools/maturity.py is the single source; the deck reads this)"""
    try:
        import maturity
    except ImportError:  # the Nev Novel tools are optional
        return None
    return {"stops": maturity.table(), "ceiling": maturity.CEILING, "default": maturity.DEFAULT_STOP}


def collect_explore(root=None):
    """🌌 Explore episodes (explore/NNN-slug/episode.json written by Claude, shots rendered by tools/explore_render.py), newest first.
    Shots are stills only: src = ../explore/<id>/<shot>.png once rendered (else null), mtime for cache-busting after a 🎲 reroll."""
    root = Path(root or ROOT)
    out = []
    for f in sorted((root / "explore").glob("*/episode.json"), reverse=True) if (root / "explore").exists() else []:
        e = read_json(f, None)
        if not isinstance(e, dict):
            continue
        shots = []
        for i, sh in enumerate(e.get("shots") or [], 1):
            sid = sh.get("id") or f"e{i}"
            png = f.parent / f"{sid}.png"
            ok = png.is_file()
            shots.append({"id": sid, "prompt": sh.get("prompt", ""), "caption": sh.get("caption", ""), "aspect": sh.get("aspect") or "16:9",
                          "hold": sh.get("hold") or 6, "src": f"../explore/{f.parent.name}/{sid}.png" if ok else None,
                          "mtime": int(png.stat().st_mtime) if ok else 0})
        out.append({"id": f.parent.name, "title": e.get("title") or f.parent.name, "topic": e.get("topic", ""), "premise": e.get("premise", ""),
                    "style": e.get("style", ""), "presence": e.get("presence"), "emotion": e.get("emotion"), "formality": e.get("formality"), "cores": e.get("cores"), "maturity": e.get("maturity"), "created": e.get("created", ""), "status": e.get("status", "draft"), "shots": shots,
                    "cover": next((x["src"] for x in shots if x["src"]), None)})
    return out


def collect_sagas(root=None):
    """📖 Sagas (explore/sagas/NNN-slug/saga.json = the bible, chNN/episode.json = a chapter of Explore shots with narration + dialogue), newest first.
    Cast refs / shot pictures are ../explore/sagas/... paths with mtimes for cache-busting after a 🎲 reroll."""
    root = Path(root or ROOT)
    base = root / "explore" / "sagas"
    out = []
    for d in sorted((p for p in base.iterdir() if p.is_dir() and (p / "saga.json").is_file()), reverse=True) if base.is_dir() else []:
        b = read_json(d / "saga.json", None)
        if not isinstance(b, dict):
            continue
        chapters = []
        for cd in sorted(p for p in d.glob("ch[0-9][0-9]*") if (p / "episode.json").is_file()):
            e = read_json(cd / "episode.json", None)
            if not isinstance(e, dict):
                continue
            shots = []
            for i, sh in enumerate(e.get("shots") or [], 1):
                sid = sh.get("id") or f"e{i}"
                png = cd / f"{sid}.png"
                ok = png.is_file()
                shots.append({"id": sid, "prompt": sh.get("prompt", ""), "caption": sh.get("caption", ""), "aspect": sh.get("aspect") or "16:9", "hold": sh.get("hold") or 6,
                              "with": sh.get("with") or [], "place": sh.get("place") or "", "narration": sh.get("narration") or "", "dialogue": sh.get("dialogue") or [],
                              "src": f"../explore/sagas/{d.name}/{cd.name}/{sid}.png" if ok else None, "mtime": int(png.stat().st_mtime) if ok else 0})
            chapters.append({"id": cd.name, "num": int(re.sub(r"\D", "", cd.name) or 0), "title": e.get("title") or cd.name, "summary": e.get("summary") or e.get("premise") or "",
                             "status": e.get("status", "draft"), "created": e.get("created", ""), "opens": e.get("opens") or [], "closes": e.get("closes") or [],
                             "presence": e.get("presence"), "emotion": e.get("emotion"), "formality": e.get("formality"), "cores": e.get("cores"),
                             "maturity": e.get("maturity"), "shots": shots})
        cast = []
        for n, v in (b.get("cast") or {}).items():
            v = v if isinstance(v, dict) else {"look": v}
            ref = v.get("ref")
            ok = bool(ref) and (root / ref).is_file()
            cast.append({"name": n, "look": v.get("look", ""), "role": v.get("role", ""), "voice": v.get("voice", ""), "status": v.get("status", ""), "first_chapter": v.get("first_chapter"),
                         "ref": f"../{ref}" if ok else None, "ref_crop": v.get("ref_crop"), "mtime": int((root / ref).stat().st_mtime) if ok else 0, "color": v.get("color")})
        covers = [sh["src"] for c in chapters for sh in c["shots"] if sh["src"]]
        out.append({"id": d.name, "title": b.get("title") or d.name, "logline": b.get("logline", ""), "created": b.get("created", ""), "style": b.get("style", ""),
                    "world": b.get("world") or {}, "lore": b.get("lore") or [], "factions": b.get("factions") or [], "places": b.get("places") or [], "cast": cast,
                    "timeline": b.get("timeline") or [], "threads": b.get("threads") or [], "chapters": chapters, "cover": covers[-1] if covers else None,
                    "cores": b.get("cores") or [], "maturity": b.get("maturity")})
    return out


def collect_mvs():
    """musicvideos/NNN-slug/mv.json + audio/analysis.json + sbNN/chapter.json (storyboards; journey chapter schema + t0/t1/lyric
    per scene): 🎵 music videos, newest first"""
    out = []
    for d in sorted((p for p in MVD.iterdir() if p.is_dir() and (p / "mv.json").exists()), reverse=True) if MVD.exists() else []:
        m = read_json(d / "mv.json", {})
        boards = []
        for c in sorted(p for p in d.iterdir() if p.is_dir() and p.name.startswith("sb") and (p / "chapter.json").exists()):
            ch = read_json(c / "chapter.json", {})
            scenes = [{**{k: sc.get(k) for k in ("shot", "camera", "caption", "prompt", "with", "place", "t0", "t1", "lyric", "headline", "headline_tag") if sc.get(k) is not None},
                       "id": sc["id"], "dialogue": sc.get("dialogue", []),
                       "src": f"../musicvideos/{d.name}/{c.name}/{sc['id']}.png" if (c / f"{sc['id']}.png").exists() else None,
                       "ts": int((c / f"{sc['id']}.png").stat().st_mtime) if (c / f"{sc['id']}.png").exists() else 0}
                      for sc in ch.get("scenes", [])]
            boards.append({"id": c.name, "title": ch.get("title", c.name), "direction": ch.get("direction"),
                           "summary": ch.get("summary", ""), "choices": ch.get("choices", []), "scenes": scenes})
        out.append({**m, "id": d.name, "title": m.get("title", d.name), "refs": m.get("refs") or [],
                    # cast: [{name, look, ...}] like journeys (the page lists them in the "Use for" select)
                    "cast": [{"name": n, **(v if isinstance(v, dict) else {"look": v})} for n, v in (m.get("cast") or {}).items()],
                    "analysis": read_json(d / "audio" / "analysis.json", None),
                    "analysis_error": (d / "audio" / "analysis_error.txt").read_text(encoding="utf-8") if (d / "audio" / "analysis_error.txt").exists() else "", "storyboards": boards,
                    # 🎚 stems: audio/stems.json from tools/mv_stems.py (lanes are 0-99 ints; segments/moments/beats in song seconds)
                    "stems_data": read_json(d / "audio" / "stems.json", None),
                    "stems_error": (d / "audio" / "stems_error.txt").read_text(encoding="utf-8") if (d / "audio" / "stems_error.txt").exists() else "",
                    # 🎤 lyric timing (tools/mv_lyrics.py): the lines only (t0/t1/conf/spread), not the word list
                    "lyrics_timing": mv_lyrics_timing(d),
                    "lyrics_error": (d / "audio" / "lyrics_error.txt").read_text(encoding="utf-8") if (d / "audio" / "lyrics_error.txt").exists() else "",
                    "lyrics_pending": (d / "audio" / "lyrics_pending").exists() and time.time() - (d / "audio" / "lyrics_pending").stat().st_mtime < 600,
                    "final_cut": mv_cut(d),
                    "created_ts": int((d / "mv.json").stat().st_ctime),
                    "rendered": int(max((p.stat().st_mtime for p in d.glob("sb*/s*.png")), default=0))})
    return out


REV_STAMP = __import__("re").compile(r"^(.+)__(\d{8})-(\d{6})\.png$")


def collect_revs(root=None):
    """🕘 past revisions: every 🎲/✎/✏/reshoot moves the replaced picture to
    <dir>/_rerolled/<stem>__YYYYMMDD-HHMMSS.png. Returns {current image key: [{src, ts}] newest first} for images that still exist."""
    root = Path(root or ROOT)
    out = {}
    for top in ("evolutions", "journeys", "musicvideos"):
        for p in (root / top).glob("*/*/_rerolled/*.png"):
            m = REV_STAMP.match(p.name)
            if not m:
                continue
            cur = p.parent.parent / (m.group(1) + ".png")
            if not cur.is_file():
                continue
            d, t = m.group(2), m.group(3)
            out.setdefault(cur.relative_to(root).as_posix(), []).append(
                {"src": "../" + p.relative_to(root).as_posix(), "ts": f"{d[:4]}-{d[4:6]}-{d[6:]} {t[:2]}:{t[2:4]}:{t[4:]}"})
    for v in out.values():
        v.sort(key=lambda r: r["ts"], reverse=True)
    return out


def collect_videos(lineages):
    """clips saved next to their source image: evolutions/<lin>/<vNN>/<image>__<engine>_seed<N>.mp4 (+ .json);
    journey scenes too: journeys/<journey>/<chNN>/<sN>__<engine>_seed<N>.mp4; music-video frames: musicvideos/<id>/<sbNN>/<sN>__..."""
    by_id = {l["id"]: l for l in lineages}
    vids = []
    for mp4 in sorted(EVO.glob("*/v*/*__*.mp4")) + (sorted(JRN.glob("*/ch*/*__*.mp4")) if JRN.exists() else [])             + (sorted(MVD.glob("*/sb*/*__*.mp4")) if MVD.exists() else []):
        lin, ver = mp4.parent.parent.name, mp4.parent.name
        top = mp4.parent.parent.parent.name  # evolutions | journeys | musicvideos
        img_stem = mp4.stem.split("__")[0]
        meta = read_json(mp4.with_suffix(".json"), {})
        subj_key = img_stem.split("_seed")[0] if "_seed" in img_stem and not img_stem.startswith("seed") else "f-modern"
        l = by_id.get(lin, {})
        mvt = read_json(MVD / lin / "mv.json", {}).get("title", lin) if top == "musicvideos" else None
        vids.append({
            "src": f"../{top}/{lin}/{ver}/{mp4.name}", "poster": f"../{top}/{lin}/{ver}/{img_stem}.png",
            "image": f"{top}/{lin}/{ver}/{img_stem}.png", "lineage": lin, "version": ver, "title": mvt or l.get("title", lin),
            "journey": top == "journeys", "mv": lin if top == "musicvideos" else False,
            "depth": l.get("depth", 0), "subject": subj_key, "subject_label": SUBJECTS.get(subj_key, {}).get("label", subj_key),
            "engine": meta.get("engine", mp4.stem.split("__")[-1].split("_seed")[0]), "tag": meta.get("tag", ""), "prompt": meta.get("prompt", ""),
            "note": meta.get("note", ""), "seconds": meta.get("seconds"), "render_seconds": meta.get("render_seconds"),
            **{k: meta[k] for k in ("song_audio", "lead_in_trimmed", "reversed", "frame") if meta.get(k)},  # 📝 clip prompt panel
            "created": int(mp4.stat().st_mtime),
        })
    # 📖 Nev Novel shots the user 🎬-marked: explore/<ep>/eN__*.mp4 and saga chapters explore/sagas/<saga>/chNN/eN__*.mp4
    xd = ROOT / "explore"
    for mp4 in (sorted(xd.glob("*/e*__*.mp4")) + sorted(xd.glob("sagas/*/ch*/e*__*.mp4"))) if xd.exists() else []:
        epdir = mp4.parent
        img_stem = mp4.stem.split("__")[0]
        meta = read_json(mp4.with_suffix(".json"), {})
        ep = read_json(epdir / "episode.json", {}) or {}
        rel_dir = epdir.relative_to(ROOT).as_posix()
        saga = epdir.parent.name if epdir.parent.parent.name == "sagas" else None
        title = ep.get("title", epdir.name)
        if saga:
            title = f"{(read_json(epdir.parent / 'saga.json', {}) or {}).get('title', saga)} · {epdir.name}: {title}"
        vids.append({
            "src": f"../{rel_dir}/{mp4.name}", "poster": f"../{rel_dir}/{img_stem}.png", "image": f"{rel_dir}/{img_stem}.png",
            "lineage": f"nev:{saga or epdir.name}", "version": epdir.name if saga else "", "title": "📖 " + title,
            "journey": False, "mv": False, "depth": 0, "subject": img_stem, "subject_label": img_stem,
            "engine": meta.get("engine", mp4.stem.split("__")[-1].split("_seed")[0]), "tag": meta.get("tag", ""), "prompt": meta.get("prompt", ""),
            "note": meta.get("note", ""), "seconds": meta.get("seconds"), "render_seconds": meta.get("render_seconds"),
            "created": int(mp4.stat().st_mtime),
        })
    return vids


def write_readme(lin):
    d = EVO / lin["id"]
    lines = [f"# {lin['id']} — {lin['title']}", "", lin["goal"], ""]
    if lin["parent"]:
        lines += [f"Branched from [`{lin['parent']}`](../{lin['parent']}/).", ""]
    lines += ["| version | what changed | why | verdict |", "|---|---|---|---|"]
    for v in lin["versions"]:
        n = v["notes"]
        cells = [f"[{v['id']}]({v['id']}/)", n.get("change", ""), n.get("why", ""), n.get("verdict", "")]
        lines.append("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    (d / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    # re-read every build: casts get added to subjects.json while long render jobs are running
    global SUBJECTS
    SUBJECTS = json.loads((ROOT / "subjects.json").read_text(encoding="utf-8"))
    lineages = collect()
    for lin in lineages:
        write_readme(lin)
    tpl = (Path(__file__).parent / "gallery_template.html").read_text(encoding="utf-8")
    import hashlib
    ui = hashlib.sha1(tpl.encode("utf-8")).hexdigest()[:12]  # page reloads itself when this changes
    videos = collect_videos(lineages)
    payload = {"ui": ui, "lineages": lineages, "videos": videos, "journeys": collect_journeys(), "mvs": collect_mvs(), "explore": collect_explore(), "sagas": collect_sagas(), "atlas": collect_atlas(), "emotion_atlas": collect_atlas(kind="emotion"), "maturity": collect_maturity(),
               "subjects": {k: v["label"] for k, v in SUBJECTS.items()},
               "subject_text": {k: v["text"] for k, v in SUBJECTS.items()},  # full character text, for search
               # image mtimes: the page adds ?v=<mtime> to image URLs so a 🎲 reroll (same file name) shows the new picture
               # instead of the browser's cached one 
               # ⤢ upscaled versions: {original image key: mtime of its _upscaled/ 2048 copy}
               # ⬚ refits: {original image key: [{src, ratio, mtime}]} from <dir>/_resized/<name>__<w>x<h>.png
               "resized": (lambda fs: {k: sorted(v, key=lambda x: x["ratio"]) for k, v in fs.items()})(
                   __import__("functools").reduce(lambda acc, p: (acc.setdefault(
                       (p.parent.parent / (p.stem.rsplit("__", 1)[0] + ".png")).relative_to(ROOT).as_posix(), []).append(
                       {"src": "../" + p.relative_to(ROOT).as_posix(), "ratio": p.stem.rsplit("__", 1)[1].replace("x", ":"),
                        "mtime": int(p.stat().st_mtime)}), acc)[1],
                       [p for top in ("evolutions", "journeys", "musicvideos") for p in (ROOT / top).glob("*/*/_resized/*__*.png")], {})),
               "upscaled": {(p.parent.parent / p.name).relative_to(ROOT).as_posix(): int(p.stat().st_mtime)
                            for top in ("evolutions", "journeys", "musicvideos") for p in (ROOT / top).glob("*/*/_upscaled/*.png")},
               "revs": collect_revs(),  # 🕘 {image key: [{src: ../…/_rerolled/…png, ts}]} newest first
               "mtimes": {**{p.relative_to(ROOT).as_posix(): int(p.stat().st_mtime)
                             for top in ("evolutions", "journeys", "musicvideos") for p in (ROOT / top).glob("*/*/*.png")},
                          **{p.relative_to(ROOT).as_posix(): int(p.stat().st_mtime) for p in (ROOT / "explore").glob("*/*.png")},
                          **{p.relative_to(ROOT).as_posix(): int(p.stat().st_mtime) for p in (ROOT / "explore").glob("sagas/*/*/*.png")}}}
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(tpl.replace("/*__DATA__*/{}", data), encoding="utf-8")
    tmp = OUT.parent / "data.json.tmp"  # atomic swap so the page never polls a half-written file
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(OUT.parent / "data.json")
    n_img = sum(len(v["images"]) for l in lineages for v in l["versions"])
    print(f"wrote {OUT.relative_to(ROOT)}: {len(lineages)} lineages, {n_img} images")


if __name__ == "__main__":
    main()
