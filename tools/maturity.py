"""Maturity dial for the 📖 Nev Novel (a tactile control, from kids' cartoons all the way up).

Seven discrete stops (a vintage TV-channel knob in the deck): Preschool, Kids, Family, Tween, Teen, Young adult, Mature.
A value is {stop: 0-6, label}. Each stop says what the STORY may hold (vocab, peril, conflict, complexity, theme darkness, endings) and how the PICTURES look
(shape language, palette, how violence is framed, lighting).

Each stop has a ceiling (in the author rules and in the image steer cue). Preschool to Young adult: no sexual content, no graphic gore, fully clothed;
  at Preschool / Kids / Family no on-screen injury or blood at all; violence below Teen is slapstick or implied.
Mature: graphic violence and sexual content between consenting adults allowed, at the discretion of the user and the model
  writing the story (this workflow may run on other models). At EVERY stop: adults only in anything romantic or sexual, never anyone under 18.

  python tools/maturity.py [stop|label]      print the table / one stop in words
Standard library only."""
import json
import sys

DEFAULT_STOP = 4  # Teen: the deck's default

STOPS = [
    {"stop": 0, "label": "Preschool", "feels_like": "gentle toddler cartoons; simple, kind, no peril, problems solved by sharing",
     "story": "tiny vocabulary and short sentences; no peril and no villain, only small worries (a lost toy, a rainy day) solved by sharing and kindness; one idea at a time; a warm happy ending every time",
     "pictures": "round soft shapes, bright primary colours, big smiles and simple faces, even gentle light, nothing frightening",
     "ceiling": "no injury, no blood, nothing scary, fully clothed"},
    {"stop": 1, "label": "Kids", "feels_like": "Saturday-morning cartoons; goofy villains, slapstick, clear good vs bad",
     "story": "playful vocabulary and jokes; silly peril and goofy villains who always fail; clear good against bad; slapstick instead of harm; simple plots with a twist; cheerful triumphant endings",
     "pictures": "bold bouncy shapes, saturated candy colours, big expressive faces and exaggerated poses, bright cheerful lighting, slapstick mishaps with no injury",
     "ceiling": "slapstick only, no injury or blood, fully clothed"},
    {"stop": 2, "label": "Family", "feels_like": "all-ages animated features; real stakes, a sad moment, an unpreachy lesson",
     "story": "warm clear vocabulary that works for every age; real stakes and a genuinely sad moment; villains with motives; humour and heart together; an unpreachy lesson; hopeful, earned endings",
     "pictures": "warm polished shapes, rich harmonious colour, expressive acting, golden storybook light, danger shown by shadow and reaction, never injury",
     "ceiling": "no on-screen injury or blood, danger implied, fully clothed"},
    {"stop": 3, "label": "Tween", "feels_like": "adventure for 10-13; friendship drama, scarier peril, mysteries",
     "story": "quick, witty vocabulary; scarier peril and real mysteries; friendship drama, rivalry and loyalty tested; mild loss; heroes make mistakes; bittersweet-leaning but hopeful endings",
     "pictures": "dynamic angular shapes, vivid contrast colours, a bit edgier energy, dramatic rim light, scary things seen as silhouettes and reactions, no injury shown",
     "ceiling": "peril implied or comic, no blood, fully clothed"},
    {"stop": 4, "label": "Teen", "feels_like": "PG-13; romance, loss, action with consequences, grey characters",
     "story": "natural modern vocabulary; first romance (chaste) and real loss; action with consequences; characters in shades of grey; secrets and betrayals; endings can be bittersweet or open",
     "pictures": "sharper cleaner shapes, moodier colour and deeper shadow, more cinematic light, fights shown through motion and aftermath, never wounds in detail",
     "ceiling": "non-graphic, violence implied, adult-only romance kept chaste, fully clothed"},
    {"stop": 5, "label": "Young adult", "feels_like": "YA novels; identity, betrayal, the cost of war, heavier choices",
     "story": "mature but accessible vocabulary; identity and belonging, betrayal, the human cost of war and power; heavy choices with no clean answer; trauma and its aftermath; hard-won, ambiguous endings",
     "pictures": "cinematic grit, desaturated palette with one accent colour, hard directional light and long shadows, grounded textures, violence as weight and aftermath without detail",
     "ceiling": "non-graphic, no gore, romance only between adults and tasteful, fully clothed"},
    # Mature: adult fiction with no content cap of its own; graphic violence and sexual content between consenting adults are allowed,
    # at the discretion of the user and the model writing the story (the workflow may run on other models). Only the ADULTS-ONLY line is fixed.
    {"stop": 6, "label": "Mature", "feels_like": "adult fiction; may include graphic violence and sexual content between consenting adults, at the discretion of the user and the model",
     "story": "adult vocabulary and subtext; grief, moral ambiguity, trauma, politics and power; slow complex plots with consequences that last; violence and sexuality may be shown "
              "explicitly when the user and the model choose to; endings unresolved or tragic when true",
     "pictures": "painterly, shadowed, unflinching framing, muted earth palette with deep darks, chiaroscuro light, faces carry the weight",
     "ceiling": "anything sexual involves consenting adults only, never anyone under 18"},
]

