"""Tests for the shared Atlas engine (tools/atlas.py) with BOTH maps: the Formality Atlas and the Emotion Atlas -- the generic CLI
(`atlas.py <formality|emotion> layout|add|reinforce|describe|near|path|list|requests|resolve`), layout determinism and the documented axes (emotion: valence
across, arousal up), kNN synapses, add / near / reinforce, values (emotion centre = neutral), requests per atlas, learning from marks (emotion blends and cores),
the thin formality_atlas.py alias. Temp copies only.
Run: python tools/test_atlas.py"""
import contextlib
import io
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import atlas as A  # noqa: E402
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
        A.main(argv)
    return buf.getvalue()


def corr(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))


tmp = Path(tempfile.mkdtemp(prefix="atlas2test_"))
emo = A.load(kind="emotion")
frm = A.load(kind="formality")
nodes = emo["nodes"]
ids = {n["id"] for n in nodes}

# ---- the Emotion Atlas data
ok(emo["kind"] == "emotion" and emo["features"] == A.EMOTION_FEATS and len(nodes) >= 58 and len({n["id"] for n in nodes}) == len(nodes), "emotion atlas: kind, 7 features, 58+ distinct nodes: %d" % len(nodes))
ok({"bittersweet", "nostalgia", "saudade", "mono-no-aware", "hiraeth", "catharsis", "found-family-warmth", "slow-burn-tension", "unrequited-love", "forbidden-love", "heartbreak", "survivor-s-guilt",
    "righteous-fury", "revenge", "redemption", "betrayal", "dread", "existential-dread", "cosmic-horror", "sublime-terror", "awe", "wonder", "whimsy", "absurdity", "cozy-comfort", "ennui", "defiance",
    "liberation", "hope-against-the-odds", "triumph", "jealousy", "shame", "pride", "camaraderie", "loneliness", "tenderness", "wanderlust", "homesickness", "grief", "serenity", "euphoria", "melancholy",
    "longing", "tension", "joy"} <= ids, "emotion atlas: every concept from the brief is a node")
ok({"joy", "wonder", "awe", "tension", "dread", "melancholy", "longing", "serenity"} == {n["id"] for n in nodes if n.get("legacy")}, "emotion atlas: the 8 old wheel emotions are legacy nodes (migration targets)")
ok(all(set(n["features"]) == set(A.EMOTION_FEATS) and all(0 <= v <= 1 for v in n["features"].values()) and n["picture"] and n["voice"] and n["beats"] and n["added_by"] for n in nodes), "every emotion node has 7 features 0-1, picture, voice, beats")
ok(len({n["family"] for n in nodes}) >= 10 and len(A.components(emo)) == 1 and all(0.1 <= e["w"] <= 1 for e in emo["edges"]), "emotion atlas: 10+ families, one connected network, synapse weights 0.1-1")
ok(all(math.hypot(n["x"], n["y"]) <= 1.0001 for n in nodes) and min(math.dist((a["x"], a["y"]), (b["x"], b["y"])) for i, a in enumerate(nodes) for b in nodes[i + 1:]) >= A.GAP - 0.002, "emotion layout: inside the unit disc, no crowding")
ok(corr([n["x"] for n in nodes], [n["features"]["valence"] for n in nodes]) > 0.85 and corr([n["y"] for n in nodes], [n["features"]["arousal"] for n in nodes]) > 0.6, "emotion layout: valence across (x), arousal up (y)")
ok(0.25 < emo["layout"]["explained"][0] <= 1 and emo["layout"]["explained"][1] >= emo["layout"]["explained"][0] and emo["meta"]["axes"]["top"].replace(" ", "") == "INTENSE", "layout notes how much variance the valence x arousal plane keeps (vs the best PCA plane) and the axis names")
# no cluster of more than 8 inside a 0.2 x 0.2 valence x arousal box (a readable spread)
dense = max(sum(1 for m in nodes if abs(m["features"]["valence"] - n["features"]["valence"]) <= 0.1 and abs(m["features"]["arousal"] - n["features"]["arousal"]) <= 0.1) for n in nodes)
ok(dense <= 12, "emotion nodes are spread across the plane (densest 0.2 x 0.2 box holds %d; 12 allowed because the pleasant / mid-arousal region legitimately holds the love, joy and bonds families)" % dense)

