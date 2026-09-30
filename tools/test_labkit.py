"""Throwaway tests for labkit/new_cast/new_set (no ComfyUI): .venv/Scripts/python tools/test_labkit.py"""
import sys, json, tempfile, io, contextlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import labkit, new_cast, new_set

n_pass = 0


def check(cond, msg):
    global n_pass
    if not cond:
        print("FAIL", msg)
        sys.exit(1)
    n_pass += 1
    print("PASS", msg)


def expect_exit(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            fn(*a)
        except SystemExit as e:
            return e.code
    return None


def w(p, o):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(o) if not isinstance(o, str) else o, encoding="utf-8")


tmp = Path(tempfile.mkdtemp())
labkit.ROOT = tmp
w(tmp / "subjects.json", {
    "f-fantasy": {"label": "Female · D&D fantasy", "text": "x"},
    "f-fantasy@cast112~1": {"label": "Female · D&D fantasy", "text": "x", "cast": "cast112"},
    "f-fantasy~1@cast118": {"label": "Female · D&D fantasy", "text": "x", "cast": "cast118"},
    "b-bands~3@cast117": {"label": "Band · musicians", "text": "x", "cast": "cast117"},
})
lin = tmp / "evolutions" / "005-foo"
w(lin / "v01" / "prompt.txt", "style A {subject} end")
w(lin / "v01" / "params.json", {"seeds": [1, 2], "steps": 25, "subjects": ["a"], "rerolls": [1], "fixes": [2], "aspect_ratio": "1:1"})
w(lin / "v02" / "prompt.txt", "style B {subject}")
w(lin / "v02" / "params.json", {"seeds": [1]})
png = lin / "v01" / "img.png"
png.write_bytes(b"x")
(tmp / "evolutions" / "007-bar").mkdir()

check(labkit.next_lineage_num() == 8, "next_lineage_num")
check(labkit.next_cast_id() == "cast119", "next_cast_id counts malformed keys")
check(labkit.next_version(lin) == "v03", "next_version")
check(labkit.version_of(png) == (lin.resolve(), (lin / "v01").resolve()), "version_of")
keys = labkit.add_cast("cast119", [{"kind": "f-fantasy", "text": "a"}, {"kind": "m-modern", "text": "b", "label": "Custom"},
                                   {"kind": "f-fantasy", "text": "c"}])
check(keys == ["f-fantasy@cast119~1", "m-modern@cast119~1", "f-fantasy@cast119~2"], "key format, per-kind counter")
d = labkit.load_subjects()
check(d[keys[0]]["label"] == "Female · D&D fantasy" and d[keys[1]]["label"] == "Custom", "labels")
check(labkit.next_cast_id() == "cast120", "next_cast_id after add")
before = (tmp / "subjects.json").read_text(encoding="utf-8")
try:
    labkit.add_cast("cast119", [{"kind": "f-fantasy", "text": "z"}])
    check(False, "overwrite refused")
except ValueError:
    check((tmp / "subjects.json").read_text(encoding="utf-8") == before, "overwrite refused, file untouched")

# new_cast
spec = tmp / "spec.json"
base = {"entries": [{"kind": "f-fantasy", "text": "q"}, {"kind": "m-fantasy", "text": "r"}], "change": "CHARACTERS: t", "why": "w"}
w(spec, {**base, "prompt_edit": ["nope", "x"]})
check(expect_exit(new_cast.main, [str(png), str(spec)]) not in (None, 0), "prompt_edit missing -> error")
check(not (lin / "v03").exists(), "no version dir after failed edit")
w(spec, base)
expect_exit(new_cast.main, [str(png), str(spec), "--dry-run"])
check(not (lin / "v03").exists() and labkit.next_cast_id() == "cast120", "new_cast dry-run writes nothing")
w(spec, {**base, "prompt_edit": ["style A", "style Z"]})
expect_exit(new_cast.main, [str(png), str(spec)])
p = json.loads((lin / "v03" / "params.json").read_text(encoding="utf-8"))
check((lin / "v03" / "prompt.txt").read_text(encoding="utf-8") == "style Z {subject} end", "prompt copied from MARKED version + edit")
check(p["seeds"] == [1001] and "rerolls" not in p and "fixes" not in p and p["aspect_ratio"] == "1:1", "params from marked version, cleaned")
check(p["subjects"] == ["f-fantasy@cast120~1", "m-fantasy@cast120~1"], "params.subjects = new keys")
check(json.loads((lin / "v03" / "notes.json").read_text(encoding="utf-8")) == {"change": "CHARACTERS: t", "why": "w", "verdict": ""}, "notes.json")

# new_set
par = "evolutions/005-foo/v01/img.png"
sspec = {"parents": [par], "why": "w", "tags": ["evolution"], "cast": {"entries": [{"kind": "f-fantasy", "text": "a"}]},
         "variants": [{"slug": "aa", "title": "A", "change": "AMPLIFY: go big: yes", "prompt": "p {subject}"},
                      {"slug": "bb", "title": "B", "change": "TWIST: other", "prompt": "q {subject}", "aspect_ratio": "16:9"}]}
sp = tmp / "set.json"
w(sp, {**sspec, "variants": [{"slug": "aa", "title": "A", "change": "X: y", "prompt": "no slot"}]})
check(expect_exit(new_set.main, [str(sp)]) not in (None, 0), "missing {subject} -> error")
w(sp, {**sspec, "parents": ["evolutions/nope.png"]})
check(expect_exit(new_set.main, [str(sp)]) not in (None, 0), "missing parent -> error")
check(sorted(x.name for x in (tmp / "evolutions").iterdir()) == ["005-foo", "007-bar"], "nothing written on errors")
w(sp, sspec)
expect_exit(new_set.main, [str(sp), "--dry-run"])
check(len(list((tmp / "evolutions").iterdir())) == 2 and labkit.next_cast_id() == "cast121", "new_set dry-run writes nothing")
expect_exit(new_set.main, [str(sp)])
l = json.loads((tmp / "evolutions/008-aa/lineage.json").read_text(encoding="utf-8"))
check(l["goal"] == "go big: yes" and l["parent"] is None and l["round"] == 0 and "cast:cast121" in l["tags"]
      and l["parent_images"] == [par], "lineage.json")
pp = json.loads((tmp / "evolutions/009-bb/v01/params.json").read_text(encoding="utf-8"))
check(pp["aspect_ratio"] == "16:9" and pp["subjects"] == ["f-fantasy@cast121~1"] and pp["steps"] == 25, "variant params")
check(json.loads((tmp / "evolutions/008-aa/v01/params.json").read_text(encoding="utf-8"))["aspect_ratio"].startswith("3:4"), "default aspect")
print(f"ALL PASS ({n_pass})")
