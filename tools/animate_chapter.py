"""Build + run the ONE `run_video.py --batch` for a journey chapter's reel, with the learned audio rules enforced.

  .venv/Scripts/python tools/animate_chapter.py journeys/015-x/ch01 [--scenes s1,s3] [--engine fasth3] [--seed N]
                                                [--tag reel] [--mode auto|narrate|silent] [--motions m.json] [--dry-run]
  also NevNovella saga chapters: explore/sagas/NNN-x/chNN (episode.json shots; see load())

Claude authors per scene (chapter.json): `motion` (required), optional `sfx`, `soundscape`, `camera_move` (video camera,
default "slow push-in"), `speaker_desc` (who talks + where in frame), `voice`, `seconds`. This tool decides the audio:
  * dialogue (non-radio)  -> line = first non-radio entry; speaker = speaker_desc | "<who>, <first clause of cast look>" | lead
  * radio-only dialogue   -> line from it, speaker = an unseen voice over a radio / intercom, off-screen
  * no dialogue + noref   -> SILENT: motion should hold "silently <verb>"; soundscape defaults to "the scene"
  * no dialogue + face    -> NARRATE the caption (journey.json `narrator_voice` overrides the voice)
Why: H3 babbles when a clip has no line; "silently" only holds when no face is on screen.
Writes chNN/_reel_batch.json, prints a table, then runs run_video.py --batch unless --dry-run.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NARRATOR_SPEAKER = "an unseen narrator off-screen, a voice-over; nobody in the picture moves their lips"
NARRATOR_VOICE = "a deep, calm storybook narrator's voice in English"
RADIO_SPEAKER = "an unseen voice over a radio / intercom, off-screen"


def look_of(v):
    return v["look"] if isinstance(v, dict) else v


def speaker_desc(j, sc, who):
    if sc.get("speaker_desc"):
        return sc["speaker_desc"]
    wl = who.lower().strip()
    wt = set(wl.replace(".", "").split())
    for name, v in j.get("cast", {}).items():
        nl = name.lower()
        nt = set(nl.split())
        if wl == nl or (wt and (wt <= nt or nt <= wt)):
            clause = look_of(v).split(",")[0].strip()
            return clause if clause.lower().startswith((wl, nl)) else f"{who}, {clause}"
    lead = j.get("name", "")
    if lead and (wl == lead.lower() or wl in lead.lower().split()):
        return lead
    return who


def load(chdir):
    """-> (journey-like dict, chapter-like dict with `scenes`). Journeys: journey.json + chapter.json. NevNovella saga chapters
    ("Animate chapter" on a saga): saga.json + episode.json; shots become scenes, the caption is the shot's
    narration (else its caption), nofigure counts as noref (no face on screen), each cast member's `voice_desc` (if any) voices their lines."""
    if (chdir / "chapter.json").exists():
        return (json.loads((chdir.parent / "journey.json").read_text(encoding="utf-8")),
                json.loads((chdir / "chapter.json").read_text(encoding="utf-8")))
    saga = json.loads((chdir.parent / "saga.json").read_text(encoding="utf-8"))
    ep = json.loads((chdir / "episode.json").read_text(encoding="utf-8"))
    cast = saga.get("cast", {})
    j = {"name": next(iter(cast), ""), "cast": {n: {"look": c.get("look", "")} for n, c in cast.items()},
         "narrator_voice": (ep.get("reel") or {}).get("narrator") or saga.get("narrator_voice")}
    scenes = []
    for sh in ep.get("shots", []):
        sc = dict(sh)
        sc["caption"] = sh.get("narration") or sh.get("caption", "")
        sc["noref"] = bool(sh.get("nofigure") or sh.get("noref"))
        sc["dialogue"] = [{"who": d["who"], "text": d["text"], **({"radio": True} if d.get("off") else {})} for d in sh.get("dialogue", [])
                          if not d["text"].strip().startswith("*")]  # "*beep-bweep*" = a sound, not a line
        if sc["dialogue"]:
            sc.setdefault("voice_of", ((ep.get("reel") or {}).get("voices") or {}).get(sc["dialogue"][0]["who"], ""))
        scenes.append(sc)
    return j, {"scenes": scenes, "reel": ep.get("reel") or {}}


