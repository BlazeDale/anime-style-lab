"""Tests for the 🎚 stems support (tools/mv_stems.py + the stems zip upload in serve_gallery).
Needs librosa + soundfile + numpy: python tools/test_mv_stems.py   [--no-server | --server-only]
Part 1: naming conventions (pure).  Part 2: a synthetic song + stems -> mv_stems.py.  Part 3: zips POSTed to a second serve_gallery
instance (another port, feedback redirected to a temp dir, rebuild stubbed) inside a temp tree (skipped with a message when serve_gallery cannot be used).
"""
import functools
import http.server
import io
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

try:
    import librosa  # noqa: F401
    import numpy as np
    import soundfile as sf
except ImportError as e:
    sys.exit("test_mv_stems needs librosa + soundfile + numpy (pip install librosa soundfile numpy): %s" % e)

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))
import mv_stems  # noqa: E402

GPY = sys.executable  # this interpreter has librosa + soundfile (checked above)
PASS = FAIL = 0


def ok(c, m):
    global PASS, FAIL
    print(("PASS " if c else "FAIL ") + m)
    PASS += bool(c)
    FAIL += not c


# ---- 1) naming conventions
def names():
    p = mv_stems.guess_role
    ok(p("Lead Vocals") == "vocals" and p("Lead Vox") == "vocals" and p("LV") == "vocals" and p("vox lead") == "vocals", "roles: lead vocal spellings")
    ok(p("BV Harmony") == "backing" and p("Backing Vocals 2") == "backing" and p("Choral") == "backing" and p("BGV") == "backing", "roles: backing vocals")
    ok(p("Kick") == "drums" and p("Snare Top") == "drums" and p("Drums") == "drums" and p("Overheads") == "drums" and p("Bass Drum") == "drums" and p("Hi Hat") == "drums", "roles: drums incl. kit pieces")
    ok(p("Bass DI") == "bass" and p("Sub") == "bass" and p("Electric Guitar L") == "guitar" and p("Gtr 2") == "guitar" and p("Bass Guitar") == "bass", "roles: bass / guitar")
    ok(p("Piano") == "keys" and p("Synth Pad") == "keys" and p("Strings") == "strings" and p("Brass Section") == "brass" and p("FX Risers") == "fx" and p("Tambourine") == "other", "roles: keys strings brass fx other")
    pl = mv_stems.pick_lead
    ok(pl(["Drums", "Lead Vocals", "BV Harmony", "Backing Vocals"]) == "Lead Vocals", "lead: 'Lead Vocals' beats backing")
    ok(pl(["Lead Vox", "BV Harmony", "Guitar"]) == "Lead Vox" and pl(["Vox Lead", "Vox Double"]) == "Vox Lead", "lead: 'Lead Vox', 'Vox Lead' (a double is never the lead)")
    ok(pl(["Vocals", "Drums"]) == "Vocals", "lead: a single plain vocal stem is taken")
    ok(pl(["Vocals 1", "Vocals 2", "Drums"]) is None, "lead: two plain vocals = ambiguous -> None")
    ok(pl(["Lead Vocals", "Lead Vocals Double", "Ad Libs"]) == "Lead Vocals", "lead: double / ad-lib excluded")
    ok(pl(["Main Vocal", "Choral"]) == "Main Vocal" and pl(["LV", "BV"]) == "LV", "lead: 'Main Vocal', 'LV'")
    ok(pl(["Lead Guitar", "Drums"]) is None and pl(["BV Harmony", "Backing Vocals"]) is None, "lead: a lead guitar / only backing = None")
    pm = mv_stems.pick_mix
    ok(pm(["Moonlight (Mix)", "Drums", "Bass"], "Moonlight") == "Moonlight (Mix)", "mix: '(Mix)' in the name")
    ok(pm(["Master", "Drums"]) == "Master" and pm(["Full Mix", "Mix Bus FX"]) == "Full Mix", "mix: Master / Full Mix")
    ok(pm(["Moonlight", "Drums", "Bass"], "Moonlight") == "Moonlight" and pm(["Moonlight_Stereo Mix", "Drums"], "Moonlight") == "Moonlight_Stereo Mix", "mix: just the song title, or title + stereo mix")
    ok(pm(["Moonlight - Tambourine", "Drums"], "Moonlight") is None, "mix: title + an instrument word is a stem, not the mix")
    ok(pm(["Drum Mix", "Bass", "Instrumental Mix"], "x") is None and pm(["Drums", "Bass", "Guitar"], "Moonlight") is None, "mix: a drum mix / instrumental is not the full mix; none = None")
    ok(pm(["Mix", "Master"]) == "Master", "mix: master ranks above mix")
    t = set()
    n1, n2, n3, n4, n5, n6 = (mv_stems.safe_name(x, t) for x in ("../../evil.wav", "Stems/Lead Vocals.wav", "x/Lead Vocals.wav", "__MACOSX/._Drums.wav", "readme.txt", "a/.hidden.wav"))
    ok(n1 == "evil.wav" and n2 == "Lead Vocals.wav" and n3 == "Lead Vocals (2).wav", "safe_name: zip-slip flattened, folders dropped, duplicate numbered: %s %s %s" % (n1, n2, n3))
    ok(mv_stems.safe_name("Moonlight (Mix) [v2].wav", set()) == "Moonlight Mix v2.wav", "safe_name: brackets dropped")
    ok(n4 is None and n5 is None and n6 is None, "safe_name: __MACOSX, non-audio and hidden files skipped")
    ok(mv_stems.safe_name("dir\\sys:tem*?.wav", set()) == "sys_tem.wav", "safe_name: odd characters replaced: %s" % mv_stems.safe_name("dir\\sys:tem*?.wav", set()))


