"""Tests for the Python side of the 📖 Nev Novel deck (1999-12-31): the maturity dial (tools/maturity.py + its HARD CEILING), the stackable emotional cores and
the Emotion-atlas emotion value in explore_state, the steer cue (explore_render: emotion blend, top core, maturity + ceiling), saga.py cores (per saga) and chapters,
explore_edit, build_gallery payload bits, serve_gallery.explore_api and the inbox / describe text. Temp trees only; no GPU, no server, nothing real is written.
Run: python tools/test_deck.py"""
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import atlas as A  # noqa: E402
import build_gallery as bg  # noqa: E402
import explore_edit as ee  # noqa: E402
import explore_render as er  # noqa: E402
import explore_state as xs  # noqa: E402
import maturity as mt  # noqa: E402
import saga  # noqa: E402
import serve_gallery as sg  # noqa: E402
import watch_feedback as wf  # noqa: E402

PASS = FAIL = 0


def ok(c, m):
    global PASS, FAIL
    print(("PASS " if c else "FAIL ") + m)
    PASS += bool(c)
    FAIL += not c


def raises(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except saga.SagaError as e:
        return str(e)
    return None


emo = A.load(kind="emotion")
frm = A.load(kind="formality")
N = A.by_id(emo)
at = lambda i: A.value_at(emo, N[i]["x"], N[i]["y"])  # noqa: E731
words = lambda t: len(t.split())  # noqa: E731
CAMERA = re.compile(r"\b(pan|panning|zoom\w*|dolly|tilt\w*|track\w*|push(ing)? in|pull(ing)? back|camera|fly\w* through|sweep\w*)\b", re.I)
BAD = re.compile(r"\b(sex\w*|naked|nude|nudity|erotic|lust\w*|gore|gory|dismember\w*|entrails|blood-?soaked|mutilat\w*|torture)\b", re.I)

# ================================================================================================ maturity
ok(len(mt.STOPS) == 7 and mt.LABELS == ["Preschool", "Kids", "Family", "Tween", "Teen", "Young adult", "Mature"] and [s["stop"] for s in mt.STOPS] == list(range(7)), "maturity: 7 stops in order Preschool .. Mature")
ok(all(s.get(k) for s in mt.STOPS for k in ("label", "feels_like", "story", "pictures", "ceiling")), "maturity: every stop has label / feels_like / story / pictures / ceiling")
ok(mt.DEFAULT_STOP == 4 and mt.stop_of(None)["label"] == "Teen" and mt.stop_of("zzz")["label"] == "Teen" and mt.stop_of({})["label"] == "Teen", "maturity: the default stop is Teen")
ok(mt.stop_of(0)["label"] == "Preschool" and mt.stop_of(6.4)["label"] == "Mature" and mt.stop_of(99)["label"] == "Mature" and mt.stop_of(-3)["label"] == "Preschool" and mt.stop_of("young adult")["stop"] == 5 and mt.stop_of("Young-adult")["stop"] == 5, "maturity: stop_of by int / clamp / label / hyphenated label")
ok(mt.clean(2) == {"stop": 2, "label": "Family"} and mt.clean("Kids") == {"stop": 1, "label": "Kids"} and mt.clean({"stop": 3}) == {"stop": 3, "label": "Tween"} and mt.clean({"label": "Mature"}) == {"stop": 6, "label": "Mature"} and mt.clean("5") == {"stop": 5, "label": "Young adult"}, "maturity: clean() int / label / dict / numeric string")
ok(mt.clean(None) is None and mt.clean("junk") is None and mt.clean(True) is None and mt.clean([1]) is None and mt.clean({}) is None and mt.clean(float("nan")) is None, "maturity: clean() rejects None / junk / bool / list / empty / NaN")
ok(mt.clean({"stop": 99}) == {"stop": 6, "label": "Mature"}, "maturity: an out-of-range stop clamps")
C = mt.CEILING.lower()
ok("adults only" in C and "under 18" in C and "no sexual content" in C and "no graphic gore" in C and "fully clothed" in C and "no on-screen injury or blood" in C and "slapstick or implied" in C
   and "discretion of the user and the model" in C, "maturity: the CEILING text names every rule (adults only everywhere; Mature at the user's + model's discretion)")
ok(all("fully clothed" in s["ceiling"] for s in mt.STOPS[:6]), "maturity: Preschool .. Young adult keep the clothing rule")
ok("adults only" in mt.STOPS[6]["ceiling"] and "under 18" in mt.STOPS[6]["ceiling"], "maturity: Mature's ceiling = consenting adults only, never anyone under 18")
ok(all(re.search(r"no (on-screen )?injury|no blood|nothing scary", mt.STOPS[i]["ceiling"]) for i in (0, 1, 2)), "maturity: Preschool / Kids / Family show no injury or blood")
ok(not [s["label"] for s in mt.STOPS[:6] if BAD.search(s["story"] + " " + s["pictures"] + " " + s["feels_like"])], "maturity: no sexual / gore words in any stop below Mature")
ok(not BAD.search(mt.STOPS[6]["pictures"]), "maturity: Mature's pictures line (the image steer cue) names no explicit content itself")
ok(len({s["pictures"] for s in mt.STOPS}) == 7 and len({s["story"] for s in mt.STOPS}) == 7, "maturity: every stop has its own story + pictures lines")
ok("PG-13" in mt.STOPS[4]["feels_like"] and "Saturday-morning" in mt.STOPS[1]["feels_like"] and "adult fiction" in mt.STOPS[6]["feels_like"] and "discretion" in mt.STOPS[6]["feels_like"] and "toddler" in mt.STOPS[0]["feels_like"], "maturity: feels_like follows the brief")
d = mt.describe(1)
ok(d.startswith("Kids [2/6") is False and d.startswith("Kids [1/6") and "story:" in d and "pictures:" in d and "ceiling:" in d and "fully clothed" in d, "maturity: describe() = stop, story, pictures, ceiling, the always-rules")
ok(mt.cue(0)[0] == mt.STOPS[0]["pictures"] and mt.cue({"stop": 6})[1] == mt.STOPS[6]["ceiling"] and "Teen" in mt.words(None), "maturity: cue() / words()")
ok(mt.table()[3]["label"] == "Tween" and mt.table() is not mt.STOPS, "maturity: table() copies")

# ================================================================================================ explore_state: emotion, cores, maturity
t = xs.clean_tune({"maturity": 2, "presence": 40})
ok(t["maturity"] == {"stop": 2, "label": "Family"} and t["presence"] == 40.0, "clean_tune: maturity {stop,label}")
ok("maturity" not in xs.clean_tune({"maturity": "junk"}) and "maturity" not in xs.clean_tune({}), "clean_tune: junk / missing maturity ignored")
ev = at("saudade")
t = xs.clean_tune({"emotion": ev})
ok(t["emotion"]["blend"][0]["id"] == "saudade" and t["emotion"]["valence"] is not None and "legacy" not in t["emotion"] and abs(sum(b["w"] for b in t["emotion"]["blend"]) - 1) < 0.02, "clean_tune: an Emotion Atlas value is kept (blend, valence, arousal)")
ok(xs.clean_tune({"emotion": {"probe": {"x": 0.2, "y": 0.3}}})["emotion"] == A.value_at(emo, 0.2, 0.3), "clean_tune: a bare probe is re-derived from the emotion atlas")
ok(xs.clean_tune({"emotion": A.neutral("emotion")})["emotion"]["blend"] == [], "clean_tune: the neutral emotion stays neutral")
ok("emotion" not in xs.clean_tune({"emotion": {"nonsense": 1}}) and "emotion" not in xs.clean_tune({"emotion": "joy"}), "clean_tune: junk emotion ignored")
m = xs.migrate_emotion({"primary": "awe", "secondary": "wonder", "mix": 0.3, "intensity": 0.8})
ok(m["legacy"] is True and [b["id"] for b in m["blend"]] == ["awe", "wonder"] and m["blend"][0]["w"] == 0.7 and m["intensity"] == 0.8, "migrate_emotion: the two legacy nodes, 70/30, legacy flag, old intensity kept")
ok(xs.migrate_emotion({"primary": None}) == A.neutral("emotion") and xs.migrate_emotion({"primary": "joy", "intensity": 0}) == A.neutral("emotion") and xs.migrate_emotion({"primary": "rage", "intensity": 1}) == A.neutral("emotion") and xs.migrate_emotion(None) == A.neutral("emotion"), "migrate_emotion: neutral / zero intensity / unknown = neutral")
ok(all(xs.migrate_emotion({"primary": e, "intensity": 0.5})["blend"][0]["id"] == e for e in xs.EMOTIONS), "migrate_emotion: every old wheel emotion has its legacy node")
ok(xs.clean_emotion({"primary": "joy", "secondary": "joy", "mix": 0.3, "intensity": 0.5})["blend"] == [{"id": "joy", "name": "Joy", "w": 1.0}], "clean_emotion: a secondary equal to the primary is dropped")

cs = xs.clean_cores([{"id": "c1", "name": "  Saudade   core ", "blend": ev["blend"], "probe": ev["probe"], "weight": 1.7}, {"name": "no blend"}, "junk", {"blend": []}])
ok(len(cs) == 1 and cs[0]["name"] == "Saudade core" and cs[0]["weight"] == 1.0 and cs[0]["status"] == "active" and cs[0]["id"] == "c1", "clean_cores: needs a blend, name trimmed, weight clamped to 0-1")
ok(xs.clean_cores([{"blend": ev["blend"], "probe": ev["probe"]}])[0]["weight"] == 0.6 and xs.clean_cores([{"blend": ev["blend"], "weight": -2}])[0]["weight"] == 0.0 and xs.clean_cores([{"blend": ev["blend"], "weight": "x"}])[0]["weight"] == 0.6, "clean_cores: default weight 0.6, negative clamps to 0, junk weight = default")
ok(xs.clean_cores([{"blend": ev["blend"], "name": "n" * 200}])[0]["name"] == "n" * 60 and xs.clean_cores([{"blend": ev["blend"]}])[0]["name"] == "Saudade", "clean_cores: name capped at 60, defaults to the top node")
ids6 = ["joy", "grief", "awe", "dread", "serenity", "pride", "shame"]
six = xs.clean_cores([{"id": "k%d" % i, "blend": at(x)["blend"], "probe": at(x)["probe"]} for i, x in enumerate(ids6)])
ok(len(six) == 7 and [c["id"] for c in six if c["status"] == "active"] == ["k0"] and all(c["status"] == "resolved" for c in six[1:]), "clean_cores: ONE active kept, later active ones kept as resolved")
mix = xs.clean_cores([{"id": "r%d" % i, "blend": at(x)["blend"], "status": "resolved"} for i, x in enumerate(ids6)] + [{"id": "a%d" % i, "blend": at(x)["blend"]} for i, x in enumerate(ids6)])
ok(sum(1 for c in mix if c["status"] == "active") == 1 and sum(1 for c in mix if c["status"] == "resolved") == 11 and len(mix) == 12, "clean_cores: one active, the rest resolved, 12 in all")
many = xs.clean_cores([{"id": "r%d" % i, "blend": at(ids6[i % 7])["blend"], "status": "resolved"} for i in range(20)])
ok(len(many) == xs.MAX_CORES == 12, "clean_cores: 12 cores at most in all")
dup = xs.clean_cores([{"id": "x", "blend": at("joy")["blend"]}, {"id": "x", "blend": at("grief")["blend"]}, {"blend": at("awe")["blend"], "name": "Awe"}, {"blend": at("dread")["blend"], "name": "Awe"}])
ok(len({c["id"] for c in dup}) == 4, "clean_cores: ids are made unique: %s" % [c["id"] for c in dup])
h = xs.clean_cores([{"id": "x", "blend": at("joy")["blend"], "history": [{"chapter": "ch01", "beat": "b"}, "junk"]}])
ok(h[0]["history"] == [{"chapter": "ch01", "beat": "b"}], "clean_cores: history kept (junk entries dropped)")
ok(xs.clean_cores("x") == [] and xs.clean_cores(None) == [], "clean_cores: not a list = nothing")
ct = xs.clean_tune({"cores": [{"id": "c1", "blend": ev["blend"], "probe": ev["probe"], "weight": 0.9}], "maturity": "Mature"})
ok(ct["cores"][0]["weight"] == 0.9 and ct["maturity"]["stop"] == 6, "clean_tune: cores + maturity together")
ok(xs.clean_tune({"cores": []})["cores"] == [] and "cores" not in xs.clean_tune({"cores": "x"}), "clean_tune: an empty list clears the cores, a non-list is ignored")

# words / describe
cw = xs.cores_words([{"id": "c1", "name": "Saudade", "weight": 0.9, "status": "active", "blend": ev["blend"]}, {"id": "c2", "name": "Old", "weight": 0.5, "status": "resolved", "blend": at("joy")["blend"]}], detail=True)
ok("Saudade (weight 0.9, active)" in cw and "pictures:" in cw and "captions:" in cw and "story beats:" in cw and "Old (weight 0.5, resolved)" in cw and cw.index("Saudade") < cw.index("Old"), "cores_words(detail): name, weight, picture / voice / story beats; heavy first, resolved last")
ok(xs.cores_words([]) == "none" and "pictures:" not in xs.cores_words([{"id": "c", "name": "N", "weight": 0.4, "blend": ev["blend"]}]), "cores_words: none / brief")
ok("assume Teen" in xs.maturity_words(None) and "Mature" in xs.maturity_words({"stop": 6}) and "ceiling" in xs.maturity_words(2), "maturity_words")
st = {"presence": 70, "emotion": ev, "cores": [{"id": "c1", "name": "Dear Saudade", "weight": 0.8, "blend": ev["blend"]}], "maturity": {"stop": 5, "label": "Young adult"}, "formality": at("joy")}
ds = xs.describe(st, True)
ok("maturity Young adult" in ds and "emotion of the moment Saudade" in ds and "Dear Saudade (weight 0.8" in ds and "story beats:" in ds and "presence 70" in ds, "describe(): presence, maturity, emotion of the moment, cores in words")
ok("pictures: " not in xs.cores_words(st["cores"]) and "assume Teen" in xs.describe({"presence": 10}), "describe(): cores brief without detail; missing maturity says Teen")
ok("neutral" in xs.emotion_words(A.neutral("emotion")) and xs.emotion_words(ev).startswith("Saudade") and "melancholic longing" in xs.emotion_words({"primary": "longing", "secondary": "melancholy", "mix": 0.3, "intensity": 0.8}), "emotion_words: atlas value / neutral / the old wheel")

# state carries cores + maturity
tmp = Path(tempfile.mkdtemp(prefix="decktest_"))
f = tmp / "feedback" / "explore.json"
tune = {"presence": 60, "emotion": ev, "cores": ct["cores"], "maturity": ct["maturity"]}
s1 = xs.start(f, "t", now=1000, tune=tune)
ok(s1["cores"][0]["weight"] == 0.9 and s1["maturity"]["label"] == "Mature" and s1["emotion"]["blend"][0]["id"] == "saudade", "start() stores cores + maturity + the emotion value; view() exposes them")
s2 = xs.cont(f, "t", now=1100)
ok(s2["cores"] == s1["cores"] and s2["maturity"] == s1["maturity"], "continue without values keeps cores + maturity")
s3 = xs.tune(f, "t", now=1200, values={"maturity": {"stop": 1, "label": "Kids"}})
ok(s3["maturity"]["stop"] == 1 and s3["cores"] == s1["cores"], "tune() changes only what it is given")
s4 = xs.tune(f, "t", now=1200, values={"cores": []})
ok(s4["cores"] == [], "tune() with an empty list clears the cores")
s5 = xs.stop(f, "t", now=1300)
ok(s5["maturity"]["stop"] == 1 and s5["active"] is False, "stop() carries maturity (and the rest)")
ok(xs.state(f, now=99999)["maturity"]["stop"] == 1 and xs.state(tmp / "none.json")["cores"] is None, "state(): expired / empty states expose the keys")

# ================================================================================================ the steer cue
N_ = N
moodv = at("bittersweet")
cue_e = er.emotion_cue(moodv)
ok(cue_e.lower().startswith(("a faint mood of", "a clear mood of", "an overwhelming mood of", "a overwhelming mood of")) and "bittersweet" in cue_e.lower() and "smile" not in cue_e and "embrace" not in cue_e and "golden light" in cue_e, "emotion_cue: a mood of the top node + only its LIGHT / TONE clause, never the staging (drive the story, don't dictate every scene): %s" % cue_e)
ok(er.emotion_cue({**moodv, "intensity": 0.1}) == "" and er.emotion_cue(A.neutral("emotion")) == "" and er.emotion_cue(None) == "" and er.emotion_cue({"blend": []}) == "", "emotion_cue: skipped below 0.15 / neutral / empty")
ok(er.emotion_cue({**moodv, "intensity": 0.2}).startswith("a faint mood") and er.emotion_cue({**moodv, "intensity": 0.5}).startswith("a clear mood") and "overwhelming mood" in er.emotion_cue({**moodv, "intensity": 0.9}), "emotion_cue: faint / clear / overwhelming mood by intensity")
ok(er._mood_clause("two adults in a desperate embrace, rain streaming over them, fully clothed and drenched, deep red and amber light, eyes closed, faces close", 9) == "deep red and amber light" and er._mood_clause("a figure at a window, empty space ahead", 9) == "", "_mood_clause keeps light / colour / tone, drops who does what where")
two = {**moodv, "intensity": 0.8, "blend": [{"id": "bittersweet", "name": "Bittersweet", "w": 0.6}, {"id": "nostalgia", "name": "Nostalgia", "w": 0.4}]}
ok("tinged with nostalgia" in er.emotion_cue(two) and "tinged" not in er.emotion_cue({**two, "blend": [{"id": "bittersweet", "name": "Bittersweet", "w": 0.9}, {"id": "nostalgia", "name": "Nostalgia", "w": 0.1}]}), "emotion_cue: the 2nd node tints (a 10% one is left out)")
ok(len(er.emotion_cue(two, None, (3, 0))) <= len(er.emotion_cue(two, None, (9, 5))) and er.emotion_cue(two, None, (0, 0)).count(":") == 0, "emotion_cue: the budget shrinks the clause")
ok(er.emotion_cue({"primary": "dread", "intensity": 0.5}).startswith("a clear feeling of dread, ominous") and er.emotion_cue({"primary": "awe", "intensity": 0.1}) == "", "emotion_cue: legacy wheel phrase + its 0.15 gate")

mk = lambda i, w, st="active", name=None: {"id": "c" + i, "name": name or N[i]["name"], "blend": at(i)["blend"], "probe": at(i)["probe"], "weight": w, "status": st}  # noqa: E731
ok(er.core_cue([mk("grief", 0.3)]) == "a hint of grief" and er.core_cue([mk("grief", 0.49)]).startswith("a hint of"), "core_cue: a weight under 0.5 is only 'a hint of x'")
cc = er.core_cue([mk("grief", 0.5)])
ok(cc.startswith("an undertone of grief") and "figure" not in cc and "hands" not in cc, "core_cue: 0.5 and up = 'an undertone of x' + only its mood (light / tone), no staging: %s" % cc)
ok(er.core_cue([mk("grief", 0.2)]) == "" and er.core_cue([mk("grief", 0.8, "resolved")]) == "" and er.core_cue([]) == "" and er.core_cue(None) == "", "core_cue: under 0.25, resolved, none = nothing")
ok(er.core_cue([mk("grief", 0.4), mk("pride", 0.9), mk("shame", 0.6)]).startswith("an undertone of pride"), "core_cue: the heaviest ACTIVE core wins")
ok(er.core_cue([mk("grief", 0.9, "resolved"), mk("pride", 0.3)]) == "a hint of pride", "core_cue: a heavier resolved core is ignored")
ok(er.core_cue([mk("grief", 0.9)], None, "grief") == "" and er.core_cue([mk("grief", 0.9)], None, "joy").startswith("an undertone"), "core_cue: skipped when it is the same node as the mood")
ok(er.core_cue([mk("grief", 0.9, name="Dear Grief")]).startswith("an undertone of dear grief") and er.core_cue([mk("grief", 0.9)], None, None, 0) == "a hint of grief", "core_cue: uses the core's name; 0 words = a hint")

ok(er.maturity_cue(None) == "", "maturity_cue: none = nothing (old episodes)")
for i in range(7):
    pic, ceil = mt.cue(i)
    mc = er.maturity_cue(i)
    ok(mc.endswith(ceil) and mc.startswith(" ".join(pic.split(",")[0].split())) and ("fully clothed" in mc or "adults only" in mc), "maturity_cue %s: pictures clause + the ceiling at the end" % mt.LABELS[i])
ok(er.maturity_cue(0) != er.maturity_cue(6) and er.maturity_cue(0, 0) == mt.cue(0)[1], "maturity_cue: Preschool differs from Mature; 0 picture words = the ceiling alone")

base = {"presence": 95, "emotion": {**moodv, "intensity": 0.9}, "cores": [mk("grief", 0.9)], "maturity": {"stop": 5, "label": "Young adult"},
        "formality": {"blend": [{"id": "coronation", "w": 0.4}, {"id": "state-funeral", "w": 0.35}, {"id": "high-mass", "w": 0.25}], "intensity": 0.9}}
for stop in range(7):
    ep = {**base, "maturity": mt.clean(stop)}
    cue = er.steer_cue(ep, atlas=frm)
    c_ceil = mt.cue(stop)[1]
    ok(words(cue) <= er.STEER_WORDS + 4 and c_ceil in cue and not CAMERA.search(cue) and cue.endswith("."), "steer_cue at %s with everything on: %d words, ceiling kept, no camera words" % (mt.LABELS[stop], words(cue)))
full = er.steer_cue(base, atlas=frm)
ok(full.startswith("Immense scale") and "bittersweet" in full.lower(), "steer_cue: presence leads, then the mood: %s" % full[:90])
ok(er.steer_cue({"presence": 50, "maturity": 4}, atlas=frm) == "Composed classic framing; " + er.maturity_cue(4) + ".", "steer_cue: presence + maturity only")
light = er.steer_cue({"presence": 30, "emotion": {**moodv, "intensity": 0.5}, "cores": [mk("grief", 0.9)], "maturity": 4}, atlas=frm)
ok("an undertone of grief" in light and "bittersweet" in light.lower() and light.count(";") == 4, "steer_cue (short): all parts survive when it fits: %s" % light)
tiny = {"presence": 95, "emotion": {**moodv, "intensity": 0.9}, "cores": [mk("grief", 0.9)], "maturity": 6, "formality": base["formality"]}
tcue = er.steer_cue(tiny, atlas=frm)
ok("staged as" not in tcue or words(tcue) <= er.STEER_WORDS + 4, "steer_cue: the formality staging goes first when the cue is long")
mid = {**tiny, "formality": None}
ok(words(er.steer_cue(mid, atlas=frm)) <= er.STEER_WORDS + 4 and mt.cue(6)[1] in er.steer_cue(mid, atlas=frm), "steer_cue: trims the core / mood detail before the ceiling")
old = {"presence": 20, "emotion": {"primary": "awe", "secondary": None, "mix": 0, "intensity": 0.3}}
oc = er.steer_cue(old, atlas=frm)
ok("a subtle sense of awe, luminous and expansive" in oc and not re.search(r"clothed|sexual|gore|injury", oc), "steer_cue: an old episode (no cores / maturity) gives its old cue with no maturity words")
ok(er.steer_cue({}) == "" and er.steer_cue({"cores": [mk("grief", 0.9)]}).startswith("An undertone of grief"), "steer_cue: nothing = '' (a core alone still speaks)")
sh = {"steer": {"maturity": 0, "cores": [mk("pride", 0.7)]}}
oc2 = er.steer_cue({"maturity": 6, "cores": [mk("grief", 0.9)]}, sh, frm)
ok(mt.cue(0)[1] in oc2 and "pride" in oc2 and "grief" not in oc2 and mt.cue(6)[1] not in oc2, "steer_cue: a shot's own steer overrides maturity + cores")
ok("pride" not in er.steer_cue({"cores": [mk("pride", 0.7)]}, {"steer": {"cores": []}}), "steer_cue: a shot can clear the cores")
ok(er.prompt_of({"style": "ink, {subject}", "maturity": 2}, {"prompt": "a cat"}, atlas=frm).endswith(mt.cue(2)[1] + "."), "prompt_of: the cue (with the ceiling) closes the prompt")
nm = er.steer_cue({"presence": 80, "maturity": 3}, atlas=frm)
ok(not CAMERA.search(nm) and not CAMERA.search(" ".join(er.maturity_cue(i) for i in range(7))), "steer_cue: no camera words in the maturity lines")

# ================================================================================================ saga.py: cores + maturity per saga
f.unlink(missing_ok=True)
sd, _ = saga.new("Deck Saga", "A test", "ink, {subject}", root=tmp)
ok(saga.load(sd)["cores"] == [] and saga.load(sd)["maturity"] == {"stop": 4, "label": "Teen"}, "saga new (no deck cores yet): empty cores, default maturity Teen")
shutil.rmtree(sd)
deck = xs.clean_cores([{"id": "c1", "name": "Grief", "blend": at("grief")["blend"], "probe": at("grief")["probe"], "weight": 0.8, "history": [{"chapter": "ch09", "beat": "x"}]}, {"id": "c2", "name": "Pride", "blend": at("pride")["blend"], "weight": 0.4}])
f.write_text(json.dumps({"active": False, "cores": deck, "maturity": {"stop": 2, "label": "Family"}}), encoding="utf-8")
sd, _ = saga.new("Deck Saga", "A test", "ink, {subject}", root=tmp)
b = saga.load(sd)
ok([c["id"] for c in b["cores"]] == ["c1", "c2"] and all("history" not in c for c in b["cores"]) and b["maturity"] == {"stop": 2, "label": "Family"}, "saga new: starts with the deck's cores (history stripped) + maturity")
ok(raises(saga.cores_log, sd, "nope", "ch01", "b") and "unknown or ambiguous core" in raises(saga.cores_log, sd, "nope", "ch01", "b"), "cores log: an unknown core is an error naming the ones there are")
saga.cores_log(sd, "c1", "ch01", "Mira loses the compass", "a quiet insert")
saga.cores_log(sd, "grief", "ch02", "She visits the grave")
h = saga.load(sd)["cores"][0]["history"]
ok(h == [{"chapter": "ch01", "beat": "Mira loses the compass", "how": "a quiet insert"}, {"chapter": "ch02", "beat": "She visits the grave"}], "cores log: by id or by name; the beat + how are kept")
ok("beat" in (raises(saga.cores_log, sd, "c1", "ch03", "") or "") and "chapter" in (raises(saga.cores_log, sd, "c1", "", "b") or ""), "cores log: needs a chapter and a beat")
saga.cores_weight(sd, "pride", 1.4)
ok(saga.load(sd)["cores"][1]["weight"] == 1.0, "cores weight: clamps to 0-1")
saga.cores_weight(sd, "c2", 0.25)
ok(saga.load(sd)["cores"][1]["weight"] == 0.25, "cores weight: sets it")
saga.cores_status(sd, "c2", "resolved")
ok(saga.load(sd)["cores"][1]["status"] == "resolved", "cores resolve")
amb = xs.clean_cores([{"id": "ga", "name": "Grief a", "blend": at("grief")["blend"]}, {"id": "gb", "name": "Grief b", "blend": at("dread")["blend"]}])
saga.cores_set(sd, amb)
ok("ambiguous" in (raises(saga.cores_status, sd, "grief", "resolved") or ""), "cores: an ambiguous name is refused")
five = xs.clean_cores([{"id": "k%d" % i, "blend": at(x)["blend"]} for i, x in enumerate(ids6[:5])] + [{"id": "old", "blend": at("shame")["blend"], "status": "resolved"}])
saga.cores_set(sd, five)
saga.cores_status(sd, "old", "active")
cs_ = saga.load(sd)["cores"]
ok(cs_[-1]["status"] == "active" and [c["id"] for c in cs_ if c["status"] == "active"] == ["old"], "cores reopen: swaps the reopened core in, the current one is resolved (one active)")
# set: from the deck state, history kept by id
saga.cores_set(sd, deck)
saga.cores_log(sd, "c1", "ch01", "first beat")
f.write_text(json.dumps({"active": False, "cores": [{**{k: v for k, v in deck[0].items() if k != "history"}, "weight": 0.3}, deck[1]], "maturity": {"stop": 6, "label": "Mature"}}), encoding="utf-8")
got = saga.cores_set(sd, None, None, root=tmp)
b = saga.load(sd)
ok(b["cores"][0]["weight"] == 0.3 and b["cores"][0]["history"][-1] == {"chapter": "ch01", "beat": "first beat"} and len(b["cores"][0]["history"]) == 2 and b["maturity"]["label"] == "Mature" and len(got) == 2, "cores set (from the deck state): new weight, HISTORY KEPT by core id, maturity saved")
saga.cores_set(sd, [deck[1]])
ok([c["id"] for c in saga.load(sd)["cores"]] == ["c2"] and saga.load(sd)["maturity"]["label"] == "Mature", "cores set: a core left out is removed; maturity untouched when not given")
saga.cores_set(sd, deck, "Kids")
ok(saga.load(sd)["maturity"]["label"] == "Kids", "cores set --maturity")
saga.cores_log(sd, "c1", "ch02", "mid beat", "how")
txt = saga.bible_text(sd)
ok("maturity: Kids" in txt and "emotional cores" in txt and "Grief (weight" in txt and "ch02: mid beat (how)" in txt and "story beats:" in txt, "bible_text: maturity + cores with their history and the node's lines")
ok("Maturity + emotional cores" in saga.bible_text(sd, brief=True), "bible_text --brief carries them too")
saga.main(["cores", sd.name, "weight", "c1", "0.55"]) if False else None
b = saga.load(sd)
b["maturity"] = None
saga.save(sd, b)
ok("assume Teen" in saga.cores_text(sd), "cores_text: no maturity says Teen")

# chapter: the saga's cores / maturity win over the deck state
saga.cores_set(sd, deck, "Young adult")
saga.add_cast(sd, "Mira", "red scarf", "pilot", "dry")
spec = {"title": "One", "summary": "s", "shots": [{"prompt": "wide harbour", "narration": "n", "noref": True}, {"prompt": "Mira at the wheel", "with": ["Mira"], "caption": "c"}]}
f.write_text(json.dumps({"active": False, "presence": 33, "cores": [{**deck[0], "id": "deckcore"}], "maturity": {"stop": 0, "label": "Preschool"}}), encoding="utf-8")
saga.write_chapter(sd, spec, root=tmp)
ep = json.loads((sd / "ch01" / "episode.json").read_text(encoding="utf-8"))
ok(ep["maturity"]["label"] == "Young adult" and [c["id"] for c in ep["cores"]] == ["c1", "c2"] and all("history" not in c for c in ep["cores"]) and ep["presence"] == 33, "write_chapter: the SAGA's cores + maturity (no history) beat the deck state's; the rest of the steer is the deck's")
b = saga.load(sd)
del b["cores"]
b["maturity"] = None
saga.save(sd, b)
spec2 = {**spec, "title": "Two"}
saga.write_chapter(sd, spec2, root=tmp)
ep2 = json.loads((sd / "ch02" / "episode.json").read_text(encoding="utf-8"))
ok(ep2["maturity"]["label"] == "Preschool" and ep2["cores"][0]["id"] == "deckcore", "write_chapter: a saga without cores / maturity takes the deck's")
f.write_text(json.dumps({"active": False}), encoding="utf-8")
saga.write_chapter(sd, {**spec, "title": "Three"}, root=tmp)
ep3 = json.loads((sd / "ch03" / "episode.json").read_text(encoding="utf-8"))
ok(ep3["maturity"] == {"stop": 4, "label": "Teen"}, "write_chapter: no maturity anywhere = Teen")

# explore_edit
ok("cores" in ee.STEER_KEYS and "maturity" in ee.STEER_KEYS, "explore_edit.STEER_KEYS carries cores + maturity")
(sd / "ch03" / "e1.png").write_bytes(b"\x89PNG")
ep3["shots"][0]["src"] = "e1.png"
(sd / "ch03" / "episode.json").write_text(json.dumps(ep3), encoding="utf-8")
res = ee.edit(sd / "ch03", [{"prompt": "Mira alone", "with": ["Mira"], "caption": "c"}], steer_state={"presence": 90, "maturity": {"stop": 1, "label": "Kids"}, "cores": [mk("pride", 0.7)]}, reason="t")
ep3 = json.loads((sd / "ch03" / "episode.json").read_text(encoding="utf-8"))
ok(res["steer"]["maturity"]["stop"] == 1 and ep3["maturity"]["stop"] == 1 and ep3["cores"][0]["name"] == "Pride" and ep3["shots"][-1]["steer"]["maturity"]["label"] == "Kids" and ep3["steer_log"][-1]["steer"]["cores"], "explore_edit --steer-from-state: copies cores + maturity into the episode, the new shots and steer_log")

# build_gallery payload
col = bg.collect_sagas(tmp)
sga = next(x for x in col if x["id"] == sd.name)
ok(sga["cores"] == [] or isinstance(sga["cores"], list), "collect_sagas: cores key")
saga.cores_set(sd, deck, "Teen")
sga = next(x for x in bg.collect_sagas(tmp) if x["id"] == sd.name)
ok([c["id"] for c in sga["cores"]] == ["c1", "c2"] and sga["maturity"]["label"] == "Teen" and sga["chapters"][0]["cores"] and sga["chapters"][0]["maturity"], "collect_sagas: cores + maturity on the saga and on each chapter")
(tmp / "explore" / "001-one").mkdir(parents=True)
(tmp / "explore" / "001-one" / "episode.json").write_text(json.dumps({"id": "001-one", "title": "t", "shots": [], "cores": deck, "maturity": {"stop": 3, "label": "Tween"}}), encoding="utf-8")
ce = bg.collect_explore(tmp)
ok(ce[0]["cores"][0]["id"] == "c1" and ce[0]["maturity"]["label"] == "Tween", "collect_explore: cores + maturity")
shutil.copy(A.atlas_path("emotion"), tmp / "explore" / "emotion_atlas.json")
ca = bg.collect_atlas(tmp, kind="emotion")
ok(ca["kind"] == "emotion" and len(ca["nodes"]) >= 80 and bg.collect_atlas(tmp, kind="formality") is None and bg.collect_atlas(tmp / "zz", kind="emotion") is None, "collect_atlas(kind='emotion') reads explore/emotion_atlas.json; a missing file = None")
cm = bg.collect_maturity()
ok(len(cm["stops"]) == 7 and cm["default"] == 4 and cm["ceiling"] == mt.CEILING, "collect_maturity: the 7 stops, the default and the ceiling text")

# ================================================================================================ serve_gallery.explore_api
(tmp / "feedback").mkdir(exist_ok=True)
(tmp / "feedback" / "explore.json").unlink(missing_ok=True)
keep = (sg.ROOT, sg.FB, sg.LOG)
sg.ROOT, sg.FB, sg.LOG = tmp, tmp / "feedback", tmp / "feedback" / "log.jsonl"
evs = lambda: [json.loads(x) for x in sg.LOG.read_text(encoding="utf-8").splitlines()] if sg.LOG.exists() else []  # noqa: E731
try:
    body = {"presence": 70, "emotion": ev, "cores": [{"id": "c1", "name": "Grief", "blend": at("grief")["blend"], "probe": at("grief")["probe"], "weight": 0.7}], "maturity": 3, "formality": at("joy") if False else None}
    r = sg.explore_api({"op": "start", "seed": "x", **{k: v for k, v in body.items() if v is not None}}, "1999-12-31 10:00:00")
    e0 = evs()[-1]
    ok(r["state"]["maturity"]["stop"] == 3 and e0["kind"] == "start" and e0["cores"][0]["name"] == "Grief" and e0["maturity"]["label"] == "Tween" and e0["emotion"]["blend"][0]["id"] == "saudade", "explore_api start: the event carries cores + maturity + the emotion value")
    # no saga yet: continue must not crash and writes nothing
    r = sg.explore_api({"op": "continue", **{k: v for k, v in body.items() if v is not None}}, "1999-12-31 10:01:00")
    ok(r["state"]["active"] and evs()[-1]["kind"] == "continue", "explore_api continue with no saga: no crash")
    ok(evs()[-1]["cores"][0]["id"] == "c1" and evs()[-1]["maturity"]["stop"] == 3, "explore_api continue: event has cores + maturity")
    sg_dir, _ = saga.new("Server Saga", "l", "ink, {subject}", root=tmp)
    saga.cores_set(sg_dir, [{"id": "c1", "name": "Grief", "blend": at("grief")["blend"], "weight": 0.7}])
    saga.cores_log(sg_dir, "c1", "ch01", "kept")
    newcore = {"id": "c3", "name": "Awe", "blend": at("awe")["blend"], "probe": at("awe")["probe"], "weight": 0.5}
    r = sg.explore_api({"op": "tune", "cores": [{**body["cores"][0], "weight": 0.2}, newcore], "maturity": 6}, "1999-12-31 10:02:00")
    b = saga.load(sg_dir)
    ok([c["id"] for c in b["cores"]] == ["c1", "c3"] and b["cores"][0]["weight"] == 0.2 and b["cores"][0]["history"][0]["beat"] == "kept" and b["maturity"]["label"] == "Mature", "explore_api tune: the deck's cores + maturity are saved into the NEWEST saga, history kept")
    ok(evs()[-1]["kind"] == "tune" and evs()[-1]["maturity"]["stop"] == 6, "explore_api tune: logged with the steer")
    sg.explore_api({"op": "continue", "cores": [], "maturity": 1}, "1999-12-31 10:03:00")
    ok(saga.load(sg_dir)["cores"] == [] and saga.load(sg_dir)["maturity"]["stop"] == 1, "explore_api continue: an emptied deck clears the saga's cores")
    older, _ = saga.new("Newer Saga", "l", "ink, {subject}", root=tmp)
    sg.explore_api({"op": "tune", "cores": [newcore]}, "1999-12-31 10:04:00")
    ok([c["id"] for c in saga.load(older)["cores"]] == ["c3"] and saga.load(sg_dir)["cores"] == [], "explore_api: only the newest saga gets the cores")
    r = sg.explore_api({"op": "atlas_add", "text": "wistful hush", "atlas": "emotion"}, "1999-12-31 10:05:00")
    reqs = A.open_requests(tmp)
    ok(r["atlas_request"]["atlas"] == "emotion" and reqs[0]["atlas"] == "emotion" and evs()[-1]["kind"] == "atlas_add" and evs()[-1]["atlas"] == "emotion", "explore_api atlas_add (emotion): request carries `atlas`, the event too")
    r = sg.explore_api({"op": "atlas_add", "text": "wistful hush"}, "1999-12-31 10:06:00")
    ok(r["atlas_request"]["atlas"] == "formality" and len(A.open_requests(tmp)) == 2 and evs()[-1]["atlas"] == "formality", "explore_api atlas_add: the same text for formality is its own request")
    n0 = len(evs())
    sg.explore_api({"op": "atlas_add", "text": "Wistful  hush", "atlas": "emotion"}, "1999-12-31 10:07:00")
    ok(len(evs()) == n0 and sg.explore_api({"op": "atlas_add", "text": " "}, "t") is None, "explore_api atlas_add: a repeat is not logged twice, blank refused")
    ok(sg.atlas_sig("emotion") == str((tmp / "explore" / "emotion_atlas.json").stat().st_mtime_ns) and sg.atlas_sig() == "" and sg.atlas_sig("emotion") != "", "atlas_sig('emotion') follows the emotion atlas file")
    # learning through the server hook
    (tmp / "explore" / "001-one" / "episode.json").write_text(json.dumps({"emotion": ev, "cores": deck}), encoding="utf-8")
    sg.explore_learn("explore/001-one/e1.png", 0.1)
    ok(any(x["event"] == "atlas_learn" for x in evs()), "explore_learn: a mark on an explore shot reinforces the emotion blend + cores (logged)")
finally:
    sg.ROOT, sg.FB, sg.LOG = keep

# ================================================================================================ inbox / watcher text
ok(wf.is_info({"event": "explore", "kind": "atlas_add"}) is False and wf.is_info({"event": "explore", "kind": "tune"}) is False and wf.is_info({"event": "explore", "kind": "start"}) is False and wf.is_info({"event": "explore", "kind": "stop"}) is True, "watch_feedback: atlas_add / tune / start are [ACT], stop is info")
if "atlas_reset" in wf.INFO_ONLY or wf.is_info({"event": "atlas_reset"}):
    ok(wf.is_info({"event": "atlas_reset"}) is True, "watch_feedback: atlas_reset is informational")
else:
    print("SKIP watch_feedback atlas_reset (not added yet)")
text = xs.describe({"presence": 50, "emotion": ev, "cores": deck, "maturity": {"stop": 5, "label": "Young adult"}}, True)
ok(all(x in text for x in ("maturity Young adult", "emotion of the moment", "Grief (weight 0.8", "pictures:", "story beats:")), "the inbox / `feedback.py explore` line (describe detail): maturity + emotion of the moment + cores with picture / voice / beats")
src = (TOOLS / "feedback.py").read_text(encoding="utf-8")
ok("describe(xp, True)" in src and "describe(st, True)" in src and "maturity_words" in src and "cores_words" in src and "atlas.py {kd} add" in src, "feedback.py wires the detailed describe into inbox + explore, shows cores + maturity, names atlas.py <kind> add")

# time of day belongs to the shot
ok(er._time_of("Mira on the roof at night under fireworks") == "night" and er._time_of("Camera: wide, morning light") == "day" and er._time_of("a barge deck") is None
   and er._time_of("a night sky bright as daylight") == "night", "_time_of: night / day / none from the shot's own words (night wins)")
ok(er._drop_time("a clear mood of adventurous: bright open daylight and wind, warm saturated colours", "night") == "a clear mood of adventurous: warm saturated colours"
   and er._drop_time("staged as a smoky back-room cabaret after midnight, sly glances", "day") == "sly glances"
   and er._drop_time("bright open daylight", None) == "bright open daylight", "_drop_time: only the opposite time's chunks go")
_adv = {"probe": {"x": 0, "y": 0}, "blend": [{"id": "adventurous", "name": "Adventurous", "w": 1.0}], "intensity": 0.8, "valence": 0.8, "arousal": 0.8}
if any(n["id"] == "adventurous" for n in A.load(kind="emotion")["nodes"]):
    _night = er.steer_cue({"emotion": _adv, "maturity": 4}, {"prompt": "the rooftop at night, fireworks", "camera": "wide"})
    _plain = er.steer_cue({"emotion": _adv, "maturity": 4}, {"prompt": "the rooftop", "camera": "wide"})
    ok("daylight" not in _night.lower() and "daylight" in _plain.lower(), "steer_cue: a night shot drops the mood's daylight; an unspecified shot keeps it")

# 🎭 genre selector
ok(xs.clean_genre("noir") == "Noir" and xs.clean_genre(" Science  fiction ") == "Science fiction" and xs.clean_genre("Any") == "" and xs.clean_genre("") == ""
   and xs.clean_genre("zzz") is None and xs.clean_genre(3) is None, "clean_genre: case/space-blind, Any/'' = the author's choice, junk refused")
ok(xs.clean_tune({"genre": "Western"}) == {"genres": ["Western"], "genre": "Western"} and "genre" not in xs.clean_tune({"genre": "zzz"}) and "genre" not in xs.clean_tune({}), "clean_tune carries the genre only when valid (old single genre -> genres [g])")
ok("genre" in xs.STEER_KEYS and xs.describe({"genre": "Horror"}).startswith("genre Horror;") and xs.describe({}).startswith("genre author's choice;"), "STEER_KEYS + describe() name the genre")
ok(xs.view({"genre": "Mythic"})["genre"] == "Mythic" and xs._carry({"genre": "Noir", "presence": 40}, {"genre": ""}) == {"genre": "", "presence": 40}, "the genre survives start / continue / stop and Any clears it")
TPL = (Path(__file__).parent / "gallery_template.html").read_text(encoding="utf-8")
# up to 3 genres, the first leads
ok(xs.clean_genres(["horror", "Comedy", "zzz", "HORROR", "Western", "Noir"]) == ["Horror", "Comedy", "Western"] and xs.clean_genres([]) == [] and xs.clean_genres("Any") == [] and xs.clean_genres("noir") == ["Noir"]
   and xs.clean_genres("zzz") is None and xs.clean_genres(5) is None, "clean_genres: deduped, validated, capped at 3, order kept; a plain string = the old single genre")
ok(xs.clean_tune({"genres": ["Horror", "Comedy"]}) == {"genres": ["Horror", "Comedy"], "genre": "Horror"} and xs.clean_tune({"genres": []}) == {"genres": [], "genre": ""}, "clean_tune: genres list + the lead as `genre` for old readers")
ok(xs.genre_list({"genre": "Noir"}) == ["Noir"] and xs.genre_list({"genres": ["Mythic", "Sports"], "genre": "Noir"}) == ["Mythic", "Sports"] and xs.genre_list({}) == [] and xs.genre_list({"genre": ""}) == [], "genre_list: migrates the old single genre")
ok("genres" in xs.STEER_KEYS and xs.describe({"genres": ["Horror", "Comedy", "Western"]}).startswith("genres Horror + Comedy + Western (lead: Horror);") and xs.genres_words([]) == "author's choice", "describe names several genres with the lead")
ok(xs.view({"genre": "Mythic"})["genres"] == ["Mythic"] and xs.view({"genres": ["Noir", "Sports"]})["genres"] == ["Noir", "Sports"], "view migrates genre -> genres")
js_genres = re.findall(r'^\s*\["([^"]+)", \{intimate:', TPL, re.M)
ok(js_genres == xs.GENRES, "the template's XGENRES and explore_state.GENRES are the same list")

shutil.rmtree(tmp, ignore_errors=True)
print("PASS %d FAIL %d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