# ---- the full range of love and passion
love = [x for x in nodes if x["family"] == "love and passion"]
lids = {x["id"] for x in love}
ok(len(love) >= 22 and {"infatuation", "first-love", "love-at-first-sight", "flirtatious-spark", "enemies-to-lovers", "burning-passion", "devotion", "adoration-from-afar", "the-confession", "reunion", "love-s-sacrifice",
    "rekindled-love", "obsessive-love", "love-hate", "secret-love", "mature-love", "parting"} <= lids, "love & passion family: the 17 new nodes are there (%d in the family)" % len(love))
ok({"longing", "unrequited-love", "forbidden-love", "tenderness", "heartbreak", "jealousy", "slow-burn-tension"} <= lids, "love & passion family: the 7 earlier love-ish nodes moved into it")
SEXUAL = ("sex", "naked", "nude", "nudity", "erotic", "lust", "seduc", "undress", "lingerie", "bed ", "bedroom", "breast", "thigh", "cleavage", "sensual", "steamy", "topless", "intercourse", "arous")
txt = lambda x: " ".join([x["picture"], x["voice"], x["beats"], " ".join(x.get("aka") or [])]).lower()  # noqa: E731
ok(not [x["id"] for x in love if any(t in txt(x) for t in SEXUAL)], "love & passion: no sexual terms in any picture / voice / beats line (passion = emotional intensity only): %s" % [x["id"] for x in love if any(t in txt(x) for t in SEXUAL)])
ok(all(not any(w in x["picture"].lower() for w in ("kiss",)) or "adult" in x["picture"].lower() or "couple" in x["picture"].lower() for x in love), "love & passion: a kiss is only ever between adults")
nm = {x["id"]: x for x in love}
ok(nm["burning-passion"]["features"]["arousal"] > 0.9 and nm["mature-love"]["features"]["arousal"] < 0.2 and nm["devotion"]["features"]["arousal"] < 0.35 and nm["infatuation"]["features"]["arousal"] > 0.6, "love & passion: passion is high arousal, devotion / mature love are quiet")
ok(nm["burning-passion"]["y"] > 0.7 and nm["mature-love"]["y"] < -0.5 and nm["obsessive-love"]["x"] < 0 < nm["reunion"]["x"] and nm["love-hate"]["x"] < nm["first-love"]["x"], "love & passion layout: passion high, quiet love low, the dark side (obsessive, love-hate) left, joyful love (reunion, first love) right")
ok(max(sum(1 for m in nodes if abs(m["features"]["valence"] - q["features"]["valence"]) <= 0.1 and abs(m["features"]["arousal"] - q["features"]["arousal"]) <= 0.1) for q in love) <= 9, "love & passion: the new nodes do not crowd one patch of the plane")
linked = [x for x in love if any(m["id"] != x["id"] and A.ekey(x["id"], m["id"]) in {A.ekey(e["a"], e["b"]) for e in emo["edges"]} for m in love)]
ok(len(linked) >= 0.8 * len(love), "love & passion: the family is interlinked (%d of %d nodes have a synapse to another love node; the rest border other families, e.g. Flirtatious spark -> Mischief)" % (len(linked), len(love)))
ok(emo["meta"]["hues"].get("love and passion") and "love and longing" not in {x["family"] for x in nodes}, "love & passion: has its own colour; the old mixed family was split")

# ---- layout is deterministic and the stored positions are what `layout` computes (both atlases)
for name, real in (("emotion", emo), ("formality", frm)):
    a1, a2 = json.loads(json.dumps(real)), json.loads(json.dumps(real))
    for a in (a1, a2):
        for n in a["nodes"]:
            n["x"] = n["y"] = 0.0
        a["edges"] = []
        A.layout(a)
    ok([(n["x"], n["y"]) for n in a1["nodes"]] == [(n["x"], n["y"]) for n in a2["nodes"]] and a1["layout"] == a2["layout"], "%s layout is deterministic" % name)
    grown = any(n.get("added_by") not in ("seed", None) for n in real["nodes"])   # nodes the author added later were placed by projection, not by a full re-layout
    ok(all(abs(n["x"] - m["x"]) < 1e-9 and abs(n["y"] - m["y"]) < 1e-9 for n, m in zip(a1["nodes"], real["nodes"])) or (grown and all(math.dist((n["x"], n["y"]), (m["x"], m["y"])) < 0.6 for n, m in zip(a1["nodes"], real["nodes"]))),
       "%s: the stored positions are what `layout` computes (a grown atlas stays close)" % name)
    ok(all(math.dist(A.project(a1, n["features"]), (n["x"], n["y"])) < 0.5 for n in a1["nodes"]), "%s: project() with the stored basis agrees with the layout (within the collision nudge)" % name)

