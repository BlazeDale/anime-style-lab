"""🌌 Explore mode state (a free-form mode where the agent explores a topic on its own, with a 15 minute stop
timer: writing stops and a Continue button must be pressed to resume).

  python tools/explore_state.py status     prints the state as JSON (active, left seconds, reason, ...)
  python tools/explore_state.py active     exit code 0 if exploring is active (timer not run out, not stopped), else 1: check it before
                                           writing more episodes

State file feedback/explore.json: {active, until (epoch), started, by, stopped?, presence (0-100), emotion (an EMOTION ATLAS value, tools/atlas.py: {probe, blend [{id, name, w} x3], genre,
secondary, mix, intensity, valence, arousal}; the old 8-emotion wheel {primary, secondary, mix, intensity} is migrated onto the matching atlas nodes), cores [{id, name, probe, blend,
weight 0-1, status active|resolved}] (up to 5 active: the story's emotional through-lines, stackable), maturity {stop 0-6, label} (tools/maturity.py; HARD CEILING at every stop: mature
themes only, no sexual content, no graphic gore, romance only between adults, fully clothed), formality {genre, secondary, mix, intensity, level, formality_level}}.
formality is now the FORMALITY ATLAS (tools/formality_atlas.py, explore/formality_atlas.json): {probe {x, y}, blend [{id, name, w} x3], genre (top node name),
secondary, mix, intensity (probe distance from the centre), level (-100 casual .. +100 formal, from y), formality_level}. Older shapes: the joypad THUMBSTICK: centre = Everyday; the rim carries 12 sub-genres (FORMALITY_RIM, clockwise from the top, 30 degrees apart,
formal on the upper half, casual below); angle = the genre or a blend of the two nearest (mix = the secondary's share 0-0.5), distance = intensity 0-1, the
vertical part = level -100 (casual) .. +100 (formal), formality_level = 50 + level/2. It drives composition / staging and the caption voice (FORMALITY_HINTS);
in the player it only changes the caption typography. A plain number 0-100 (the retired fader) is still accepted.
presence = the "cinematic presence" knob = how the PICTURES are composed (0 Intimate: close, quiet, personal .. 50 Filmic: composed, classic framing ..
100 Epic: vast, dramatic, grand); emotion = the emotion wheel (angle = which emotion, or a blend of the two nearest; mix = the secondary's share
0-0.5; intensity 0-1; primary null = neutral, no steer). Claude lets them drive topic, shot scale, framing and light (presence) and captions,
palette and mood (emotion), and writes them into each episode.json as `presence` / `emotion`. The player never animates pictures: they only
set hold time and the crossfade / caption tint. Expiry is computed on read (no thread): once
now > until the state reads active=false with reason "timer" (the page then shows a Continue button that must be pressed).
serve_gallery uses these same functions (POST /api/explore ops start | continue | stop). Standard library only."""
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "feedback" / "explore.json"
EPISODES = ROOT / "explore"
MINUTES = 15
EMOTIONS = ["joy", "wonder", "awe", "tension", "dread", "melancholy", "longing", "serenity"]  # around the wheel, neighbours blend (same order as the page)
FORMALITY_RIM = ["Courtly", "Ritual", "Martial", "Diplomatic", "Festive", "Domestic", "Feral", "Street", "Slacker", "Smart-casual", "Professional", "Academic"]
FORMALITY_HINTS = {  # genre -> pictures · caption voice (same table as the page)
    "Everyday": "relaxed but composed, ordinary life done well · plain-spoken captions",
    "Feral": "untamed, chaotic, wild-haired, nothing arranged · breathless fragments",
    "Slacker": "rumpled, lounging, unmade beds and couches · lazy, deadpan captions",
    "Street": "candid, graffiti, sneakers, caught in passing · slangy captions",
    "Domestic": "homey, pajamas, kitchen tables, mess of real life · warm, chatty captions",
    "Festive": "parties, festivals, crowds, colour and play · exclamations",
    "Smart-casual": "neat but easy, cafés and weekends · light, friendly captions",
    "Professional": "offices, uniforms of work, tidy desks · crisp, matter-of-fact captions",
    "Academic": "libraries, gowns, lecterns, quiet order · measured, learned captions",
    "Diplomatic": "state dinners, flags, protocol, careful distance · courteous, guarded captions",
    "Martial": "parade grounds, ranks, drill, strict symmetry · clipped, commanding captions",
    "Ritual": "vestments, altars, processions, sacred ceremony · liturgical captions",
    "Courtly": "thrones, regalia, absolute symmetry and hierarchy · high, archaic captions",
}
DEAD = 0.12
MAX_ACTIVE_CORES, MAX_CORES = 5, 12
DEFAULT_CORE_WEIGHT = 0.6
ADJ = {"joy": "joyful", "wonder": "wondering", "awe": "awed", "tension": "tense", "dread": "dreadful", "melancholy": "melancholic",
       "longing": "yearning", "serenity": "serene"}


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def clean_tune(body):
    """validate the knob + wheel values from a POST body -> only the keys that were given and valid"""
    out = {}
    body = body or {}
    if body.get("presence") is not None:
        try:
            out["presence"] = round(max(0.0, min(100.0, float(body["presence"]))), 1)
        except (TypeError, ValueError):
            pass
    fo = body.get("formality")
    if isinstance(fo, dict) and (isinstance(fo.get("probe"), dict) or isinstance(fo.get("blend"), list)):
        v = clean_atlas_value(fo, None, "formality")  # the Formality Atlas value: {probe, blend, genre, ...}
        if v:
            out["formality"] = v
    elif isinstance(fo, dict):
        g = fo.get("genre")
        if g in FORMALITY_RIM or g == "Everyday":
            sec = fo.get("secondary") if fo.get("secondary") in FORMALITY_RIM and fo.get("secondary") != g and g != "Everyday" else None
            try:
                mix = max(0.0, min(0.5, float(fo.get("mix") or 0))) if sec else 0.0
                inten = max(0.0, min(1.0, float(fo.get("intensity") or 0))) if g != "Everyday" else 0.0
                lvl = fo.get("level")
                lvl = formality_level_of(g, sec, mix, inten) if lvl is None else max(-100.0, min(100.0, float(lvl)))
            except (TypeError, ValueError):
                mix, inten, lvl = 0.0, 0.0, 0.0
            if inten <= 0:
                g, sec, mix, lvl = "Everyday", None, 0.0, 0
            out["formality"] = {"genre": g, "secondary": sec, "mix": round(mix, 2), "intensity": round(inten, 2), "level": round(lvl), "formality_level": 50 + round(lvl) / 2}
    elif fo is not None:
        try:
            out["formality"] = round(max(0.0, min(100.0, float(fo))), 1)
        except (TypeError, ValueError):
            pass
    e = body.get("emotion")
    if isinstance(e, dict):
        v = clean_emotion(e)
        if v:
            out["emotion"] = v
    if isinstance(body.get("cores"), list):
        out["cores"] = clean_cores(body["cores"])
    if body.get("maturity") is not None:
        import maturity as mt
        m = mt.clean(body["maturity"])
        if m:
            out["maturity"] = m
    return out


