"""Tests for 📖 Nev Novel sagas: saga.py (bible edits, duplicate refusal, chapter validation, thread bookkeeping, setref, bible output),
explore_edit on a saga chapter, saga_render prompt assembly with reference images (dry-run, no GPU), collect_sagas, the server's saga routes.
Run: python tools/test_saga.py     Temp tree only; no GPU, no ComfyUI, nothing real is touched."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_gallery as bg  # noqa: E402
import explore_edit as ee  # noqa: E402
import explore_render as er  # noqa: E402
import explore_state as xs  # noqa: E402
import ref_reroll as rr  # noqa: E402
import saga  # noqa: E402
import saga_render as sr  # noqa: E402
import serve_gallery as sgl  # noqa: E402

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


tmp = Path(tempfile.mkdtemp(prefix="sagatest_"))
STEER = {"presence": 30, "emotion": {"primary": "serenity", "secondary": None, "mix": 0.0, "intensity": 0.6}, "formality": None}
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 32

# ---------------------------------------------------------------------------------------------------------------- new / bible edits
sd, warns = saga.new("The Glass Harbour", "A pilot owes the tide", "ink wash and gouache, soft grain, muted palette, {subject}", root=tmp, world={"setting": "A drowned port city", "tone": "wistful"})
ok(sd.name == "001-the-glass-harbour" and (sd / "saga.json").is_file() and not warns, "new: 001-slug dir + saga.json skeleton")
b = saga.load(sd)
ok(set(b) >= {"id", "title", "logline", "created", "style", "world", "lore", "factions", "places", "cast", "timeline", "threads"} and b["world"]["setting"] == "A drowned port city" and b["cast"] == {}, "skeleton has every bible section")
ok("{subject}" in raises(saga.new, "X", "l", "no slot here", root=tmp) or "{subject}" in (raises(saga.new, "X", "l", "no slot here", root=tmp) or ""), "a style without a {subject} slot is refused")
ok(raises(saga.new, "X", "", "{subject}", root=tmp) is not None, "a logline is required")
_, w2 = saga.new("Second", "l", "painted, {subject}, at night in a rainy city", root=tmp)
ok(len(w2) == 1 and sorted(p.name for p in saga.list_sagas(tmp)) == ["001-the-glass-harbour", "002-second"], "numbering continues; a setting word in the style is flagged")
ok(saga.resolve("current", tmp).name == "002-second" and saga.resolve("1", tmp).name == "001-the-glass-harbour" and saga.resolve("glass", tmp).name == "001-the-glass-harbour", "resolve: current = newest, number, slug fragment")
ok(raises(saga.resolve, "zzz", tmp) is not None, "unknown saga is an error")
shutil.rmtree(tmp / "explore" / "sagas" / "002-second")

saga.add_cast(sd, "Mira", "red scarf, grey eyes, short black hair, weathered flight jacket", "pilot", "dry, quick")
saga.add_cast(sd, "Tobias", "tall, soot-stained apron, bandaged left hand", "engineer", "slow, kind")
saga.add_cast(sd, "Kiri", "a small copper-feathered heron with a cracked beak", "companion", "")
e = raises(saga.add_cast, sd, "mira", "different look")
ok(e and "already exists" in e, "cast: duplicate refused (case-insensitive)")
saga.add_cast(sd, "Mira", "", "ace pilot", "", "injured", update=True)
ok(saga.load(sd)["cast"]["Mira"]["role"] == "ace pilot" and saga.load(sd)["cast"]["Mira"]["status"] == "injured" and saga.load(sd)["cast"]["Mira"]["look"].startswith("red scarf"), "cast --update changes only what is given")
saga.add_cast(sd, "Mira", "", "", "", "alive", update=True)
saga.add_place(sd, "Glass Harbour", "mirrored quays, black water, brass lamps")
saga.add_place(sd, "The Lull Tower", "a leaning signal tower of green copper")
ok("already exists" in (raises(saga.add_place, sd, "glass harbour", "x") or ""), "place: duplicate refused")
saga.add_lore(sd, "The Lull", "Every tenth tide is silent.")
ok("already exists" in (raises(saga.add_lore, sd, "the lull", "x") or ""), "lore: duplicate refused")
saga.add_faction(sd, "Harbour Guild", "keep the sea quiet", "blue coats")
ok("already exists" in (raises(saga.add_faction, sd, "Harbour Guild", "a", "b") or ""), "faction: duplicate refused")
t1 = saga.thread_open(sd, "Who cut the signal cable?")
t2 = saga.thread_open(sd, "What is the Lull hiding?")
ok((t1, t2) == ("t1", "t2") and "already exists" in (raises(saga.thread_open, sd, "who cut the signal cable?") or ""), "thread ids t1, t2; duplicate text refused")
ok("unknown thread" in (raises(saga.thread_close, sd, "t9") or ""), "closing an unknown thread is an error")

# ---------------------------------------------------------------------------------------------------------------- chapter validation
def good_shots():
    return [
        {"prompt": "wide establishing view of the harbour, glass-still water, a small tug approaching", "narration": "The harbour was glass at dawn.", "aspect": "21:9", "place": "Glass Harbour", "noref": True, "with": ["Mira"]},
        {"prompt": "medium shot, Mira at the tug's wheel, scarf in the wind", "with": ["Mira"], "place": "Glass Harbour", "dialogue": [{"who": "Mira", "text": "Quiet, isn't it?"}]},
        {"prompt": "close-up of Tobias wiping his hands", "with": ["Tobias", "Mira"], "dialogue": [{"who": "Tobias", "text": "You are late."}, {"who": "Mira", "text": "The tide was early."}, {"who": "Harbour master", "text": "Both of you, inside.", "off": True}]},
        {"prompt": "the leaning tower against the sky, no one in sight", "nofigure": True, "narration": "Nobody had climbed it in years.", "place": "The Lull Tower"},
        {"prompt": "Kiri the heron on a brass lamp", "with": ["Kiri"], "caption": "A heron watches"},
    ]


spec = {"title": "Arrival", "summary": "Mira reaches the harbour and meets Tobias.", "opens": ["t1"], "closes": [], "shots": good_shots()}
bad = json.loads(json.dumps(spec))
bad["shots"][1]["with"] = ["Mira", "Nobody"]
bad["shots"][2]["dialogue"].append({"who": "Kiri", "text": "caw"})  # Kiri is not in frame
bad["shots"][2]["dialogue"] += [{"who": "Mira", "text": "a"}, {"who": "Mira", "text": "b"}]  # 6 lines
bad["opens"] = ["t7"]
bad["closes"] = ["t2"]  # never opened in a chapter
bad["shots"][3]["prompt"] = ""
bad["shots"][4]["aspect"] = "7:5"
e = raises(saga.write_chapter, sd, bad, steer=STEER, root=tmp) or ""
ok("'Nobody'" in e and "not in the cast" in e, "validation: `with` names a stranger")
ok("'Kiri' is not in frame" in e and "off-screen" in e, "validation: speaker not in frame must be marked off")
ok("max 4" in e, "validation: more than 4 dialogue lines")
ok("unknown thread 't7'" in e and "no prompt" in e and "aspect must be one of" in e, "validation: unknown thread in opens, empty prompt, bad aspect")
ok(not (sd / "ch01").exists() and saga.load(sd)["timeline"] == [], "a refused chapter writes nothing")
e2 = raises(saga.write_chapter, sd, {**spec, "opens": [], "closes": ["t2"]}, steer=STEER, root=tmp) or ""
ok("thread t2" in e2 or "t2" in e2, "closing a thread that is not open yet is refused: " + e2.splitlines()[0][:80])
ok("title" in (raises(saga.write_chapter, sd, {"summary": "s", "shots": good_shots()}, steer=STEER, root=tmp) or ""), "chapter needs a title")

r = saga.write_chapter(sd, spec, steer=STEER, now="1999-12-31 12:00:00", root=tmp)
cd = sd / "ch01"
ep = json.loads((cd / "episode.json").read_text(encoding="utf-8"))
ok(r["chapter"] == "ch01" and r["shots"] == 5 and ep["saga"] == "001-the-glass-harbour" and ep["chapter"] == 1 and ep["id"] == "001-the-glass-harbour/ch01" and ep["status"] == "draft", "chapter written: episode.json with saga + chapter + id")
ok([s["id"] for s in ep["shots"]] == ["e1", "e2", "e3", "e4", "e5"] and ep["shots"][2]["dialogue"][2] == {"who": "Harbour master", "text": "Both of you, inside.", "off": True}, "shots numbered e1.., dialogue kept (off flag)")
ok(ep["shots"][4]["caption"] == "A heron watches" and ep["shots"][0]["caption"] == "The harbour was glass at dawn." and ep["shots"][1]["caption"] == "Quiet, isn't it?", "caption defaults to the narration / first line")
ok(ep["presence"] == 30 and ep["emotion"]["primary"] == "serenity" and ep["style"] == b["style"] and ep["steer_log"] == [] and ep["shots"][0]["noref"] is True and ep["shots"][3]["nofigure"] is True, "explore steer + style copied; noref / nofigure kept")
b = saga.load(sd)
ok(b["cast"]["Mira"]["first_chapter"] == "ch01" and b["cast"]["Tobias"]["first_chapter"] == "ch01" and b["cast"]["Kiri"]["first_chapter"] == "ch01" and b["places"][0]["first_chapter"] == "ch01" and b["places"][1]["first_chapter"] == "ch01", "first_chapter set for cast + places")
ok(b["timeline"] == [{"chapter": "ch01", "event": "Mira reaches the harbour and meets Tobias."}], "timeline entry added")
ok(next(t for t in b["threads"] if t["id"] == "t1")["opened"] == "ch01" and next(t for t in b["threads"] if t["id"] == "t2")["opened"] is None, "t1 is opened by ch01; t2 stays unattached until a chapter lists it")
spec_dup = {**spec, "chapter": 1}
ok("without pictures" in (raises(saga.write_chapter, sd, spec_dup, steer=STEER, root=tmp) or ""), "explicit chapter number that exists: refused unless replace")
saga.write_chapter(sd, {**spec_dup, "title": "Arrival (redo)", "opens": ["t1"]}, replace=True, steer=STEER, root=tmp)
ok(json.loads((cd / "episode.json").read_text(encoding="utf-8"))["title"] == "Arrival (redo)" and len(saga.load(sd)["timeline"]) == 1, "--replace rewrites the chapter and its timeline entry (no duplicate)")

# second chapter: closes t1, status change, new thread inline
spec2 = {"title": "The Cable", "summary": "The cable is found cut from inside.", "event": "Mira finds the cut cable", "opens": [{"id": "t3", "text": "Why was the cable cut from inside the tower?"}], "closes": ["t1"],
         "status_changes": {"Tobias": "injured"}, "shots": good_shots()[:2]}
saga.write_chapter(sd, spec2, steer=STEER, root=tmp)
b = saga.load(sd)
th = {t["id"]: t for t in b["threads"]}
ok(th["t1"]["status"] == "closed" and th["t1"]["closed_in"] == "ch02" and th["t3"]["opened"] == "ch02" and th["t3"]["status"] == "open" and th["t2"]["status"] == "open", "thread bookkeeping: closes -> closed_in, inline opens -> new thread, others untouched")
ok(b["cast"]["Tobias"]["status"] == "injured" and b["timeline"][-1] == {"chapter": "ch02", "event": "Mira finds the cut cable"}, "status_changes applied; custom timeline event")
ok("already closed" in (raises(saga.write_chapter, sd, {**spec2, "title": "T3", "opens": [], "closes": ["t1"]}, steer=STEER, root=tmp) or ""), "closing an already-closed thread is refused")
ok("already" in (raises(saga.write_chapter, sd, {**spec2, "title": "T3", "closes": [], "opens": ["t3"]}, steer=STEER, root=tmp) or ""), "re-opening an open thread from another chapter is refused")
ok(saga.next_chapter(sd) == 3 and saga.current(tmp)["next_name"] == "ch03" and saga.current(tmp)["in_flight"]["chapter"] == "ch02", "current: next chapter number + the chapter in flight")

# ---------------------------------------------------------------------------------------------------------------- setref
(cd / "e2.png").write_bytes(PNG)
(sd / "ch02" / "e1.png").write_bytes(PNG)
ok("no such picture" in (raises(saga.setref, sd, "Mira", "ch01/e9.png", root=tmp) or ""), "setref: missing picture refused")
ok("not in the cast" in (raises(saga.setref, sd, "Nobody", "ch01/e2.png", root=tmp) or "") or "unknown cast" in (raises(saga.setref, sd, "Nobody", "ch01/e2.png", root=tmp) or ""), "setref: unknown character refused")
ok("fractions" in (raises(saga.setref, sd, "Mira", "ch01/e2.png", crop=[0.5, 0.1, 0.51, 0.9], root=tmp) or ""), "setref: a sliver crop is refused")
k, out = saga.setref(sd, "mira", "ch01/e2.png", crop=[0.2, 0.0, 0.8, 0.6], root=tmp)
ok(k == "Mira" and out == "explore/sagas/001-the-glass-harbour/ch01/e2.png" and saga.load(sd)["cast"]["Mira"]["ref"] == out and saga.load(sd)["cast"]["Mira"]["ref_crop"] == [0.2, 0.0, 0.8, 0.6], "setref stores the project-relative path + crop")
saga.setref(sd, "Tobias", "explore/sagas/001-the-glass-harbour/ch02/e1.png", root=tmp)
ok(saga.load(sd)["cast"]["Tobias"]["ref"].endswith("ch02/e1.png") and "ref_crop" not in saga.load(sd)["cast"]["Tobias"], "setref also takes a project path; no crop")
ok("pictures" in (raises(saga.write_chapter, sd, {**spec, "chapter": 1}, replace=True, steer=STEER, root=tmp) or "") or "picture" in (raises(saga.write_chapter, sd, {**spec, "chapter": 1}, replace=True, steer=STEER, root=tmp) or ""), "a chapter with pictures can no longer be replaced")

# ---------------------------------------------------------------------------------------------------------------- bible output
bt = saga.bible_text(sd, brief=True)
ok("Mira [alive]" in bt and "red scarf, grey eyes" in bt and "ref explore/sagas/001-the-glass-harbour/ch01/e2.png" in bt and "NO REF YET" in bt, "bible: cast looks, status, refs, who still needs a ref")
ok("Glass Harbour" in bt and "mirrored quays" in bt and "The Lull" in bt and "t3: Why was the cable cut" in bt and "Closed: t1" in bt, "bible: places, lore, open threads, closed threads")
ok("ch02 The Cable" in bt and "ch01 Arrival (redo)" in bt and "NEXT: ch03" in bt, "bible: chapter summaries + the next chapter")
for n in (3, 4, 5):
    saga.write_chapter(sd, {"title": f"C{n}", "summary": f"summary {n}", "shots": good_shots()[:1]}, steer=STEER, root=tmp)
bt = saga.bible_text(sd, brief=True)
ok("ch05 C5" in bt and "ch03 C3" in bt and "ch02 The Cable" not in bt and "(last 3)" in bt, "--brief lists only the last 3 chapters")
ok("ch02 The Cable" in saga.bible_text(sd, brief=False), "full bible lists them all")

# ---------------------------------------------------------------------------------------------------------------- explore_edit on a saga chapter
c = ee.current(tmp)
ok(c and c["id"] == "001-the-glass-harbour/ch05" and c["unrendered"] == 1, "explore_edit current finds the active saga chapter: %s" % (c or {}).get("id"))
ok(c["dir"].endswith("ch05"), "...with its directory")
e5 = sd / "ch05"
# a chapter with 3 shots, the first rendered
saga.write_chapter(sd, {"title": "C6", "summary": "six", "shots": good_shots()[:3]}, steer=STEER, root=tmp)
e6 = sd / "ch06"
(e6 / "e1.png").write_bytes(PNG)
try:
    ee.edit(e6, [{"prompt": "Nobody stands there", "with": ["Ghost"], "narration": "x"}], from_id="e2")
    errmsg = ""
except ee.EditError as ex:
    errmsg = str(ex)
ok("Ghost" in errmsg, "re-steer of a saga chapter validates `with` names too")
try:
    ee.edit(e6, [{"prompt": "p", "with": ["Mira"], "dialogue": [{"who": "Tobias", "text": "hi"}]}], from_id="e2")
    errmsg = ""
except ee.EditError as ex:
    errmsg = str(ex)
ok("not in frame" in errmsg, "...and dialogue speakers")
res = ee.edit(e6, [{"prompt": "the sea rises", "with": ["Mira"], "narration": "Then the sea turned.", "dialogue": [{"who": "Mira", "text": "Back!"}]}, {"prompt": "the tower falls", "nofigure": True, "narration": "It fell."}],
              from_id=None, steer_state=STEER, reason="turn toward battle", ts="1999-12-31 13:00:00")
ep6 = json.loads((e6 / "episode.json").read_text(encoding="utf-8"))
ok(res["kept"] == ["e1"] and [s["id"] for s in ep6["shots"]] == ["e1", "e2", "e3"] and ep6["shots"][1]["narration"] == "Then the sea turned." and ep6["shots"][1]["dialogue"][0]["who"] == "Mira" and ep6["shots"][2]["nofigure"] is True, "re-steer keeps the rendered shot, replaces the rest, keeps narration/dialogue/with")
ok(ep6["shots"][1]["steer"]["presence"] == 30 and ep6["steer_log"][-1]["reason"] == "turn toward battle", "steer copied + logged")
try:
    ee.edit(e6, [{"prompt": "x", "narration": "y"}], from_id="e1")
    refused = False
except ee.EditError as ex:
    refused = "already have a picture" in str(ex)
ok(refused, "explore_edit refuses a shot that already has a picture")

# ---------------------------------------------------------------------------------------------------------------- render prompt assembly (no GPU)
epr = json.loads((cd / "episode.json").read_text(encoding="utf-8"))
epr["status"] = "draft"
(cd / "episode.json").write_text(json.dumps(epr), encoding="utf-8")
shots = epr["shots"]
ok(sr.root_of(cd) == tmp.resolve(), "saga_render finds the project root from the chapter dir")
bib = sr.load_bible(cd)
p = er.prompt_of(epr, shots[1], True, None, cd)  # e2: Mira has a ref
ok(p.startswith("ink wash and gouache") and "medium shot, Mira at the tug's wheel" in p, "prompt: the saga style with {subject} filled by the shot prompt")
ok("In the scene: Mira (red scarf, grey eyes, short black hair, weathered flight jacket)." in p, "prompt: the character's look repeated verbatim")
ok("Reference image 1 shows Mira: appearance only." in p, "prompt: names the reference image: appearance only")
ok("Setting: Glass Harbour, mirrored quays, black water, brass lamps." in p, "prompt: the place's look from the bible")
ok("Draw each named character exactly as described" in p, "prompt: the consistency clause")
ok("close, quiet" in p or "personal framing" in p, "prompt: the explore steer cue is appended last (presence 30)")
ok(sr.refs_of(bib, shots[1], tmp) == [("explore/sagas/001-the-glass-harbour/ch01/e2.png", "Mira")], "refs: Mira's ref image")
p3 = er.prompt_of(epr, shots[2], True, None, cd)  # Tobias + Mira, order of `with`
ok(sr.refs_of(bib, shots[2], tmp) == [("explore/sagas/001-the-glass-harbour/ch02/e1.png", "Tobias"), ("explore/sagas/001-the-glass-harbour/ch01/e2.png", "Mira")]
   and "Reference image 1 shows Tobias" in p3 and "Reference image 2 shows Mira" in p3 and p3.index("Tobias (tall") < p3.index("Mira (red"), "two characters: refs numbered in `with` order, both looks repeated")
ok("Kiri" not in p3 and "Harbour master" not in p3, "only the characters in frame are described")
ok("Exactly 2 named characters, each appearing once and never duplicated: Tobias, Mira." in p3 and "Exactly" not in p, "two or more in frame: the head count, nobody duplicated; one person: no count")
ok(sr.refs_of(bib, shots[0], tmp) == [] and "Reference image" not in er.prompt_of(epr, shots[0], True, None, cd) and "In the scene: Mira (" in er.prompt_of(epr, shots[0], True, None, cd), "noref shot: the look is described but no reference image is fed")
p4 = er.prompt_of(epr, shots[3], True, None, cd)  # nofigure
ok("There are no people in this image" in p4 and "Draw each named character" not in p4 and "Setting: The Lull Tower" in p4.replace("Setting: The Lull Tower", "Setting: The Lull Tower"), "nofigure shot: run_journey's no-people branch")
p5 = er.prompt_of(epr, shots[4], True, None, cd)  # Kiri, no ref, no look in place
ok("Kiri (a small copper-feathered heron" in p5 and "Reference image" not in p5 and sr.refs_of(bib, shots[4], tmp) == [], "a character without a ref: look only")
cam = er.prompt_of(epr, {**shots[1], "camera": "low angle, 35mm, Mira left third, facing right"}, False, None, cd)
ok(cam.startswith("Camera: low angle, 35mm, Mira left third, facing right.") and "close, quiet" not in cam, "a `camera` field leads; --no-steer drops the cue")
ok("Draw each" in er.prompt_of(epr, shots[1], True, None, cd) and er.prompt_of(epr, shots[1], True) != er.prompt_of(epr, shots[1], True, None, cd), "prompt_of without edir is the plain explore prompt (one-off episodes unchanged)")
b0 = saga.load(sd)
b0["cast"]["Mira"]["look"] = "short silver hair, red scarf"
saga.save(sd, b0)
ok("short silver hair, red scarf" in er.prompt_of(epr, shots[1], True, None, cd), "a bible edit applies at the next shot (looks are read at render time)")
(tmp / "explore" / "sagas" / "001-the-glass-harbour" / "ch01" / "e2.png").unlink()
ok(sr.refs_of(saga.load(sd), shots[1], tmp) == [], "a ref whose file is gone is skipped, not an error")
(tmp / "explore" / "sagas" / "001-the-glass-harbour" / "ch01" / "e2.png").write_bytes(PNG)
j = sr.journey_view(saga.load(sd), epr)
ok(j["ref_crop"] == {"explore/sagas/001-the-glass-harbour/ch01/e2.png": [0.2, 0.0, 0.8, 0.6]} and j["cast"]["Mira"]["ref"].endswith("e2.png") and j["ref_resolution"] == 512, "journey view: ref_crop passed on for build_graph")
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    er.main([str(cd), "--dry-run"])
out = buf.getvalue()
ok("would render e1" in out and "refs:" in out and "Mira" in out and "dry-run: 4 shot(s) to render" in out, "explore_render --dry-run on a saga chapter prints prompts + refs")
ok(er.same_shot({"prompt": "a", "with": ["Mira"]}, {"prompt": "a", "with": ["Mira", "Tobias"]}) is False and er.same_shot({"prompt": "a", "with": ["Mira"]}, {"prompt": "a", "with": ["Mira"]}), "a changed cast list counts as a rewritten shot")
ok(sr.extra_json(epr, shots[2], cd)["refs"][0]["who"] == "Tobias", "eN.json records the references that were fed")

# ---------------------------------------------------------------------------------------------------------------- gallery payload + server routes
(cd / "e1.png").write_bytes(PNG)
sg = bg.collect_sagas(tmp)
g = sg[0] if sg else {}
ok(len(sg) == 1 and g["id"] == "001-the-glass-harbour" and g["title"] == "The Glass Harbour" and len(g["chapters"]) == 6 and g["chapters"][0]["shots"][0]["src"] == "../explore/sagas/001-the-glass-harbour/ch01/e1.png", "collect_sagas: bible + chapters + shot paths")
ok(g["chapters"][0]["shots"][2]["dialogue"][2]["off"] is True and g["chapters"][0]["shots"][0]["narration"] == "The harbour was glass at dawn." and g["chapters"][0]["shots"][1]["with"] == ["Mira"], "collect_sagas: narration, dialogue, with, place")
mira = next(c for c in g["cast"] if c["name"] == "Mira")
ok(mira["ref"] == "../explore/sagas/001-the-glass-harbour/ch01/e2.png" and mira["ref_crop"] == [0.2, 0.0, 0.8, 0.6] and next(c for c in g["cast"] if c["name"] == "Kiri")["ref"] is None, "collect_sagas: cast portraits (None without a ref)")
ok(g["cover"].endswith("ch02/e1.png") or g["cover"].endswith("ch01/e2.png") or g["cover"].endswith("e1.png"), "collect_sagas: cover = the newest rendered picture")
ok([t["id"] for t in g["threads"] if t["status"] == "open"] == ["t2", "t3"] and g["timeline"][0]["chapter"] == "ch01", "collect_sagas: threads + timeline")
ok(bg.collect_explore(tmp) == [], "one-off Explore collector ignores the sagas dir")
old = sgl.ROOT
sgl.ROOT = tmp
try:
    ok(sgl.explore_png(cd / "e2.png") is False, "server: a saga shot without its saved graph is not rerollable yet")
    (cd / "e2.workflow.json").write_text("{}", encoding="utf-8")
    ok(sgl.explore_png(cd / "e2.png") is True, "server: explore_png accepts explore/sagas/NNN/chNN/eN.png with a saved graph")
finally:
    sgl.ROOT = old
ok(rr.is_ref(cd / "e2.png") and rr.is_ref(Path("x") / "explore" / "004-x" / "e1.png") and not rr.is_ref(Path("x") / "evolutions" / "004-x" / "v01" / "e1.png"), "ref_reroll accepts saga shots")
import re  # noqa: E402
src = (TOOLS / "serve_gallery.py").read_text(encoding="utf-8")
pat = re.search(r'ref_reroll\.py"\), key\] if re\.fullmatch\(r"([^"]+)", key\)', src)
ok(pat and re.fullmatch(pat.group(1), "explore/sagas/001-x/ch02/e5.png") and re.fullmatch(pat.group(1), "explore/004-x/e1.png") and not re.fullmatch(pat.group(1), "explore/sagas/001-x/e5.png"), "server: the reroll worker routes saga shots to ref_reroll.py")
ok(any(e["id"] == "001-the-glass-harbour/ch05" for e in xs.episodes(tmp)), "explore_state.episodes lists saga chapters (so a continue request counts as handled)")

# ---------------------------------------------------------------------------------------------------------------- pacing (reading time vs render time)
ok(saga.beat_secs("") == 0 and abs(saga.beat_secs("Hi.") - (0.25 + 2.2)) < 1e-9, "pacing: a short line = min typing + min dwell, like the template's vnBeatMs")
line = "one two three four five six seven eight nine ten"
ok(abs(saga.beat_secs(line) - (len(line) * 0.034 + 0.9 + 10 * 0.33)) < 1e-9, "pacing: typing 34 ms/char + 900 ms + 330 ms/word")
ok(saga.reading_secs({"caption": "x", "hold": 7}) == 7, "pacing: a shot with no text counts its hold")
ok(saga.render_median([30, 50, 40, 115]) == 45 and saga.render_median([]) == saga.PACE_FALLBACK_S, "pacing: median render time (an outlier doesn't skew it), fallback when no times")
thin = [{"narration": "Short."}] * 4
rich = [{"narration": line + " " + line, "dialogue": [{"who": "A", "text": line}] * 4}] * 4
pt, pr = saga.pacing(thin, 40), saga.pacing(rich, 40)
ok(pt["target_s"] == 24 and not pt["ok"] and len(pt["short"]) == 4, "pacing: thin shots fall short of 60% of a 40 s render")
ok(pr["ok"] and not pr["short"], "pacing: narration + 4 lines of ~10 words cover it")

# ---------------------------------------------------------------------------------------------------------------- story lint (entertainment, not just mechanics)
tell = [{"narration": "She had always known the station was strange, the way you know a song. Years of quiet.", "place": f"p{i}"} for i in range(8)]
w_ = saga.story_lint({}, tell, None, None)
ok(any("telling, not showing" in x for x in w_) and any("summary / backstory" in x for x in w_) and any("narration only" in x for x in w_), "story lint: narration-heavy, backstory phrasing, narration-only shots are flagged")
ok(any("montage" in x for x in w_) and any("no `scenes`" in x for x in w_) and any("no `choices`" in x for x in w_) and any("no `hook`" in x for x in w_), "story lint: montage, missing scenes / choices / hook are flagged")
good_shots = [{"place": "bar", "narration": "Rain.", "dialogue": [{"who": "Mira", "text": "Give me the key."}, {"who": "Tobias", "text": "You know what it costs, and you know who pays it, so think hard before you ask me again tonight."}, {"who": "Kiri", "text": "Squawk."}]} for _ in range(8)]
good = {"scenes": [{"title": "The ask", "shots": [1, 4], "goal": "get the key", "obstacle": "Tobias refuses", "turn": "he names a price", "stakes": "the harbour floods"},
                   {"title": "The price", "shots": [5, 8], "goal": "pay without losing Kiri", "obstacle": "the tide", "turn": "Kiri flies off", "stakes": "Kiri"}],
        "choices": [{"who": "Mira", "choice": "trades her compass", "cost": "her way home"}], "hook": "Where did Kiri go?"}
ok(saga.story_lint(good, good_shots, saga.load(sd), 9) == [], "story lint: a chapter with real scenes, a costly choice by the lead, a hook and distinct voices is clean")
ok(any("scene 1" in x and "obstacle" in x for x in saga.story_lint({**good, "scenes": [{**good["scenes"][0], "obstacle": ""}, good["scenes"][1]]}, good_shots, saga.load(sd), 9)), "story lint: a scene without an obstacle is flagged")
ok(any("no costly choice by the lead" in x for x in saga.story_lint({**good, "choices": [{"who": "Tobias", "choice": "x", "cost": "y"}]}, good_shots, saga.load(sd), 9)), "story lint: only side characters choosing is flagged")
same = [{"place": "bar", "dialogue": [{"who": w, "text": "five words in this line"} for w in ("Mira", "Tobias", "Kiri")]} for _ in range(4)]
ok(any("same rhythm" in x for x in saga.story_lint(good, same, saga.load(sd), 9)), "story lint: every speaker in the same rhythm is flagged")

# 🎭 faces: the expression for this exact moment goes into the prompt; the reference never sets the expression; missing face cues are linted
ft = sr.faces_text({"with": ["Mira", "Tobias"], "faces": {"Mira": "eyes wide, jaw tight.", "Tobias": "", "Ghost": "smiling"}})
ok(ft == "Faces (expressions for this exact moment): Mira: eyes wide, jaw tight." and sr.faces_text({"with": ["Mira"]}) == "", "faces_text: only names in frame with a cue, physical terms passed through")
ok("never copy a reference image's facial expression" in sr.CONSISTENCY, "the consistency clause forbids copying a reference's expression")
wsh = [{**s, "with": ["Mira", "Tobias"]} for s in good_shots]
ok(any("no `faces` cue" in x for x in saga.story_lint(good, wsh, saga.load(sd), 9)) and not any("no `faces`" in x for x in saga.story_lint(good, [{**s, "faces": {"Mira": "x"}} for s in wsh], saga.load(sd), 9)), "story lint: character shots without a face cue are flagged; with cues, clean")
ok(not any("no `faces`" in x for x in saga.story_lint(good, [{**s, "camera": "extreme wide shot"} for s in wsh], saga.load(sd), 9)), "story lint: wide shots don't need face cues")
e_, w_ = saga.validate_shot(saga.load(sd), {"prompt": "p", "with": ["Mira"], "faces": {"Tobias": "x"}, "caption": "c"})
ok(any("not in frame" in x for x in w_) and saga.validate_shot(saga.load(sd), {"prompt": "p", "faces": "bad", "caption": "c"})[0], "faces: a name not in frame warns; a non-dict errors")

# ⚙ render knobs (bake-off): saga.json "render" {steps, ref_resolution, max_refs} + per-call overrides
import saga_bench as sbn  # noqa: E402
ok(sbn.parse_variant("B:ref_resolution=512,steps=20") == ("B", {"ref_resolution": 512, "steps": 20}) and sbn.parse_variant("A:") == ("A", {}), "bench: variant parsing")
try:
    sbn.parse_variant("X:cfg=3"); ok(False, "bench: unknown knob refused")
except ValueError:
    ok(True, "bench: unknown knob refused")
ok(sbn.gpu_seconds({"status": {"messages": [["execution_start", {"timestamp": 1000}], ["execution_success", {"timestamp": 43500}]]}}) == 42.5 and sbn.gpu_seconds({}) is None, "bench: GPU seconds from ComfyUI's own stamps")
bk = {"cast": {"A": {"look": "a", "ref": "a.png"}, "B": {"look": "b", "ref": "b.png"}}, "render": {"max_refs": 1, "ref_resolution": 512}}
ok(sr.journey_view(bk)["ref_resolution"] == 512 and sr.journey_view({"cast": {}})["ref_resolution"] == 512, "render knobs: ref_resolution from saga.json render (default 512)")

shutil.rmtree(tmp, ignore_errors=True)
print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
