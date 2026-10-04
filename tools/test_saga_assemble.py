#!/usr/bin/env python
"""tests for tools/saga_assemble.py: python tools/test_saga_assemble.py   (needs ffmpeg; synthetic chapter in a temp tree)"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import saga_assemble as S
import mv_assemble as MA

PASS = FAIL = 0
sys.stdout.reconfigure(encoding="utf-8")


def ok(c, msg):
    global PASS, FAIL
    if c:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", msg)


def ff(*a):
    r = subprocess.run([S.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostdin", *a], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


# ---- pure arithmetic
st, tot = S.timeline([3, 5, 5])
ok(st == [0, 2.5, 7.0] and tot == 12.0, f"timeline overlaps pieces by the dissolve: {st} {tot}")
pl = S.plan_hooks([0, 6, 12, 18, 24, 30, 36, 42, 48, 54], 60)
ok(all(S.HOOK_MIN <= b - a <= S.HOOK_MAX for a, b in pl) and pl[0][0] == 0 and pl[-1][1] == 60 and all(x[1] == y[0] for x, y in zip(pl, pl[1:])), f"hooks: 10-30 s, contiguous, whole chapter: {pl}")
pl = S.plan_hooks([0, 50], 60)
ok(pl[0] == (0, 50) and pl[-1][1] == 60, f"a shot longer than the max is taken whole: {pl}")
ok(S.plan_hooks([0], 8) == [(0, 8)], "a short chapter is one hook")
g = S.join_graph([3, 5, 5])
ok("xfade=transition=fade:duration=0.5:offset=2.500" in g and "acrossfade=d=0.5" in g and "[vout]" in g and "[aout]" in g, "join graph: dissolves + closing fade")

# ---- a synthetic chapter: e1 clip (with audio), e2 clip (no audio), e3 still
tmp = Path(tempfile.mkdtemp(prefix="sagaasm_"))
ch = tmp / "explore" / "sagas" / "900-test-saga" / "ch01"
ch.mkdir(parents=True)
(ch.parent / "saga.json").write_text(json.dumps({"title": "Test Saga"}), encoding="utf-8")
(ch / "episode.json").write_text(json.dumps({"title": "Opening", "shots": [{"id": "e1", "narration": "One."}, {"id": "e2"}, {"id": "e3", "hold": 4}, {"id": "e4"}]}), encoding="utf-8")
ff("-f", "lavfi", "-i", "testsrc=s=320x180:r=24:d=5", "-f", "lavfi", "-i", "sine=f=440:d=5", "-shortest", "-pix_fmt", "yuv420p", str(ch / "e1__fasth3-reel_seed1.mp4"))
ff("-f", "lavfi", "-i", "testsrc2=s=320x180:r=24:d=6", "-pix_fmt", "yuv420p", str(ch / "e2__fasth3-reel_seed1.mp4"))
ff("-f", "lavfi", "-i", "color=c=yellow:s=320x180:d=1", "-frames:v", "1", str(ch / "e2.png"))
ff("-f", "lavfi", "-i", "color=c=blue:s=320x180:d=1", "-frames:v", "1", str(ch / "e3.png"))
ff("-f", "lavfi", "-i", "color=c=red:s=320x180:d=1", "-frames:v", "1", str(ch / "e4.png"))
ff("-f", "lavfi", "-i", "color=c=green:s=320x180:d=1", "-frames:v", "1", str(ch / "e9.png"))  # not a shot of the episode: ignored
ps = S.resolve(ch, {})
ok([(p["id"], p["kind"]) for p in ps] == [("e1", "clip"), ("e2", "clip"), ("e3", "still"), ("e4", "still")], f"resolve: clip else still, shot order: {[(p['id'], p['kind']) for p in ps]}")
# a 👎 clip falls back to the still
bad = {MA.rel(ch / "e2__fasth3-reel_seed1.mp4"): {"actions": ["nope"]}}
ok([(p["id"], p["kind"]) for p in S.resolve(ch, bad)][1] == ("e2", "still"), "a 👎 clip -> the still")
ok(S.out_paths(ch, "draft").name == "test-saga-ch01-draft.mp4" and S.out_paths(ch, "suno").name == "test-saga-ch01-suno.mp4", "output names")

# ---- draft build
S.build(ch, "draft", gallery=False, marks={})
d = S.out_paths(ch, "draft")
tl = json.loads(d.with_suffix(".json").read_text(encoding="utf-8"))
ok(d.is_file() and tl["w"] == 960 and tl["h"] == 540 and len(tl["pieces"]) == 4, "draft: 960x540 file + timeline with one piece per shot")
exp = 4.85 + 5.85 + 4 + 6 - 3 * 1.0  # trimmed clips (first 0.15 s dropped) + stills, minus 3 one-second dissolves; the title is over the first shot, no card
ok(abs(S.dur_of(d) - tl["duration"]) < 0.4 and abs(tl["duration"] - exp) < 0.4, f"draft duration ~{exp}: {tl['duration']} / {S.dur_of(d)}")
ok(S.has_audio(d), "draft has an audio track")
st = json.loads((ch / "cut" / "_status.json").read_text(encoding="utf-8"))
ok(st["state"] == "done" and st["target"] == "draft", "status: done")
ok(not any((ch / "cut").glob("sagaasm_*")), "the work folder is cleaned up")
ok(S.master_current(ch, {})[0] is False, "no master yet -> not current")

# ---- master + hooks + suno (hooks / suno build the 1080p master first)
S.build(ch, "hooks", gallery=False, marks={})
m = S.out_paths(ch, "youtube")
ok(m.is_file() and json.loads(m.with_suffix(".json").read_text(encoding="utf-8"))["w"] == 1920, "hooks built the 1920x1080 master first")
ok(S.master_current(ch, {})[0], "master is current right after the build")
hj = json.loads((S.out_paths(ch, "hooks") / "hooks.json").read_text(encoding="utf-8"))
hk = hj["hooks"]
ok(len(hk) >= 1 and all((S.out_paths(ch, "hooks") / h["file"]).is_file() for h in hk) and hk[0]["file"].startswith("01-"), f"hooks cut: {[h['file'] for h in hk]}")
ok(all(abs(S.dur_of(S.out_paths(ch, "hooks") / h["file"]) - (h["t1"] - h["t0"])) < 0.5 for h in hk), "each hook is as long as planned")
os.utime(ch / "e3.png", None)
os.utime(m, (1000, 1000))
ok(not S.master_current(ch, {})[0], "a picture newer than the master -> rebuild")
S.build(ch, "suno", gallery=False, marks={})
sn = S.out_paths(ch, "suno")
ok(sn.is_file() and json.loads(sn.with_suffix(".json").read_text(encoding="utf-8"))["target"] == "suno", "suno build (a tiny master is copied under the cap)")
# captions option
S.build(ch, "draft", captions=True, gallery=False, marks={})
ok(json.loads(d.with_suffix(".json").read_text(encoding="utf-8"))["captions"] is True, "captions flag recorded")
# ---- 🎵 music: a synthetic sine song, clip sound off vs low, looping when the song is shorter than the video
def mean_db(path, t0, t1):
    r = subprocess.run([S.FFMPEG, "-hide_banner", "-nostdin", "-ss", str(t0), "-t", str(t1 - t0), "-i", str(path), "-vn", "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True)
    import re as _re
    mm = _re.search(r"mean_volume: (-?[\d.]+|-inf) dB", r.stderr)
    return float("-inf") if not mm or mm.group(1) == "-inf" else float(mm.group(1))
ff("-f", "lavfi", "-i", "sine=f=220:d=8", "-c:a", "libmp3lame", str(ch / "cut" / "music.mp3"))  # 8 s: shorter than the ~23 s video -> loops
epj = json.loads((ch / "episode.json").read_text(encoding="utf-8"))
epj["reel"] = {"music": {"file": "music.mp3", "name": "t.mp3", "clip_sound": "off", "offset": 0}}
(ch / "episode.json").write_text(json.dumps(epj), encoding="utf-8")
mi = S.music_info(ch)
ok(mi and mi["clip_sound"] == "off" and mi["offset"] == 0, "music_info reads reel.music")
S.build(ch, "draft", gallery=False, marks={})
tl = json.loads(d.with_suffix(".json").read_text(encoding="utf-8"))
ok(tl["music"]["file"] == "music.mp3" and tl["music"]["clip_sound"] == "off", "timeline records the music")
ok(S.has_audio(d) and abs(S.dur_of(d) - tl["duration"]) < 0.5, "music: audio present, length = the video")
ok(mean_db(d, 8, 12) > -40 and mean_db(d, 18, 20) > -40, "music loops: the song is still playing after its 8 s end (mid + late sections audible)")
ok(mean_db(d, 0, 0.3) < mean_db(d, 4, 6) - 6, "music fades in")
ok(mean_db(d, tl["duration"] - 0.5, tl["duration"]) < mean_db(d, 8, 12) - 6, "music fades out at the end")
off_db = mean_db(d, 1.5, 3.5)  # inside e1's clip (sine 440 Hz) while the song plays
epj["reel"]["music"]["clip_sound"] = "full"
(ch / "episode.json").write_text(json.dumps(epj), encoding="utf-8")
S.build(ch, "draft", gallery=False, marks={})
full_db = mean_db(d, 1.5, 3.5)
epj["reel"]["music"]["clip_sound"] = "low"
(ch / "episode.json").write_text(json.dumps(epj), encoding="utf-8")
S.build(ch, "draft", gallery=False, marks={})
low_db = mean_db(d, 1.5, 3.5)
ok(full_db > off_db + 0.8 and off_db - 0.3 <= low_db <= full_db - 0.3, f"clip sound: off {off_db:.1f} dB < low {low_db:.1f} dB < full {full_db:.1f} dB over a clip with sound")
# master_current: a changed song / option makes the master stale
S.build(ch, "youtube", gallery=False, marks={})
ok(S.master_current(ch, {})[0], "master current with the music")
epj["reel"]["music"]["offset"] = 3
(ch / "episode.json").write_text(json.dumps(epj), encoding="utf-8")
os.utime(m, (os.stat(ch / "episode.json").st_mtime + 5,) * 2)  # the master is newer than episode.json: only the music check can flag it
ok("music" in S.master_current(ch, {})[1], "a changed music option -> the master is stale: " + S.master_current(ch, {})[1])
epj["reel"]["music"]["offset"] = 0
(ch / "episode.json").write_text(json.dumps(epj), encoding="utf-8")
os.utime(m, (os.stat(ch / "episode.json").st_mtime + 5,) * 2)
ok(S.master_current(ch, {})[0], "back to the built options -> current again")
os.utime(ch / "cut" / "music.mp3", (os.stat(m).st_mtime + 50,) * 2)
ok("music" in S.master_current(ch, {})[1] or "changed" in S.master_current(ch, {})[1], "a replaced song file -> stale")
os.utime(ch / "cut" / "music.mp3", (os.stat(m).st_mtime - 50,) * 2)
epj.pop("reel"); (ch / "episode.json").write_text(json.dumps(epj), encoding="utf-8")
os.utime(m, (os.stat(ch / "episode.json").st_mtime + 5,) * 2)
ok(not S.master_current(ch, {})[0], "music removed -> the master (built with it) is stale")
# ---- 🎞 immersion pass: pure decisions
import saga_edit as E
ok(E.edit_opts({})["title"] == "over" and E.edit_opts({})["look"] == 0.5 and E.edit_opts({"reel": {"edit": {"look": 9, "title": "card", "letterbox": 2.39, "trim": 0}}}) == {**E.DEFAULTS, "look": 1.0, "title": "card", "letterbox": 2.39, "trim": False}, "edit_opts: defaults, clamps, overrides")
fps = 24
mot = [0.0] * 24 + [3.0] * 48 + [0.0] * 36  # 1 s frozen head, 2 s of motion, 1.5 s frozen tail
ss, to = E.trim_span(mot, fps)
ok(abs(ss - 1.15) < 0.01 and abs(to - 3.0) < 0.3, f"trim_span drops the frozen head (+0.15 s) and tail: {ss} {to}")
ok(E.trim_span([3.0] * 48, fps) == (0.15, 2.0), "trim_span: a clip with motion all through loses only its first 0.15 s")
ok(E.trim_span([0.0] * 48, fps)[1] - E.trim_span([0.0] * 48, fps)[0] >= 1.5, "trim_span never leaves less than 1.5 s")
beats = [i * 0.5 for i in range(0, 80)]  # 120 bpm
bo, dn = E.beat_grid(beats, 4, 0.0, 30)
ok(dn[:3] == [0.0, 2.0, 4.0] and bo[1] == 0.5, "beat_grid: downbeats every 4th beat")
bo2, dn2 = E.beat_grid(beats, 4, 1.0, 30)
ok(bo2[0] == 0.0 and abs(bo2[1] - 0.5) < 1e-6, "beat_grid: shifted by the song start offset")
ext, _ = E.beat_grid(beats, 4, 0.0, 60)
ok(ext[-1] >= 60 and abs(ext[-1] - ext[-2] - 0.5) < 1e-6, "beat_grid: extended periodically past the last beat")
ds = [1.0, 1.0, 1.0]
bnd = [(1.5, 6.0, 4.85), (1.5, 7.0, 5.85), (2.0, 6.0, 4.0), (2.0, 9.0, 6.0)]
lens = E.snap_lengths(bnd, ds, bo, dn)
ss_, cuts, t = 0.0, [], 0.0
for k in range(3):
    cuts.append(round(t + lens[k] - ds[k] / 2, 3))
    t += lens[k] - ds[k]
ok(all(abs(c / 0.5 - round(c / 0.5)) < 1e-6 for c in cuts) and all(bnd[k][0] <= lens[k] <= bnd[k][1] for k in range(3)) and lens[3] == 6.0, f"snap_lengths: every cut lands on a beat, inside the bounds, the last piece untouched: {cuts} {lens}")
ok(any(abs(c / 2 - round(c / 2)) < 1e-6 for c in cuts), "snap_lengths: prefers downbeats where it costs little")
ok(E.snap_lengths(bnd, ds, [], []) == [4.85, 5.85, 4.0, 6.0], "no beats -> natural lengths")
ok(E.snap_lengths([(1.5, 1.6, 1.55), (1.5, 6, 3)], [1.0], [0.2], []) == [1.55, 3], "no beat inside the bounds -> natural length")
ok(E.dissolve_len(0.5) == 1.0 and E.dissolve_len(1.0) == 1.0 and E.dissolve_len(2.0) == 1.2 and E.dissolve_len(0.3) == 0.8 and E.dissolve_len(None) == 1.0 and E.dissolve_len(0.5, 0.7) == 0.7, "dissolve length: ~1 beat, clamped 0.8-1.2 s, 1.0 s without music")
pcs = [{"place": "Quay", "tod": "dusk"}, {"place": "Quay", "tod": "dusk"}, {"place": "Attic", "tod": "night"}, {"place": "Attic", "tod": None}, {"place": "Mill", "tod": "night"}]
trs = E.transitions(pcs)
ok([t["kind"] for t in trs] == ["dissolve", "dip", "dissolve", "dissolve"] and trs[1]["d"] == 0.6, "transitions: a dip only where the place changes AND the time of day jumps")
ok(all(t["kind"] == "dissolve" for t in E.transitions(pcs, dip=False)), "dip can be switched off")
ok(E.clamp_transitions([{"kind": "dissolve", "d": 1.2}], [2.0, 6.0])[0]["d"] == 0.8, "a dissolve never exceeds 40 % of its shorter neighbour")
ok(E.tod("a night market, moonlit") == "night" and E.tod("at sunset on the quay") == "dusk" and E.tod("a quiet room") is None, "time-of-day heuristic")
ids = [f"e{i}" for i in range(1, 25)]
mv = E.kb_moves(ids)
ok(all(a_ != b_ for a_, b_ in zip(mv, mv[1:])) and len(set(mv)) == 4 and mv == E.kb_moves(ids), "Ken Burns: all four moves used, never the same twice in a row, deterministic")
ok(all(E.kb_filter(m_, 100, 960, 540).startswith("zoompan=") for m_ in E.KB_MOVES) and "1.08-0.08" in E.kb_filter("pull", 100, 1, 1), "kb_filter per move")
ok(E.caption_times(6.0, 1.0, 1.0) == (1.6, 4.85) and E.caption_times(6.0, 0.0, 3.0, after=4.9) is None and E.caption_times(2.0, 1.0, 1.0) is None, "caption timing: 0.6 s after the incoming dissolve, gone before the outgoing one, skipped when there is no room")
ok(E.caption_times(8, 1.0, 1.0, after=3.0)[0] == 3.0 and "lt(t,1.60)" in E.fade_alpha(1.6, 4.8), "caption can wait for the title; fade expression")
a_, dim, end = E.title_alpha(8.0)
ok(0 < end <= 5.3 and "min(1,t/0.6)" in dim and E.title_alpha(3.0)[2] <= 3.0, f"title over the first shot: fades inside the piece ({end})")
ok(E.look_filter(0) == "" and "colorbalance" in E.look_filter(0.5) and "noise" in E.look_filter(0.5) and "vignette" in E.look_filter(0.5) and E.look_filter(1) != E.look_filter(0.2), "look filter scales with strength, off at 0")
g = S.join_graph([6, 6, 6], [1.0, 0.6], None, ["dissolve", "dip"], 3.0, 1.5, "eq=contrast=1.02")
ok("transition=fadeblack:duration=0.6" in g and "transition=fade:duration=1.0:offset=5.000" in g and "fade=t=out:st=13.400:d=3.0" in g and "tpad=stop_mode=add:stop_duration=1.5" in g and "eq=contrast=1.02" in g, "join graph: dip + dissolve, 3 s end fade, tail of black, shared look")

# ---- 🎞 immersion pass: a real build with a beat grid (cached analysis), no title card, the music rings on after the picture
import hashlib
mp = ch / "cut" / "music.mp3"
epj["reel"] = {"music": {"file": "music.mp3", "name": "t.mp3", "clip_sound": "off", "offset": 0}, "edit": {"look": 0.5}}
(ch / "episode.json").write_text(json.dumps(epj), encoding="utf-8")
stt = mp.stat()
(ch / "cut" / "music.beats.json").write_text(json.dumps({"key": {"mtime": int(stt.st_mtime), "size": stt.st_size}, "beats": [i * 0.5 for i in range(0, 80)], "tempo": 120.0}), encoding="utf-8")
S.build(ch, "draft", gallery=False, marks={})
tl = json.loads(d.with_suffix(".json").read_text(encoding="utf-8"))
ok(tl["beat_snapped"] and tl["title_s"] is None and tl["edit"]["title"] == "over" and tl["pieces"][0]["t0"] == 0, "build: beats snapped, the first shot starts at 0 (title over it, no card)")
cutsm = [p["t0"] + tl["transitions"][i]["d"] / 2 for i, p in enumerate(tl["pieces"][1:])]
ok(all(abs(c / 0.5 - round(c / 0.5)) < 0.12 for c in cutsm), f"build: every cut lands on a beat (frame rounding aside): {[round(c, 2) for c in cutsm]}")
ok(tl["duration"] == round(tl["picture_s"] + 1.5, 3) and abs(S.dur_of(d) - tl["duration"]) < 0.5, "build: the music tail (1.5 s) rings on after the picture")
ok(mean_db(d, tl["picture_s"] - 2.6, tl["picture_s"] - 2.0) > mean_db(d, tl["duration"] - 0.4, tl["duration"]) + 6, "the music fades out over the tail")
ok(tl["pieces"][2]["move"] in E.KB_MOVES and tl["pieces"][3]["move"] != tl["pieces"][2]["move"], "build: stills record their Ken Burns moves, different in a row")
# captions with overview lines and the title card option
epj["shots"][0]["overview"] = "A line of the story to read on screen."
epj["shots"][2]["overview"] = "Another line, shown later in the chapter."
epj["reel"]["edit"] = {"title": "card", "look": 0}
(ch / "episode.json").write_text(json.dumps(epj), encoding="utf-8")
S.build(ch, "draft", gallery=False, marks={})
tl = json.loads(d.with_suffix(".json").read_text(encoding="utf-8"))
ok(tl["title_s"] == 3.0 and tl["pieces"][0]["t0"] > 2.0 and tl["captions"] is True, "title: card option puts a separate card first")
cp = [p for p in tl["pieces"] if p["caption"]]
ok(cp and all(p["caption"][0] >= 1.5 for p in cp[1:]) and all(p["caption"][1] <= p["dur"] - 0.1 for p in cp), f"captions appear after the dissolve and end before the next one: {[p['caption'] for p in cp]}")
# ---- 🎞 fit to a typed song length (no song file): uniform speed, silent track, exact length; the saga-level music video
ok(E.parse_length("4:05") == 245 and E.parse_length("245") == 245 and E.parse_length("1:02:03") == 3723 and E.parse_length("x") is None and E.parse_length("") is None and E.fmt_len(245) == "4:05", "parse_length / fmt_len")
ok(E.parse_range("ch01-ch03", ["ch01", "ch02", "ch03", "ch04"]) == ["ch01", "ch02", "ch03"] and E.parse_range("ch02", ["ch01", "ch02"]) == ["ch02"] and E.parse_range("ch03-ch01", ["ch01", "ch02", "ch03"]) == ["ch01", "ch02", "ch03"] and E.parse_range("zz", ["ch01"]) == [], "parse_range")
fr = E.fit_report([5.0] * 45, 44.0, 245.0)
ok(fr["ok"] and abs(fr["factor"] - 225 / 289) < 1e-3 and fr["cells"] == 45, "fit_report: factor = natural / (target + dissolves)")
fr = E.fit_report([5.0] * 20, 19.0, 245.0)
ok(not fr["ok"] and fr["factor"] == E.SPEED_MIN and fr["cells_needed"] > 0 and "more cell" in fr["message"] and "too slow" in fr["message"] and "4:05" in fr["message"], f"fit_report: too slow -> how many cells to add: {fr['message']}")
fr = E.fit_report([5.0] * 60, 59.0, 100.0)
ok(not fr["ok"] and fr["factor"] == E.SPEED_MAX and fr["cells_needed"] < 0 and "drop" in fr["message"], f"fit_report: too fast -> how many to drop: {fr['message']}")
for f_ in ("music.mp3", "music.beats.json"):
    (ch / "cut" / f_).unlink(missing_ok=True)
epj.pop("reel", None)
for sh_ in epj["shots"]:
    sh_.pop("overview", None)
(ch / "episode.json").write_text(json.dumps(epj), encoding="utf-8")
S.build(ch, "draft", gallery=False, marks={}, length="0:20")
tl = json.loads(d.with_suffix(".json").read_text(encoding="utf-8"))
ok(abs(S.dur_of(d) - 20.0) <= 0.05 and tl["duration"] == 20.0, f"length-only: the cut is exactly 20 s long ({S.dur_of(d):.3f})")
ok(S.has_audio(d) and mean_db(d, 1, 15) == float("-inf") or mean_db(d, 1, 15) < -80, "length-only: a silent audio track is present")
ok(tl["silent"] and 0.7 <= tl["speed_factor"] <= 1.4 and not tl["beat_snapped"] and tl["target_len"] == 20.0, f"length-only: speed factor {tl['speed_factor']}, silent, no beat snapping")
ok(abs(tl["pieces"][-1]["t0"] + tl["pieces"][-1]["dur"] - 20.0) < 0.3, "length-only: the end fade lands at the target length")
S.build(ch, "youtube", gallery=False, marks={}, length="0:20")
ok(S.master_current(ch, {}, None, "0:20")[0] and "length" in S.master_current(ch, {}, None, "0:25")[1], "master_current: a different typed length makes the master stale")
try:
    S.build(ch, "draft", gallery=False, marks={}, length="0:08")
    ok(False, "a length that needs a factor outside 0.7-1.4 should fail")
except RuntimeError as e_:
    ok("drop" in str(e_) or "too fast" in str(e_), "a hopeless length fails with the cells-to-drop message: " + str(e_))
# saga-level music video over two chapters, length only
ch2 = ch.parent / "ch02"
ch2.mkdir()
(ch2 / "episode.json").write_text(json.dumps({"title": "Second", "shots": [{"id": "e1", "place": "Attic"}, {"id": "e2", "place": "Attic"}]}), encoding="utf-8")
ff("-f", "lavfi", "-i", "testsrc=s=320x180:r=24:d=5", "-pix_fmt", "yuv420p", str(ch2 / "e1__fasth3-a_seed1.mp4"))
ff("-f", "lavfi", "-i", "color=c=green:s=320x180:d=1", "-frames:v", "1", str(ch2 / "e2.png"))
sj = json.loads((ch.parent / "saga.json").read_text(encoding="utf-8"))
sj["mv"] = {"chapters": "ch01-ch02", "length": "0:40", "clip_sound": "off"}
(ch.parent / "saga.json").write_text(json.dumps(sj), encoding="utf-8")
mvd = {"range": "ch01-ch02", "length": None}
S.build(ch.parent, "draft", gallery=False, marks={}, mv=mvd)
md = ch.parent / "cut" / "test-saga-ch01-ch02-draft.mp4"
mt = json.loads(md.with_suffix(".json").read_text(encoding="utf-8"))
ok(md.is_file() and abs(S.dur_of(md) - 40.0) <= 0.05 and mt["range"] == "ch01-ch02" and mt["speed_factor"] and mt["length_arg"] == "0:40", f"music video: one file over both chapters, exactly 40 s, speed {mt['speed_factor']}x recorded")
ok([p["id"] for p in mt["pieces"]] == ["e1", "e2", "e3", "e4", "e1", "e2"] and [p.get("chapter") for p in mt["pieces"]] == ["ch01"] * 4 + ["ch02"] * 2 and mt["title_s"] is None, "music video: every shot of both chapters in order, no title cards")
ok(S.has_audio(md) and mean_db(md, 1, 30) < -80, "music video: silent audio track by default")
ok(any(t["kind"] == "dissolve" for t in mt["transitions"]), "music video: dissolves between cells")
S.build(ch.parent, "hooks", gallery=False, marks={}, mv=mvd)
hdir = ch.parent / "cut" / "hooks-ch01-ch02"
ok((hdir / "hooks.json").is_file() and len(list(hdir.glob("*.mp4"))) >= 2, "music video: hooks cut from the saga master (hooks-ch01-ch02/)")
ok(S.master_current(ch.parent, {}, mvd)[0], "music video: master current")
try:
    S.build(ch.parent, "draft", gallery=False, marks={}, mv={"range": "ch01-ch02", "length": "9:00"})
    ok(False, "a 9:00 length over ~25 s of cells should fail")
except RuntimeError as e_:
    ok("more cell" in str(e_), "music video: too few cells -> says how many to add")
# nothing to build
empty = tmp / "explore" / "sagas" / "901-x" / "ch01"
empty.mkdir(parents=True)
(empty / "episode.json").write_text(json.dumps({"shots": [{"id": "e1"}]}), encoding="utf-8")
try:
    S.build(empty, "draft", gallery=False, marks={})
    ok(False, "an empty chapter should fail")
except RuntimeError:
    ok(json.loads((empty / "cut" / "_status.json").read_text(encoding="utf-8"))["state"] == "error", "empty chapter -> error status")

print(f"PASS {PASS} FAIL {FAIL}")
sys.exit(1 if FAIL else 0)