# ---- values: emotion centre = neutral, formality centre = Everyday
v0 = A.value_at(emo, 0, 0)
ok(v0 == A.neutral("emotion") and v0["blend"] == [] and v0["genre"] is None and A.value_at(frm, 0, 0) == A.neutral("formality") and A.neutral("formality")["genre"] == "Everyday", "emotion centre is neutral (no blend); formality centre is Everyday")
n = {x["id"]: x for x in nodes}["saudade"]
v = A.value_at(emo, n["x"], n["y"])
nn = sorted((math.hypot(m["x"] - n["x"], m["y"] - n["y"]), m["id"]) for m in nodes)[:3]
ok([b["id"] for b in v["blend"]] == [i for _, i in nn] and abs(sum(b["w"] for b in v["blend"]) - 1) < 1e-9 and 0 <= v["valence"] <= 1 and 0 <= v["arousal"] <= 1 and "level" not in v and v["intensity"] > 0.5,
   "emotion value: the 3 nearest, weights sum to 1, valence + arousal of the blend, no formality level")
ok("level" in A.value_at(frm, 0.1, 0.6) and "valence" not in A.value_at(frm, 0.1, 0.6), "formality values keep level / formality_level")
ok(A.blend_words(v0, emo) == "neutral (no emotional steer)" and A.blend_words(v, emo).startswith("Saudade ") and A.blend_words(v, emo).count("%") == 3, "blend words: %s" % A.blend_words(v, emo))
d = A.describe_value(v, emo)
ok("pictures:" in d and "captions:" in d and "story beats:" in d and "valence" in d, "describe (emotion): the blend + picture / voice / beats lines")
out = run(["emotion", "describe", json.dumps(v)])
ok("Saudade" in out and "story beats" in out, "CLI describe works for the emotion atlas")

# ---- generic CLI: list, near, path, add, reinforce (emotion), on temp copies
f1 = tmp / "emo.json"
shutil.copy(A.atlas_path("emotion"), f1)
ok("63 nodes" in run(["emotion", "list", "--file", str(f1)]) or "nodes," in run(["emotion", "list", "--file", str(f1)]), "CLI list (emotion)")
ok(run(["emotion", "near", "homesick", "--file", str(f1)]).splitlines()[0].split()[1] == "homesickness", "CLI near finds an existing emotion by words")
ok(run(["emotion", "near", "saudade", "--file", str(f1)]).splitlines()[0].split()[1] == "saudade", "near: exact name")
p = A.path(emo, "joy", "grief")
ek = {A.ekey(e["a"], e["b"]) for e in emo["edges"]}
ok(p[0] == "joy" and p[-1] == "grief" and all(A.ekey(p[i], p[i + 1]) in ek for i in range(len(p) - 1)), "path along the synapses (emotion)")
out = run(["emotion", "add", "Wistful hope", "--family", "resolve and hope", "--features", "valence=.55,arousal=.3,intimacy=.2,temporal=.85,moral_weight=.3,agency=.4,absurdity=0",
           "--picture", "a figure waiting at dawn, pale gold light low on the horizon, hands loosely clasped", "--voice", "soft, forward-leaning, careful", "--beats", "A long wait ends with only a hint of what is coming.",
           "--aka", "hopeful waiting", "--file", str(f1)])
