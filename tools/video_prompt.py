"""Build an image-to-video prompt in MiniMax H3's native format from what the lab already knows about an image.

Format (from the official H3 image-to-video template):
  <header: medium + the subject "from <Picture 1> in its original scene" + look + "environment is constant">
  SHOT 1: The scene opens exactly on image 1; <action>; <camera>.
  SHOT 2: ...                                   (optional)
  Audio: <soundscape>, <music>.

What goes in:
  subject  = the character + scene text from subjects.json (per cast)        -> who/where (never invented)
  style    = the image's style prompt (its version's prompt.txt)              -> a STYLE LOCK line so the clip keeps the
             medium (2D cel vs 3D vs painted) and doesn't drift to photoreal
  motion   = what happens (the user's 🎬 note, or Claude's action arc)        -> SHOT lines
  camera / sound / music = short phrases

  python tools/video_prompt.py <image.png> --motion "..." [--camera "..."] [--shot "..." --shot "..."] [--sound "..."] [--music "..."]
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THREE_D = re.compile(r"\b(3D|CGI|live-action|photoreal\w*|photograph\w*|film still)\b", re.I)
PAINTED = re.compile(r"\b(oil|watercolou?r|gouache|painterly|painted|ink wash)\b", re.I)


def image_context(image):
    """-> (subject_key, subject_text, style_title, style_prompt) for an evolutions/<lin>/<vNN>/<name>.png"""
    p = Path(image).resolve()
    vdir, ldir = p.parent, p.parent.parent
    if (vdir / "episode.json").exists():  # 📖 a Nev Novel shot (explore/NNN/eN.png or a saga chapter explore/sagas/NNN/chNN/eN.png; 🎬 from the user)
        ep = json.loads((vdir / "episode.json").read_text(encoding="utf-8"))
        sh = next(s for s in ep["shots"] if s["id"] == p.stem)
        subject = f"the scene, {sh['prompt']}"
        if (ldir / "saga.json").exists() and sh.get("with"):  # saga: the cast in frame, by look
            cast = json.loads((ldir / "saga.json").read_text(encoding="utf-8")).get("cast", {})
            looks = "; ".join(f"{n} is {(cast.get(n) or {}).get('look', '')}" for n in sh["with"] if n in cast)
            subject += f". In the scene: {looks}" if looks else ""
        style = ep.get("style") or "{subject}"
        return f"explore:{vdir.name}", subject, ep.get("title", vdir.name), style if "{subject}" in style else style + " {subject}"
    if (ldir / "journey.json").exists() or (ldir / "mv.json").exists():  # a 🧭 journey scene / 🎵 storyboard frame (sbNN/sN.png)
        if (ldir / "journey.json").exists():
            j = json.loads((ldir / "journey.json").read_text(encoding="utf-8"))
        else:
            import run_journey  # the renderer's own mv.json -> journey mapping (singer = lead)
            j = run_journey.mv_as_journey(json.loads((ldir / "mv.json").read_text(encoding="utf-8")))
        ch = json.loads((vdir / "chapter.json").read_text(encoding="utf-8"))
        sc = next(s for s in ch["scenes"] if s["id"] == p.stem)
        cast = j.get("cast", {})
        others = "; ".join(f"{n} is {c['look'] if isinstance(c, dict) else c}" for n, c in cast.items() if n in sc.get("with", []))
        # a noref scene describes the scene itself: giving the lead's full sheet to a scene she isn't in turns the
        # scene's other characters into the lead. The lead is only named if the scene prompt names her.
        if sc.get("noref"):
            subject = f"the scene, {sc['prompt']}"
        else:
            subject = f"{j['name']}, {j['character']}, {sc['prompt']}"
        return f"journey:{ldir.name}", subject + (f". In the scene: {others}" if others else ""), j.get("title", ldir.name), j["style"]
    subjects = json.loads((ROOT / "subjects.json").read_text(encoding="utf-8"))
    key = p.stem.split("_seed")[0] if not p.stem.startswith("seed") else "f-modern"
    lineage = json.loads((ldir / "lineage.json").read_text(encoding="utf-8"))
    style = (vdir / "prompt.txt").read_text(encoding="utf-8").strip()
    return key, subjects[key]["text"], lineage.get("title", ldir.name), style


def style_lock(title, style_prompt):
    """medium + the style's own visual traits, phrased as a constraint on every frame"""
    head, _, traits = style_prompt.partition("{subject}")
    traits = traits.lstrip(" .,").strip()
    if not traits:  # prompt without a slot: use everything
        traits = style_prompt
    traits = re.sub(r"\s+", " ", traits)[:420].rstrip(" ,.")
    if THREE_D.search(style_prompt):
        medium = "3D animated film"
        guard = "keep the same rendering, proportions and lighting as the reference"
    elif PAINTED.search(style_prompt):
        medium = "painted 2D animation"
        guard = "keep the brushwork, paper texture and palette of the reference; no photorealism, no 3D rendering"
    else:
        medium = "hand-drawn 2D anime animation"
        guard = "keep the linework, flat cel shading and palette of the reference; no photorealism, no 3D rendering"
    return medium, f"{traits}. Every frame keeps the exact art style of <Picture 1>: {guard}"


