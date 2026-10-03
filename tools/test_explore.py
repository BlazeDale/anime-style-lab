"""Tests for 🌌 Explore mode: explore_state (timer, expiry, tune), POST/GET /api/explore on a second server instance (port 8794, temp tree),
the [ACT]/info classification, feedback.explore_pending, build_gallery.collect_explore and explore_render --dry-run,
plus the Formality Atlas values (clean_tune / describe / the atlas_add op / learning from ❤ 👎), the image steer cue, explore_edit (re-steering the story in flight)
and the renderer's re-read of episode.json.
Run: python tools/test_explore.py     Temp tree only; no GPU, no ComfyUI, nothing real is touched."""
import functools
import http.server
import json
import shutil
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_gallery as bg  # noqa: E402
import explore_edit as ee  # noqa: E402
import explore_render as er  # noqa: E402
import formality_atlas as fa  # noqa: E402
import explore_state as xs  # noqa: E402
import feedback as fbk  # noqa: E402
import serve_gallery as sg  # noqa: E402
import watch_feedback as wf  # noqa: E402

PASS = FAIL = 0


def ok(c, m):
    global PASS, FAIL
    print(("PASS " if c else "FAIL ") + m)
    PASS += bool(c)
    FAIL += not c


tmp = Path(tempfile.mkdtemp(prefix="exptest_"))
f = tmp / "feedback" / "explore.json"

# ---- state: idle -> start -> expiry on read -> continue -> stop
st = xs.state(f, now=1000)
ok(not st["active"] and st["reason"] == "idle", "no file = idle, not active")
st = xs.start(f, "t", now=1000)
ok(st["active"] and st["left"] == 900 and st["until"] == 1900, "start opens a 15 minute window")
ok(xs.is_active(f, now=1899) and not xs.is_active(f, now=1901), "active until the deadline, then not (computed on read, no thread)")
st = xs.state(f, now=1901)
ok(st["reason"] == "timer" and st["paused"] and st["left"] == 0, "after the deadline: reason timer, paused (needs Continue)")
st = xs.cont(f, "t", now=2000)
ok(st["active"] and st["until"] == 2900 and st["started"] == 2000, "continue after a timeout: a fresh 15 minutes")
st = xs.cont(f, "t", now=2100)
ok(st["until"] == 3000 and st["started"] == 2000, "continue while running keeps the original start, resets the timer")
st = xs.stop(f, "t", now=2200)
ok(not st["active"] and st["reason"] == "stopped" and not st["paused"], "stop: not active, reason stopped")
ok(xs.state(f, now=99999)["reason"] == "stopped", "a stopped state stays stopped (not 'timer')")

