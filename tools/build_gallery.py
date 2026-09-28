"""Scan evolutions/ and write gallery/index.html (+ regenerate each lineage README.md).

Per lineage:  lineage.json  {title, goal, parent: "NNN-slug/vNN"|null, round, tags}
Per version:  prompt.txt, params.json, notes.json {change, why, verdict}, seed*.png
"""
import json
import pathlib
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVO = ROOT / "evolutions"
JRN = ROOT / "journeys"
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
                    "refs": j.get("refs") or [j.get("source", "")], "style": j.get("style", ""), "chapters": chapters,
                    # cast: [{name, look, ref (library cameo portrait), from}]
                    "cast": [{"name": n, **(v if isinstance(v, dict) else {"look": v})} for n, v in j.get("cast", {}).items()],
                    "created": int((d / "journey.json").stat().st_ctime),
                    "rendered": int(max((p.stat().st_mtime for p in d.glob("ch*/s*.png")), default=0))})
    return out


def collect_videos(lineages):
    """clips saved next to their source image: evolutions/<lin>/<vNN>/<image>__<engine>_seed<N>.mp4 (+ .json);
    journey scenes too: journeys/<journey>/<chNN>/<sN>__<engine>_seed<N>.mp4"""
    by_id = {l["id"]: l for l in lineages}
    vids = []
    for mp4 in sorted(EVO.glob("*/v*/*__*.mp4")) + (sorted(JRN.glob("*/ch*/*__*.mp4")) if JRN.exists() else []):
        lin, ver = mp4.parent.parent.name, mp4.parent.name
        top = mp4.parent.parent.parent.name  # evolutions | journeys
        img_stem = mp4.stem.split("__")[0]
        meta = read_json(mp4.with_suffix(".json"), {})
        subj_key = img_stem.split("_seed")[0] if "_seed" in img_stem and not img_stem.startswith("seed") else "f-modern"
        l = by_id.get(lin, {})
        vids.append({
            "src": f"../{top}/{lin}/{ver}/{mp4.name}", "poster": f"../{top}/{lin}/{ver}/{img_stem}.png",
            "image": f"{top}/{lin}/{ver}/{img_stem}.png", "lineage": lin, "version": ver, "title": l.get("title", lin),
            "journey": top == "journeys",
            "depth": l.get("depth", 0), "subject": subj_key, "subject_label": SUBJECTS.get(subj_key, {}).get("label", subj_key),
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
    payload = {"ui": ui, "lineages": lineages, "videos": videos, "journeys": collect_journeys(),
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
                       [p for top in ("evolutions", "journeys") for p in (ROOT / top).glob("*/*/_resized/*__*.png")], {})),
               "upscaled": {(p.parent.parent / p.name).relative_to(ROOT).as_posix(): int(p.stat().st_mtime)
                            for top in ("evolutions", "journeys") for p in (ROOT / top).glob("*/*/_upscaled/*.png")},
               "mtimes": {p.relative_to(ROOT).as_posix(): int(p.stat().st_mtime)
                          for top in ("evolutions", "journeys") for p in (ROOT / top).glob("*/*/*.png")}}
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