E2 = A.load(f1, "emotion")
nw = A.by_id(E2)["wistful-hope"]
ok("added wistful-hope" in out and len(E2["nodes"]) == len(nodes) + 1 and nw["beats"].startswith("A long wait") and nw["aka"] == ["hopeful waiting"] and E2["kind"] == "emotion", "add (emotion): a node with a beats line: %s" % out.strip()[:100])
others = [m for m in E2["nodes"] if m["id"] != "wistful-hope"]
ok(min(math.dist((nw["x"], nw["y"]), (m["x"], m["y"])) for m in others) >= A.GAP - 0.002 and math.hypot(nw["x"], nw["y"]) <= 1.0001 and nw["x"] > 0 and len(A.components(E2)) == 1, "add: lands on the pleasant side, not crowding, still connected")
near3 = {e["a"] if e["b"] == "wistful-hope" else e["b"] for e in E2["edges"] if "wistful-hope" in (e["a"], e["b"])}
ok(near3 >= {x[1] for x in sorted((A.fdist(nw, o), o["id"]) for o in others)[:3]}, "add: wired to its 3 nearest neighbours")
ok(all((o["x"], o["y"]) == (q["x"], q["y"]) for o, q in zip(E2["nodes"], nodes)), "add: existing nodes do not move")
for args, why in ((["Saudade", "--family", "x", "--features", "valence=.5", "--picture", "p", "--voice", "v"], "same name"),
                  (["Bittersweet feeling", "--family", "x", "--features", "valence=.1,arousal=.9", "--picture", "p", "--voice", "v"], "fuzzy-same name"),
                  (["Quiet thing", "--family", "x", "--features", ",".join("%s=%s" % (k, val) for k, val in n["features"].items()), "--picture", "p", "--voice", "v"], "identical features")):
    try:
        run(["emotion", "add"] + args + ["--file", str(f1)])
        refused = False
    except ValueError:
        refused = True
    ok(refused and len(A.load(f1, "emotion")["nodes"]) == len(nodes) + 1, "add refuses a duplicate (%s)" % why)
try:
    run(["emotion", "add", "Nothing", "--features", "formality=1", "--picture", "p", "--voice", "v", "--file", str(f1)])
    bad = False
except SystemExit:
    bad = True
ok(bad, "add rejects a feature the atlas does not have (formality atlas features are not emotion features)")
e0 = A.edge_of(A.load(f1, "emotion"), "joy", "euphoria")
out = run(["emotion", "reinforce", "joy", "euphoria", "+0.05", "--file", str(f1)])
e1 = A.edge_of(A.load(f1, "emotion"), "joy", "euphoria")
ok(e1 and abs(e1["w"] - min(1.0, (e0["w"] if e0 else 0.2) + 0.05)) < 1e-9 and e1["uses"] == (e0["uses"] if e0 else 0) + 1, "reinforce (emotion) +0.05, counts a use")
run(["emotion", "reinforce", "euphoria", "joy", "-9", "--file", str(f1)])
ok(A.edge_of(A.load(f1, "emotion"), "joy", "euphoria")["w"] == 0.1, "reinforce clamps at 0.1")
a = A.load(f1, "emotion")
a["edges"][0]["w"], a["edges"][0]["uses"] = 0.77, 9
A.save(a, f1)
out = run(["emotion", "layout", "--file", str(f1)])
ok(A.load(f1, "emotion")["edges"][0]["w"] == 0.77 and "edges rebuilt" not in out, "`layout` keeps learned weights (emotion)")
run(["emotion", "layout", "--edges", "--file", str(f1)])
ok(A.load(f1, "emotion")["edges"][0]["uses"] == 0, "`layout --edges` rebuilds the synapses")

# ---- the kind is told apart: the same CLI drives the formality atlas
f2 = tmp / "for.json"
shutil.copy(A.atlas_path("formality"), f2)
ok("tea-ceremony" in run(["formality", "list", "--file", str(f2)]) and run(["formality", "near", "funeral", "--file", str(f2)]).splitlines()[0].split()[1] == "state-funeral", "CLI list / near (formality)")
out = run(["formality", "add", "Courthouse hearing", "--family", "social register", "--features", "rigidity=.9,hierarchy=.8,ritual=.55,ornament=.3,tradition=.8,publicness=.55,intimacy=.05,chaos=0",
           "--picture", "a wood-panelled courtroom, a raised bench", "--voice", "measured, procedural", "--file", str(f2)])
ok("added courthouse-hearing" in out and A.load(f2, "formality")["kind"] == "formality", "CLI add (formality) still works through atlas.py")
try:
    run(["formality", "add", "Warm glow", "--features", "valence=.9", "--picture", "p", "--voice", "v", "--file", str(f2)])
    cross = False
except SystemExit:
    cross = True
ok(cross, "an emotion feature is refused on the formality atlas")
_b = io.StringIO()
with contextlib.redirect_stdout(_b):
    fa.main(["list", "--file", str(f2)])
ok(fa.main.__module__ == "formality_atlas" and "tea-ceremony" in _b.getvalue(), "formality_atlas.py is a thin alias of `atlas.py formality`")
ok(fa.value_at(frm, 0, 0) == fa.neutral() and fa.neutral("emotion")["blend"] == [] and fa.load()["kind"] == "formality" and fa.FEATS == A.FORMALITY_FEATS, "the alias keeps the old API (value_at / neutral / load / FEATS)")