def migrate_emotion(e, atlas=None):
    """the retired 8-emotion wheel {primary, secondary, mix, intensity} -> an Emotion Atlas value on the matching legacy nodes (ids joy, wonder, awe, tension, dread,
    melancholy, longing, serenity); neutral / unusable -> the neutral value"""
    import atlas as fa
    atlas = atlas or fa.load(kind="emotion")
    if not isinstance(e, dict) or e.get("primary") not in EMOTIONS:
        return fa.neutral("emotion")
    nd = fa.by_id(atlas)
    pri = e["primary"]
    sec = e.get("secondary") if e.get("secondary") in EMOTIONS and e.get("secondary") != pri else None
    try:
        mix = max(0.0, min(0.5, float(e.get("mix") or 0))) if sec else 0.0
        inten = max(0.0, min(1.0, float(e.get("intensity") or 0)))
    except (TypeError, ValueError):
        mix, inten = 0.0, 0.0
    if pri not in nd or inten <= 0:
        return fa.neutral("emotion")
    bl = [(pri, 1 - mix)] + ([(sec, mix)] if sec and sec in nd else [])
    tot = sum(w for _, w in bl)
    x = sum(nd[i]["x"] * w for i, w in bl) / tot
    y = sum(nd[i]["y"] * w for i, w in bl) / tot
    v = clean_atlas_value({"probe": {"x": x, "y": y}, "blend": [{"id": i, "w": w} for i, w in bl], "intensity": inten}, atlas)
    v["legacy"] = True   # keeps its own blend (the page does not re-derive it from the probe)
    return v