# monsters, undead and bosses keep their gravitas even in a cozy toy-like style: a more ominous approach, the weight of
# those characters stays intact
MENACE_KEY = re.compile(r"^(z-|b-|boss)", re.I)
MENACE_LABEL = re.compile(r"\b(boss|dangerous|undead|zombie|monster|shambler)\b", re.I)
# "ominous ... light dimming, shadows deepening" darkened the whole clip: the mood now comes from motion and sound,
# and the scene's own lighting is kept
MENACE = ("Mood: eerie and unsettling, played completely straight despite the cozy toy-like look: slow, deliberate, "
          "unnatural movement with real weight, uncanny stillness between motions, low camera angles that make it loom; "
          "never comedic, cute or bouncy. Keep the scene's original lighting, brightness and colours exactly as in "
          "<Picture 1>: no darkening, no dimming.")


def is_menacing(key):
    if MENACE_KEY.match(key):
        return True
    subjects = json.loads((ROOT / "subjects.json").read_text(encoding="utf-8"))
    return bool(MENACE_LABEL.search((subjects.get(key) or {}).get("label", "")))


def build(image, motion, camera="the camera slowly pushes in", shots=None, sound="", music="", line="", voice="", vocal="", face="", sfx="",
          speaker="", soundscape=""):
    # sfx: action sounds IN ORDER, each tied to a visible action ("the bolt clacks, a sharp crack of the shot"); they play before the line
    # vocal: an expressed, non-word sound ("a short amused giggle", "a weary sigh"); face: micro-expressions
    # line: one short spoken NPC-style bark (4-8 words fits 5 s); voice: e.g. a clear, cocky young woman's voice
    key, subject, title, style = image_context(image)
    medium, lock = style_lock(title, style)
    who = subject.split(",")[0].strip()
    who = re.sub(r"^(a|an)\s+", "the ", who, flags=re.I)
    lines = [
        f"{medium[0].upper() + medium[1:]} in the style of {title}. {who[0].upper() + who[1:]} from <Picture 1> in their original scene: {subject}. "
        f"Art style: {lock}. The environment is constant throughout."
        # fasth3 can burn a spoken line into the frame as a subtitle, so say so explicitly
        + (" No subtitles, captions or on-screen text: spoken words are heard only." if line
           # with no line, "spoken words are heard" invites made-up speech
           else " No subtitles, captions or on-screen text.")
    ]
    menace = is_menacing(key)
    if menace:
        lines[0] += " " + MENACE
    # background ambience/drone is rated "meh" every time: with no explicit --sound, voices and SFX play over silence
    ambient = bool(sound)
    pron = "she" if key.startswith("f-") else "he" if key.startswith("m-") else "they"
    poss = {"she": "her", "he": "his"}.get(pron, "their")
    if face:  # micro-expressions read best stated as visible face changes
        motion = f"{motion.rstrip('. ')}; {poss} face shows {face.rstrip('. ')}"
    if vocal and not line:  # expressed, not said: no words at all
        motion = f"{motion.rstrip('. ')}, and {pron} lets out {vocal.rstrip('. ')} without saying any words"
        sound = f"{vocal.rstrip('. ')} from {voice or 'the character'}, no words" + (f", over {sound}" if sound else "")
        music = ""
    if line and speaker:  # multi-character scene (journeys): name who talks, no look to camera, nobody else speaks
        # "they ... says" in a crowded frame gives the line to the wrong person
        motion = f'{motion.rstrip(". ")}, then {speaker} says: "{line}"; only {speaker} speaks, everyone else stays silent'
        voice = voice or "a clear voice"
        sound = (f"{sfx.rstrip('. ')}, then " if sfx else "") + f'{voice} of {speaker} saying "{line}", lip-synced to {speaker} only'             + (f", over {sound}" if sound else "")
        music = ""
    elif line:  # the character speaks: put it in the action and lead the audio with it; no music over dialogue
        lead = f", {pron} lets out {vocal.rstrip('. ')}," if vocal else ","
        motion = f'{motion.rstrip(". ")}{lead} then {pron} looks at the camera and says: "{line}"'
        voice = voice or ("a clear young woman's voice" if pron == "she" else "a clear man's voice" if pron == "he" else "a clear voice")
        sound = (f"{sfx.rstrip('. ')}, then " if sfx else "") + (f"{vocal.rstrip('. ')} then " if vocal else "") \
            + f'{voice} saying "{line}", lip-synced' + (f", over {sound}" if sound else "")
        music = ""
    elif not vocal:  # no line: H3 invents gibberish speech. Describing the people as stoic and wordless works better
        # than mentioning speech at all ("no speech, no voices" made it worse)
        motion = f"{motion.rstrip('. ')}; every figure is stoic and wordless, lips pressed firmly together, faces still as masks"
    if sfx and not line:
        sound = f"{sfx.rstrip('. ')}" + (f", over {sound}" if sound else "")
    shots = shots or [f"{motion.rstrip('. ')}; {camera.rstrip('. ')}"]
    for i, sh in enumerate(shots, 1):
        opener = "The scene opens exactly on image 1; " if i == 1 else "Cut to "
        lines.append(f"SHOT {i}: {opener}{sh.rstrip('. ')}.")
    # generated music tends to come out off-key and H3 adds music unless told not to
    if menace and sound:  # its sounds are deep and heavy too (still tied to visible actions, no drone bed)
        sound = f"{sound.rstrip('. ')}, every sound eerie and unsettling"
    silent = not line and not vocal
    if silent and sound:
        # lead with the soundscape as the ONLY sound; no mention of speech/voices and no "silence between sounds" (gaps get filled with babble)
        sound = f"Only the sounds of {soundscape or 'the action'} can be heard: {sound.rstrip('. ')}, continuous from start to end"
    audio = ", ".join(x.rstrip(". ") for x in (sound, music) if x)
    if not music:
        audio = (audio + "; " if audio else "") + "no music" + ("" if ambient or silent else ", no background hum or drone, clean silence between sounds")
    if audio:
        lines.append(f"Audio: {audio}.")
    return "\n".join(lines)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("image"); ap.add_argument("--motion", required=True)
    ap.add_argument("--camera", default="the camera slowly pushes in")
    ap.add_argument("--shot", action="append"); ap.add_argument("--sound", default=""); ap.add_argument("--music", default="")
    ap.add_argument("--line", default=""); ap.add_argument("--voice", default="")
    ap.add_argument("--vocal", default=""); ap.add_argument("--face", default=""); ap.add_argument("--sfx", default="")
    a = ap.parse_args()
    print(build(a.image, a.motion, a.camera, a.shot, a.sound, a.music, a.line, a.voice, a.vocal, a.face, a.sfx, getattr(a, "speaker", "")))