# ---- requests are per atlas; atlas_add with an `atlas` field
root = tmp / "root"
(root / "explore" / "001-x").mkdir(parents=True)
r1 = A.add_request(root, "wistful hush", "1999-12-31 10:00:00", "emotion")
r2 = A.add_request(root, "wistful hush", None, "formality")
r3 = A.add_request(root, "Wistful  hush", None, "emotion")
ok(r1["atlas"] == "emotion" and r1["new"] and r2["new"] and r2["id"] != r1["id"] and r3["id"] == r1["id"] and "new" not in r3, "requests: deduplicated per atlas")
ok([r["id"] for r in A.open_requests(root, "emotion")] == [r1["id"]] and [r["id"] for r in A.open_requests(root, "formality")] == [r2["id"]] and len(A.open_requests(root)) == 2, "requests: listed per atlas")
old = [{"id": "a1", "text": "old", "ts": "t", "status": "open"}]
(root / "feedback" / "atlas_requests.json").write_text(json.dumps(old), encoding="utf-8")
ok(A.open_requests(root, "formality")[0]["id"] == "a1" and A.open_requests(root, "emotion") == [], "requests without an atlas field are formality ones")
ok(A.resolve_request(root, "a1", "node") == 1 and A.open_requests(root) == [], "requests resolve by id")

# ---- learning: a mark reinforces the episode's emotion blend, its active cores, and the formality blend; sagas' chapters too
(root / "explore" / "sagas" / "001-s" / "ch01").mkdir(parents=True)
shutil.copy(A.atlas_path("emotion"), root / "explore" / "emotion_atlas.json")
shutil.copy(A.atlas_path("formality"), root / "explore" / "formality_atlas.json")
ev = A.value_at(emo, n["x"], n["y"])
core = A.value_at(emo, {x["id"]: x for x in nodes}["triumph"]["x"], {x["id"]: x for x in nodes}["triumph"]["y"])
ep = {"emotion": ev, "cores": [{"id": "c1", "name": "T", "blend": core["blend"], "weight": 0.6, "status": "active"}, {"id": "c2", "name": "R", "blend": ev["blend"], "weight": 0.5, "status": "resolved"}]}
(root / "explore" / "001-x" / "episode.json").write_text(json.dumps(ep), encoding="utf-8")
(root / "explore" / "sagas" / "001-s" / "ch01" / "episode.json").write_text(json.dumps(ep), encoding="utf-8")
ids3 = [b["id"] for b in ev["blend"]]
c3 = [b["id"] for b in core["blend"]]
t = A.learn_from_mark(root, "explore/001-x/e3.png", 0.1, kind="emotion")
EA = A.load(root / "explore" / "emotion_atlas.json", "emotion")
ok(t == 6 and all(A.edge_of(EA, ids3[i], ids3[j])["uses"] >= 1 for i in range(3) for j in range(i + 1, 3)) and all(A.edge_of(EA, c3[i], c3[j])["uses"] >= 1 for i in range(3) for j in range(i + 1, 3)),
   "learn_from_mark (emotion): a ❤ strengthens the moment's blend AND the active cores' blends (not resolved ones)")
t2 = A.learn_from_mark(root, "explore/sagas/001-s/ch01/e2.png", -0.1, kind="emotion")
ok(t2 == 6, "learn_from_mark works for saga chapter shots too")
ok(A.learn_from_mark(root, "explore/001-x/e3.png", 0.1, kind="formality") == 0 and A.learn_from_mark(root, "evolutions/001-x/v01/a.png", 0.1, kind="emotion") == 0 and A.learn_from_mark(root, "explore/sagas/001-s/e1.png", 0.1, kind="emotion") == 0,
   "learn_from_mark ignores episodes without that atlas' value and non-episode images")