def clean_emotion(e, atlas=None):
    """any emotion value (atlas value, old wheel object) -> a valid atlas value, or None when unusable"""
    if not isinstance(e, dict):
        return None
    if "primary" in e and not isinstance(e.get("blend"), list) and not isinstance(e.get("probe"), dict):
        return migrate_emotion(e, atlas)
    if isinstance(e.get("probe"), dict) or isinstance(e.get("blend"), list):
        return clean_atlas_value(e, atlas, "emotion")
    return None


def _slug_id(s, taken):
    import re
    base = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:20] or "core"
    out, n = base, 2
    while out in taken:
        out, n = f"{base}-{n}", n + 1
    return out


def clean_cores(raw, atlas=None):
    """validate the stackable emotional cores from a POST body / saga.json -> a list of {id, name, probe, blend, weight 0-1, status, history?}.
    A core needs a usable probe / blend; at most MAX_ACTIVE_CORES stay active (later ones are dropped), MAX_CORES in all; ids are made unique"""
    if not isinstance(raw, list):
        return []
    import atlas as fa
    atlas = atlas or fa.load(kind="emotion")
    out, taken, active = [], set(), 0
    for c in raw:
        if not isinstance(c, dict):
            continue
        v = clean_emotion(c, atlas)
        if not v or not v.get("blend"):
            continue
        status = "resolved" if c.get("status") == "resolved" else "active"
        if status == "active" and active >= MAX_ACTIVE_CORES:
            continue
        try:
            wt = max(0.0, min(1.0, float(c["weight"]))) if c.get("weight") is not None else DEFAULT_CORE_WEIGHT
        except (TypeError, ValueError):
            wt = DEFAULT_CORE_WEIGHT
        cid = _slug_id(c.get("id") or c.get("name") or v["genre"], taken)
        taken.add(cid)
        name = " ".join(str(c.get("name") or v["genre"]).split())[:60] or v["genre"]
        core = {"id": cid, "name": name, "probe": v["probe"], "blend": v["blend"], "weight": round(wt, 2), "status": status}
        hist = [h for h in (c.get("history") or []) if isinstance(h, dict)][:60]
        if hist:
            core["history"] = hist
        out.append(core)
        active += status == "active"
        if len(out) >= MAX_CORES:
            break
    return out