# ---- 2) synthetic song
SR = 22050
DUR = 40


def tone(f, amp, t0, t1, sr=SR, harm=0.0):
    t = np.arange(int(DUR * sr)) / sr
    y = amp * np.sin(2 * np.pi * f * t) + harm * amp * np.sin(2 * np.pi * 2 * f * t)
    y[(t < t0) | (t >= t1)] = 0
    return y.astype(np.float32)


def drums(sr=SR):
    rng = np.random.default_rng(1)
    y = np.zeros(int(DUR * sr), dtype=np.float32)
    for k in range(int(DUR * 2)):  # a click every 0.5 s (120 bpm), a hole at 18-22 s
        t = k * 0.5
        if 18 <= t < 22:
            continue
        n = int(0.01 * sr)
        y[int(t * sr):int(t * sr) + n] = rng.uniform(-0.5, 0.5, n)
        for off, prob in ((0.25, 0.4), (0.125, 0.2)):  # an irregular groove: a pure click train would match the song at every beat
            if rng.random() < prob and not 18 <= t + off < 22:
                y[int((t + off) * sr):int((t + off) * sr) + n] = rng.uniform(-0.3, 0.3, n)
    return y


def stems_audio(sr_bass=SR):
    bass = tone(110, 0.3, 4, 40, sr_bass)
    t = np.arange(len(bass)) / sr_bass
    bass[(t >= 28) & (t < 36)] *= 1 / 3  # quiet under the solo
    gtr = tone(440, 0.15, 10, 40, SR, 0.3)
    t2 = np.arange(len(gtr)) / SR
    gtr[(t2 >= 28) & (t2 < 36)] *= 4  # the solo
    vox = tone(300, 0.3, 12, 26)
    return {"drums": drums(), "bass": bass, "gtr": gtr, "vox": vox}