# ---- knob + wheel values
ct = xs.clean_tune({"presence": 140, "formality": -4, "emotion": {"primary": "longing", "secondary": "melancholy", "mix": 0.9, "intensity": 1.4}})
ok(ct["presence"] == 100.0 and ct["formality"] == 0.0 and [b["id"] for b in ct["emotion"]["blend"]] == ["longing", "melancholy"] and ct["emotion"]["mix"] == 0.5 and ct["emotion"]["intensity"] == 1.0 and ct["emotion"]["legacy"], "clean_tune clamps presence 0-100, mix 0-0.5, intensity 0-1; an old wheel emotion migrates onto the atlas nodes: %s" % ct["emotion"]["blend"])
ok(xs.clean_tune({"emotion": {"primary": "rage", "secondary": "joy", "intensity": 1}})["emotion"] == fa.neutral("emotion"), "unknown emotion = neutral")
ok(xs.clean_tune({"presence": "x"}) == {} and xs.clean_tune({}) == {} and xs.clean_tune(None) == {}, "junk / missing values are ignored")
ok(len(xs.clean_tune({"emotion": {"primary": "joy", "secondary": "joy", "mix": .3, "intensity": .5}})["emotion"]["blend"]) == 1, "secondary can't equal the primary")
st = xs.start(f, "t", now=5000, tune={"presence": 80, "emotion": {"primary": "awe", "secondary": None, "mix": 0.0, "intensity": 0.5}})
ok(st["presence"] == 80 and st["emotion"]["primary"] == "awe" and st["formality"] is None, "start stores presence + emotion")
st = xs.start(f, "t", now=5000, tune={"presence": 80, "formality": 90, "emotion": {"primary": "awe", "secondary": None, "mix": 0.0, "intensity": 0.5}})
ok(st["formality"] == 90, "start stores formality")
st = xs.cont(f, "t", now=5100)
ok(st["presence"] == 80 and st["emotion"]["primary"] == "awe" and st["formality"] == 90, "continue without values keeps them")
st = xs.tune(f, "t", now=5200, values={"presence": 10})
ok(st["presence"] == 10 and st["emotion"]["primary"] == "awe" and st["until"] == 6000 and st["formality"] == 90, "tune changes values without touching the timer")
st = xs.stop(f, "t", now=5300)
ok(st["presence"] == 10 and st["formality"] == 90, "values survive Stop")
ok(xs.formality_word(0) == "Casual" and xs.formality_word(50) == "Natural" and xs.formality_word(100) == "Formal" and xs.formality_word(25) == "leaning casual", "formality words")
ok(xs.clean_tune({"formality": "x"}) == {} and xs.clean_tune({"formality": 250})["formality"] == 100.0, "formality is clamped, junk ignored")
# the joypad stick object (1999-12-31): {genre, secondary, mix, intensity, level}; centre = Everyday; a number still works
stk = xs.clean_tune({"formality": {"genre": "Martial", "secondary": "Diplomatic", "mix": 0.2, "intensity": 0.5, "level": 23}})["formality"]
ok(stk == {"genre": "Martial", "secondary": "Diplomatic", "mix": 0.2, "intensity": 0.5, "level": 23, "formality_level": 61.5}, "clean_tune keeps the stick object (+ formality_level = 50 + level/2): %s" % stk)
stk = xs.clean_tune({"formality": {"genre": "Courtly", "secondary": "Courtly", "mix": 0.9, "intensity": 3}})["formality"]
ok(stk["secondary"] is None and stk["mix"] == 0 and stk["intensity"] == 1.0 and stk["level"] == 100 and stk["formality_level"] == 100.0, "stick: secondary must differ, mix / intensity clamp, level computed when missing: %s" % stk)
ok(xs.clean_tune({"formality": {"genre": "Bogus", "intensity": 1}}) == {} and xs.clean_tune({"formality": {"genre": "Feral", "intensity": 0}})["formality"] == {"genre": "Everyday", "secondary": None, "mix": 0.0, "intensity": 0.0, "level": 0, "formality_level": 50.0}, "stick: unknown genre ignored, zero push = Everyday")
ok(xs.formality_level_of("Feral", None, 0, 1) == -100 and xs.formality_level_of("Diplomatic", None, 0, 1) == 0 and xs.formality_level_of("Martial", "Diplomatic", 0.2, 0.5) == 23, "level maths matches the page")
ok(xs.formality_words({"genre": "Martial", "secondary": "Diplomatic", "mix": 0.3, "intensity": 0.9}) == "Martial -> Diplomatic 70/30 · strong" and xs.formality_words({"genre": "Everyday", "intensity": 0}) == "Everyday · neutral" and xs.formality_words(90) == "Formal", "formality_words for the stick and for old numbers")
d = xs.describe({"presence": 50, "emotion": None, "formality": {"genre": "Martial", "secondary": "Diplomatic", "mix": 0.3, "intensity": 0.9, "level": 40}})
ok("Martial -> Diplomatic 70/30 · strong" in d and "level +40" in d and "parade grounds" in d, "describe() prints the stick in words with the hint: %s" % d)
ok(xs.presence_word(0) == "Intimate" and xs.presence_word(50) == "Filmic" and xs.presence_word(100) == "Epic" and xs.presence_word(75) == "leaning epic", "presence words")
e = {"primary": "longing", "secondary": "melancholy", "mix": 0.3, "intensity": 0.8}
ok(xs.emotion_words(e) == "melancholic longing · strong (longing -> melancholy 70/30)", "emotion words match the page: " + xs.emotion_words(e))
ok("neutral" in xs.emotion_words(None) and "presence 10 (Intimate)" in xs.describe(xs.state(f, now=5300)) and "formality 90 (Formal)" in xs.describe(xs.state(f, now=5300)), "describe() for the [ACT] output")
ok(xs.EMOTIONS == ["joy", "wonder", "awe", "tension", "dread", "melancholy", "longing", "serenity"], "wheel order = the page's")

# ---- episodes
ed = tmp / "explore" / "001-lighthouse"
ed.mkdir(parents=True)
ep = {"id": "001-lighthouse", "title": "Lighthouse", "topic": "lights at sea", "premise": "p", "style": "soft watercolour, muted palette, {subject}",
      "created": "1999-12-31 12:00:00", "status": "draft", "presence": 20, "formality": 80, "emotion": {"primary": "serenity", "secondary": None, "mix": 0, "intensity": 0.5},
      "shots": [{"id": "e1", "prompt": "a keeper climbs the stairs", "caption": "Up we go.", "hold": 7},
                {"id": "e2", "prompt": "the lamp turns", "caption": "It turns.", "aspect": "9:16"},
                {"id": "e3", "prompt": "dawn on the rock", "caption": "Dawn."}]}
(ed / "episode.json").write_text(json.dumps(ep), encoding="utf-8")
(ed / "e1.png").write_bytes(b"png")
sm = xs.episodes(tmp)
ok(len(sm) == 1 and sm[0]["shots"] == 3 and sm[0]["rendered"] == 1 and sm[0]["id"] == "001-lighthouse", "episodes() summary: %s" % sm)
col = bg.collect_explore(tmp)
ok(len(col) == 1 and col[0]["cover"] == "../explore/001-lighthouse/e1.png" and col[0]["shots"][0]["src"] and col[0]["shots"][1]["src"] is None and col[0]["shots"][1]["aspect"] == "9:16"
   and col[0]["shots"][0]["hold"] == 7 and col[0]["shots"][2]["hold"] == 6 and col[0]["presence"] == 20 and col[0]["formality"] == 80 and col[0]["emotion"]["primary"] == "serenity", "build_gallery.collect_explore payload")