def clean_atlas_value(fo, atlas=None, kind="formality"):
    """validate an Atlas value (formality or emotion): probe clamped into the unit disc, blend ids must exist (unknown ones dropped, weights renormalised to 1);
    with no usable blend the value is recomputed from the probe. None when there is neither a probe nor a blend"""
    import atlas as fa
    atlas = atlas or fa.load(kind=kind)
    kind = fa.kind_of(atlas)
    nd = fa.by_id(atlas)
    try:
        pr = fo.get("probe") if isinstance(fo.get("probe"), dict) else None
        x, y = (float(pr["x"]), float(pr["y"])) if pr else (None, None)
    except (KeyError, TypeError, ValueError):
        x = y = None
    if x is not None and not (math.isfinite(x) and math.isfinite(y)):
        x = y = None
    bl = []
    for b in (fo.get("blend") or [])[:3]:
        try:
            if isinstance(b, dict) and b.get("id") in nd:
                bl.append((b["id"], max(0.0, float(b.get("w", 0)))))
        except (TypeError, ValueError):
            pass
    tot = sum(w for _, w in bl)
    if x is not None and nd and (not bl or tot <= 0):
        return fa.value_at(atlas, x, y)
    if not bl or tot <= 0:
        return None
    blend = [{"id": i, "name": nd[i]["name"], "w": round(w / tot, 2)} for i, w in bl]
    w1, w2 = blend[0]["w"], blend[1]["w"] if len(blend) > 1 else 0.0
    if x is None:
        x, y = nd[blend[0]["id"]]["x"], nd[blend[0]["id"]]["y"]
    x, y = fa._clamp_disc(x, y)
    try:
        inten = max(0.0, min(1.0, float(fo["intensity"])))
    except (KeyError, TypeError, ValueError):
        inten = min(1.0, math.hypot(x, y))
    out = {"probe": {"x": round(x, 3), "y": round(y, 3)}, "blend": blend, "genre": blend[0]["name"], "secondary": blend[1]["name"] if len(blend) > 1 and w2 >= 0.05 else None,
           "mix": round(min(0.5, w2 / (w1 + w2)), 2) if len(blend) > 1 and w1 + w2 else 0.0, "intensity": round(inten, 2)}
    if fo.get("warped") is True:
        out["warped"] = True   # taken from a pulled / pushed map: the blend is the user's, keep it as given
    if fo.get("legacy") is True:
        out["legacy"] = True   # a migrated wheel value keeps its own blend too
    if kind == "emotion":
        out.update(fa._extras(atlas, kind, x, y, blend))
    else:
        try:
            lvl = int(round(max(-100.0, min(100.0, float(fo["level"])))))
        except (KeyError, TypeError, ValueError):
            lvl = int(round(max(-1.0, min(1.0, y)) * 100))
        out.update({"level": lvl, "formality_level": 50 + lvl / 2})
    return out


def formality_level_of(genre, secondary, mix, intensity):
    """the stick's vertical part, -100 (casual, down) .. +100 (formal, up), the same maths as the page"""
    if genre not in FORMALITY_RIM or not intensity:
        return 0
    i = FORMALITY_RIM.index(genre)
    a = i * 30
    if secondary in FORMALITY_RIM:
        a += (1 if (FORMALITY_RIM.index(secondary) - i) % 12 == 1 else -1) * (mix or 0) * 30
    return round(math.cos(math.radians(a)) * (DEAD + intensity * (1 - DEAD)) * 100)


def presence_word(v):
    v = 50 if v is None else v
    return "Intimate" if v <= 12 else "leaning intimate" if v < 38 else "Filmic" if v <= 62 else "leaning epic" if v < 88 else "Epic"


def formality_words(f):
    """'Martial -> Diplomatic 70/30 · strong' / 'Everyday · neutral' for the stick object; the old words for a number"""
    if isinstance(f, dict) and f.get("blend"):
        import formality_atlas as fa
        return fa.blend_words(f)
    if isinstance(f, dict):
        g, inten = f.get("genre") or "Everyday", f.get("intensity") or 0
        if g == "Everyday" or not inten:
            return "Everyday · neutral"
        sec, mix = f.get("secondary"), f.get("mix") or 0
        name = f"{g} -> {sec} {round((1 - mix) * 100)}/{round(mix * 100)}" if sec else g
        return f"{name} · {'subtle' if inten < 0.34 else 'moderate' if inten < 0.67 else 'strong'}"
    return formality_word(f)


def formality_word(v):
    v = 50 if v is None else v
    return "Casual" if v <= 12 else "leaning casual" if v < 38 else "Natural" if v <= 62 else "leaning formal" if v < 88 else "Formal"