def merge_motions(chdir, spec):
    """--motions spec.json: {reel: {feel, soundscape, camera, voices {name: voice}}, shots|scenes: {id: {motion, sfx, soundscape, camera_move,
    speaker_desc, seconds}}} written into the chapter file (chapter.json / episode.json) so the reel's direction is kept with the chapter."""
    f = chdir / ("chapter.json" if (chdir / "chapter.json").exists() else "episode.json")
    ch = json.loads(f.read_text(encoding="utf-8"))
    key = "scenes" if "scenes" in ch else "shots"
    per = spec.get("shots") or spec.get("scenes") or {}
    ids = {x["id"] for x in ch[key]}
    bad = sorted(set(per) - ids)
    if bad:
        raise SystemExit(f"unknown shot/scene ids in the motions file: {bad}")
    keep = ("motion", "sfx", "soundscape", "camera_move", "speaker_desc", "seconds", "voice", "overview")  # overview = the cut's on-screen story line
    for x in ch[key]:
        x.update({k: v for k, v in (per.get(x["id"]) or {}).items() if k in keep})
    if spec.get("reel"):
        ch["reel"] = {**(ch.get("reel") or {}), **spec["reel"]}
    f.write_text(json.dumps(ch, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return f


def decide(j, sc, mode="auto"):
    """-> (kind, fields dict, warnings list) for one scene"""
    warns = []
    if mode == "music":  # the cut is set to a song and the clips' own audio is edited out: no lines, no narrator,
        # nobody talks (mouths closed, so no lip flap under the music); the picture's motion and feel are all that matter
        if "silently" not in sc["motion"].lower():
            warns.append('music mode: put "silently" on the main verb so nobody mouths words')
        return "music", {"soundscape": sc.get("soundscape") or "the scene"}, warns
    if mode == "storybook":  # storybook: every scene is a narrated caption
        return "narrate", {"line": sc.get("caption", ""), "speaker": NARRATOR_SPEAKER,
                           "voice": j.get("narrator_voice") or NARRATOR_VOICE}, warns
    dlg = sc.get("dialogue") or []
    spoken = [d for d in dlg if not d.get("radio")]
    if spoken:
        if len(spoken) > 1:
            warns.append(f"{len(spoken)} spoken lines; using only the first (\"{spoken[0]['text']}\"). "
                         "Split into two clips if both matter.")
        d = spoken[0]
        return "dialogue", {"line": d["text"], "speaker": speaker_desc(j, sc, d["who"]), "voice": sc.get("voice", "")}, warns
    if dlg:  # radio only
        return "radio", {"line": dlg[0]["text"], "speaker": RADIO_SPEAKER, "voice": sc.get("voice", "")}, warns
    silent = bool(sc.get("noref")) if mode == "auto" else mode == "silent"
    if silent:
        if "silently" not in sc["motion"].lower():
            warns.append('motion has no "silently": H3 will babble. Put it on the main verb, e.g. "<subject> silently <verb> ..." '
                         "(your text is not rewritten).")
        if not sc.get("noref"):
            warns.append("silent on a scene with a visible face: H3 tends to babble here (narration is safer).")
        return "silent", {"soundscape": sc.get("soundscape") or "the scene"}, warns
    return "narrate", {"line": sc.get("caption", ""), "speaker": NARRATOR_SPEAKER,
                       "voice": j.get("narrator_voice") or NARRATOR_VOICE}, warns


def build(chdir, scenes=None, engine="fasth3", seed=None, tag="reel", mode="auto"):
    """-> (batch list, table rows, warnings [(scene, msg)]); SystemExit if a scene lacks `motion`"""
    chdir = Path(chdir)
    j, ch = load(chdir)
    feel = ch.get("reel") or {}  # chapter-wide feel shared by every clip
    pick = [s for s in ch["scenes"] if not scenes or s["id"] in scenes]
    if scenes and len(pick) != len(set(scenes)):
        raise SystemExit(f"unknown scene(s): {sorted(set(scenes) - {s['id'] for s in ch['scenes']})}")
    missing = [s["id"] for s in pick if not (s.get("motion") or "").strip()]
    if missing:
        raise SystemExit(f"scenes without a `motion` field: {', '.join(missing)}. Author a motion per scene in chapter.json first "
                         "(what moves, continuing scene to scene; 'silently' on the verb where no line is spoken).")
    try:
        rel = chdir.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        rel = chdir.as_posix()
    batch, rows, warns = [], [], []
    for sc in pick:
        kind, f, w = decide(j, sc, mode)
        warns += [(sc["id"], m) for m in w]
        motion = sc["motion"].rstrip(". ") + (f". {feel['feel']}" if feel.get("feel") else "")
        item = {"image": f"{rel}/{sc['id']}.png", "engine": engine, "tag": tag, "allow_repeat": True,
                "motion": motion, "camera": sc.get("camera_move") or feel.get("camera") or "slow push-in"}
        if sc.get("sfx"):
            item["sfx"] = sc["sfx"]
        if kind in ("silent", "music") and not sc.get("soundscape") and feel.get("soundscape"):
            f["soundscape"] = feel["soundscape"]
        if kind in ("dialogue", "radio") and not f.get("voice") and sc.get("voice_of"):
            f["voice"] = sc["voice_of"]
        if seed is not None:
            item["seed"] = seed
        if sc.get("seconds"):
            item["seconds"] = sc["seconds"]
        item.update({k: v for k, v in f.items() if v})
        batch.append(item)
        rows.append((sc["id"], kind, f.get("line") or f"(soundscape: {f.get('soundscape')})", f.get("speaker", "")))
    return batch, rows, warns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("chapter")
    ap.add_argument("--scenes")
    ap.add_argument("--engine", default="fasth3")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--tag", default="reel")
    ap.add_argument("--mode", choices=["auto", "narrate", "silent", "storybook", "music"], default=None,
                    help="default: music for NevNovella saga chapters (their cut is set to a song, clip audio dropped), auto for journeys")
    ap.add_argument("--motions", help="JSON {reel, shots: {id: {motion, sfx, ...}}} merged into the chapter file first")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    chdir = Path(a.chapter)
    chdir = chdir if chdir.is_absolute() else ROOT / chdir
    scenes = [s.strip() for s in a.scenes.split(",")] if a.scenes else None
    if a.motions:
        print("motions merged into", merge_motions(chdir, json.loads(Path(a.motions).read_text(encoding="utf-8"))))
    mode = a.mode or ("auto" if (chdir / "chapter.json").exists() else "music")
    batch, rows, warns = build(chdir, scenes, a.engine, a.seed, a.tag, mode)
    out = chdir / "_reel_batch.json"
    out.write_text(json.dumps(batch, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{'scene':<6}{'mode':<10}{'line / soundscape':<55}speaker")
    for sid, kind, line, spk in rows:
        print(f"{sid:<6}{kind:<10}{line[:52]:<55}{spk[:60]}")
    for sid, m in warns:
        print(f"WARNING {sid}: {m}")
    print(f"wrote {out}")
    if a.dry_run:
        print("(dry run: run_video not started)")
        return 0
    cmd = [sys.executable, str(ROOT / "tools" / "run_video.py"), "--batch", str(out)]
    print("running:", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    sys.exit(main())