# ---- factory reset, backups, restore (temp copies only)
import serve_gallery as sg  # noqa: E402
for kind in ("emotion", "formality"):
    rt = tmp / ("rs_" + kind)
    (rt / "explore").mkdir(parents=True)
    live = A.atlas_path(kind, rt)
    shutil.copy(A.atlas_path(kind), live)
    base = A.load(live, kind)
    pre_added = [n["id"] for n in base["nodes"] if n.get("added_by") != "seed"]   # nodes the live author already added to the real atlas
    seeds = [n["id"] for n in base["nodes"] if n.get("added_by") == "seed"]
    A.save(base, live)
    ok(A.load(live, kind)["factory"]["seed_nodes"] and A.load(live, kind)["factory"]["ts"], "%s: a factory note is stored on save" % kind)
    fresh = json.loads(json.dumps(A.load(live, kind)))
    A.rebuild_edges(fresh)
    init = {A.ekey(e["a"], e["b"]): e["w"] for e in fresh["edges"]}
    a = A.load(live, kind)
    ids2 = [n["id"] for n in a["nodes"]][:3]
    A.reinforce(a, ids2[0], ids2[1], 0.5)
    A.reinforce(a, ids2[1], ids2[2], -0.5)
    extra = A.add_node(a, "Zzz extra thing", "added", {k: (0.31 if i % 2 else 0.77) for i, k in enumerate(A.feats_of(a))}, "p", "v", by="claude", force=True)
    A.save(a, live)
    learned = A.load(live, kind)
    r = A.reset_atlas(learned)
    now_w = {A.ekey(e["a"], e["b"]): e["w"] for e in learned["edges"] if "zzz-extra-thing" not in (e["a"], e["b"])}
    ok(all(abs(now_w[k] - init[k]) < 1e-9 for k in now_w if k in init) and all(e["uses"] == 0 for e in learned["edges"]) and sorted(r["kept_added"]) == sorted(pre_added + ["zzz-extra-thing"]) and r["removed_nodes"] == [] and "zzz-extra-thing" in A.by_id(learned),
       "%s reset: weights back to initial, uses 0, the added node is KEPT by default (and wired)" % kind)
    l2 = A.load(live, kind)
    r2 = A.reset_atlas(l2, True)
    ok(sorted(r2["removed_nodes"]) == sorted(pre_added + ["zzz-extra-thing"]) and "zzz-extra-thing" not in A.by_id(l2) and [n["id"] for n in l2["nodes"]] == seeds and len(A.components(l2)) == 1 and not [e for e in l2["edges"] if "zzz-extra-thing" in (e["a"], e["b"])],
       "%s reset --remove-added drops the later nodes and their synapses, keeps the network connected" % kind)
    # backups: unique names inside one second, newest 5 kept
    paths = [A.backup_atlas(kind, rt) for _ in range(7)]
    ok(len({p.name for p in paths}) == 7 and len(A.list_backups(kind, rt)) == 5 and paths[-1].exists() and not paths[0].exists(), "%s backups: written, never collide, only the newest 5 are kept" % kind)
    # CLI reset / backups / restore on the temp file
    f = str(live)
    before = A.load(live, kind)
    out = A.main  # noqa: F841
    o1 = run([kind, "reset", "--remove-added", "--file", f])
    after = A.load(live, kind)
    ok("backup" in o1 and "zzz-extra-thing" not in A.by_id(after) and all(e["uses"] == 0 for e in after["edges"]), "%s CLI reset --remove-added: %s" % (kind, o1.strip()[:90]))
    ok(len(run([kind, "backups", "--file", f]).split()) >= 1, "%s CLI backups lists them" % kind)
    o2 = run([kind, "restore", "--file", f])
    back = A.load(live, kind)
    ok("restored" in o2 and "zzz-extra-thing" in A.by_id(back) and [e["w"] for e in back["edges"]] == [e["w"] for e in before["edges"]], "%s CLI restore brings back the pre-reset weights + the removed node" % kind)
    nb = len(A.list_backups(kind, rt))
    A.restore_atlas(kind, None, rt)
    ok(len(A.list_backups(kind, rt)) >= min(5, nb) and A.list_backups(kind, rt)[-1].exists(), "%s restore itself leaves a fresh backup (undoable)" % kind)
    try:
        A.restore_atlas(kind, "nope.json", rt)
        miss = False
    except FileNotFoundError:
        miss = True
    ok(miss, "%s restore of a missing backup is refused" % kind)