# ---- explore_render: plan + dry-run (no GPU, no graph)
ok([s["id"] for _, s in er.plan(ep, ed)] == ["e2", "e3"] and [s["id"] for _, s in er.plan(ep, ed, ["e3"])] == ["e3"], "plan: shots without a png, --only limits")
ok(er.prompt_of(ep, ep["shots"][0], steer=False) == "soft watercolour, muted palette, a keeper climbs the stairs", "prompt = style with {subject} filled")
ok(er.prompt_of({"style": "ink"}, {"prompt": "a cat"}) == "a cat. ink" and er.prompt_of({}, {"prompt": "a cat"}) == "a cat", "free styles / no style")
ok(er.aspect_name(None) == "16:9 (Widescreen)" and er.aspect_name("9:16") == "9:16 (Portrait Widescreen)" and er.seed_of({}, 3) == 1003 and er.seed_of({"seed": 7}, 3) == 7, "aspect default 16:9, seeds")
import contextlib  # noqa: E402
import io  # noqa: E402
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    er.main([str(ed), "--dry-run"])
out = buf.getvalue()
ok("would render e2" in out and "would render e3" in out and "would render e1" not in out and "dry-run: 2 shot(s)" in out, "explore_render --dry-run lists the missing shots only")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    er.main([str(ed), "--dry-run", "--only", "e3"])
ok("would render e3" in buf.getvalue() and "e2" not in buf.getvalue().split("dry-run")[0], "--only e3")
ok(json.loads((ed / "episode.json").read_text(encoding="utf-8"))["status"] == "draft", "dry-run changes nothing")
er.patch(ed, "e2", src="explore/001-lighthouse/e2.png")
er.patch(ed, status="rendering")
e2 = json.loads((ed / "episode.json").read_text(encoding="utf-8"))
ok(e2["status"] == "rendering" and e2["shots"][1]["src"].endswith("e2.png") and e2["shots"][0]["caption"] == "Up we go.", "patch() updates one shot / the episode and keeps the rest")
ok(er.final_status(e2, ed) == "paused", "episode with missing pngs ends as paused")
(ed / "e2.png").write_bytes(b"x")
(ed / "e3.png").write_bytes(b"x")
ok(er.final_status(e2, ed) == "done", "all pngs present = done")
import ref_reroll as rr  # noqa: E402
ok(rr.is_ref(tmp / "explore" / "001-lighthouse" / "e1.png") and not rr.is_ref(tmp / "evolutions" / "001-x" / "v01" / "a.png"), "ref_reroll accepts explore shots (🎲 reroll)")

# ---- event classification + inbox
ok(not wf.is_info({"event": "explore", "kind": "start"}) and not wf.is_info({"event": "explore", "kind": "continue"}), "watch_feedback: start / continue are [ACT]")
ok(wf.is_info({"event": "explore", "kind": "stop"}) and not wf.is_info({"event": "explore", "kind": "tune"}) and not wf.is_info({"event": "explore", "kind": "atlas_add"}) and wf.is_info({"event": "atlas_learn"}),
   "watch_feedback: stop / atlas_learn are info; tune (= re-steer the story in flight) and atlas_add are [ACT]")
(tmp / "feedback").mkdir(exist_ok=True)
xs.start(f, "t", now=time.time())  # active for real
lg = tmp / "feedback" / "log.jsonl"
lg.write_text(json.dumps({"event": "explore", "kind": "start", "seed": "tides", "ts": "1999-12-31 13:00:00", "presence": 70, "formality": 20,
                          "emotion": {"primary": "awe", "secondary": None, "mix": 0, "intensity": 0.6}}) + "\n", encoding="utf-8")
xp = fbk.explore_pending(tmp)
ok(xp and xp["seed"] == "tides", "inbox: an unhandled start request shows while active")
ok("presence 70 (leaning epic)" in xs.describe(xp) and "formality 20 (leaning casual)" in xs.describe(xp), "the event carries the knob + wheel + fader")
(tmp / "feedback" / "explore_handled.json").write_text(json.dumps({"ts": "1999-12-31 13:05:00"}), encoding="utf-8")
ok(fbk.explore_pending(tmp) is None, "handled once explorereply ran")
(tmp / "feedback" / "explore_handled.json").unlink()
ep["created"] = "1999-12-31 13:01:00"
(ed / "episode.json").write_text(json.dumps(ep), encoding="utf-8")
ok(fbk.explore_pending(tmp) is None, "handled once an episode newer than the request exists")
ep["created"] = "1999-12-31 12:00:00"
(ed / "episode.json").write_text(json.dumps(ep), encoding="utf-8")
ok(fbk.explore_pending(tmp) is not None, "an older episode does not count")
xs.stop(f, "t")
ok(fbk.explore_pending(tmp) is None, "no nag while not exploring")
lg.unlink()