def emotion_words(e):
    """an Emotion Atlas value: 'Bittersweet 48% · Nostalgia 32% · Saudade 20%'; neutral: 'neutral (no emotional steer)'. The retired wheel object still reads the old way:
    'melancholic longing · strong (longing -> melancholy 70/30)'"""
    if isinstance(e, dict) and (isinstance(e.get("blend"), list) or isinstance(e.get("probe"), dict)):
        import atlas as fa
        return fa.blend_words(e, kind="emotion")
    if not e or not e.get("primary"):
        return "neutral (no emotional steer)"
    i = e.get("intensity") or 0
    lvl = "subtle" if i < 0.34 else "moderate" if i < 0.67 else "strong"
    sec, mix = e.get("secondary"), e.get("mix") or 0
    name = f"{ADJ[sec]} {e['primary']}" if sec and mix >= 0.15 else e["primary"]
    blend = f" ({e['primary']} -> {sec} {round((1 - mix) * 100)}/{round(mix * 100)})" if sec else ""
    return f"{name} · {lvl}{blend}"


def core_words(c):
    """one core in words: 'Saudade (weight 0.6, active): Saudade 60% · Nostalgia 40%'"""
    return f"{c.get('name') or c.get('genre')} (weight {float(c.get('weight', DEFAULT_CORE_WEIGHT)):g}, {c.get('status', 'active')})"


def cores_words(cores, atlas=None, detail=False):
    """the stacked cores for the [ACT] output: heavy first; with detail, each core's picture / voice / story beats from the atlas"""
    cs = [c for c in (cores or []) if isinstance(c, dict)]
    if not cs:
        return "none"
    import atlas as fa
    atlas = atlas or fa.load(kind="emotion")
    out = []
    for c in sorted(cs, key=lambda c: (c.get("status") == "resolved", -float(c.get("weight", DEFAULT_CORE_WEIGHT)))):
        s = core_words(c)
        if detail and c.get("status", "active") == "active":
            n = fa.top_node(c, atlas)
            if n:
                s += f" [{fa.blend_words(c, kind='emotion')}; pictures: {n.get('picture', '')}; captions: {n.get('voice', '')}; story beats: {n.get('beats', '')}]"
        out.append(s)
    return "; ".join(out)


def maturity_words(m):
    import maturity as mt
    return mt.describe(m) if m else "not set (assume Teen; the hard ceiling always applies)"


def describe(st, detail=False):
    """one line of what the knob + dial + atlases + cores say, for the [ACT] output and `feedback.py explore` (detail adds the cores' lines)"""
    p = st.get("presence")
    fo = st.get("formality")
    em = st.get("emotion")
    if isinstance(em, dict) and em.get("blend"):
        import atlas as fa
        emw = fa.describe_value(em, kind="emotion")
    else:
        emw = emotion_words(em)
    head = f"presence {50 if p is None else p:g} ({presence_word(p)}); maturity {maturity_words(st.get('maturity'))}; emotion of the moment {emw}; cores {cores_words(st.get('cores'), detail=detail)}"
    if isinstance(fo, dict) and fo.get("blend"):
        import formality_atlas as fa
        return f"{head}; formality {fa.describe_value(fo)}"
    if isinstance(fo, dict):
        g = fo.get("genre") or "Everyday"
        lvl = fo.get("level") or 0
        return f"{head}; formality {formality_words(fo)} (level {lvl:+d}; {FORMALITY_HINTS.get(g, '')})"
    return f"{head}; formality {50 if fo is None else fo:g} ({formality_word(fo)})"


