"""Evolve/cross set from the pin tray: one new lineage per variant (v01 only).
usage: new_set.py <spec.json> [--render] [--dry-run]
spec: {"parents":[png..], "why", "tags":[..], "cast":{"id"?, "entries":[..]} | "subjects":[keys],
       "aspect_ratio"?, "variants":[{slug,title,change:"LABEL: goal",prompt,aspect_ratio?}]}"""
import sys, json, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import labkit
from config import VENV_PYTHON


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    render, dry = "--render" in argv, "--dry-run" in argv
    if len(args) != 1:
        sys.exit(__doc__)
    spec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    R = labkit.ROOT
    parents = spec.get("parents") or []
    if not parents:
        sys.exit("spec needs parents")
    for p in parents:
        if not (R / p).exists():
            sys.exit(f"parent not found: {p}")
    if not spec.get("variants"):
        sys.exit("spec needs variants")
    for v in spec["variants"]:
        for k in ("slug", "title", "change", "prompt"):
            if not v.get(k):
                sys.exit(f"variant missing {k}")
        if "{subject}" not in v["prompt"]:
            sys.exit(f"variant {v['slug']}: prompt must contain {{subject}}")
    tags = list(spec.get("tags") or [])
    cast = spec.get("cast")
    if cast:
        cid = cast.get("id") or labkit.next_cast_id()
        subjects = labkit.preview_keys(cid, cast["entries"]) if dry else labkit.add_cast(cid, cast["entries"])
        tags.append(f"cast:{cid}")
    elif spec.get("subjects"):
        subjects = spec["subjects"]
        miss = [s for s in subjects if s not in labkit.load_subjects()]
        if miss:
            sys.exit(f"unknown subjects: {miss}")
    else:
        sys.exit("spec needs cast or subjects")
    num = labkit.next_lineage_num()
    for v in spec["variants"]:  # check collisions before writing anything
        if (R / "evolutions" / f"{num:03d}-{v['slug']}").exists():
            sys.exit("lineage dir exists")
    made = []
    for v in spec["variants"]:
        d = R / "evolutions" / f"{num:03d}-{v['slug']}"
        change = v["change"]
        goal = change.split(": ", 1)[1] if ": " in change else change
        if not dry:
            (d / "v01").mkdir(parents=True)
            (d / "lineage.json").write_text(json.dumps(
                {"title": v["title"], "goal": goal, "parent": None, "parent_images": parents,
                 "round": 0, "tags": tags}, indent=2, ensure_ascii=False), encoding="utf-8")
            (d / "v01" / "prompt.txt").write_text(v["prompt"], encoding="utf-8")
            (d / "v01" / "params.json").write_text(json.dumps(
                {"seeds": [1001], "steps": 25, "cfg": 1,
                 "aspect_ratio": v.get("aspect_ratio") or spec.get("aspect_ratio") or "3:4 (Portrait Standard)",
                 "megapixels": 1, "model": "qwen_image_2.1_int8_convrot.safetensors",
                 "sampler": "euler", "scheduler": "simple", "subjects": subjects},
                indent=2, ensure_ascii=False), encoding="utf-8")
            (d / "v01" / "notes.json").write_text(json.dumps(
                {"change": change, "why": spec.get("why", ""), "verdict": ""}, indent=2, ensure_ascii=False), encoding="utf-8")
        made.append(d.relative_to(R).as_posix() + "/v01")
        num += 1
    print(("[dry-run] would create:\n" if dry else "created:\n") + "\n".join(made))
    print("subjects:", ", ".join(subjects))
    if render and not dry:
        sys.exit(subprocess.call([str(VENV_PYTHON), "-u", "tools/run_version.py", *made], cwd=R))


if __name__ == "__main__":
    main(sys.argv[1:])