# ---- Formality Atlas values through clean_tune / describe (1999-12-31)
atlas = fa.load()
fv = fa.value_at(atlas, 0.1, 0.6)
c = xs.clean_tune({"formality": fv})["formality"]
ok(c == fv and abs(sum(b["w"] for b in c["blend"]) - 1) < 1e-9 and len(c["blend"]) == 3 and c["genre"] == c["blend"][0]["name"], "clean_tune keeps an atlas value: %s" % xs.formality_words(c))
ok(xs.clean_tune({"formality": {"probe": {"x": 0.2, "y": 0.4}}})["formality"] == fa.value_at(atlas, 0.2, 0.4), "a bare probe is re-derived from the atlas")
c3 = xs.clean_tune({"formality": {"blend": [{"id": "rave", "w": 3}, {"id": "bogus", "w": 1}, {"id": "punk", "w": 1}], "probe": {"x": 0.5, "y": -0.2}}})["formality"]
ok([b["id"] for b in c3["blend"]] == ["rave", "punk"] and [b["w"] for b in c3["blend"]] == [0.75, 0.25] and c3["genre"] == "Rave" and c3["secondary"] == "Punk" and c3["mix"] == 0.25 and c3["level"] == -20, "unknown blend ids are dropped, weights renormalised, level from y")
ok(xs.clean_tune({"formality": {"probe": {"x": "a"}, "blend": [{"id": "nope"}]}}) == {} and xs.clean_tune({"formality": {"probe": {"x": 9, "y": 9}}})["formality"]["probe"] == {"x": 0.707, "y": 0.707}, "junk atlas values are ignored; a far probe clamps to the disc")
ok(fa.value_at(atlas, 0, 0) == fa.neutral() and xs.clean_tune({"formality": fa.neutral()})["formality"]["genre"] == "Everyday", "the centre is the neutral Everyday value")
d = xs.describe({"presence": 50, "emotion": None, "formality": fv})
ok(fa.blend_words(fv) in d and "pictures:" in d and "captions:" in d and "level +60" in d, "describe() prints the blend in words + the top neuron's picture and voice: %s" % d[:160])
ok(xs.formality_words(fv) == fa.blend_words(fv) and xs.formality_words({"genre": "Martial", "intensity": 0.9, "secondary": None}) == "Martial · strong", "formality_words: atlas blend and old objects")

# ---- the image steer cue (hard-wired into explore_render)
tea = next(n for n in atlas["nodes"] if n["id"] == "tea-ceremony")
ep0 = {"presence": 20, "emotion": {"primary": "awe", "secondary": None, "mix": 0, "intensity": 0.3}, "formality": fa.value_at(atlas, tea["x"], tea["y"])}
cue = er.steer_cue(ep0, atlas=atlas)
import re  # noqa: E402
ok("close, quiet, personal framing" in cue.lower() and "a subtle sense of awe, luminous and expansive" in cue and "tatami" in cue and cue.endswith(".") and len(cue.split()) <= 40, "steer cue: presence + emotion + the blend's picture: %s" % cue)
ok(not re.search(r"\b(pan|zoom|dolly|tracking|push in|camera|move|moving)\b", cue, re.I) and "\n" not in cue, "steer cue never mentions camera movement")
ok(er.steer_cue({"presence": 50}) == "Composed classic framing." and er.steer_cue({}) == "", "steer cue: filmic = composed classic framing; nothing to say = empty")
ok(er.presence_cue(10).startswith("very close") and "close, quiet, personal framing" in er.presence_cue(30) and er.presence_cue(35).startswith("fairly close") and er.presence_cue(65).startswith("wide composed")
   and "vast scale, dramatic light, grand composition" in er.presence_cue(75) and er.presence_cue(95).startswith("immense"), "presence wording interpolates at the edges")
ok(er.emotion_cue({"primary": "awe", "intensity": 0.1}) == "" and er.emotion_cue({"primary": None}) == "" and er.emotion_cue(None) == "", "emotion below 0.15 / neutral is skipped")
ok("tinged with melancholy" in er.emotion_cue({"primary": "longing", "secondary": "melancholy", "mix": 0.3, "intensity": 0.8}) and er.emotion_cue({"primary": "longing", "secondary": "melancholy", "mix": 0.3, "intensity": 0.8}).startswith("an overwhelming sense of longing")
   and all(k in er.EMO_CUE for k in xs.EMOTIONS) and er.emotion_cue({"primary": "dread", "intensity": 0.5}).startswith("a clear feeling of dread, ominous"), "emotion blend names both; all 8 emotions have a mood phrase; scaled by intensity")