# the server op, called directly with the module's ROOT / FB / LOG pointed at a temp tree
srt = tmp / "srv"
(srt / "explore").mkdir(parents=True)
(srt / "feedback").mkdir()
for kind in ("emotion", "formality"):
    shutil.copy(A.atlas_path(kind), A.atlas_path(kind, srt))
    a = A.load(A.atlas_path(kind, srt), kind)
    A.reinforce(a, a["nodes"][0]["id"], a["nodes"][1]["id"], 0.4)
    A.add_node(a, "Server extra", "added", {k: (0.2 if i % 2 else 0.9) for i, k in enumerate(A.feats_of(a))}, "p", "v", by="user", force=True)
    A.save(a, A.atlas_path(kind, srt))
old = (sg.ROOT, sg.FB, sg.LOG)
sg.ROOT, sg.FB, sg.LOG = srt, srt / "feedback", srt / "feedback" / "log.jsonl"
try:
    res = sg.explore_api({"op": "atlas_reset", "atlas": "emotion"}, "1999-12-31 20:00:00", "gallery")
    E3 = A.load(A.atlas_path("emotion", srt), "emotion")
    ok(res and res["ok"] is True and res["atlas"] == "emotion" and res["backup"].startswith("emotion_atlas.backup-") and (srt / "explore" / res["backup"]).exists() and "server-extra" in res["summary"]["kept_added"]
       and "server-extra" in A.by_id(E3) and all(e["uses"] == 0 for e in E3["edges"]) and "state" in res and "episodes" in res, "server atlas_reset: backup, reset, response shape: %s" % sorted(res))
    res2 = sg.explore_api({"op": "atlas_reset", "atlas": "formality", "remove_added": True}, "1999-12-31 20:00:01", "gallery")
    F3 = A.load(A.atlas_path("formality", srt), "formality")
    ok("server-extra" in res2["summary"]["removed_nodes"] and "server-extra" not in A.by_id(F3) and all(n.get("added_by") == "seed" for n in F3["nodes"]), "server atlas_reset remove_added drops the added node")
    evs = [json.loads(x) for x in (srt / "feedback" / "log.jsonl").read_text(encoding="utf-8").splitlines()]
    ok([e["event"] for e in evs] == ["atlas_reset", "atlas_reset"] and evs[0]["backup"] == res["backup"] and "server-extra" in evs[1]["removed"] and evs[0]["atlas"] == "emotion", "server atlas_reset logs an informational atlas_reset event")
    ok(sg.explore_api({"op": "atlas_reset", "atlas": "emotion"}, "t", "api") is None, "server atlas_reset needs a same-origin browser request (by != gallery is refused)")
finally:
    sg.ROOT, sg.FB, sg.LOG = old
import watch_feedback as wf  # noqa: E402
ok(wf.is_info({"event": "atlas_reset"}), "atlas_reset is an informational event for the watcher")

# ---- researched story links (import-story): they become the factory wiring, feature fixes re-lay out, reset rebuilds from them
import copy  # noqa: E402
S = copy.deepcopy(emo)
S.pop("story", None)
res = {"sources": [{"key": "t17", "cite": "Thornton & Tamir 2017"}],
       "links": [{"a": "grief", "b": "hope-against-the-odds", "w": 0.9, "kind": "arc_pair", "dir": "a->b", "why": "grief turns to hope", "src": ["t17"]},
                 {"a": "betrayal", "b": "revenge", "w": 0.95, "kind": "transition", "why": "the revenge plot"},
                 {"a": "betrayal", "b": "revenge", "w": 0.4, "kind": "cooccur"},
                 {"a": "nope-not-a-node", "b": "grief", "w": 0.5}],
       "feature_fixes": [{"id": "grief", "feature": "arousal", "to": 0.33, "why": "VAD norm"}]}
r = A.import_story(S, res)
eg = A.edge_of(S, "grief", "hope-against-the-odds")
ok(r["links"] == 3 and r["skipped"] == 1 and eg and eg["w"] == 0.9 and eg["kind"] == "arc_pair" and eg.get("dir") == "a->b", "import-story: links become edges with kind/dir, unknown ids skipped")
ok(A.edge_of(S, "betrayal", "revenge")["w"] == 0.95, "import-story: a duplicate pair keeps its strongest weight")
ok(A.by_id(S)["grief"]["features"]["arousal"] == 0.33 and A.by_id(S)["grief"]["feature_notes"][0]["why"] == "VAD norm" and r["fixed"], "import-story: feature fixes applied and noted")
ok(all(e["w"] <= 0.5 for e in S["edges"] if e.get("kind") == "similar") and len(A.components(S)) == 1, "import-story: nearest neighbours kept at half weight, the map stays one connected piece")
A.reinforce(S, "grief", "hope-against-the-odds", 0.05)
A.reset_atlas(S)
ok(A.edge_of(S, "grief", "hope-against-the-odds")["w"] == 0.9 and A.edge_of(S, "grief", "hope-against-the-odds")["uses"] == 0, "reset rebuilds the researched wiring (learned weight gone)")
ok(A.path(S, "betrayal", "revenge") == ["betrayal", "revenge"], "path glides along the story link")

