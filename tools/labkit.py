"""Shared mechanics for lab tools (numbering, cast writing). Creative text stays with the caller."""
import json, re, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # tests monkeypatch this


def _subjects_path():
    return ROOT / "subjects.json"


def load_subjects():
    return json.loads(_subjects_path().read_text(encoding="utf-8"))


def save_subjects(d):
    _subjects_path().write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def next_lineage_num():
    nums = [int(m.group(1)) for p in (ROOT / "evolutions").glob("*") if p.is_dir()
            for m in [re.match(r"(\d+)-", p.name)] if m]
    return 1 + max(nums, default=0)


def next_cast_id():
    d = load_subjects()
    nums = []
    for k, v in d.items():
        nums += [int(x) for x in re.findall(r"cast(\d+)", k)]
        if isinstance(v, dict) and isinstance(v.get("cast"), str):
            nums += [int(x) for x in re.findall(r"cast(\d+)", v["cast"])]
    return f"cast{1 + max(nums, default=0)}"


def next_version(lineage_dir):
    lineage_dir = Path(lineage_dir)
    nums = [int(m.group(1)) for p in lineage_dir.glob("v*") if p.is_dir()
            for m in [re.fullmatch(r"v(\d+)", p.name)] if m]
    return f"v{1 + max(nums, default=0):02d}"


def version_of(png):
    p = Path(png)
    if not p.is_absolute():
        p = ROOT / p
    p = p.resolve()
    v = p.parent
    lin = v.parent
    if not re.fullmatch(r"v\d+", v.name) or lin.parent.name != "evolutions":
        raise ValueError(f"not an evolutions/<lineage>/<vNN>/<name>.png path: {png}")
    return lin, v


def default_label(kind, d=None):
    """Most common existing label for this kind (keeps the convention, incl. the middle dot)."""
    d = d or load_subjects()
    c = collections.Counter(v["label"] for k, v in d.items()
                            if isinstance(v, dict) and v.get("label") and re.match(re.escape(kind) + r"(@|~|$)", k))
    if c:
        return c.most_common(1)[0][0]
    return kind


def preview_keys(cast_id, entries):
    """The keys add_cast would write (no file changes)."""
    n, keys = collections.Counter(), []
    for e in entries:
        n[e["kind"]] += 1
        keys.append(f"{e['kind']}@{cast_id}~{n[e['kind']]}")
    return keys


def add_cast(cast_id, entries):
    """entries: [{kind, text, label?}]. Keys `<kind>@<cast>~<n>` (n per kind from 1). Returns keys in order."""
    d = load_subjects()
    new, keys = {}, preview_keys(cast_id, entries)
    for e, key in zip(entries, keys):
        if not re.fullmatch(r"[a-z]-[a-z]+", e["kind"]):
            raise ValueError(f"bad kind {e['kind']!r}")
        if not e.get("text", "").strip():
            raise ValueError(f"empty text for {e['kind']}")
        if key in d:
            raise ValueError(f"subject key already exists: {key}")
        new[key] = {"label": e.get("label") or default_label(e["kind"], d), "text": e["text"], "cast": cast_id}
    d.update(new)
    save_subjects(d)
    return keys


def parent_subject(png):
    """Subject key of a rendered lab image ("<key>_seed<N>.png"), if it's a known subject; else None (old "seedN.png", scenes)."""
    stem = Path(png).stem
    key = stem.rsplit("_seed", 1)[0] if "_seed" in stem else None
    return key if key and key in load_subjects() else None