fb2 = {"blend": [{"id": "rave", "w": 0.6}, {"id": "punk", "w": 0.4}], "intensity": 0.8}
fb3 = {"blend": [{"id": "rave", "w": 0.88}, {"id": "punk", "w": 0.12}], "intensity": 0.8}
ok("warehouse" in er.formality_cue(fb2, atlas) and "safety pins" in er.formality_cue(fb2, atlas) and "safety pins" not in er.formality_cue(fb3, atlas) and "warehouse" in er.formality_cue(fb3, atlas), "formality cue is weighted: a node under 0.2 is left out")
ok(er.formality_cue({"genre": "Everyday", "intensity": 0}, atlas) == "" and er.formality_cue(fa.neutral(), atlas) == "" and er.formality_cue({"blend": [{"id": "rave", "w": 1}], "intensity": 0.1}, atlas) == "", "formality cue skipped for neutral / faint")
ok("parade grounds" in er.formality_cue({"genre": "Martial", "secondary": "Diplomatic", "mix": 0.1, "intensity": 0.9}, atlas) and er.formality_cue(90) == "formal, ceremonial, ordered staging" and er.formality_cue(10).startswith("casual") and er.formality_cue(50) == "", "old stick objects and old numbers still give a cue")
big = {"presence": 95, "emotion": {"primary": "longing", "secondary": "melancholy", "mix": 0.3, "intensity": 0.9}, "formality": {"blend": [{"id": "coronation", "w": 0.4}, {"id": "state-funeral", "w": 0.35}, {"id": "high-mass", "w": 0.25}], "intensity": 0.9}}
ok(len(er.steer_cue(big, atlas=atlas).split()) <= 39 and er.steer_cue(big, atlas=atlas).startswith("Immense scale"), "the cue stays short even with everything on: %d words" % len(er.steer_cue(big, atlas=atlas).split()))
ok("vast scale" in er.steer_cue({"presence": 20}, {"steer": {"presence": 80}}).lower() and er.steer_cue({"presence": 20}, {"steer": {"emotion": None}}).startswith("Close"), "a shot's own `steer` overrides the episode's")
sh = {"prompt": "a cat"}
pc = er.prompt_of({"style": "ink, {subject}", "presence": 80}, sh, atlas=atlas)
ok(pc == "ink, a cat " + er.steer_cue({"presence": 80}) and er.prompt_of({"style": "ink, {subject}", "presence": 80}, sh, steer=False) == "ink, a cat" and er.prompt_of({"style": "ink"}, sh, atlas=atlas) == "a cat. ink", "prompt_of appends the cue after the style; --no-steer / no steer values leave it as before")
(ed / "e3.png").unlink()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    er.main([str(ed), "--dry-run"])
ok("steer cue: " in buf.getvalue() and "Close, quiet, personal framing" in buf.getvalue(), "explore_render --dry-run shows the steer cue")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    er.main([str(ed), "--dry-run", "--no-steer"])
ok("steer cue" not in buf.getvalue(), "--no-steer drops it")
(ed / "e3.png").write_bytes(b"x")

# ---- explore_edit: re-steer the story in flight; the renderer re-reads episode.json
ed2 = tmp / "explore" / "002-flight"
ed2.mkdir(parents=True)
ep2 = {"id": "002-flight", "title": "In flight", "topic": "t", "style": "ink, {subject}", "created": "1999-12-31 14:00:00", "status": "rendering", "presence": 50, "formality": 30,
       "emotion": {"primary": "serenity", "secondary": None, "mix": 0, "intensity": 0.5},
       "shots": [{"id": f"e{i}", "prompt": f"scene {i}", "caption": f"caption {i}"} for i in range(1, 7)]}
(ed2 / "episode.json").write_text(json.dumps(ep2), encoding="utf-8")
for i in (1, 2, 3):
    (ed2 / f"e{i}.png").write_bytes(b"png")
(ed / "episode.json").write_text(json.dumps({**ep, "status": "done"}), encoding="utf-8")
cur = ee.current(tmp)
ok(cur and cur["id"] == "002-flight" and cur["rendered"] == 3 and cur["unrendered"] == 3 and [x["id"] for x in cur["shots"]] == ["e4", "e5", "e6"], "explore_edit current: the newest episode that is not done, with rendered / unrendered counts")
buf = io.StringIO()
ee.ROOT = tmp
with contextlib.redirect_stdout(buf):
    ee.main(["current"])
ee.ROOT = Path(ee.__file__).resolve().parent.parent
ok("002-flight" in buf.getvalue() and "3 rendered / 3 unrendered" in buf.getvalue() and "caption 5" in buf.getvalue(), "explore_edit current prints it")
ep_before = (ed2 / "episode.json").read_bytes()
for bad_from in ("e2", "e1"):
    try:
        ee.edit(ed2, [{"prompt": "x", "caption": "y"}], bad_from)
        refused = None
    except ee.EditError as e:
        refused = str(e)
    ok(refused and "already have a picture" in refused and "e3" in refused and (ed2 / "episode.json").read_bytes() == ep_before, "edit --from %s refuses: rendered shots are listed and nothing is written" % bad_from)
for bad in ([], [{"prompt": "", "caption": "c"}], [{"prompt": "p", "caption": ""}], [{"prompt": "p", "caption": "c", "aspect": "5:7"}]):
    try:
        ee.edit(ed2, bad)
        raised = False
    except ee.EditError:
        raised = True
    ok(raised and (ed2 / "episode.json").read_bytes() == ep_before, "edit rejects bad input %s" % json.dumps(bad)[:40])
try:
    ee.edit(ed2, [{"prompt": "x", "caption": "y"}], "e99")
    raised = False
except ee.EditError as e:
    raised = "unknown shot" in str(e)
