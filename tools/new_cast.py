"""More-characters flow: new version in the marked image's lineage with a new cast.
usage: new_cast.py <marked png> <spec.json> [--render] [--dry-run]
spec: {"entries":[{kind,text,label?}], "change","why","prompt_edit":["old","new"]?, "cast":"castN"?}"""
import sys, json, subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import labkit
from config import VENV_PYTHON


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    render, dry = "--render" in argv, "--dry-run" in argv
    if len(args) != 2:
        sys.exit(__doc__)
    png, spec = args[0], json.loads(Path(args[1]).read_text(encoding="utf-8"))
    R = labkit.ROOT
    lin, vdir = labkit.version_of(png)
    if not (vdir / "prompt.txt").exists():
        sys.exit(f"no prompt.txt in {vdir}")
    prompt = (vdir / "prompt.txt").read_text(encoding="utf-8")
    if spec.get("prompt_edit"):
        old, new = spec["prompt_edit"]
        if old not in prompt:
            sys.exit(f"prompt_edit: {old!r} not found in {vdir.name}/prompt.txt")
        prompt = prompt.replace(old, new)
    for k in ("entries", "change", "why"):
        if not spec.get(k):
            sys.exit(f"spec missing {k}")
    cast = spec.get("cast") or labkit.next_cast_id()
    newdir = lin / labkit.next_version(lin)
    params = json.loads((vdir / "params.json").read_text(encoding="utf-8"))
    for k in ("rerolls", "fixes"):
        params.pop(k, None)
    params["seeds"] = [1001]
    if dry:
        keys = labkit.preview_keys(cast, spec["entries"])
        print(f"[dry-run] would create {newdir.relative_to(R).as_posix()} from {vdir.name} (cast {cast})")
    else:
        keys = labkit.add_cast(cast, spec["entries"])
        newdir.mkdir()
        (newdir / "prompt.txt").write_text(prompt, encoding="utf-8")
        params["subjects"] = keys
        (newdir / "params.json").write_text(json.dumps(params, indent=2, ensure_ascii=False), encoding="utf-8")
        (newdir / "notes.json").write_text(json.dumps(
            {"change": spec["change"], "why": spec["why"], "verdict": ""}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(newdir.relative_to(R).as_posix())
    print("\n".join(keys))
    if render and not dry:
        sys.exit(subprocess.call([str(VENV_PYTHON), "-u", "tools/run_version.py",
                                  newdir.relative_to(R).as_posix()], cwd=R))


if __name__ == "__main__":
    main(sys.argv[1:])