def write_set(d, song_name="song.wav"):
    """audio/stems/*.wav|flac in mixed formats + audio/song.wav (the sum) + a hand-made analysis.json"""
    (d / "audio" / "stems").mkdir(parents=True, exist_ok=True)
    a = stems_audio()
    bass44 = stems_audio(44100)["bass"]
    sf.write(d / "audio" / "stems" / "Drums.wav", np.stack([a["drums"], a["drums"]], 1), SR)        # stereo
    sf.write(d / "audio" / "stems" / "Bass.flac", bass44, 44100)                                    # other rate + flac
    sf.write(d / "audio" / "stems" / "Lead Guitar.wav", a["gtr"], SR)
    sf.write(d / "audio" / "stems" / "Lead Vocals.wav", a["vox"], SR)
    sf.write(d / "audio" / song_name, (a["drums"] + a["bass"] + a["gtr"] + a["vox"]).astype(np.float32) * 0.8, SR)
    (d / "audio" / "analysis.json").write_text(json.dumps({"duration": DUR, "peaks": [[-0.1, 0.1]], "beats": [], "tempo": 120.0, "sections": [20.0]}), encoding="utf-8")
    (d / "mv.json").write_text(json.dumps({"title": "Stem Test", "audio": "musicvideos/%s/audio/%s" % (d.name, song_name), "stems": []}), encoding="utf-8")