ok(raised, "unknown --from shot")
old_shot = er.next_shot(ed2)[2]  # the renderer is about to render e4 (read before the rewrite)
newst = {"presence": 90, "emotion": {"primary": "tension", "secondary": None, "mix": 0, "intensity": 0.6}, "formality": fa.value_at(atlas, 0.0, 0.7)}
res = ee.edit(ed2, [{"prompt": "the cliffs close in", "caption": "Then the weather turned.", "aspect": "21:9"}, {"prompt": "she runs", "caption": "Run."}], None, newst, "love story turns to a chase", ts="1999-12-31 14:30:00")
e2j = json.loads((ed2 / "episode.json").read_text(encoding="utf-8"))
ok([x["id"] for x in e2j["shots"]] == ["e1", "e2", "e3", "e4", "e5"] and e2j["shots"][3]["prompt"] == "the cliffs close in" and e2j["shots"][3]["aspect"] == "21:9" and e2j["shots"][2]["prompt"] == "scene 3"
   and [r["id"] for r in res["removed"]] == ["e4", "e5", "e6"] and [a["id"] for a in res["added"]] == ["e4", "e5"], "edit replaces the unrendered tail; kept shots untouched; new ids continue from the last kept shot")
ok(e2j["presence"] == 90 and e2j["emotion"]["primary"] == "tension" and e2j["formality"]["probe"] == {"x": 0.0, "y": 0.7} and e2j["shots"][4]["steer"]["presence"] == 90 and "steer" not in e2j["shots"][0], "--steer-from-state: the current steer goes into the episode and onto the new shots")
lg2 = e2j["steer_log"][-1]
ok(lg2["ts"] == "1999-12-31 14:30:00" and lg2["from"] == "e4" and lg2["reason"] == "love story turns to a chase" and lg2["removed"] == ["e4", "e5", "e6"] and lg2["added"] == ["e4", "e5"] and lg2["steer"]["presence"] == 90, "steer_log records ts, steer, from, reason, removed, added")
ep_n, i_n, sh_n = er.next_shot(ed2)
ok(sh_n["id"] == "e4" and sh_n["prompt"] == "the cliffs close in" and i_n == 4 and not er.same_shot(old_shot, sh_n) and er.same_shot(sh_n, dict(sh_n)), "the renderer re-reads: the next shot is the REWRITTEN e4; the one rendering during the rewrite no longer matches")
(ed2 / "e4.png").write_bytes(b"old"); (ed2 / "e4.json").write_text("{}", encoding="utf-8")
er.set_aside(ed2, "e4")
ok(not (ed2 / "e4.png").exists() and list((ed2 / "_discarded").glob("e4__*.png")) and er.next_shot(ed2)[2]["id"] == "e4", "a picture rendered from a rewritten shot is set aside, so the id renders again")
ok(er.steer_cue(e2j, e2j["shots"][4], atlas).startswith("Immense scale") or "vast scale" in er.steer_cue(e2j, e2j["shots"][4], atlas).lower(), "the new shots render with the new steer: %s" % er.steer_cue(e2j, e2j["shots"][4], atlas)[:80])
(ed2 / "e4.png").write_bytes(b"x"); (ed2 / "e5.png").write_bytes(b"x")
try:
    ee.edit(ed2, [{"prompt": "x", "caption": "y"}])
    raised = False
except ee.EditError as e:
    raised = "nothing left" in str(e)
ok(raised, "everything rendered = nothing to rewrite")
ep2["status"] = "done"
(ed2 / "episode.json").write_text(json.dumps({**e2j, "status": "done"}), encoding="utf-8")
ok(ee.current(tmp) is None, "explore_edit current: none when every episode is done")
(ed2 / "episode.json").write_text(json.dumps({**e2j, "status": "done", "shots": e2j["shots"][:5]}), encoding="utf-8")

# ---- Apply = a tune = [ACT] "re-steer requested" until explorereply or a steer_log entry
xs.start(f, "t", now=time.time())
lg = tmp / "feedback" / "log.jsonl"
lg.write_text(json.dumps({"event": "explore", "kind": "tune", "ts": "1999-12-31 15:00:00", "presence": 80, "formality": fv, "emotion": None}) + "\n", encoding="utf-8")
xp = fbk.explore_pending(tmp)
ok(xp and xp["kind"] == "tune" and fa.blend_words(fv) in xs.describe(xp), "inbox: an Apply (tune) shows as a re-steer request while exploring: %s" % (xp or {}).get("kind"))
(tmp / "feedback" / "explore_handled.json").write_text(json.dumps({"ts": "1999-12-31 15:05:00"}), encoding="utf-8")
ok(fbk.explore_pending(tmp) is None, "re-steer handled once explorereply ran")
(tmp / "feedback" / "explore_handled.json").unlink()
ok(fbk.explore_pending(tmp) is not None, "(and it is back when the reply file is gone)")
(ed2 / "episode.json").write_text(json.dumps({**e2j, "status": "done", "steer_log": [{"ts": "1999-12-31 15:01:00", "steer": {}, "from": "e4", "reason": "r", "removed": [], "added": []}]}), encoding="utf-8")
ok(fbk.explore_pending(tmp) is None, "re-steer handled once an episode's steer_log has an entry newer than the tune")
(ed2 / "episode.json").write_text(json.dumps({**e2j, "status": "done"}), encoding="utf-8")
lg.write_text(json.dumps({"event": "explore", "kind": "start", "ts": "1999-12-31 15:10:00", "seed": ""}) + "\n" + json.dumps({"event": "explore", "kind": "tune", "ts": "1999-12-31 15:11:00"}) + "\n", encoding="utf-8")
ok(fbk.explore_pending(tmp)["kind"] == "start", "a pending start is shown before a pending tune")
xs.stop(f, "t")
lg.unlink()

