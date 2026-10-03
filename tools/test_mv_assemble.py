#!/usr/bin/env python
"""tests for tools/mv_assemble.py: python tools/test_mv_assemble.py   (needs ffmpeg + numpy + Pillow; builds a tiny synthetic music video in a temp folder)"""
import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
import mv_assemble as A

PASS = FAIL = 0


def ok(c, msg):
    global PASS, FAIL
    if c:
        PASS += 1
    else:
        FAIL += 1
        print("FAIL", msg)


def ff(*a):
    r = subprocess.run([A.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostdin", *a], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def wj(p, d):
    Path(p).write_text(json.dumps(d), encoding="utf-8")


# ---- 1. the ❤ rule --------------------------------------------------------------------------------------------------
tmp = Path(tempfile.mkdtemp(prefix="mvasm_"))
A.ROOT = tmp  # everything (marks, audio, the gallery rebuild guard) resolves inside the temp tree
mv = tmp / "musicvideos" / "900-test"
sb = mv / "sb01"
sb.mkdir(parents=True)
(mv / "audio").mkdir()
names = ["s1__fasth3-a_seed1.mp4", "s1__fasth3-b_seed1.mp4", "s1__fasth3-c_seed1.mp4", "s1__fasth3-c_seed1__lipsync.mp4", "s10__fasth3-x_seed1.mp4"]
for i, n in enumerate(names):
    (sb / n).write_bytes(b"x")
    os.utime(sb / n, (1000 + i * 10, 1000 + i * 10))
R = lambda n: A.rel(sb / n)
ok(A.pick_clip(sb, "s1", {}).name == "s1__fasth3-c_seed1.mp4", "newest clip wins, *__lipsync.mp4 ignored, s10 is not s1")
ok(A.pick_clip(sb, "s1", {R(names[1]): {"actions": ["love"]}}).name == names[1], "a ❤ clip beats a newer one")
ok(A.pick_clip(sb, "s1", {R(names[2]): {"actions": ["nope"]}}).name == names[1], "a 👎 clip is skipped")
ok(A.pick_clip(sb, "s1", {R(names[2]): {"actions": ["nope"]}, R(names[0]): {"actions": ["love"]}}).name == names[0], "older ❤ beats newer non-❤")
ok(A.pick_clip(sb, "s1", {R(names[0]): {"action": "love"}}).name == names[0], "legacy single `action` field counts")
ok(A.pick_clip(sb, "s1", {R(n): {"actions": ["nope"]} for n in names[:3]}) is None, "all 👎 -> no clip (storyboard still)")
ok(A.pick_clip(sb, "s7", {}) is None, "no clip for a frame -> None")

# ---- 1b. 📰 headlines (lower thirds) --------------------------------------------------------------------------------------
hch = {"scenes": [{"id": "s1", "t0": 0, "t1": 4, "headline": "Robot dog: 100% chaos"}, {"id": "s2", "t0": 4, "t1": 8}, {"id": "s3", "t0": 8, "t1": 12, "headline": "B", "headline_tag": "LIVE"}]}
htl = {"fps": 24, "total_f": 24 * 12, "output": {}, "pieces": [{"frame": "s1", "a_f": 0}, {"frame": "s2", "a_f": 96}, {"frame": "s3", "a_f": 192}, {"frame": "s1", "a_f": 240, "label": "s1b"}]}
hp = A.headline_plan(htl, hch, {"headline_tag": "SAMPLE NEWS"}, {})
ok([(round(a), round(b), t, g) for a, b, t, g in hp] == [(0, 4, "Robot dog: 100% chaos", "SAMPLE NEWS"), (8, 10, "B", "LIVE"), (10, 12, "Robot dog: 100% chaos", "SAMPLE NEWS")],
   "headline plan: only cuts whose own frame has a headline; scene tag > mv tag; a reused frame shows its own headline: %s" % hp)
ok(A.headline_plan({**htl, "output": {"headlines": False}}, hch, {}, {}) == [], "output.headlines false -> none")
ok(A.headline_plan(htl, {"scenes": [{"id": "s1"}]}, {}, {}) == [], "no scene has a headline -> off by default")
ok(A.headline_plan({**htl, "output": {"headlines": True, "headline_tag": "TAG"}}, {"scenes": [{"id": "s1", "headline": "x"}]}, {}, {})[0][3] == "TAG", "output.headline_tag wins")
ok(A.headline_plan(htl, {"scenes": [{"id": "s1", "headline": "x"}]}, {}, {})[0][3] == "BREAKING", "default tag BREAKING")
hdir = Path(tempfile.mkdtemp(prefix="mvhl_"))
hg, hcur = A.headline_filters(hdir, hp, 1280, 720, "[in]", {})
hs = ";".join(hg)
ok(len(hg) == 3 and hcur == "[hl2]" and hs.startswith("[in]drawbox") and "textfile=hl0.txt" in hs and "0xe8358f" in hs and "0x081642" in hs, "filter graph: one chained block per cut, pink tag + navy bar + drawtext via textfile")
ok((hdir / "hl0.txt").read_text(encoding="utf-8") == "ROBOT DOG: 100% CHAOS" and (hdir / "hlt1.txt").read_text(encoding="utf-8") == "LIVE" and "expansion=none" in hs, "text lives in textfiles (uppercase, no escaping, % safe)")
ok(A.headline_filters(hdir, [], 1280, 720, "[in]", {}) == ([], "[in]"), "no headlines -> empty chain")
shutil.rmtree(hdir, ignore_errors=True)

# ---- 2. timeline math (fake probe) ---------------------------------------------------------------------------------------
chap = {"scenes": [{"id": "s1", "t0": 0, "t1": 4, "preroll": 2.0}, {"id": "s2", "t0": 4, "t1": 8}, {"id": "s3", "t0": 8, "t1": 12}, {"id": "s4", "t0": 12, "t1": 16}]}
for n, eng, extra in [("s1__fasth3-i_seed1", "fasth3", {"song_audio": {"t0": 0, "preroll": 2.0}}), ("s2__ltxia2v-s_seed1", "ltxia2v", {"song_audio": {"t0": 5.0, "seconds": 2.0}}),
                      ("s3__fasth3-m_seed1", "fasth3", {"reversed": True}), ("s4__fasth3-m_seed1", "fasth3", {})]:
    (sb / f"{n}.mp4").write_bytes(b"x")
    wj(sb / f"{n}.json", {"engine": eng, **extra})
FR = {"s1": 7 * 24, "s2": 48, "s3": 130, "s4": 60}  # s1 window 6 s = 144 frames: a 168-frame clip trims; s3 window 96: 130 trims from its tail (reversed); s4 window 96: 60 slows
probe = lambda p: {"frames": FR[Path(p).name.split("__")[0]], "fps": 24.0, "w": 10, "h": 10, "dur": 1, "audio": False}
edit = {"output": {"fps": 24, "preroll": 2.0, "w": 320, "h": 180},
        "cuts": [{"frame": "s1", "look": "now", "in": {"type": "cut"}}, {"frame": "s2", "look": "now", "in": {"type": "cut"}},
                 {"frame": "s3", "look": "memory", "in": {"type": "dissolve", "dur": 1.0}}, {"frame": "s4", "look": "memory", "in": {"type": "fadeblack", "dur": 0.5}}]}
tl = A.resolve(edit, chap, mv, {}, probe_fn=probe, song_dur=16.0)
pc = tl["pieces"]
ok(tl["total_f"] == (2 + 16) * 24 and pc[0]["a_f"] == 0, "video = preroll + song; the first piece starts at video 0 (the preroll)")
ok(pc[1]["a_f"] == (2 + 4) * 24 and pc[2]["a_f"] == (2 + 8) * 24 and pc[3]["a_f"] == (2 + 12) * 24, "every piece starts at song time + preroll")
ok(pc[0]["b_f"] == pc[1]["a_f"] and pc[-1]["b_f"] == tl["total_f"], "windows tile the timeline")
ok(pc[1]["ext_f"] == 24 and pc[2]["ext_f"] == 12 and pc[3]["ext_f"] == 0, "a transition of d frames extends the OUTGOING piece by d (dissolve 1.0 s = 24, fadeblack 0.5 s = 12)")
ok(pc[2]["in"]["d_f"] == 24 and pc[1]["in"]["d_f"] == 0 and pc[3]["in"]["type"] == "fadeblack", "incoming side records the overlap")
ok(sum(p["n_f"] for p in pc) - sum(p["in"]["d_f"] for p in pc) == tl["total_f"], "sum of rendered frames minus the xfade overlaps = total video frames (song sync survives the blends)")
ok(all(pc[i]["a_f"] + pc[i]["n_f"] - pc[i + 1]["in"]["d_f"] == pc[i + 1]["a_f"] for i in range(3)), "xfade offset lands each incoming piece on its own start frame")
ok(pc[0]["kind"] == "clip" and pc[0]["fit"].startswith("trim") and pc[0]["speed"] == 1.0, "a long non-singing clip is trimmed")
s = pc[1]
ok(s["kind"] == "sing" and s["clip_f0"] == (2 + 5.0) * 24 and s["pre_f"] == 24 and s["s0"] == 0 and s["speed"] == 1.0, "singing clip: frame 0 at song t0 (+preroll), window start filled by holding its first frame, never stretched")
ok("hold-first" in s["fit"] and "hold-last" in s["fit"] and abs(s["sync_t"] - 7.0) < 1e-9, "singing fit string + sync time")
ok(s["clip_f0"] + s["clip_frames"] + 24 >= s["a_f"] + s["n_f"] - 72, "singing clip placement is independent of the window")
ok(pc[2]["s0"] == 130 - 96 and pc[2]["reversed"], "a reversed clip longer than its window keeps its TAIL (it must end on the next frame)")
ok(pc[3]["fit"] == "slow" or pc[3]["fit"].startswith("slow"), "a short clip slows down first")
ok(abs(pc[3]["speed"] - 1.25) < 1e-6 and "hold-last" in pc[3]["fit"], "slowdown capped at 1.25x, then the last frame is held (60 frames x 1.25 = 75 < 96)")
FR["s4"] = 90
pc = A.resolve(edit, chap, mv, {}, probe_fn=probe, song_dur=16.0)["pieces"]
ok(pc[3]["fit"] == "slow" and abs(pc[3]["speed"] - 96 / 90) < 1e-3, "slow exactly to the window when within 1.25x")
edit2 = json.loads(json.dumps(edit))
edit2["cuts"][1]["in"] = {"type": "zoomy-nonsense", "dur": 1}
ok(A.resolve(edit2, chap, mv, {}, probe_fn=probe, song_dur=16.0)["pieces"][1]["in"]["type"] == "cut", "unknown transition falls back to a cut")
edit3 = json.loads(json.dumps(edit))
edit3["cuts"][1]["clip"] = "nothing.mp4"
ok(A.resolve(edit3, chap, mv, {}, probe_fn=probe, song_dur=16.0)["pieces"][1]["kind"] == "still", "a missing clip falls back to the storyboard still")

# ---- 3. --plan from a fake stems.json ------------------------------------------------------------------------------------
chap2 = {"scenes": [{"id": "s1", "t0": 0, "t1": 5, "preroll": 3.0, "place": "the side table", "cut_why": "intro"},
                    {"id": "s2", "t0": 5, "t1": 10, "place": "the stage", "with": ["the microphone"], "cut_why": "verse"},
                    {"id": "s3", "t0": 10, "t1": 15, "prompt": "a warm faded flashback of a balcony", "with": ["Bob"], "cut_why": "flashback"},
                    {"id": "s4", "t0": 15, "t1": 20, "place": "the stage", "cut_why": "band slams back: hard cut"},
                    {"id": "s5", "t0": 20, "t1": 25, "place": "the stage", "cut_why": "breakdown"},
                    {"id": "s6", "t0": 25, "t1": 30, "place": "the stage", "lyric": "(la la la)", "cut_why": "the drop"},
                    {"id": "s7", "t0": 30, "t1": 35, "place": "the stage", "lyric": "(instrumental)", "cut_why": "outro"}]}
stems = {"tempo": 120, "downbeats": [25.0, 27.0, 29.0], "moments": [{"t": 20.1, "t1": 23, "kind": "breakdown"}, {"t": 25.0, "kind": "drop"}]}
chap2["memory_cast"] = ["bob"]
pl = A.plan_edit(chap2, stems)
ty = {c["frame"]: c["in"]["type"] for c in pl["cuts"]}
ok(ty == {"s1": "cut", "s2": "cut", "s3": "dissolve", "s4": "cut", "s5": "fadeblack", "s6": "flash", "s7": "cut"}, "plan transitions from the music: " + str(ty))
lk = {c["frame"]: c["look"] for c in pl["cuts"]}
ok(lk["s3"] == "memory" and lk["s2"] == "now" and lk["s4"] == "now", "flashback / memory_cast scenes are MEMORY, the stage is NOW")
ok(pl["cuts"][0]["fx"] == ["dust"] and pl["cuts"][-1]["fx"] == ["dust"] and not pl["cuts"][3]["fx"], "dust on the first and last frame only")
ok(pl["output"]["preroll"] == 3.0 and pl["output"]["w"] == 1920 and pl["output"]["lyrics"] is False, "output defaults, preroll from the chapter")
ok(pl["overlays"] and pl["overlays"][0]["type"] == "beatflash" and pl["overlays"][0]["t0"] == 25.0 and pl["overlays"][0]["t1"] == 30, "beatflash from the drop to the last sung frame")
ok("hard cut" in pl["cuts"][3]["why"] and all(c["why"] for c in pl["cuts"]) and pl["cuts"][2]["in"]["dur"] >= 0.6, "every cut has a why; dissolves are 0.6-1.0 s")
ok(not A.plan_edit(chap2, None)["overlays"], "no stems -> no drop -> no beatflash")

# ---- 4. a real tiny assembly ------------------------------------------------------------------------------------------
W, H = 320, 180
song = mv / "audio" / "song.wav"
ff("-f", "lavfi", "-i", "sine=f=440:d=8:r=48000", "-ac", "2", str(song))
wj(mv / "mv.json", {"title": "T", "audio": "x"})
mvj = json.loads((mv / "mv.json").read_text()); mvj["audio"] = A.rel(song); wj(mv / "mv.json", mvj)
wj(mv / "audio" / "lyrics_timing.json", {"lines": [{"text": "hello there", "t0": 1.0, "t1": 2.5, "conf": 0.9}, {"text": "weak line", "t0": 3.0, "t1": 4.0, "conf": 0.2}]})
wj(mv / "audio" / "stems.json", {"tempo": 120, "downbeats": [5.0, 6.0, 7.0], "moments": []})
chap3 = {"scenes": [{"id": "s1", "t0": 0, "t1": 3, "preroll": 1.0, "cut_why": "a"}, {"id": "s2", "t0": 3, "t1": 5.5, "cut_why": "b"}, {"id": "s3", "t0": 5.5, "t1": 8, "cut_why": "c"}]}
for f in list((sb).glob("*")):
    f.unlink()
wj(mv / "sb01" / "chapter.json", chap3)
ramp = "color=c=gray:s=320x180:r=24:d=2,format=gray,geq=lum='16+4*N'"
ff("-f", "lavfi", "-i", "color=c=0x406080:s=320x180:r=24:d=3", "-f", "lavfi", "-i", "sine=f=880:d=3:r=48000", "-shortest", "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", str(sb / "s1__fasth3-intro_seed1.mp4"))
wj(sb / "s1__fasth3-intro_seed1.json", {"engine": "fasth3", "song_audio": {"t0": 0, "preroll": 1.0}})
ff("-f", "lavfi", "-i", ramp, "-c:v", "libx264", "-crf", "8", "-pix_fmt", "yuv420p", str(sb / "s2__ltxia2v-sing_seed1.mp4"))
wj(sb / "s2__ltxia2v-sing_seed1.json", {"engine": "ltxia2v", "song_audio": {"t0": 3.5, "seconds": 2.0, "preroll": 0.0}})
ff("-f", "lavfi", "-i", "testsrc=s=320x180:d=1", "-frames:v", "1", str(sb / "s3.png"))
edit = A.plan_edit(chap3, None)
edit["output"].update(w=W, h=H, grain=0, vignette=0, lyrics=True)
edit["cuts"][1]["look"] = "none"
edit["cuts"][2]["in"] = {"type": "dissolve", "dur": 0.5}
edit["cuts"][2]["fx"] = ["lightleak"]
edit["cuts"][0]["look"] = "none"
edit["cuts"][0]["fx"] = ["dust"]
edit["cuts"][2]["look"] = "none"
edit["overlays"] = [{"type": "beatflash", "t0": 5, "t1": 8, "strength": 0.05}]
wj(mv / "edit.json", edit)
t0 = time.time()
res = A.assemble(mv, draft=False, out="cut/t.mp4")
out = mv / "cut" / "t.mp4"
ok(out.is_file() and out.with_suffix(".json").is_file() and (mv / "cut" / "t_strip.jpg").is_file(), "mp4 + json + strip written")
ok(not (mv / "_assembly").exists(), "_assembly cleaned up")
r = subprocess.run([A.FFPROBE, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,nb_read_packets,r_frame_rate", "-count_packets", "-of", "json", str(out)], capture_output=True, text=True)
d = json.loads(r.stdout)
vs = next(s for s in d["streams"] if s["codec_type"] == "video")
ok(abs(float(d["format"]["duration"]) - 9.0) < 0.05, "duration = preroll + song: %s" % d["format"]["duration"])
ok(abs(int(vs["nb_read_packets"]) - 9 * 24) <= 1 and vs["width"] == W and vs["height"] == H, "frame count and size: %s" % vs)
ok(res["preroll"] == 1.0 and len(res["cuts"]) == 3 and res["cuts"][1]["kind"] == "sing" and res["cuts"][2]["in"] == "dissolve", "resolved json lists the cuts")
st = json.loads((mv / "cut" / "_status.json").read_text())
ok(st["state"] == "done", "status done")
# audio: the intro's 880 Hz, then the song's 440 Hz without a gap
raw = subprocess.run([A.FFMPEG, "-v", "error", "-i", str(out), "-f", "f32le", "-ac", "1", "-ar", "48000", "-"], capture_output=True).stdout
au = np.frombuffer(raw, dtype=np.float32)
win = lambda a, b: au[int(a * 48000):int(b * 48000)]
def dom(x):
    sp = np.abs(np.fft.rfft(x)); return np.argmax(sp) * 48000 / len(x)
ok(abs(len(au) / 48000 - 9.0) < 0.05, "audio length = video length")
ok(abs(dom(win(0.2, 0.8)) - 880) < 15, "the first preroll second is the intro clip's own audio")
ok(abs(dom(win(1.5, 2.5)) - 440) < 15 and abs(dom(win(7.0, 8.9)) - 440) < 15, "after the preroll it is the original song")
rms = [float(np.sqrt(np.mean(win(a / 10, a / 10 + 0.1) ** 2))) for a in range(15, 88)]
ok(min(rms) > 0.05, "song audio is continuous across every cut and transition (no dips): min rms %.3f" % min(rms))
# picture sync: the singing clip's frame k has luma 16+4k; its frame 0 must sit at video time preroll + 3.5 = frame 108
def luma(n):
    x = subprocess.run([A.FFMPEG, "-v", "error", "-i", str(out), "-vf", f"select=eq(n\\,{n}),scale=16:9,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True).stdout
    return float(np.frombuffer(x, dtype=np.uint8).mean())
c0 = int(round((1.0 + 3.5) * 24))
ok(abs(luma(c0 - 4) - 16) < 6 and abs(luma(c0) - 16) < 6, "before the singing clip starts its first frame is held (luma 16)")
ok(abs(luma(c0 + 10) - (16 + 40)) < 7 and abs(luma(c0 + 30) - (16 + 120)) < 8, "singing clip frame k sits at video frame c0+k (+/- 1 frame): %.0f %.0f" % (luma(c0 + 10), luma(c0 + 30)))
ok(abs(res["cuts"][1]["sync_t"] - (1.0 + 3.5)) < 1 / 24, "reported sync time = preroll + song_audio.t0")
# lyrics: frame at 1.0+1.7 s has text pixels (a white-ish area at the bottom third), a frame with no line does not
def bottom_max(n):
    x = subprocess.run([A.FFMPEG, "-v", "error", "-i", str(out), "-vf", f"select=eq(n\\,{n}),crop=320:40:0:140,format=gray", "-frames:v", "1", "-f", "rawvideo", "-"], capture_output=True).stdout
    return int(np.frombuffer(x, dtype=np.uint8).max())
ok(bottom_max(int((1.0 + 1.75) * 24)) > 200, "lyric line (conf 0.9) is drawn in the bottom third")
ok(bottom_max(int((1.0 + 3.5) * 24)) < 200, "a low-confidence line (conf 0.2) is not drawn by default")
# ---- 4b. build targets: ▶ YouTube master, 🎵 Suno (size-capped, reuses a current master), 🪝 Hooks ----------------
import mv_hooks as HK
def contiguous(p, total):
    return abs(p[0][0]) < 1e-6 and abs(p[-1][1] - total) < 1e-6 and all(abs(a[1] - b[0]) < 1e-6 for a, b in zip(p, p[1:]))
starts = [i * 6.0 for i in range(10)]                     # scenes every 6 s over a 60 s song
lines = [(5.0, 7.5), (11.0, 13.0), (17.5, 19.0), (23.0, 25.5), (29.0, 31.0), (40.0, 43.0), (47.0, 49.0)]  # 6, 12, 24, 30, 42, 48 are mid-line
hp = HK.plan_hooks(starts, lines, 60.0)
ok(contiguous(hp, 60.0) and all(10 <= b - a <= 30 for a, b in hp), "hooks cover the whole song, each 10-30 s: %s" % hp)
ok(not any(HK.in_line(a, lines) for a, _ in hp[1:]), "no hook starts in the middle of a sung line when a gap is available: %s" % hp)
ok(set(round(a, 3) for a, _ in hp[1:]) <= set(starts) | {round((b1 + a2) / 2, 3) for (_, b1), (a2, _) in zip(lines, lines[1:])},
   "boundaries are scene changes or vocal-gap midpoints")
hp2 = HK.plan_hooks([i * 5.0 for i in range(1, 12)], [], 60.0)
ok(contiguous(hp2, 60.0) and all(set([a, b]) <= set(i * 5.0 for i in range(13)) for a, b in hp2) and all(15 <= b - a <= 25 for a, b in hp2), "no vocals: scene changes, lengths near 20 s: %s" % hp2)
hp3 = HK.plan_hooks([], [(0.5, 59.5)], 60.0)              # one endless line, no scenes: still split (mid-line is the last resort)
ok(contiguous(hp3, 60.0) and len(hp3) >= 2, "a song with no clean boundary still gets split: %s" % hp3)
ok(contiguous(HK.plan_hooks([3.0], [], 8.0), 8.0), "a song shorter than a hook: one piece, relaxed")
voc = tmp / "voc.wav"   # a 'vocal' that never stops except one 0.2 s breath at 2.9-3.1 s, and a 20 ms click-gap at 4.5 s (a consonant)
ff("-f", "lavfi", "-i", "aevalsrc='0.5*sin(2*PI*300*t)*(1-between(t,2.9,3.1))*(1-between(t,4.5,4.52))':s=48000:d=6", str(voc))
dips, level_at = HK.vocal_dips(voc, offset=1.0)
ok(any(3.9 <= t <= 4.1 and lv < 0.05 for t, lv in dips), "the breath is found as a quiet dip (video time = song + offset): %s" % dips)
ok(level_at(2.5) > 0.5 and level_at(5.51) > 0.5, "a 20 ms gap inside a 'word' is not quiet (+-60 ms rule): %.2f" % level_at(5.51))
hp4 = HK.plan_hooks([], [(1.0, 7.0)], 7.0, lo=1, hi=6, aim=3, dips=dips, level_at=level_at)
ok(any(abs(a - 4.0) < 0.1 for a, _ in hp4[1:]), "the planner cuts at the breath: %s" % hp4)
vk, ak = A.suno_rates(240, 150)
ok(abs((vk + ak) * 240 / 8000 - 150 * 0.93) < 1 and A.suno_rates(10, 150)[0] == 12000 and A.suno_rates(5000, 10)[0] == 800, "suno bitrate: fills the cap with margin, clamped 800k-12M: %s" % vk)
ed = json.loads((mv / "edit.json").read_text()); ed["output"]["suno_mb"] = 0.15; wj(mv / "edit.json", ed)
time.sleep(1.2)
ry = A.build_target(mv, "youtube")
master = mv / "cut" / "test.mp4"
ok(master.is_file() and json.loads(master.with_suffix(".json").read_text())["target"] == "youtube" and ry["target"] == "youtube", "▶ YouTube = the master cut/<slug>.mp4, target recorded")
ok(A.master_current(mv)[0], "a fresh master is current: %s" % (A.master_current(mv),))
mt = master.stat().st_mtime
rs = A.build_target(mv, "suno")
suno = mv / "cut" / "test-suno.mp4"
sj = json.loads(suno.with_suffix(".json").read_text())
ok(suno.is_file() and sj["target"] == "suno" and sj["from"] == "test.mp4" and master.stat().st_mtime == mt, "🎵 Suno re-encodes the current master (not rebuilt)")
pr = json.loads(subprocess.run([A.FFPROBE, "-v", "error", "-show_entries", "format=duration:stream=width,height", "-of", "json", str(suno)], capture_output=True, text=True).stdout)
ok(abs(float(pr["format"]["duration"]) - 9.0) < 0.1 and pr["streams"][0]["width"] == W, "Suno: whole song, same size as the master: %s" % pr)
rh = A.build_target(mv, "hooks")
hj = json.loads((mv / "export" / "hooks" / "auto" / "hooks.json").read_text())
ok(hj["from"] == "test.mp4" and hj["hooks"] and all((mv / "export" / "hooks" / "auto" / h["file"]).is_file() for h in hj["hooks"])
   and contiguous([(h["t0"], h["t1"]) for h in hj["hooks"]], 9.0), "🪝 hooks: files + hooks.json covering the cut: %s" % hj["hooks"])
ok(json.loads((mv / "cut" / "_status.json").read_text())["state"] == "done", "status done after hooks")
os.utime(mv / "sb01" / "chapter.json", (time.time() + 5, time.time() + 5))
ok(not A.master_current(mv)[0] and "chapter.json" in A.master_current(mv)[1], "an edit after the master makes it stale (Suno / Hooks then rebuild it first)")
# --plan never overwrites, --replan does
(mv / "edit.json").write_text(json.dumps({"marker": 1}), encoding="utf-8")
A.assemble(mv, plan_only=True)
ok(json.loads((mv / "edit.json").read_text()) == {"marker": 1}, "--plan does not overwrite an existing edit.json")
A.assemble(mv, plan_only=True, replan=True)
ok(len(json.loads((mv / "edit.json").read_text())["cuts"]) == 3, "--replan writes a fresh plan")
# no clips at all + draft: stills fill in
for f in sb.glob("*.mp4"):
    f.unlink()
wj(mv / "edit.json", {**edit, "cuts": [dict(c, clip=None) for c in edit["cuts"]]})
res2 = A.assemble(mv, draft=True)
ok(res2["w"] == 1280 and res2["h"] == 720 and all(c["kind"] == "still" for c in res2["cuts"]) and (mv / "cut" / "test-draft.mp4").exists(), "--draft without any clip: stills with Ken Burns, 1280x720")
# ---- 5. the server op: POST /api/mv {op: assemble} queues on the reroll worker (a 2nd server instance on a spare port, in a temp tree) ----
import functools, http.server, threading, urllib.request, urllib.error
try:
    import serve_gallery as sg
    for need in ("MVDIR", "mv_save", "mv_load", "Handler", "REROLLS", "LOG"):
        assert hasattr(sg, need), "serve_gallery has no %s" % need
except Exception as e:  # the server part is optional: skip it cleanly
    sg = None
    print("SKIP server section (serve_gallery cannot be used here): %s" % e)
if sg:
    sroot = Path(tempfile.mkdtemp(prefix="mvsrv_"))
    saved = {k: getattr(sg, k) for k in dir(sg) if k.isupper() and isinstance(getattr(sg, k), Path)}
    sg.ROOT = sroot  # every path constant of the server is re-pointed into the temp tree
    for k, v in saved.items():
        try:
            setattr(sg, k, sroot / v.relative_to(saved["ROOT"]))
        except ValueError:
            pass
    sg.FB.mkdir(parents=True, exist_ok=True)
    tmpfb = sg.FB
    sg.rebuild_bg = lambda: None  # never rebuild a gallery from a test
    d = sg.MVDIR / "997-asm-test"
    (d / "audio").mkdir(parents=True)
    sg.mv_save(d, {"title": "Asm Test", "idea": "", "lyrics": "", "status": "draft", "audio": None, "vocals": None, "refs": [], "markers": [], "ref_requests": []})
    try:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(sg.Handler, directory=str(sroot)))
    except Exception as e:
        srv = None
        print("SKIP server section (cannot start): %s" % e)
    if srv:
        PORT = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        def mvpost(body):
            r = urllib.request.Request("http://127.0.0.1:%d/api/mv" % PORT, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
            try:
                return json.loads(urllib.request.urlopen(r, timeout=30).read())
            except urllib.error.HTTPError as e:
                return {"error": json.loads(e.read()).get("error"), "status": e.code}
        try:
            ok(mvpost({"op": "assemble", "mv": "997-asm-test"}).get("status") == 400 and not sg.REROLLS, "assemble without a song / storyboard is refused")
            mm = sg.mv_load(d); mm["audio"] = "musicvideos/997-asm-test/audio/song.wav"; sg.mv_save(d, mm)
            (d / "sb01").mkdir(); wj(d / "sb01" / "chapter.json", {"scenes": []})
            r = mvpost({"op": "assemble", "mv": "997-asm-test", "draft": True})
            ok(r.get("queued") == 1 and sg.REROLLS == ["mvasm:997-asm-test|draft"], "draft build queued on the reroll worker: %s" % sg.REROLLS)
            ok(json.loads((d / "cut" / "_status.json").read_text())["state"] == "queued", "cut/_status.json says queued")
            mvpost({"op": "assemble", "mv": "997-asm-test", "draft": True})
            ok(sg.REROLLS == ["mvasm:997-asm-test|draft"], "the same build is queued once")
            mvpost({"op": "assemble", "mv": "997-asm-test"})
            ok(sg.REROLLS == ["mvasm:997-asm-test|draft", "mvasm:997-asm-test|youtube"], "no target = the YouTube master, its own queue entry")
            mvpost({"op": "assemble", "mv": "997-asm-test", "target": "suno"}); mvpost({"op": "assemble", "mv": "997-asm-test", "target": "hooks"})
            ok(sg.REROLLS[-2:] == ["mvasm:997-asm-test|suno", "mvasm:997-asm-test|hooks"], "Suno and Hooks queue as their own entries")
            ok(json.loads((d / "cut" / "_status.json").read_text())["target"] == "hooks", "the queued status names the target")
            ok(mvpost({"op": "assemble", "mv": "997-asm-test", "target": "tiktok"}).get("status") == 400, "an unknown target is refused")
            ev = [json.loads(l) for l in sg.LOG.read_text().splitlines()]
            ok(any(e.get("event") == "mv_assemble" and e.get("draft") for e in ev), "logs an informational mv_assemble event")
            import watch_feedback
            ok("mv_assemble" in watch_feedback.INFO_ONLY, "the feedback watcher treats mv_assemble as info")
        finally:
            srv.shutdown(); sg.REROLLS.clear()
    shutil.rmtree(sroot, ignore_errors=True)
print(f"took {time.time() - t0:.0f}s")
print(f"PASS {PASS}" + (f"  FAIL {FAIL}" if FAIL else ""))
shutil.rmtree(tmp, ignore_errors=True)
sys.exit(1 if FAIL else 0)
