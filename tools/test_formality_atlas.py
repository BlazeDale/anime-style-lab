"""Tests for the Formality Atlas CLI/library (tools/formality_atlas.py): layout determinism, add places near similar neurons, reinforce clamps, blend values,
fuzzy search, glide paths, requests, learning from marks. Temp copies only.
Run: python tools/test_formality_atlas.py"""
import contextlib
import io
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import formality_atlas as fa  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
PASS = FAIL = 0


def ok(c, m):
    global PASS, FAIL
    print(("PASS " if c else "FAIL ") + m)
    PASS += bool(c)
    FAIL += not c


def run(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fa.main(argv)
    return buf.getvalue()


tmp = Path(tempfile.mkdtemp(prefix="atlastest_"))
real = fa.load()
nodes = real["nodes"]
ok(len(nodes) >= 48 and len({n["id"] for n in nodes}) == len(nodes), "the atlas has 48+ distinct neurons: %d" % len(nodes))
fams = {n["family"] for n in nodes}
ok({"dress codes", "ceremony and ritual", "social register", "spatial order", "eras and aesthetics", "speech register", "stick registers"} <= fams, "all six families + the retired stick registers: %s" % sorted(fams))
ids = {n["id"] for n in nodes}
ok({"white-tie", "black-tie", "cocktail", "business-formal", "business-casual", "smart-casual", "streetwear", "athleisure", "loungewear", "festival-wear", "coronation", "state-funeral", "wedding",
    "graduation", "tea-ceremony", "high-mass", "temple-procession", "military-parade", "changing-of-the-guard", "royal-court", "diplomatic-summit", "boardroom", "faculty-senate",
    "family-sunday-dinner", "sleepover", "dive-bar", "rave", "campfire", "perfect-symmetry", "grid-order", "procession-axis", "organic-sprawl", "cluttered-nest", "wilderness",
    "regency-ballroom", "victorian-parlour", "art-deco-gala", "mid-century-office", "brutalist-civic", "bauhaus", "punk", "grunge", "y2k", "liturgical", "legalese", "newsreader",
    "chatty", "slang", "silence"} <= ids, "every concept from the brief is a neuron")
ok({"everyday", "feral", "slacker", "street", "domestic", "festive", "professional", "academic", "diplomatic", "martial", "ritual", "courtly"} <= ids, "the 13 retired stick genres are neurons")
ok(all(set(n["features"]) == set(fa.FEATS) and all(0 <= v <= 1 for v in n["features"].values()) and n["picture"] and n["voice"] and n["added_by"] for n in nodes), "every neuron has 8 features 0-1, a picture, a voice, added_by")

# ---- layout: deterministic, Everyday at the origin, formal up, inside the unit disc, no crowding
a1, a2 = json.loads(json.dumps(real)), json.loads(json.dumps(real))
for a in (a1, a2):
    for n in a["nodes"]:
        n["x"] = n["y"] = 0.0
    a["edges"] = []
    fa.layout(a)
ok([(n["x"], n["y"]) for n in a1["nodes"]] == [(n["x"], n["y"]) for n in a2["nodes"]] and a1["layout"] == a2["layout"], "layout is deterministic")
grown = any(n.get("added_by") not in ("seed", None) for n in nodes)  # neurons the author added later (atlas_add) were placed by projection, not by a full re-layout
ok(all(abs(n["x"] - m["x"]) < 1e-9 and abs(n["y"] - m["y"]) < 1e-9 for n, m in zip(a1["nodes"], nodes)) or (grown and all(math.dist((n["x"], n["y"]), (m["x"], m["y"])) < 0.6 for n, m in zip(a1["nodes"], nodes))),
   "the stored positions are what `layout` computes (a map grown with atlas_add stays close to a fresh layout)")
by = fa.by_id(a1)
ok(by["everyday"]["x"] == 0 and by["everyday"]["y"] == 0, "Everyday sits at the origin")
ok(all(math.hypot(n["x"], n["y"]) <= 1.0001 for n in a1["nodes"]) and max(math.hypot(n["x"], n["y"]) for n in a1["nodes"]) > 0.95, "inside the unit disc and filling it")
hi = [n["y"] for n in a1["nodes"] if n["features"]["rigidity"] >= 0.8]
lo = [n["y"] for n in a1["nodes"] if n["features"]["rigidity"] <= 0.1]
ok(sum(hi) / len(hi) > 0.4 and sum(lo) / len(lo) < -0.1, "the most formal region is up (mean y of rigid neurons %.2f), the loosest down (%.2f)" % (sum(hi) / len(hi), sum(lo) / len(lo)))
mind = min(math.hypot(a["x"] - b["x"], a["y"] - b["y"]) for i, a in enumerate(a1["nodes"]) for b in a1["nodes"][i + 1:])
ok(mind >= fa.GAP - 0.002, "no two neurons crowd each other (closest %.3f)" % mind)
ok(by["coronation"]["y"] > 0.7 and by["sleepover"]["y"] < -0.2 and abs(by["rave"]["x"] - by["perfect-symmetry"]["x"]) > 0.3, "formal ceremony high, sleepover low, order and chaos apart on x")
# every neuron's stored position is roughly where projecting its features puts it (relaxing only nudges)
ok(all(math.dist(fa.project(a1, n["features"]), (n["x"], n["y"])) < 0.3 for n in a1["nodes"]), "project() with the stored basis agrees with the layout (within the collision nudge)")

# ---- edges: 3 nearest neighbours (feature space), connected, weights 0.1-1 from similarity
ok(all(0.1 <= e["w"] <= 1.0 and e["uses"] >= 0 for e in nodes and real["edges"]), "edge weights 0.1-1")
have = {fa.ekey(e["a"], e["b"]) for e in real["edges"]}
kn = 2 if real.get("story") else 3  # with researched story links the factory keeps only the 2 nearest look-alikes, at half weight
ok(all(fa.ekey(n["id"], m) in have for n in nodes for m in [x[1] for x in sorted((fa.fdist(n, o), o["id"]) for o in nodes if o["id"] != n["id"])[:kn]]), "every neuron is wired to its %d nearest neighbours" % kn)
ok(not real.get("story") or all(sum(1 for e in real["edges"] if n["id"] in (e["a"], e["b"])) >= 3 for n in nodes), "with story links every neuron has 3+ synapses")
ok(len(fa.components(real)) == 1, "the network is one connected piece (always navigable)")
ok(fa.sim_w(0.0) == 1.0 and fa.sim_w(0.3) > fa.sim_w(0.6) > fa.sim_w(1.2) and fa.sim_w(5) == 0.1, "similarity -> weight falls with distance, floors at 0.1")
# `layout` keeps learned weights unless --edges
f1 = tmp / "atlas.json"
shutil.copy(fa.ATLAS, f1)
a = fa.load(f1)
a["edges"][0]["w"], a["edges"][0]["uses"] = 0.77, 9
fa.save(a, f1)
out = run(["layout", "--file", str(f1)])
b = fa.load(f1)
ok(b["edges"][0]["w"] == 0.77 and b["edges"][0]["uses"] == 9 and "edges rebuilt" not in out, "`layout` keeps learned synapse weights")
run(["layout", "--edges", "--file", str(f1)])
ok(fa.load(f1)["edges"][0]["w"] != 0.77 and fa.load(f1)["edges"][0]["uses"] == 0, "`layout --edges` rebuilds the synapses from scratch")

# ---- add: placed by projecting the features, wired to the nearest, refuses duplicates
f2 = tmp / "add.json"
shutil.copy(fa.ATLAS, f2)
out = run(["add", "Courthouse hearing", "--family", "social register", "--features", "rigidity=.9,hierarchy=.8,ritual=.55,ornament=.3,tradition=.8,publicness=.55,intimacy=.05,chaos=0",
           "--picture", "a wood-panelled courtroom, a raised bench, a clerk, wigs and robes, silent gallery", "--voice", "measured, formal, procedural", "--aka", "trial, court case", "--file", str(f2)])
A2 = fa.load(f2)
nw = fa.by_id(A2)["courthouse-hearing"]
ok("added courthouse-hearing" in out and len(A2["nodes"]) == len(nodes) + 1 and nw["added_by"] == "claude" and nw["aka"] == ["trial", "court case"], "add: the CLI grows the map: %s" % out.strip()[:120])
d_leg, d_rave = math.dist((nw["x"], nw["y"]), (by["legalese"]["x"], by["legalese"]["y"])), math.dist((nw["x"], nw["y"]), (by["rave"]["x"], by["rave"]["y"]))
ok(nw["y"] > 0.4 and d_leg < 0.45 and d_rave > 1.0 and math.hypot(nw["x"], nw["y"]) <= 1.0001, "add: a formal court lands up near Legalese / Royal court, far from Rave (%.2f vs %.2f)" % (d_leg, d_rave))
near3 = {e["a"] if e["b"] == "courthouse-hearing" else e["b"] for e in A2["edges"] if "courthouse-hearing" in (e["a"], e["b"])}
want = {x[1] for x in sorted((fa.fdist(nw, o), o["id"]) for o in A2["nodes"] if o["id"] != "courthouse-hearing")[:3]}
ok(near3 >= want and all(0.1 <= e["w"] <= 1 for e in A2["edges"]), "add: wired to its 3 nearest neighbours: %s" % sorted(near3))
ok(min(math.dist((nw["x"], nw["y"]), (o["x"], o["y"])) for o in A2["nodes"] if o["id"] != "courthouse-hearing") >= fa.GAP - 0.002 and len(fa.components(A2)) == 1, "add: not crowding anyone, still connected")
ok(all((o["x"], o["y"]) == (p["x"], p["y"]) for o, p in zip(A2["nodes"], nodes)), "add: existing neurons do not move")
for args, why in ((["Courthouse hearing", "--family", "x", "--features", "rigidity=.5", "--picture", "p", "--voice", "v"], "same name"),
                  (["Black Tie", "--family", "x", "--features", "rigidity=.2,chaos=.9", "--picture", "p", "--voice", "v"], "fuzzy-same name"),
                  (["Totally new thing", "--family", "x", "--features", ",".join("%s=%s" % (k, v) for k, v in by["rave"]["features"].items()), "--picture", "p", "--voice", "v"], "identical features")):
    try:
        run(["add"] + args + ["--file", str(f2)])
        refused = False
    except ValueError:
        refused = True
    ok(refused and len(fa.load(f2)["nodes"]) == len(nodes) + 1, "add refuses a duplicate (%s)" % why)
try:
    run(["add", "Nothing", "--file", str(f2)])
    exited = False
except SystemExit:
    exited = True
ok(exited, "add needs features, a picture and a voice")
run(["add", "Totally new thing", "--family", "x", "--features", "rigidity=.5", "--picture", "p", "--voice", "v", "--force", "--file", str(f2)])
ok("totally-new-thing" in fa.by_id(fa.load(f2)), "--force overrides the duplicate checks")

# ---- reinforce clamps
f3 = tmp / "re.json"
shutil.copy(fa.ATLAS, f3)
e0 = fa.edge_of(fa.load(f3), "white-tie", "black-tie")
w0, u0 = (e0["w"], e0["uses"]) if e0 else (None, 0)
out = run(["reinforce", "white-tie", "black-tie", "+0.05", "--file", str(f3)])
e1 = fa.edge_of(fa.load(f3), "white-tie", "black-tie")
ok(e1 and abs(e1["w"] - min(1.0, (w0 if w0 is not None else 0.2) + 0.05)) < 1e-9 and e1["uses"] == u0 + 1 and "uses=%d" % (u0 + 1) in out, "reinforce +0.05 adds to the weight and counts a use")
run(["reinforce", "white-tie", "black-tie", "+5", "--file", str(f3)])
ok(fa.edge_of(fa.load(f3), "white-tie", "black-tie")["w"] == 1.0, "reinforce clamps at 1.0")
run(["reinforce", "black-tie", "white-tie", "-9", "--file", str(f3)])
e2 = fa.edge_of(fa.load(f3), "white-tie", "black-tie")
ok(e2["w"] == 0.1 and e2["uses"] == u0 + 3, "reinforce clamps at 0.1 (either order of ids)")
run(["reinforce", "rave", "coronation", "0.1", "--file", str(f3)])
ok(abs(fa.edge_of(fa.load(f3), "rave", "coronation")["w"] - 0.3) < 1e-9, "reinforcing a missing synapse creates it at 0.2 first")
try:
    run(["reinforce", "rave", "nope", "--file", str(f3)])
    raised = False
except KeyError:
    raised = True
ok(raised, "reinforce rejects unknown ids")
A3 = fa.load(f3)
bl = [{"id": "rave"}, {"id": "punk"}, {"id": "grunge"}, {"id": "bogus"}]
before = {fa.ekey(a_, b_): (fa.edge_of(A3, a_, b_) or {"w": 0.2})["w"] for a_, b_ in (("rave", "punk"), ("rave", "grunge"), ("punk", "grunge"))}
touched = fa.reinforce_blend(A3, bl, 0.05)
ok(len(touched) == 3 and all(abs(e["w"] - min(1.0, before[fa.ekey(e["a"], e["b"])] + 0.05)) < 1e-9 for e in touched), "reinforce_blend: every pair of the blend's neurons (+0.05), unknown ids skipped")

# ---- values, words, describe
v = fa.value_at(real, 0.1, 0.6)
ok(len(v["blend"]) == 3 and abs(sum(b["w"] for b in v["blend"]) - 1) < 1e-9 and all(round(b["w"] * 100) == b["w"] * 100 or abs(b["w"] * 100 - round(b["w"] * 100)) < 1e-6 for b in v["blend"])
   and v["level"] == 60 and v["formality_level"] == 80 and v["genre"] == v["blend"][0]["name"] and 0 < v["mix"] <= 0.5 and v["blend"][0]["w"] >= v["blend"][1]["w"] >= v["blend"][2]["w"], "value_at: 3 nearest, whole percents summing to 1, level from y")
nn = sorted((math.hypot(n["x"] - 0.1, n["y"] - 0.6), n["id"]) for n in nodes)[:3]
ok([b["id"] for b in v["blend"]] == [i for _, i in nn], "value_at: the blend is the 3 nearest neurons")
ok(fa.value_at(real, 3, 0)["probe"]["x"] == 1.0 and fa.value_at(real, 0, -4)["level"] == -100 and fa.value_at(real, 0, 0) == fa.neutral() and fa.neutral()["genre"] == "Everyday", "probe clamps to the disc; the centre is neutral Everyday")
bn = by["black-tie"]
vb = fa.value_at(real, bn["x"], bn["y"])
ok(vb["blend"][0]["id"] == "black-tie" and vb["blend"][0]["w"] >= 0.5, "on a neuron it dominates the blend")
w = fa.blend_words(vb)
ok(w.startswith("Black tie ") and w.count("%") == 3 and w.count(" · ") == 2, "blend words: %s" % w)
out = run(["describe", json.dumps(vb), "--file", str(fa.ATLAS)])
ok("Black tie" in out and "pictures:" in out and "captions:" in out and "dinner jackets" in out, "describe: the blend in words + the top neuron's picture and voice")
ok(fa.is_atlas_value(vb) and not fa.is_atlas_value(50) and not fa.is_atlas_value({"genre": "Martial"}), "is_atlas_value tells the new shape from the old ones")

# ---- fuzzy search (the page ports this)
ok(fa.near(real, "funeral", 1)[0][0] == "state-funeral" and fa.near(real, "Tea Ceremony", 1)[0] == ("tea-ceremony", 1.0) and fa.near(real, "a wedding", 1)[0][0] == "wedding", "near: name / word matches")
ok(fa.near(real, "bioluminescent jellyfish", 1)[0][1] < fa.MATCH and fa.near(real, "pirate captain", 1)[0][1] < fa.MATCH, "near: nothing close scores under the match threshold (-> ask for a new neuron)")
ok(run(["near", "state", "funerals", "--file", str(fa.ATLAS)]).splitlines()[0].split()[1] == "state-funeral", "near CLI")
ok(fa.score("slang", by["slang"]) == 1.0 and fa.dice("abc", "abc") == 1.0 and fa.tokens("The feeling of a Funerals") == {"funeral"}, "score / dice / tokens")

# ---- paths
p = fa.path(real, "white-tie", "rave")
ek = {fa.ekey(e["a"], e["b"]) for e in real["edges"]}
ok(p[0] == "white-tie" and p[-1] == "rave" and all(fa.ekey(p[i], p[i + 1]) in ek for i in range(len(p) - 1)) and fa.path(real, "rave", "rave") == ["rave"] and fa.path(real, "rave", "zz") == [], "path: along existing synapses")
mk = lambda i: {"id": i, "features": {}}  # noqa: E731
toy = {"nodes": [mk("a"), mk("b"), mk("c")], "edges": [{"a": "a", "b": "b", "w": 1.0}, {"a": "b", "b": "c", "w": 1.0}, {"a": "a", "b": "c", "w": 0.1}]}
ok(fa.path(toy, "a", "c") == ["a", "b", "c"], "path: strong synapses are short (1/w)")

# ---- requests from the page + learning from marks
root = tmp / "root"
(root / "explore" / "001-x").mkdir(parents=True)
r1 = fa.add_request(root, "  hushed   library ", "1999-12-31 10:00:00")
r1b = fa.add_request(root, "Hushed library")
r2 = fa.add_request(root, "ironic tuxedo")
ok(r1["id"] == "a1" and r1["new"] and "new" not in r1b and r1b["id"] == "a1" and r2["id"] == "a2" and [r["id"] for r in fa.open_requests(root)] == ["a1", "a2"], "requests: deduplicated while open, ids a1 a2")
ok(fa.resolve_request(root, "a1", "node") == 1 and [r["id"] for r in fa.open_requests(root)] == ["a2"] and fa.resolve_request(root, "ironic tuxedo") == 1 and fa.open_requests(root) == [] and fa.resolve_request(root, "zzz") == 0, "requests: resolved by id or text")
shutil.copy(fa.ATLAS, root / "explore" / "formality_atlas.json")
(root / "explore" / "001-x" / "episode.json").write_text(json.dumps({"formality": v}), encoding="utf-8")
n_ = fa.learn_from_mark(root, "explore/001-x/e3.png", 0.1)
A4 = fa.load(root / "explore" / "formality_atlas.json")
ids3 = [b["id"] for b in v["blend"]]
ok(n_ == 3 and all(fa.edge_of(A4, ids3[i], ids3[j])["uses"] >= 1 for i in range(3) for j in range(i + 1, 3)), "learn_from_mark: a ❤ strengthens the episode's blend pairs")
ok(fa.learn_from_mark(root, "evolutions/001-x/v01/a.png", 0.1) == 0 and fa.learn_from_mark(root, "explore/002-none/e1.png", 0.1) == 0, "learn_from_mark ignores other images and missing episodes")
shutil.rmtree(tmp, ignore_errors=True)
print("PASS %d FAIL %d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