# ---- orbit values (the deck's orbit view: centre -> 3 links -> 2 sub-links each; each orbit weighs less, sub-links only colour their parent)
ov = {"orbit": True, "intensity": 0.7, "probe": {"x": 0.1, "y": 0.1},
      "blend": [{"id": "grief", "w": 0.4}] + [{"id": i, "w": 0.12} for i in ("bittersweet", "catharsis", "heartbreak")] + [{"id": i, "w": 0.04} for i in ("nostalgia", "tension", "relief", "dread", "jealousy", "parting")],
      "tree": {"center": "grief", "ring1": ["bittersweet", "catharsis", "heartbreak"], "kids": {"bittersweet": ["nostalgia", "tension"], "catharsis": ["relief", "dread"], "heartbreak": ["jealousy", "parting"]}, "k1": [0, 2, 1], "k2": {"catharsis": [1, 0]}, "lp": [True, False, False], "lm": {"catharsis": [False, True]}, "d1": 3, "d2": {"catharsis": 2}}}
si = A.story_items(ov)
ok(si[0] == ("grief", 0.4) and len(si) == 4 and all(abs(w - 0.2) < 1e-9 for _, w in si[1:]), "story_items: the centre leads, each link carries its two sub-links' weight (sub-links only colour their parent): %s" % si)
ok(A.tree_pairs(ov)[:3] == [("grief", "bittersweet"), ("grief", "catharsis"), ("grief", "heartbreak")] and len(A.tree_pairs(ov)) == 9 and A.tree_pairs({"blend": []}) == [], "tree_pairs: centre-link and link-sub-link pairs only")
E2 = copy.deepcopy(emo)
t_ = A.reinforce_value(E2, ov, 0.05)
ok(len(t_) == 9 and A.edge_of(E2, "nostalgia", "tension") is None or A.edge_of(E2, "nostalgia", "tension")["uses"] == A.edge_of(emo, "nostalgia", "tension")["uses"], "learning: an orbit value thickens only its tree's 9 links (sub-links of one parent are not wired to each other)")
ok(len(A.reinforce_blend(copy.deepcopy(emo), ov["blend"], 0.05)) == 3, "a 10-neuron blend reinforces only its top 3 pairs")
dv = A.describe_value(ov, emo)
ok(dv.startswith("orbit: Grief → Bittersweet (Nostalgia, Tension) · Catharsis (Relief, Dread) · Heartbreak (Jealousy, Parting);") and "grief 40%" in dv.lower(), "describe_value says the tree, then the flat blend: " + dv[:140])
import explore_state as xs2  # noqa: E402
cv = xs2.clean_atlas_value(ov, emo, "emotion")
ok(cv["orbit"] is True and cv["tree"]["center"] == "grief" and len(cv["blend"]) == 10 and cv["tree"]["kids"]["catharsis"] == ["relief", "dread"] and cv["intensity"] == 0.7 and cv["tree"]["k1"] == [0, 2, 1] and cv["tree"]["k2"] == {"catharsis": [1, 0]} and cv["tree"]["lp"] == [True, False, False] and cv["tree"]["lm"] == {"catharsis": [False, True]} and cv["tree"]["d1"] == 3 and cv["tree"]["d2"] == {"catharsis": 2}, "the server keeps an orbit value's 10 neurons and its tree")
ok(len(xs2.clean_atlas_value({**ov, "orbit": False}, emo, "emotion")["blend"]) == 3 and "tree" not in xs2.clean_atlas_value({**ov, "orbit": False}, emo, "emotion"), "a plain value still keeps 3")
import explore_render as er2  # noqa: E402
cue = er2.emotion_cue(ov, emo)
ok(cue.startswith("an overwhelming mood of grief, tinged with") and "nostalgia" not in cue.split(":")[0], "the image cue reads the centre + a link (the sub-links fold into their link): " + cue[:90])

shutil.rmtree(tmp, ignore_errors=True)
print("PASS %d FAIL %d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
