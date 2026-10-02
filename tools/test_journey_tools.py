"""Tests for scene_fix.py and animate_chapter.py (pure python, never renders):  .venv/Scripts/python tools/test_journey_tools.py
Works on a synthetic journey built in a temp dir (FIXTURE_*); no project content is read or written."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import animate_chapter as ac  # noqa: E402
import scene_fix as sf  # noqa: E402

JOURNEY_NAME = "001-fixture-journey"
FIXTURE_JOURNEY = {
    "title": "Fixture Journey", "name": "Queen Aurel", "source": "evolutions/001-x/v01/f-fantasy_seed1001.png",
    "style": "Painterly illustration of {subject}.",
    "character": "Queen Aurel, an adult queen in her fifties with long silver braids, a crown of iron leaves and a long green cloak",
    "world": "Harrow, a walled river city of slate roofs and timber-framed houses",
    "cast": {"the marching guard": "ranks of helmeted soldiers in grey tabards",
             "the Stone Colossus": "a giant made of fitted grey boulders",
             "Captain Hale Roan": "the captain of the harbor watch, a broad man in a blue coat with a brass whistle",
             "the townsfolk": "frightened villagers in wool coats", "the watchmen": "city guards in blue tabards"},
    "refs": ["evolutions/001-x/v01/f-fantasy_seed1001.png"], "ref_resolution": 768,
}


def _scene(sid, shot, camera, prompt, caption, with_, place, noref=False, dialogue=None):
    sc = {"id": sid, "shot": shot, "camera": camera, "prompt": prompt, "caption": caption, "with": with_, "place": place, "seed": 1001}
    if noref:
        sc["noref"] = True
    if dialogue:
        sc["dialogue"] = dialogue
    return sc


FIXTURE_CHAPTER = {"title": "One", "direction": "", "summary": "", "choices": [], "scenes": [
    _scene("s1", "extreme wide establishing, from behind", "extreme wide shot from a dark hillside behind her, face NOT visible",
           "a tall queen in a crown of iron leaves watches an army march", "The city had walls and bells.",
           ["the marching guard", "the Stone Colossus"], "a dark hillside at night", noref=True),
    _scene("s2", "telephoto over-the-shoulder", "telephoto over-the-shoulder shot from behind the captain's left shoulder",
           "the siege of the western gatehouse at night", "The gate held for eleven blows.",
           ["Captain Hale Roan", "the Stone Colossus", "the watchmen"], "the battlements of a gatehouse", noref=True,
           dialogue=[{"who": "Captain Hale", "text": "Hold the gate! HOLD IT!", "pos": [54, 10], "tail": "bl"}]),
    _scene("s3", "medium-wide tracking", "medium-wide shot (knees up) at eye level, camera moving alongside her",
           "walking calmly through a burning market square past a stone fountain", "She did not hurry.",
           ["the marching guard", "the townsfolk"], "a market square with a stone fountain"),
    _scene("s4", "insert close-up", "insert extreme close-up from above of two hands only, NO face, NO head",
           "close-up of cobblestones with a fallen soldier's steel gauntlet", "Every one who fell belonged to her.",
           [], "a cobbled lane near the market square", noref=True),
    _scene("s5", "bird's-eye wide", "bird's-eye view from a bell tower looking straight down",
           "from above, dozens of city guards standing back to back", "The watch changed sides.",
           ["the watchmen"], "the cathedral square at night", noref=True),
    _scene("s6", "wide-angle profile standoff", "low-angle wide-angle shot from the cathedral steps, profile standoff",
           "a tense standoff on the cathedral steps between the queen and the captain", "One captain left, and one door.",
           ["Captain Hale Roan", "the townsfolk", "the watchmen"], "the steps of a cathedral at night",
           dialogue=[{"who": "Aurel", "text": "You have so many soldiers, Captain. They are mine now.", "pos": [10, 10], "tail": "br"},
                     {"who": "Captain Hale", "text": "Never.", "pos": [60, 10], "tail": "bl"}]),
]}
FAILS = []
PASSES = 0


def check(name, cond, extra=""):
    global PASSES
    if cond:
        PASSES += 1
        print("PASS", name)
    else:
        FAILS.append(name)
        print("FAIL", name, extra)


def tempcopy():
    tmp = Path(tempfile.mkdtemp(prefix="jtools_"))
    jd = tmp / "journeys" / JOURNEY_NAME
    (jd / "ch01").mkdir(parents=True)
    (jd / "journey.json").write_text(json.dumps(FIXTURE_JOURNEY), encoding="utf-8")
    (jd / "ch01" / "chapter.json").write_text(json.dumps(FIXTURE_CHAPTER), encoding="utf-8")
    sf.ROOT = ac.ROOT = tmp
    return tmp, jd / "ch01"


def run(mod, argv):
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = mod.main(argv)
        return code, out.getvalue()
    except SystemExit as e:
        return e.code, out.getvalue()


def rj(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def scene(ch, sid):
    return next(s for s in rj(ch / "chapter.json")["scenes"] if s["id"] == sid)


def test_scene_fix():
    tmp, ch = tempcopy()
    try:
        before = rj(ch / "chapter.json")
        nrev = len(before.get("revisions", []))
        old_cam = scene(ch, "s3")["camera"]
        # dry run writes nothing
        code, out = run(sf, [str(ch), "s3", "--why", "x", "--camera-append", "NEW BIT", "--dry-run"])
        check("scene_fix dry-run writes nothing", rj(ch / "chapter.json") == before and code == 0 and "NEW BIT" in out)
        # real edit, no render
        code, out = run(sf, [str(ch), "s3", "--why", "hem too short", "--camera-append", "her gown fully covers her feet",
                             "--prompt-append", "high-necked gown.", "--with", "the marching guard", "--noref", "--no-render"])
        s = scene(ch, "s3")
        check("scene_fix camera-append", s["camera"] == old_cam.rstrip(" .") + "; her gown fully covers her feet", s["camera"])
        check("scene_fix prompt-append", s["prompt"].endswith("high-necked gown."))
        check("scene_fix with + noref", s["with"] == ["the marching guard"] and s["noref"] is True)
        revs = rj(ch / "chapter.json")["revisions"]
        check("scene_fix revision logged", len(revs) == nrev + 1 and revs[-1]["scene"] == "s3" and revs[-1]["why"] == "hem too short"
              and len(revs[-1]["date"]) == 10, revs[-1])
        raw = (ch / "chapter.json").read_text(encoding="utf-8")
        check("scene_fix file format", raw.endswith("}\n") and not raw.endswith("\n\n") and "\\u" not in raw)
        code, out = run(sf, [str(ch), "s3", "--why", "face back", "--ref", "--with", "", "--no-render"])
        s = scene(ch, "s3")
        check("scene_fix --ref clears noref, --with '' empties", "noref" not in s and s["with"] == [])
        # replace on camera and prompt
        word = "cobblestones"
        s4 = scene(ch, "s4")
        assert word in s4["prompt"] or word in s4["camera"]
        run(sf, [str(ch), "s4", "--why", "r", "--replace", word, "flagstones", "--no-render"])
        s4b = scene(ch, "s4")
        check("scene_fix --replace hits camera/prompt", word not in s4b["prompt"] + s4b["camera"] and "flagstones" in s4b["prompt"] + s4b["camera"])
        # replace with no match -> error and nothing written
        snap = (ch / "chapter.json").read_text(encoding="utf-8")
        code, out = run(sf, [str(ch), "s4", "--why", "r", "--replace", "zzzz-nope", "y", "--no-render"])
        check("scene_fix --replace error when no match", code not in (0, None) and "zzzz-nope" in str(code) and
              (ch / "chapter.json").read_text(encoding="utf-8") == snap, code)
        # sheet replace
        j0 = rj(ch.parent / "journey.json")
        phrase = j0["character"].split(" ")[3]
        code, out = run(sf, [str(ch), "s3", "--why", "gown", "--sheet-replace", phrase, phrase + " [X]", "--no-render"])
        j1 = rj(ch.parent / "journey.json")
        check("scene_fix --sheet-replace edits journey.json", j1["character"] == j0["character"].replace(phrase, phrase + " [X]"))
        check("scene_fix sheet edit logged in revision", "character sheet" in rj(ch / "chapter.json")["revisions"][-1]["why"])
        code, out = run(sf, [str(ch), "s3", "--why", "g", "--sheet-replace", "zzz-none", "q", "--no-render"])
        check("scene_fix --sheet-replace error when absent", code not in (0, None))
        code, out = run(sf, [str(ch), "s9", "--why", "g", "--camera", "c"])
        check("scene_fix unknown scene errors", code not in (0, None))
        code, out = run(sf, [str(ch), "s3", "--why", "g"])
        check("scene_fix nothing-to-change errors", code not in (0, None))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def add_motions(ch, skip=()):
    d = rj(ch / "chapter.json")
    for s in d["scenes"]:
        if s["id"] in skip:
            continue
        s["motion"] = f"the scene {s['id']} unfolds slowly"
    (ch / "chapter.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return d


def test_animate():
    tmp, ch = tempcopy()
    try:
        code, out = run(ac, [str(ch), "--dry-run"])
        check("animate: missing motion errors listing scenes", code not in (0, None) and all(x in str(code) for x in ("s1", "s6")), code)
        add_motions(ch, skip=("s5",))
        code, out = run(ac, [str(ch), "--dry-run"])
        check("animate: only s5 listed missing", code not in (0, None) and "s5" in str(code) and "s1" not in str(code), code)
        d = add_motions(ch)
        # make s1 motion carry 'silently' and leave s4 without to test the warning
        for s in d["scenes"]:
            if s["id"] == "s1":
                s["motion"] = "the queen silently watches her army march"
            if s["id"] == "s3":
                s["speaker_desc"] = None
                s.pop("speaker_desc")
        (ch / "chapter.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        code, out = run(ac, [str(ch), "--dry-run", "--seed", "1007", "--tag", "reel2"])
        check("animate: dry-run ok", code == 0, out)
        batch = rj(ch / "_reel_batch.json")
        by = {Path(b["image"]).stem: b for b in batch}
        caps = {s["id"]: s["caption"] for s in d["scenes"]}
        check("animate: batch item basics", by["s1"]["image"].endswith("ch01/s1.png") and not Path(by["s1"]["image"]).is_absolute()
              and by["s1"]["engine"] == "fasth3" and by["s1"]["tag"] == "reel2" and by["s1"]["seed"] == 1007
              and by["s1"]["allow_repeat"] is True and by["s1"]["camera"] == "slow push-in")
        check("animate: noref no dialogue -> silent (no line)", "line" not in by["s1"] and by["s1"]["soundscape"] == "the scene")
        check("animate: silent with 'silently' -> no warning for s1", "WARNING s1" not in out)
        check("animate: silent without 'silently' warns", "WARNING s4" in out and "silently" in out.split("WARNING s4")[1].split("\n")[0])
        check("animate: dialogue -> line + cast speaker", by["s2"]["line"] == "Hold the gate! HOLD IT!"
              and by["s2"]["speaker"].startswith("Captain Hale, the captain of the harbor watch"), by["s2"].get("speaker"))
        check("animate: face visible -> narrator with caption", by["s3"]["line"] == caps["s3"] and "unseen narrator" in by["s3"]["speaker"]
              and by["s3"]["voice"] == ac.NARRATOR_VOICE)
        check("animate: multi spoken lines -> first + warning, lead speaker", by["s6"]["line"].startswith("You have so many soldiers")
              and by["s6"]["speaker"] == "Queen Aurel" and "WARNING s6" in out, by["s6"].get("speaker"))
        # forced modes
        run(ac, [str(ch), "--dry-run", "--mode", "narrate", "--scenes", "s1,s3"])
        b = {Path(x["image"]).stem: x for x in rj(ch / "_reel_batch.json")}
        check("animate: --scenes subset + --mode narrate", set(b) == {"s1", "s3"} and b["s1"]["line"] == caps["s1"])
        run(ac, [str(ch), "--dry-run", "--mode", "silent", "--scenes", "s3"])
        b = rj(ch / "_reel_batch.json")[0]
        check("animate: --mode silent on face scene", "line" not in b and b["soundscape"] == "the scene")
        # overrides: narrator_voice, speaker_desc, voice, radio
        j = rj(ch.parent / "journey.json")
        j["narrator_voice"] = "a gravelly old storyteller"
        (ch.parent / "journey.json").write_text(json.dumps(j), encoding="utf-8")
        d = rj(ch / "chapter.json")
        for s in d["scenes"]:
            if s["id"] == "s2":
                s["speaker_desc"] = "the captain on the left third"
                s["voice"] = "a hoarse man's voice"
            if s["id"] == "s5":
                s["dialogue"] = [{"who": "Dispatch", "text": "All units fall back.", "radio": True}]
        (ch / "chapter.json").write_text(json.dumps(d), encoding="utf-8")
        run(ac, [str(ch), "--dry-run"])
        b = {Path(x["image"]).stem: x for x in rj(ch / "_reel_batch.json")}
        check("animate: narrator_voice override", b["s3"]["voice"] == "a gravelly old storyteller")
        check("animate: speaker_desc + voice override", b["s2"]["speaker"] == "the captain on the left third" and b["s2"]["voice"] == "a hoarse man's voice")
        check("animate: radio-only", b["s5"]["speaker"] == ac.RADIO_SPEAKER and b["s5"]["line"] == "All units fall back.")
        code, out = run(ac, [str(ch), "--dry-run", "--scenes", "s7"])
        check("animate: unknown scene errors", code not in (0, None))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_ref_targeting():
    """run_journey.scene_refs / scene_prompt with per-reference notes + ref_for (an egg crop must not reach every scene)"""
    import run_journey as rjn
    lead, egg = "journeys/t/lead.png", "journeys/t/ch01/s3.png"
    j = {"name": "Anselm", "source": lead, "style": "Style of {subject}.", "character": "an old ferryman", "world": "a lake",
         "cast": {"the egg": "a glowing pearl-white egg", "Lina": "a sick girl"}, "refs": [lead, egg],
         "ref_crop": {egg: [0.3, 0.3, 0.6, 0.8]}, "ref_notes": {egg: "the siren's egg: a glowing pearl-white egg"},
         "ref_for": {egg: "the egg"}}
    s_egg = {"id": "s1", "prompt": "he holds it", "with": ["the egg"]}
    s_no = {"id": "s2", "prompt": "he sleeps", "with": ["Lina"]}
    s_noref = {"id": "s3", "prompt": "the lake at dusk", "noref": True, "with": ["the egg"]}
    s_nofig = {"id": "s4", "prompt": "close on the egg", "noref": True, "nofigure": True, "with": ["the egg"]}
    check("refs: egg scene = lead then egg", rjn.scene_refs(j, s_egg) == [(lead, "Anselm"), (egg, "the egg")])
    check("refs: scene without the egg = lead only", rjn.scene_refs(j, s_no) == [(lead, "Anselm")])
    check("refs: noref scene keeps the egg", rjn.scene_refs(j, s_noref) == [(egg, "the egg")])
    p = rjn.scene_prompt(j, s_egg)
    check("prompt: egg ref named with its note", "Reference image 2 shows the siren's egg: a glowing pearl-white egg." in p, p)
    check("prompt: no-egg scene has no reference labels", "Reference image" not in rjn.scene_prompt(j, s_no))
    p = rjn.scene_prompt(j, s_noref)
    check("prompt: noref egg scene calls it reference image 1", "Reference image 1 shows the siren's egg" in p, p)
    p = rjn.scene_prompt(j, s_nofig)
    check("prompt: nofigure scene says (reference image 1)", "the egg is a glowing pearl-white egg (reference image 1)" in p and "no people" in p, p)
    j2 = {**j, "ref_notes": {lead: "face only"}, "ref_for": {}, "refs": [lead]}
    check("prompt: noted lead ref is labelled", "Reference image 1 shows Anselm: face only." in rjn.scene_prompt(j2, s_no))
    j3 = {k: v for k, v in j.items() if k not in ("ref_notes", "ref_for")}
    check("legacy: no notes = every ref is a lead ref, no labels", len(rjn.scene_refs(j3, s_no)) == 2 and "Reference image" not in rjn.scene_prompt(j3, s_no))


def demo():
    """a real --dry-run on a temp copy (motions added there only)"""
    tmp, ch = tempcopy()
    try:
        d = rj(ch / "chapter.json")
        motions = {"s1": "the queen silently watches her army march down the hill",
                   "s2": "the giant's fist slams the gate and the watchmen stagger back",
                   "s3": "she walks calmly on through the burning square as embers drift",
                   "s4": "a hand slowly closes around the fallen gauntlet",
                   "s5": "the dead guards turn their heads in unison and step forward",
                   "s6": "the captain grips his sword as she raises one hand toward the doors"}
        for s in d["scenes"]:
            s["motion"] = motions[s["id"]]
        (ch / "chapter.json").write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(">>> animate_chapter --dry-run (temp copy)")
        ac.main([str(ch), "--dry-run"])
        print(">>> first batch item:")
        print(json.dumps(rj(ch / "_reel_batch.json")[1], indent=2, ensure_ascii=False))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_mv():
    """music-video storyboards: run_journey.load() on a musicvideos/NNN (mv.json instead of journey.json) + tools/mv_analyze.py"""
    import run_journey as rjn
    tmp = Path(tempfile.mkdtemp(prefix="mvtools_"))
    try:
        d = tmp / "musicvideos" / "001-x"
        (d / "sb01").mkdir(parents=True)
        lead = "evolutions/t/v01/lead.png"
        mv = {"title": "T", "name": "", "style": "Style of {subject}.", "character": "a singer in a red coat", "world": "a pier", "cast": {"Drummer": "a tall drummer"},
              "refs": [lead], "ref_crop": {lead: [0.1, 0.1, 0.6, 0.6]}, "ref_notes": {lead: "face only"}, "ref_for": {}, "ref_resolution": 640, "markers": [], "lyrics": "la"}
        (d / "mv.json").write_text(json.dumps(mv), encoding="utf-8")
        (d / "sb01" / "chapter.json").write_text(json.dumps({"title": "sb", "scenes": [{"id": "s1", "prompt": "she sings on the pier", "with": ["Drummer"], "t0": 1, "t1": 4, "lyric": "la"}]}), encoding="utf-8")
        j, ch, params = rjn.load(d / "sb01")
        check("mv load: name defaults to the singer, refs/style/world carried over", j["name"] == "the singer" and j["refs"] == [lead] and j["source"] == lead and j["world"] == "a pier" and j["ref_resolution"] == 640)
        check("mv load: chapter + default params", ch["scenes"][0]["lyric"] == "la" and params["aspect_ratio"].startswith("16:9"))
        sc = ch["scenes"][0]
        check("mv scene_refs: the lead's reference", rjn.scene_refs(j, sc) == [(lead, "the singer")])
        pr = rjn.scene_prompt(j, sc)
        check("mv scene_prompt: singer + cast + setting", "the singer, a singer in a red coat, she sings on the pier" in pr and "Drummer is a tall drummer" in pr and "Reference image 1 shows the singer: face only." in pr, pr)
        mv["name"] = "Mira"; (d / "mv.json").write_text(json.dumps(mv), encoding="utf-8")
        check("mv load: a filled name wins", rjn.load(d / "sb01")[0]["name"] == "Mira")
        mv["refs"] = []; (d / "mv.json").write_text(json.dumps(mv), encoding="utf-8")
        j0 = rjn.load(d / "sb01")[0]
        check("mv without references: no lead reference at all", rjn.scene_refs(j0, sc) == [] and j0["source"] == "")
        # a real journey still loads from journey.json
        jd = tmp / "journeys" / "001-y"; (jd / "ch01").mkdir(parents=True)
        (jd / "journey.json").write_text(json.dumps({"name": "Anselm", "source": lead, "style": "S {subject}", "character": "c", "world": "w"}), encoding="utf-8")
        (jd / "ch01" / "chapter.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
        check("journey load unchanged", rjn.load(jd / "ch01")[0]["name"] == "Anselm")
        check("label: music video vs journey icons", rjn.label(d / "sb01", {"id": "s1"}).startswith("🎵") and rjn.label(jd / "ch01", {"id": "s1"}).startswith("🧭"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # mv_analyze under the helper interpreter (config comfy_python: librosa + soundfile + numpy)
    import math
    import subprocess
    import wave
    from config import COMFY_PYTHON
    probe = subprocess.run([COMFY_PYTHON, "-c", "import librosa, soundfile, numpy"], capture_output=True)
    if probe.returncode:
        check("mv_analyze (skipped: librosa/soundfile not installed)", True)
        return
    tmp = Path(tempfile.mkdtemp(prefix="mvan_"))
    try:
        sr, secs = 22050, 30
        frames = bytearray()
        for i in range(sr * secs):
            t = i / sr
            v = 0.3 * math.sin(2 * math.pi * (220 if t < 15 else 330) * t) + (0.5 * math.sin(2 * math.pi * 1000 * t) if (t % 0.5) < 0.02 else 0)
            frames += int(max(-1, min(1, v)) * 32000).to_bytes(2, "little", signed=True)
        w = tmp / "t.wav"
        with wave.open(str(w), "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); f.writeframes(bytes(frames))
        out = tmp / "a.json"
        r = subprocess.run([str(COMFY_PYTHON), str(Path(__file__).parent / "mv_analyze.py"), str(w), str(out)], capture_output=True, text=True)
        check("mv_analyze runs", r.returncode == 0 and out.exists(), r.stderr[-300:])
        a = json.loads(out.read_text(encoding="utf-8"))
        check("mv_analyze: duration, ~3000 peak buckets in -1..1, beats, tempo",
              abs(a["duration"] - secs) < 0.1 and 2900 <= len(a["peaks"]) <= 3000 and all(-1 <= lo <= hi <= 1 for lo, hi in a["peaks"]) and len(a["beats"]) > 10 and a["tempo"] > 0)
        check("mv_analyze: sections are seconds inside the track", all(0 < t < secs for t in a["sections"]), str(a["sections"]))
        check("mv_analyze: no temp file left", not list(tmp.glob("*.tmp")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_render_helpers():
    """run_video model resolution (stock name -> same-basename file in a sub-folder -> missing), plain_t2i, fix_area.strip_named"""
    import run_video as rvid
    import run_version as rv
    import fix_area as fa
    sub_lora = "Sub\\wan_lora.safetensors"
    listing = {"loras": {sub_lora, "other.safetensors"}, "vae": {"a.safetensors", "alt.safetensors"},
               "diffusion_models": {"x/model.safetensors"}, "checkpoints": set()}
    saved = dict(rvid._INSTALLED)
    rvid._INSTALLED.clear(); rvid._INSTALLED.update(listing)
    try:
        check("resolve_model: stock name kept", rvid.resolve_model("other.safetensors", "loras") == ("other.safetensors", True))
        check("resolve_model: basename found in a sub-folder", rvid.resolve_model("wan_lora.safetensors", "loras") == (sub_lora, True))
        check("resolve_model: missing is reported", rvid.resolve_model("nope.safetensors", "loras") == ("nope.safetensors", False))
        check("resolve_model: unlistable folder is trusted", rvid.resolve_model("anything.safetensors", "checkpoints") == ("anything.safetensors", True))
        rvid._INSTALLED["text_encoders"] = {"real.safetensors"}
        g = {"1": {"class_type": "LoraLoaderModelOnly", "inputs": {"lora_name": "wan_lora.safetensors", "strength_model": 1}},
             "2": {"class_type": "VAELoader", "inputs": {"vae_name": "orig.safetensors"}},
             "3": {"class_type": "UNETLoader", "inputs": {"unet_name": "model.safetensors"}}}
        rvid.resolve_models(g, {"vae": {"orig.safetensors": "alt.safetensors"}})
        check("resolve_models: lora by basename, vae alternate, unet by basename",
              g["1"]["inputs"]["lora_name"] == sub_lora and g["2"]["inputs"]["vae_name"] == "alt.safetensors"
              and g["3"]["inputs"]["unet_name"] == "x/model.safetensors" and rvid.MISSING == [], str(rvid.MISSING))
        g["4"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": "gone.safetensors"}}
        rvid.resolve_models(g, {})
        check("resolve_models: missing text encoder reported", rvid.MISSING == [("text_encoders", "gone.safetensors")]
              and "gone.safetensors" in rvid.missing_message("wan22"))
    finally:
        rvid._INSTALLED.clear(); rvid._INSTALLED.update(saved); rvid.MISSING.clear()
    g = {"k": {"class_type": "KSampler", "inputs": {"latent_image": ["m", 0], "denoise": 0.5}},
         "l": {"class_type": "EmptyLatentImage", "inputs": {}},
         "t": {"class_type": "TextEncodeQwenImage21", "inputs": {"prompt": "In the marked area: a hat. Everything else stays as it is. A girl by a lake."}}}
    rv.plain_t2i(g)
    check("plain_t2i: sampler back on the empty latent, wrapper stripped",
          g["k"]["inputs"]["latent_image"] == ["l", 0] and g["k"]["inputs"]["denoise"] == 1.0 and g["t"]["inputs"]["prompt"] == "A girl by a lake.")
    out = fa.strip_named("A girl in black combat boots, a red scarf and a grey coat. She stands on a pier.", "remove the boots")
    check("strip_named: drops the clause naming the removed thing", "boot" not in out and "scarf" in out and "pier" in out, out)
    check("strip_named: nothing to remove -> unchanged", fa.strip_named("A girl.", "make the sky pink") == "A girl.")


if __name__ == "__main__":
    test_scene_fix()
    test_animate()
    test_ref_targeting()
    test_mv()
    test_render_helpers()
    print(f"\n{PASSES} PASS, {len(FAILS)} FAIL {FAILS}")
    if "--demo" in sys.argv:
        demo()
    sys.exit(1 if FAILS else 0)