CEILING = ("At every stop: anything romantic or sexual involves adults only, never anyone under 18. Preschool to Young adult: no sexual content, no graphic gore, "
           "characters fully clothed; at Preschool / Kids / Family no on-screen injury or blood at all, and violence below Teen is slapstick or implied. "
           "Mature: graphic violence and sexual content between consenting adults are allowed, at the discretion of the user and the model writing the story.")

LABELS = [s["label"] for s in STOPS]


def clamp_stop(v, default=DEFAULT_STOP):
    try:
        return max(0, min(len(STOPS) - 1, int(round(float(v)))))
    except (TypeError, ValueError):
        return default


def stop_of(v):
    """a value ({stop, label} / int / label string / None) -> the stop dict (None -> the default stop)"""
    if isinstance(v, dict):
        if v.get("stop") is not None:
            return STOPS[clamp_stop(v["stop"])]
        v = v.get("label")
    if isinstance(v, str):
        for s in STOPS:
            if s["label"].lower() == v.strip().lower() or s["label"].lower().replace(" ", "-") == v.strip().lower():
                return s
        try:
            return STOPS[clamp_stop(float(v))]
        except ValueError:
            return STOPS[DEFAULT_STOP]
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return STOPS[clamp_stop(v)]
    return STOPS[DEFAULT_STOP]


def clean(v):
    """validate a maturity value from a POST body / file -> {stop, label}, or None when absent / unusable"""
    if isinstance(v, dict):
        v = v["stop"] if v.get("stop") is not None else v.get("label")
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, str):
        t = v.strip().lower().replace("-", " ")
        hit = next((x for x in STOPS if x["label"].lower() == t), None)
        if hit:
            return {"stop": hit["stop"], "label": hit["label"]}
        try:
            v = float(t)
        except ValueError:
            return None
    if isinstance(v, (int, float)) and v == v and abs(v) != float("inf"):
        x = STOPS[clamp_stop(v)]
        return {"stop": x["stop"], "label": x["label"]}
    return None


def words(v):
    s = stop_of(v)
    return f"{s['label']} ({s['stop']}/6, {s['feels_like']})"


def describe(v):
    """for feedback.py explore / inbox: the stop and what it means, with the ceiling"""
    s = stop_of(v)
    return (f"{s['label']} [{s['stop']}/6: {s['feels_like']}]; story: {s['story']}; pictures: {s['pictures']}; ceiling: {s['ceiling']} "
            "(always: adults only in anything romantic or sexual)")


def cue(v, max_words=None):
    """the maturity part of the image steer cue: (pictures clause, ceiling clause) -- the ceiling is never dropped"""
    s = stop_of(v)
    return s["pictures"], s["ceiling"]


def table():
    return [dict(s) for s in STOPS]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(describe(sys.argv[1]))
    else:
        for s in STOPS:
            print(f"{s['stop']} {s['label']:<12} {s['feels_like']}")
        print(CEILING)
        json.dumps(table())