def synth():
    root = Path(tempfile.mkdtemp(prefix="mvstems_"))
    try:
        d = root / "musicvideos" / "997-synth"
        d.mkdir(parents=True)
        write_set(d)
        t0 = time.time()
        r = subprocess.run([GPY, str(TOOLS / "mv_stems.py"), str(d)], capture_output=True, text=True)
        ok(r.returncode == 0 and (d / "audio" / "stems.json").exists(), "mv_stems.py runs (%.0f s): %s" % (time.time() - t0, (r.stdout or r.stderr).strip()[-200:]))
        res = json.loads((d / "audio" / "stems.json").read_text(encoding="utf-8"))
        S = {s["name"]: s for s in res["stems"]}
        ok(set(S) == {"Drums", "Bass", "Lead Guitar", "Lead Vocals"}, "four stems found in flac / wav, mono / stereo, 22k / 44k: %s" % sorted(S))
        ok(S["Drums"]["role"] == "drums" and S["Bass"]["role"] == "bass" and S["Lead Guitar"]["role"] == "guitar" and S["Lead Vocals"]["role"] == "vocals", "roles from the file names")
        ok(S["Lead Vocals"]["lead"] and not S["Drums"]["lead"], "the lead vocal is flagged")
        ok(all(abs(s["offset_s"]) <= 0.02 for s in res["stems"]) and not res["warnings"], "aligned stems: offset ~0, no warning: %s" % [s["offset_s"] for s in res["stems"]])
        ok(S["Bass"]["segments"] and abs(S["Bass"]["segments"][0][0] - 4) < 0.3 and abs(S["Bass"]["segments"][0][1] - 40) < 0.3, "bass activity 4-40 s: %s" % S["Bass"]["segments"])
        ok(len(S["Drums"]["segments"]) == 2 and abs(S["Drums"]["segments"][0][1] - 18) < 0.7 and abs(S["Drums"]["segments"][1][0] - 22) < 0.7, "drums: two segments around the 18-22 s gap: %s" % S["Drums"]["segments"])
        ok(any(abs(t - 4) < 0.3 for t in S["Bass"]["entrances"]) and any(abs(t - 22) < 0.7 for t in S["Drums"]["entrances"]), "entrances: bass at 4 s, drums back at 22 s after the gap: %s %s" % (S["Bass"]["entrances"], S["Drums"]["entrances"]))
        ok(len(S["Bass"]["lane"]) == 1500 and max(S["Bass"]["lane"]) <= 99 and S["Bass"]["lane"][300] > 0 and S["Bass"]["lane"][100] == 0, "lane: 1500 ints 0-99, silent before the entrance")
        M = res["moments"]
        bd = [m for m in M if m["kind"] == "breakdown" and "Drums" in m["stems"]]
        ok(bd and abs(bd[0]["t"] - 18) < 0.8 and abs(bd[0]["t1"] - 22) < 0.8, "breakdown: drums silent ~18-22 s: %s" % bd)
        so = [m for m in M if m["kind"] == "solo" and m["stems"] == ["Lead Guitar"]]
        ok(so and abs(so[0]["t"] - 28) < 1.0 and abs(so[0]["t1"] - 36) < 1.0, "solo: the guitar ~28-36 s while the vocals are silent: %s" % so)
        ok(any(m["kind"] == "enter" and "Bass" in m["stems"] and abs(m["t"] - 4) < 0.3 for m in M) and any(m["kind"] == "enter" and "Lead Vocals" in m["stems"] for m in M), "enter moments for the bass and the vocals")
        ok(any(m["kind"] == "exit" and "Lead Vocals" in m["stems"] and abs(m["t"] - 26) < 0.5 for m in M), "exit: the vocals stop at 26 s")
        ok(M == sorted(M, key=lambda m: (m["t"], m["kind"])) and res["beat_source"] == "drums" and 100 < res["tempo"] < 140 and res["downbeats"], "moments sorted; beats from the drum stem at ~120 bpm (%.1f), downbeats present" % res["tempo"])
        sh = S["Lead Guitar"]["share_by_section"]
        ok(len(sh) == 2 and sh[1] > sh[0], "share_by_section has one entry per section span and the guitar gets more of the second: %s" % sh)
        r = subprocess.run([GPY, str(TOOLS / "mv_stems.py"), str(d), "--summary"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok(r.returncode == 0 and "breakdown" in r.stdout and "solo" in r.stdout and "Lead Guitar" in r.stdout and "downbeats:" in r.stdout, "--summary prints the table")
        # a stem whose file starts 0.2 s late -> offset -0.2 and a warning, lanes shifted into place
        x, sr_ = sf.read(d / "audio" / "stems" / "Drums.wav")
        sf.write(d / "audio" / "stems" / "Drums.wav", np.concatenate([np.zeros((int(0.2 * sr_), 2)), x]), sr_)
        r = subprocess.run([GPY, str(TOOLS / "mv_stems.py"), str(d)], capture_output=True, text=True)
        res = json.loads((d / "audio" / "stems.json").read_text(encoding="utf-8"))
        dr = [s for s in res["stems"] if s["name"] == "Drums"][0]
        ok(r.returncode == 0 and abs(dr["offset_s"] + 0.2) <= 0.015 and dr["offset_ok"] and any("Drums" in w for w in res["warnings"]), "a late stem: offset %.3f s (expected -0.200) + warning: %s" % (dr["offset_s"], res["warnings"]))
        (d / "audio" / "stems" / "Broken.wav").write_bytes(b"not audio at all")
        r = subprocess.run([GPY, str(TOOLS / "mv_stems.py"), str(d)], capture_output=True, text=True)
        res = json.loads((d / "audio" / "stems.json").read_text(encoding="utf-8"))
        ok(r.returncode == 0 and [s["file"] for s in res["skipped"]] == ["Broken.wav"] and len(res["stems"]) == 4, "an unreadable file is skipped with a note")
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---- 3) the zip upload against a second server instance
def zip_bytes(files):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            z.writestr(name, data)
    return b.getvalue()


def wav_bytes(y, sr=SR):
    b = io.BytesIO()
    sf.write(b, y, sr, format="WAV")
    return b.getvalue()


def server():
    try:
        import serve_gallery as sg
        for need in ("MVDIR", "mv_save", "mv_load", "Handler", "REROLLS", "LOG", "LOCK"):
            assert hasattr(sg, need), "serve_gallery has no %s" % need
    except Exception as e:
        print("SKIP server section (serve_gallery cannot be used here): %s" % e)
        return
    sroot = Path(tempfile.mkdtemp(prefix="mvsrv_"))
    old_root = sg.ROOT
    for k, v in [(k, getattr(sg, k)) for k in dir(sg) if k.isupper() and isinstance(getattr(sg, k), Path)]:
        try:
            setattr(sg, k, sroot / v.relative_to(old_root))  # every path constant of the server now points into the temp tree
        except ValueError:
            pass
    sg.ROOT = sroot
    shutil.copytree(TOOLS, sroot / "tools", ignore=shutil.ignore_patterns("__pycache__", "*.html", "*.js"))  # the server runs ROOT/tools/*.py
    sg.FB.mkdir(parents=True, exist_ok=True)
    tmpfb = sroot
    sg.rebuild_bg = lambda: None  # never rebuild a gallery from a test
    d = sg.MVDIR / "998-stems-test"
    (d / "audio").mkdir(parents=True)
    sg.mv_save(d, {"title": "Moonlight", "idea": "", "lyrics": "", "status": "draft", "audio": None, "vocals": None, "refs": [], "markers": [], "ref_requests": []})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(sg.Handler, directory=str(sg.ROOT)))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def post(kind, name, data):
        req = urllib.request.Request("http://127.0.0.1:%d/api/mv/upload?mv=998-stems-test&kind=%s&name=%s" % (port, kind, name), data=data, method="POST")
        try:
            return json.loads(urllib.request.urlopen(req, timeout=120).read())
        except urllib.error.HTTPError as e:
            return {"error": json.loads(e.read()).get("error"), "status": e.code}

    def wait(cond, what, timeout=240):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if cond():
                return True
            time.sleep(1)
        print("  (timed out waiting for %s)" % what)
        return False

    ad = d / "audio"
    a = stems_audio()
    tone_quiet = wav_bytes(tone(200, 0.001, 0, 40))
    try:
        ok(post("stems", "x.mp3", b"abc").get("status") == 400 and post("stems", "x.zip", b"").get("status") == 400, "stems: only a non-empty .zip is accepted")
        bad = post("stems", "x.zip", b"this is not a zip")
        ok("couldn't read the zip" in (bad.get("error") or ""), "a corrupt zip is refused with a message: %s" % bad)
        files = {"Drums.wav": wav_bytes(a["drums"]), "Bass.wav": wav_bytes(a["bass"]), "Lead Guitar.wav": wav_bytes(a["gtr"]), "Lead Vocals.wav": wav_bytes(a["vox"]),
                 "BV Harmony.wav": wav_bytes(a["vox"] * 0.5), "../../evil.wav": tone_quiet, "__MACOSX/._Drums.wav": b"junk", "notes.txt": b"hi"}
        j = post("stems", "stems.zip", zip_bytes(files))
        m = j.get("mv") or {}
        ok(bool(m) and len(m.get("stems", [])) == 6, "zip A (no mix): 6 audio files extracted: %s" % [s["name"] for s in m.get("stems", [])])
        sd = ad / "stems"
        ok(sorted(p.name for p in sd.iterdir()) == sorted(["Drums.wav", "Bass.wav", "Lead Guitar.wav", "Lead Vocals.wav", "BV Harmony.wav", "evil.wav"]), "zip-slip neutralised: ../../evil.wav landed flattened inside audio/stems, junk skipped")
        ok(not (d.parent / "evil.wav").exists() and not (d.parent.parent / "evil.wav").exists() and not (d / "evil.wav").exists() and not (ad / "evil.wav").exists(), "...and nothing escaped the stems folder")
        ok(m.get("audio_from") == "stems-mixdown" and m.get("audio") is None, "no mix in the zip -> mixdown scheduled (audio_from=stems-mixdown)")
        ok(m.get("vocals_from") == "stems" and m.get("vocals", "").endswith("audio/vocals.wav") and m["stems_info"]["vocals"] == "Lead Vocals.wav", "lead vocal picked (not the BV) -> audio/vocals.wav: %s" % m.get("stems_info"))
        ok(wait((lambda: (ad / "stems.json").exists()), "zip A analysis") and (ad / "song.wav").exists(), "mixdown + analysis finished")
        info = sf.info(ad / "song.wav")
        ok(info.samplerate == 48000 and info.subtype == "PCM_16" and abs(info.duration - DUR) < 0.6, "mixdown = 48 kHz 16-bit wav of the full length (%s, %.1f s)" % (info.subtype, info.duration))
        mj = json.loads((d / "mv.json").read_text(encoding="utf-8"))
        ok(mj["audio"].endswith("audio/song.wav") and (ad / "analysis.json").exists(), "mv.audio set after the mixdown; the song got its normal analysis")
        ok(np.abs(sf.read(ad / "song.wav")[0]).max() <= 0.97, "mixdown is soft-limited (peak <= 0.97)")
        res = json.loads((ad / "stems.json").read_text(encoding="utf-8"))
        ok(len(res["stems"]) == 6 and any(s["lead"] and s["name"] == "Lead Vocals" for s in res["stems"]) and sum(1 for s in res["stems"] if s["lead"]) == 1 and any(m2["kind"] == "solo" for m2 in res["moments"]), "stems.json from the zip: 6 stems, exactly one lead vocal, a solo moment")
        ok(not any(abs(s["offset_s"]) > 0.02 for s in res["stems"] if s["name"] in ("Drums", "Bass")), "stems line up with their own mixdown")

        # zip B: a full mix + Lead Vox replaces the mixdown / old lead; the mix file is not a stem
        files = {"Moonlight (Mix).wav": wav_bytes((a["drums"] + a["bass"] + a["gtr"] + a["vox"]) * 0.8), "Lead Vox.wav": wav_bytes(a["vox"]), "BV Harmony.wav": wav_bytes(a["vox"] * 0.5),
                 "Drums.wav": wav_bytes(a["drums"]), "Lead Guitar.wav": wav_bytes(a["gtr"])}
        m = post("stems", "b.zip", zip_bytes(files)).get("mv") or {}
        ok(m.get("audio_from") == "stems-mix-file" and m.get("audio", "").endswith("audio/song.wav") and "Moonlight Mix.wav" in m["stems_info"]["song"], "zip B: 'Moonlight (Mix).wav' becomes the song: %s" % m.get("stems_info"))
        ok(m["stems_info"]["vocals"] == "Lead Vox.wav" and m.get("vocals_from") == "stems" and [s["name"] for s in m["stems"]] == ["BV Harmony", "Drums", "Lead Guitar", "Lead Vox"], "Lead Vox picked over BV Harmony; the mix is not among the stems: %s" % [s["name"] for s in m["stems"]])
        ok(wait((lambda: (ad / "stems.json").exists() and (ad / "analysis.json").exists()), "zip B analysis"), "zip B analysed")
        ok(abs(sf.read(ad / "song.wav")[0]).max() > 0 and sf.info(ad / "song.wav").samplerate == SR and not list(sd.glob("Kiss*")), "song.wav is the mix file itself (22050 Hz), not a mixdown")
        time.sleep(1)

        # zip C: the user already uploaded a song + vocals by hand -> both kept
        hand_song, hand_voc = wav_bytes(a["bass"]), wav_bytes(a["vox"] * 0.25)
        (ad / "song.wav").write_bytes(hand_song)
        (ad / "vocals.wav").write_bytes(hand_voc)
        with sg.LOCK:
            mm = sg.mv_load(d)
            mm.pop("audio_from", None); mm.pop("vocals_from", None)
            mm["audio"], mm["vocals"] = "musicvideos/998-stems-test/audio/song.wav", "musicvideos/998-stems-test/audio/vocals.wav"
            sg.mv_save(d, mm)
        (ad / "stems.json").unlink(missing_ok=True)
        m = post("stems", "c.zip", zip_bytes({"Mix.wav": wav_bytes(a["gtr"]), "Lead Vocals.wav": wav_bytes(a["vox"]), "Drums.wav": wav_bytes(a["drums"])})).get("mv") or {}
        ok((ad / "song.wav").read_bytes() == hand_song and (ad / "vocals.wav").read_bytes() == hand_voc and "audio_from" not in m and "vocals_from" not in m, "zip C: a hand-uploaded song and vocals are never overwritten")
        ok("kept" in m["stems_info"]["song"] and "kept" in m["stems_info"]["vocals"] and [s["name"] for s in m["stems"]] == ["Drums", "Lead Vocals"], "...and the page is told so: %s" % m.get("stems_info"))
        ok(wait((lambda: (ad / "stems.json").exists()), "zip C analysis"), "zip C analysed against the kept song")
        time.sleep(1)

        # 🎤 lyric placement is queued on the reroll worker (none runs in this test instance)
        def mvpost(body):
            r = urllib.request.Request("http://127.0.0.1:%d/api/mv" % port, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
            try:
                return json.loads(urllib.request.urlopen(r, timeout=30).read())
            except urllib.error.HTTPError as e:
                return {"error": json.loads(e.read()).get("error"), "status": e.code}
        ok(mvpost({"op": "lyrics_place", "mv": "998-stems-test"}).get("status") == 400 and "mvlyrics:998-stems-test" not in sg.REROLLS, "lyrics_place without saved lyrics is refused")
        mvpost({"op": "save", "mv": "998-stems-test", "lyrics": "Well\nYou were sitting"})
        ok("mvlyrics:998-stems-test" in sg.REROLLS and (ad / "lyrics_pending").exists(), "saving changed lyrics queues the placement (pending marker written)")
        sg.REROLLS.clear(); (ad / "lyrics_pending").unlink()
        ok("mv" in mvpost({"op": "lyrics_place", "mv": "998-stems-test"}) and sg.REROLLS == ["mvlyrics:998-stems-test"], "lyrics_place queues it once")
        mvpost({"op": "lyrics_place", "mv": "998-stems-test"})
        ok(sg.REROLLS == ["mvlyrics:998-stems-test"], "...and not twice")
        sg.REROLLS.clear(); (ad / "lyrics_pending").unlink(missing_ok=True)
        mvpost({"op": "save", "mv": "998-stems-test", "lyrics": "Well\nYou were sitting", "idea": "same words"})
        ok(not sg.REROLLS, "a save that leaves the lyrics unchanged does not re-queue")
        post("vocals", "v.wav", wav_bytes(a["vox"]))
        ok("mvlyrics:998-stems-test" in sg.REROLLS, "a vocals upload queues the placement")
        sg.REROLLS.clear(); (ad / "lyrics_pending").unlink(missing_ok=True)

        # removing the stems
        with sg.LOCK:
            pass
        r = urllib.request.Request("http://127.0.0.1:%d/api/mv" % port, data=json.dumps({"op": "stems_clear", "mv": "998-stems-test"}).encode(), method="POST", headers={"Content-Type": "application/json"})
        j = json.loads(urllib.request.urlopen(r, timeout=30).read())
        ok("stems" not in j["mv"] and not sd.exists() and not (ad / "stems.json").exists() and (ad / "song.wav").exists(), "stems_clear removes the stems and their analysis, keeps the song")
        log = [json.loads(x) for x in (sg.LOG.read_text(encoding="utf-8").splitlines())]
        ok(sum(1 for e in log if e.get("event") == "mv_upload" and e.get("kind") == "stems") == 3, "a mv_upload event per stems zip")
        ok(sum(1 for e in log if e.get("event") == "mv_lyrics") >= 3, "mv_lyrics events logged")
    finally:
        srv.shutdown()
        shutil.rmtree(d, ignore_errors=True)
        shutil.rmtree(tmpfb, ignore_errors=True)


if __name__ == "__main__":
    if "--server-only" not in sys.argv:
        names()
        synth()
    if "--no-server" not in sys.argv:
        server()
    print("%d passed, %d failed" % (PASS, FAIL))
    sys.exit(1 if FAIL else 0)