# ---- HTTP: a second server instance on the temp tree
fb = tmp / "feedback"
sg.ROOT, sg.FB, sg.LOG, sg.STATE = tmp, fb, fb / "log.jsonl", fb / "state.json"
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8794), functools.partial(sg.Handler, directory=str(tmp)))
threading.Thread(target=srv.serve_forever, daemon=True).start()
f.unlink(missing_ok=True)


def call(method, body=None):
    req = urllib.request.Request("http://127.0.0.1:8794/api/explore", data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        return 200, json.loads(urllib.request.urlopen(req, timeout=20).read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


code, j = call("GET")
ok(code == 200 and j["state"]["active"] is False and j["state"]["reason"] == "idle" and "001-lighthouse" in [e["id"] for e in j["episodes"]], "GET /api/explore: idle state + episode summary")
emo = {"primary": "dread", "secondary": "tension", "mix": 0.25, "intensity": 0.7}
code, j = call("POST", {"op": "start", "seed": "deep sea lights", "presence": 90, "formality": 15, "emotion": emo})
ok(code == 200 and j["state"]["active"] and 890 < j["state"]["left"] <= 900 and j["state"]["presence"] == 90 and j["state"]["formality"] == 15 and j["state"]["emotion"]["secondary"] == "Tension", "POST start: active, ~15 min, knob + wheel + fader stored")
code, j = call("GET")
ok(j["state"]["active"] and j["state"]["emotion"]["blend"][0]["id"] == "dread", "GET shows it live")
code, j = call("POST", {"op": "tune", "presence": 5})
ok(j["state"]["presence"] == 5 and j["state"]["active"] and j["state"]["emotion"]["blend"][0]["id"] == "dread", "POST tune: changes the values only")
code, j = call("POST", {"op": "tune", "formality": {"genre": "Ritual", "secondary": "Martial", "mix": 0.25, "intensity": 0.6, "level": 40}})
ok(j["state"]["formality"]["genre"] == "Ritual" and j["state"]["formality"]["secondary"] == "Martial" and j["state"]["formality"]["intensity"] == 0.6 and j["state"]["presence"] == 5, "POST tune: the stick object is stored")
raw = json.loads(f.read_text(encoding="utf-8"))
raw["until"] = time.time() - 5  # the 15 minutes ran out
f.write_text(json.dumps(raw), encoding="utf-8")
code, j = call("GET")
ok(not j["state"]["active"] and j["state"]["reason"] == "timer" and j["state"]["paused"], "after expiry GET reads active=false, reason timer")
code, j = call("POST", {"op": "continue"})
ok(j["state"]["active"] and j["state"]["presence"] == 5, "POST continue resumes (values kept)")
code, j = call("POST", {"op": "stop"})
ok(not j["state"]["active"] and j["state"]["reason"] == "stopped", "POST stop")
code, j = call("POST", {"op": "bogus"})
ok(code == 400, "unknown op -> 400")
ev = [json.loads(line) for line in (fb / "log.jsonl").read_text(encoding="utf-8").splitlines()]
kinds = [x["kind"] for x in ev if x["event"] == "explore"]
ok(kinds == ["start", "tune", "tune", "continue", "stop"], "log.jsonl: start, tune, tune, continue, stop events: %s" % kinds)
ok(ev[0]["seed"] == "deep sea lights" and ev[0]["presence"] == 90 and ev[0]["formality"] == 15 and ev[0]["emotion"]["blend"][0]["id"] == "dread" and "cores" in ev[0] and "maturity" in ev[0], "the start event carries the seed + knob + emotion + cores + maturity + fader")
ok(sg.explore_png(tmp / "explore" / "001-lighthouse" / "e1.png") is False, "explore_png needs the saved graph next to the picture")
(ed / "e1.workflow.json").write_text("{}", encoding="utf-8")
ok(sg.explore_png(tmp / "explore" / "001-lighthouse" / "e1.png") is True and sg.is_img("explore/001-lighthouse/e1.png") and sg.norm("../explore/001-lighthouse/e1.png?v=2") == "explore/001-lighthouse/e1.png", "server accepts explore shots (marks, reroll)")

# ---- the Atlas over HTTP: GET /api/explore/atlas, the atlas_add op, learning from ❤ / 👎
shutil.copy(fa.ATLAS, tmp / "explore" / "formality_atlas.json")
atp = tmp / "explore" / "formality_atlas.json"
g = json.loads(urllib.request.urlopen("http://127.0.0.1:8794/api/explore/atlas", timeout=20).read())
ok(len(g["nodes"]) >= 48 and len(g["edges"]) >= len(g["nodes"]) and "layout" in g, "GET /api/explore/atlas serves the atlas json")
code, j = call("GET")
sig0 = j["atlas_sig"]
ok(code == 200 and sig0 and j["atlas_requests"] == [], "GET /api/explore carries atlas_sig + the open atlas requests")
n_ev = len((fb / "log.jsonl").read_text(encoding="utf-8").splitlines())
code, j = call("POST", {"op": "atlas_add", "text": "  quiet   library hush "})
ok(code == 200 and j["atlas_request"]["id"] == "a1" and j["atlas_request"]["text"] == "quiet library hush" and j["atlas_request"]["status"] == "open", "POST atlas_add records the typed feeling (whitespace normalised)")
code, j = call("POST", {"op": "atlas_add", "text": "Quiet library hush"})
ev = [json.loads(line) for line in (fb / "log.jsonl").read_text(encoding="utf-8").splitlines()][n_ev:]
ok(j["atlas_request"]["id"] == "a1" and [x["kind"] for x in ev] == ["atlas_add"] and ev[0]["text"] == "quiet library hush", "an identical open request is not logged twice; the event is atlas_add")
code, j = call("POST", {"op": "atlas_add", "text": " "})
ok(code == 400, "an empty feeling -> 400")
code, j = call("GET")
ok([r["text"] for r in j["atlas_requests"]] == ["quiet library hush"] and fa.open_requests(tmp)[0]["id"] == "a1", "open requests listed (the inbox shows them)")
at = fa.load(atp)
nn = fa.add_node(at, "Library hush", "social register", {"rigidity": 0.5, "hierarchy": 0.3, "ritual": 0.4, "ornament": 0.2, "tradition": 0.6, "publicness": 0.3, "intimacy": 0.5, "chaos": 0.0},
                 "a reading room, whispered requests, lamps on long tables", "murmured, courteous, hushed", "claude", ["quiet library"])
fa.save(at, atp)
ok(fa.resolve_request(tmp, "a1", nn["id"]) == 1 and fa.open_requests(tmp) == [], "adding the node closes the request")
code, j = call("GET")
ok(j["atlas_sig"] != sig0 and j["atlas_requests"] == [], "the atlas file changed: atlas_sig moves (the page refetches and draws the new neuron in)")
# learning
fv2 = fa.value_at(fa.load(atp), 0.1, 0.6)
e1 = json.loads((ed / "episode.json").read_text(encoding="utf-8"))
(ed / "episode.json").write_text(json.dumps({**e1, "formality": fv2}), encoding="utf-8")
ids3 = [b["id"] for b in fv2["blend"]]
pairs = [(ids3[i], ids3[j2]) for i in range(3) for j2 in range(i + 1, 3)]
wref = {}
for a_, b_ in pairs:
    e_ = fa.edge_of(fa.load(atp), a_, b_)
    wref[(a_, b_)] = (e_["w"], e_["uses"]) if e_ else (0.2, 0)


def post_fb(action):
    req = urllib.request.Request("http://127.0.0.1:8794/api/feedback", data=json.dumps({"src": "explore/001-lighthouse/e1.png", "action": action}).encode(), method="POST", headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def weights():
    A = fa.load(atp)
    return {(a_, b_): (fa.edge_of(A, a_, b_)["w"], fa.edge_of(A, a_, b_)["uses"]) for a_, b_ in pairs}


clamp = lambda v: round(max(0.1, min(1.0, v)), 3)  # noqa: E731
exp = {k: (clamp(w + 0.1), u + 1) for k, (w, u) in wref.items()}
post_fb("love")
ok(weights() == exp, "❤ on an explore shot strengthens the synapses between its formality blend (+0.1, uses +1): %s" % list(weights().values()))
exp = {k: (clamp(w - 0.1), u + 1) for k, (w, u) in exp.items()}
post_fb("love")  # toggled off = undone
ok(weights() == exp, "un-loving takes it back (-0.1)")
exp = {k: (clamp(w - 0.1), u + 1) for k, (w, u) in exp.items()}
post_fb("nope")
ok(weights() == exp, "👎 weakens them (-0.1)")
exp = {k: (clamp(w + 0.1), u + 1) for k, (w, u) in exp.items()}
post_fb("clear")
ok(weights() == exp and all(0.1 <= w <= 1.0 for w, _ in weights().values()), "clearing the mark restores it; weights stay clamped 0.1-1.0")
evs = [json.loads(line) for line in (fb / "log.jsonl").read_text(encoding="utf-8").splitlines()]
ok(sum(1 for x in evs if x["event"] == "atlas_learn") == 4, "each change logs an informational atlas_learn event")
(ed / "episode.json").write_text(json.dumps({**e1, "formality": 80}), encoding="utf-8")
w0 = json.dumps(fa.load(atp)["edges"])
post_fb("love"); post_fb("love")
ok(json.dumps(fa.load(atp)["edges"]) == w0, "an episode without an atlas blend (old number) teaches the atlas nothing")
srv.shutdown()
# --redo: retire() moves a shot's picture + graph + sidecar to _rerolled/ with one stamp (so 🕘 lists it) and skips shots without a picture
rd = tmp / "redo"
rd.mkdir()
for n in ("e1.png", "e1.workflow.json", "e1.json", "e2.png"):
    (rd / n).write_text("x", encoding="utf-8")
got = er.retire(rd, ["e1", "e3"], stamp="20261002-000000")
ok(got == ["e1"] and not (rd / "e1.png").exists() and (rd / "_rerolled" / "e1__20261002-000000.png").is_file()
   and (rd / "_rerolled" / "e1.workflow__20261002-000000.json").is_file() and (rd / "e2.png").is_file(), "redo: retire moves the picture + graph to _rerolled/, leaves the rest")
shutil.rmtree(tmp, ignore_errors=True)
print("PASS %d FAIL %d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