def view(raw, now=None):
    """raw state -> what everyone reads: {active, until, started, by, left, reason, paused, minutes}.
    reason: "timer" (ran out: needs Continue), "stopped" (user pressed Stop), "idle" (never started), "" (active)"""
    now = time.time() if now is None else now
    raw = raw or {}
    until = float(raw.get("until") or 0)
    if raw.get("active") and now <= until:
        return {"active": True, "until": until, "started": raw.get("started"), "by": raw.get("by", ""), "left": round(until - now, 1),
                "reason": "", "paused": False, "minutes": MINUTES, "presence": raw.get("presence"), "emotion": raw.get("emotion"), "formality": raw.get("formality"),
                "cores": raw.get("cores"), "maturity": raw.get("maturity")}
    if raw.get("active"):  # the 15 minutes ran out
        reason = "timer"
    else:
        reason = "stopped" if raw.get("stopped") else "idle"
    return {"active": False, "until": until, "started": raw.get("started"), "by": raw.get("by", ""), "left": 0,
            "reason": reason, "paused": reason == "timer", "minutes": MINUTES, "presence": raw.get("presence"), "emotion": raw.get("emotion"),
            "formality": raw.get("formality"), "cores": raw.get("cores"), "maturity": raw.get("maturity")}


def state(path=FILE, now=None):
    return view(_read(path), now)


def is_active(path=FILE, now=None):
    return state(path, now)["active"]


def _carry(cur, tune):
    """the knob + wheel values survive start / continue / stop; a request that carries new ones replaces them"""
    out = {k: cur[k] for k in ("presence", "emotion", "formality", "cores", "maturity") if cur.get(k) is not None}
    out.update(tune or {})
    return out


def start(path=FILE, by="gallery", now=None, tune=None):
    """▶ Start exploring: a fresh 15 minute window (tune = clean_tune(body): presence / emotion)"""
    now = time.time() if now is None else now
    raw = {"active": True, "started": now, "until": now + MINUTES * 60, "by": by, **_carry(_read(path), tune)}
    _write(path, raw)
    return view(raw, now)


def cont(path=FILE, by="gallery", now=None, tune=None):
    """▶ Continue exploring: another 15 minutes from now (keeps the original start time while still running)"""
    now = time.time() if now is None else now
    cur = _read(path)
    started = cur.get("started") if cur.get("active") and now <= float(cur.get("until") or 0) else now
    raw = {"active": True, "started": started or now, "until": now + MINUTES * 60, "by": by, **_carry(cur, tune)}
    _write(path, raw)
    return view(raw, now)


def tune(path=FILE, by="gallery", now=None, values=None):
    """change the knob + wheel without touching the timer (the page's Apply while exploring)"""
    now = time.time() if now is None else now
    raw = {**_read(path), **(values or {})}
    _write(path, raw)
    return view(raw, now)


def stop(path=FILE, by="gallery", now=None):
    now = time.time() if now is None else now
    cur = _read(path)
    raw = {"active": False, "started": cur.get("started"), "until": cur.get("until", 0), "by": by, "stopped": now, **_carry(cur, None)}
    _write(path, raw)
    return view(raw, now)


def episodes(root=ROOT):
    """newest first: [{id, title, topic, status, created, shots, rendered}] from explore/NNN-slug/episode.json"""
    out = []
    d = Path(root) / "explore"
    for f in sorted(d.glob("*/episode.json"), reverse=True) if d.exists() else []:
        e = _read(f)
        if not e:
            continue
        sh = e.get("shots") or []
        out.append({"id": e.get("id") or f.parent.name, "title": e.get("title", ""), "topic": e.get("topic", ""), "status": e.get("status", "draft"),
                    "created": e.get("created", ""), "shots": len(sh), "rendered": sum(1 for s in sh if (f.parent / f"{s.get('id')}.png").is_file())})
    for f in sorted(d.glob("sagas/*/ch*/episode.json"), reverse=True) if d.exists() else []:  # 📖 saga chapters
        e = _read(f)
        if not e:
            continue
        sh = e.get("shots") or []
        out.append({"id": e.get("id") or f"{f.parent.parent.name}/{f.parent.name}", "title": e.get("title", ""), "topic": e.get("topic", ""), "status": e.get("status", "draft"),
                    "created": e.get("created", ""), "shots": len(sh), "rendered": sum(1 for s in sh if (f.parent / f"{s.get('id')}.png").is_file())})
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    st = state()
    if cmd == "active":
        sys.exit(0 if st["active"] else 1)
    print(json.dumps(st, indent=2))
    print(describe(st))
