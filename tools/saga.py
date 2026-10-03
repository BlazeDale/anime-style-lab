"""📖 Sagas: a visual-novel / graphic-novel story that Claude invents and keeps continuous (the agent invents the lore, characters, world and environments
and keeps continuity as the story goes).

Claude is the AUTHOR; this tool is the saga BIBLE + the checks. Data (explore/sagas/NNN-slug/):
  saga.json     {id, title, logline, created, style ("...{subject}..." look only), ref_resolution?, world {setting, rules, tech_or_magic, tone},
                 lore [{topic, text}], factions [{name, aim, look}], places [{name, look, first_chapter}],
                 cast {name: {look (appearance only), role, voice, ref (png), ref_crop?, status, first_chapter}},
                 timeline [{chapter, event}], threads [{id, text, opened, status open|closed, closed_in}]}
  chNN/episode.json  the Explore episode schema + saga, chapter, summary, opens, closes; per shot also with [cast names], place, camera?, narration,
                 dialogue [{who, text, off?}] (0-4 lines), noref / nofigure (like journeys)
  chNN/eK.png   rendered by tools/explore_render.py explore/sagas/NNN-slug/chNN (refs of the characters in `with` are fed as reference images)

  python tools/saga.py new "<title>" --logline "..." --style "...{subject}..." [--setting ... --rules ... --tech ... --tone ...]
  python tools/saga.py current [--json]                 the active (newest) saga, its next chapter number, the chapter in flight
  python tools/saga.py bible [<saga>] [--brief]         the bible for Claude to READ before writing (cast looks, places, open threads, last 3 chapters)
  python tools/saga.py cast  <saga> "<name>" --look "..." --role "..." --voice "..." [--status alive] [--update]
  python tools/saga.py place <saga> "<name>" --look "..." [--update]
  python tools/saga.py lore  <saga> "<topic>" --text "..." [--update]
  python tools/saga.py faction <saga> "<name>" --aim "..." --look "..." [--update]
  python tools/saga.py thread <saga> open "<text>" [--id t7] | close <id> [--in chNN]
  python tools/saga.py chapter <saga> chapter.json [--replace]   validate + write chNN/episode.json, update timeline + thread statuses
  python tools/saga.py setref <saga> "<name>" ch01/e3.png [--crop x0,y0,x1,y1] | --clear
  python tools/saga.py cores <saga> show                 the saga's stacked EMOTIONAL CORES (through-lines) + maturity, with each core's history
  python tools/saga.py cores <saga> set [--file cores.json] [--maturity "Teen"]   save the cores (default: the deck's, from feedback/explore.json) into saga.json (history kept by id)
  python tools/saga.py cores <saga> log <core> --chapter chNN --beat "..." [--how "..."]   record a beat that served a core (id or name)
  python tools/saga.py cores <saga> resolve <core> | reopen <core> | weight <core> 0.8     retire / revive a core, or change its weight
A saga's `cores` [{id, name, probe, blend, weight 0-1, status active|resolved, history [{chapter, beat, how}]}] (max 5 active) and `maturity` {stop 0-6, label} are SAVED PER SAGA in saga.json;
a new saga starts with the deck's. <saga> = the id (001-the-glass-harbour), its number, a unique part of the slug, or `current`. Duplicates are refused (--update edits an existing entry)."""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent
MAX_DIALOGUE = 4
# pacing (the dialogue per shot scales with the average time the next picture takes to render, so the story keeps the reader busy
# while it renders): each shot's READING time in the player should cover
# PACE_SHARE of the median image render time, so the story keeps moving while the next picture renders
PACE_SHARE = 0.6
PACE_FALLBACK_S = 38.0
VN_TYPE_MS = 34  # mirrors gallery_template.html vnTypeMs / vnReadMs


def beat_secs(text):
    """seconds the player spends on one line (typing + reading dwell), same formula as the template's vnBeatMs"""
    t = str(text or "").strip()
    if not t:
        return 0.0
    words = len(t.split())
    return (max(250, len(t) * VN_TYPE_MS) + max(2200, 900 + words * 330)) / 1000


def reading_secs(shot):
    """seconds of reading in one shot: the narration, then each dialogue line (a shot with neither shows its caption for its hold)"""
    beats = [shot.get("narration")] + [d.get("text") for d in (shot.get("dialogue") or []) if isinstance(d, dict)]
    s = sum(beat_secs(b) for b in beats)
    return s if s else float(shot.get("hold") or 6)


def render_median(times=None):
    """median GPU seconds per Qwen image (feedback/model_times.json via pipeline), fallback PACE_FALLBACK_S"""
    if times is None:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import pipeline
            times = pipeline.model_times().get("QI2.1") or []
        except Exception:
            times = []
    xs = sorted(float(x) for x in times if x)
    if not xs:
        return PACE_FALLBACK_S
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else (xs[m - 1] + xs[m]) / 2


def pacing(shots, render_s=None):
    """-> {render_s, target_s, per_shot [secs], short [(index, secs)], avg_s, ok}: shots whose reading time is under PACE_SHARE of a render"""
    r = render_median() if render_s is None else render_s
    target = round(PACE_SHARE * r, 1)
    per = [round(reading_secs(s), 1) for s in shots if isinstance(s, dict)]
    short = [(i, v) for i, v in enumerate(per, 1) if v < 0.8 * target]  # "don't have to be 100%": only shots well under count as short
    avg = round(sum(per) / len(per), 1) if per else 0.0
    return {"render_s": round(r, 1), "target_s": target, "per_shot": per, "short": short, "avg_s": avg, "ok": avg >= 0.95 * target}


# ---------------------------------------------------------------------------------------------------------------- story lint
# (beautiful pictures still need an entertaining story): catches the mechanical causes before a chapter renders. A chapter.json may (should) carry
#   scenes  [{title, shots: [first, last] (1-based, inclusive), goal, obstacle, turn, stakes}]   2-4 real scenes, each with someone wanting something against resistance
#   choices [{who, choice, cost}]                                                                  at least one decision by the lead that costs something
#   hook    "the open question the chapter ends on"
TELLING = re.compile(r"\b(had always|had never|never once|always had|used to|for years|in (his|her|their) life|the kind of (man|woman|person)|was the kind|she knew|he knew|"
                     r"they knew|felt like|the way you|which meant|it turned out|of course)\b", re.I)
STORY_FIELDS = ("goal", "obstacle", "turn", "stakes")


def _words(t):
    return len(str(t or "").split())


def story_lint(spec, shots, bible=None, n=None):
    """-> [warning]: telling vs showing, montage (a new place every shot), missing / thin scenes, no costly choice by the lead, no closing hook,
    every speaker sounding alike, a mystery opened and closed too fast"""
    out = []
    shots = [s for s in shots or [] if isinstance(s, dict)]
    if not shots:
        return out
    narr = sum(_words(s.get("narration")) for s in shots)
    dlg = sum(_words(d.get("text")) for s in shots for d in (s.get("dialogue") or []) if isinstance(d, dict))
    if narr + dlg and narr / (narr + dlg) > 0.45:
        out.append(f"story: telling, not showing: {round(100 * narr / (narr + dlg))}% of the words are narration (aim under 45%): let scenes play out in dialogue and action")
    tell = [i for i, s in enumerate(shots, 1) if TELLING.search(str(s.get("narration") or ""))]
    if len(tell) >= 3:
        out.append("story: summary / backstory narration in shots " + ", ".join(map(str, tell)) + " ('had always', 'used to', 'the way you'...): dramatise it or cut it")
    nonly = [i for i, s in enumerate(shots, 1) if str(s.get("narration") or "").strip() and not (s.get("dialogue") or [])]
    if len(nonly) > len(shots) // 2:
        out.append(f"story: {len(nonly)} of {len(shots)} shots are narration only: give more of them a voice in the scene")
    moves = sum(1 for a, b in zip(shots, shots[1:]) if (a.get("place") or "") != (b.get("place") or ""))
    scenes = spec.get("scenes") or []
    if not scenes:
        out.append("story: no `scenes` [{title, shots: [first, last], goal, obstacle, turn, stakes}]: plan 2-4 scenes where someone wants something against resistance")
        if len(shots) > 3 and moves / (len(shots) - 1) > 0.45:
            out.append(f"story: montage: the place changes {moves} times in {len(shots)} shots: stay in a scene long enough for it to build")
    else:
        if not 2 <= len(scenes) <= 4:
            out.append(f"story: {len(scenes)} scenes (2-4 keeps each one long enough to build)")
        for k, sc in enumerate(scenes, 1):
            miss = [f for f in STORY_FIELDS if not str((sc or {}).get(f) or "").strip()]
            rng = (sc or {}).get("shots") or []
            span = (int(rng[1]) - int(rng[0]) + 1) if isinstance(rng, list) and len(rng) == 2 and all(str(x).isdigit() for x in rng) else 0
            if miss:
                out.append(f"story: scene {k} ({(sc or {}).get('title') or '?'}) has no {', '.join(miss)}")
            if span and span < 3:
                out.append(f"story: scene {k} is only {span} shot(s): too short to build")
    lead = next(iter((bible or {}).get("cast") or {}), None)
    ch = [c for c in spec.get("choices") or [] if isinstance(c, dict) and str(c.get("choice") or "").strip() and str(c.get("cost") or "").strip()]
    if not ch:
        out.append("story: no `choices` [{who, choice, cost}]: the lead should decide something that costs her")
    elif lead and not any(c.get("who") == lead for c in ch):
        out.append(f"story: no costly choice by the lead ({lead}): she reacts instead of driving")
    blank = [i for i, s in enumerate(shots, 1) if (s.get("with") or []) and not s.get("nofigure") and not (s.get("faces") or {})
             and not re.search(r"\b(wide|extreme wide|establishing|silhouette|from behind|aerial)\b", str(s.get("camera") or ""), re.I)]
    if len(blank) >= 2:
        out.append("story: no `faces` cue in shots " + ", ".join(map(str, blank)) + " (character shots that aren't wide): say what each face shows in this moment, in physical terms (eyes, jaw, mouth, brows)")
    if not str(spec.get("hook") or "").strip():
        out.append("story: no `hook`: end on an open question the reader has to see answered")
    lens = {}
    for s in shots:
        for d in s.get("dialogue") or []:
            if isinstance(d, dict) and d.get("who"):
                lens.setdefault(d["who"], []).append(_words(d.get("text")))
    avg = {w: sum(v) / len(v) for w, v in lens.items() if len(v) >= 2}
    if len(avg) >= 3 and max(avg.values()) <= 1.3 * min(avg.values()):
        out.append("story: every speaker talks in the same rhythm (" + ", ".join(f"{w} {a:.0f}w" for w, a in avg.items()) + "): give each a voice (clipped, rambling, formal, halting...)")
    if bible and n:
        fast = [t["id"] for t in bible.get("threads") or [] if t["id"] in (spec.get("closes") or []) and t.get("opened") and int(str(t["opened"])[2:] or 0) >= n - 1]
        if fast:
            out.append(f"story: thread(s) {', '.join(fast)} close within a chapter of opening: let a mystery breathe (or replace it with a bigger question)")
    return out
SETTING_WORDS = re.compile(r"\b(night|dawn|dusk|sunset|sunrise|midday|morning|evening|rain|snow|fog|storm|interior|candlelit|moonlit|firelit|forest|city|street|room)\b", re.I)


class SagaError(Exception):
    pass


def sagas_dir(root=None):
    return Path(root or ROOT) / "explore" / "sagas"


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:40] or "saga"


def list_sagas(root=None):
    d = sagas_dir(root)
    return sorted((p for p in d.iterdir() if p.is_dir() and (p / "saga.json").is_file()), key=lambda p: p.name) if d.is_dir() else []


def resolve(ref, root=None):
    """saga dir from an id / number / slug fragment / None / 'current' (the newest)"""
    all_ = list_sagas(root)
    if not all_:
        raise SagaError("no sagas yet: python tools/saga.py new \"<title>\" --logline ... --style ...")
    if ref in (None, "", "current"):
        return all_[-1]
    exact = [p for p in all_ if p.name == ref]
    if exact:
        return exact[0]
    num = [p for p in all_ if p.name.split("-")[0] == str(ref).zfill(3)]
    if num:
        return num[0]
    part = [p for p in all_ if slugify(ref) in p.name]
    if len(part) == 1:
        return part[0]
    raise SagaError(f"unknown or ambiguous saga {ref!r} (have: {', '.join(p.name for p in all_)})")


def load(sdir):
    return json.loads((Path(sdir) / "saga.json").read_text(encoding="utf-8"))


def save(sdir, bible):
    sdir = Path(sdir)
    tmp = sdir / "saga.json.tmp"
    tmp.write_text(json.dumps(bible, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(sdir / "saga.json")


def chapter_dirs(sdir):
    return sorted((p for p in Path(sdir).glob("ch[0-9][0-9]*") if (p / "episode.json").is_file()), key=lambda p: p.name)


def chapter_num(name):
    return int(re.sub(r"\D", "", name) or 0)


def next_chapter(sdir):
    return max([chapter_num(p.name) for p in chapter_dirs(sdir)] or [0]) + 1


def ch_name(n):
    return f"ch{int(n):02d}"


def _norm(s):
    return re.sub(r"\s+", " ", str(s).strip().lower())


def _find(items, key, name):
    return next((x for x in items if _norm(x.get(key, "")) == _norm(name)), None)


def _need(v, what):
    if not str(v or "").strip():
        raise SagaError(f"{what} is required")
    return str(v).strip()


# ---------------------------------------------------------------------------------------------------------------- creation
def new(title, logline, style, root=None, world=None, now=None):
    title, logline, style = _need(title, "title"), _need(logline, "--logline"), _need(style, "--style")
    if "{subject}" not in style:
        raise SagaError("--style needs a {subject} slot (the look only: medium, linework, palette, finish; no places or times of day)")
    d = sagas_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    n = max([int(p.name.split("-")[0]) for p in d.iterdir() if p.is_dir() and p.name.split("-")[0].isdigit()] or [0]) + 1
    sid = f"{n:03d}-{slugify(title)}"
    w = world or {}
    bible = {"id": sid, "title": title, "logline": logline, "created": now or time.strftime("%Y-%m-%d %H:%M:%S"), "style": style,
             "world": {"setting": w.get("setting", ""), "rules": w.get("rules", ""), "tech_or_magic": w.get("tech_or_magic", ""), "tone": w.get("tone", "")},
             "lore": [], "factions": [], "places": [], "cast": {}, "timeline": [], "threads": []}
    try:  # a new saga starts with the deck's cores (no history yet) and maturity
        import explore_state
        import maturity as mt
        st = explore_state.state(Path(root or ROOT) / "feedback" / "explore.json")
        bible["cores"] = [{k: v for k, v in c.items() if k != "history"} for c in explore_state.clean_cores(st.get("cores") or [])]
        bible["maturity"] = mt.clean(st.get("maturity")) or mt.clean(mt.DEFAULT_STOP)
    except Exception:
        bible.setdefault("cores", [])
    (d / sid).mkdir()
    save(d / sid, bible)
    return d / sid, [f"style mentions a setting word ({m.group(0)}): style = the look only" for m in [SETTING_WORDS.search(style)] if m]


def add_cast(sdir, name, look, role="", voice="", status="alive", update=False):
    b = load(sdir)
    name = _need(name, "name")
    cur = _find([{"name": k, **(v if isinstance(v, dict) else {})} for k, v in b["cast"].items()], "name", name)
    if cur and not update:
        raise SagaError(f"cast member {cur['name']!r} already exists (use --update to change them)")
    if cur:
        e = b["cast"][cur["name"]]
        for k, v in (("look", look), ("role", role), ("voice", voice)):
            if v:
                e[k] = v
        if status:
            e["status"] = status
        save(sdir, b)
        return cur["name"]
    b["cast"][name] = {"look": _need(look, "--look"), "role": role, "voice": voice, "ref": None, "status": status or "alive", "first_chapter": None}
    save(sdir, b)
    return name


def add_place(sdir, name, look, update=False):
    b = load(sdir)
    name = _need(name, "name")
    cur = _find(b["places"], "name", name)
    if cur and not update:
        raise SagaError(f"place {cur['name']!r} already exists (use --update)")
    if cur:
        cur["look"] = _need(look, "--look")
    else:
        b["places"].append({"name": name, "look": _need(look, "--look"), "first_chapter": None})
    save(sdir, b)


def add_lore(sdir, topic, text, update=False):
    b = load(sdir)
    topic = _need(topic, "topic")
    cur = _find(b["lore"], "topic", topic)
    if cur and not update:
        raise SagaError(f"lore topic {cur['topic']!r} already exists (use --update)")
    if cur:
        cur["text"] = _need(text, "--text")
    else:
        b["lore"].append({"topic": topic, "text": _need(text, "--text")})
    save(sdir, b)


def add_faction(sdir, name, aim, look, update=False):
    b = load(sdir)
    name = _need(name, "name")
    cur = _find(b["factions"], "name", name)
    if cur and not update:
        raise SagaError(f"faction {cur['name']!r} already exists (use --update)")
    if cur:
        cur.update({k: v for k, v in (("aim", aim), ("look", look)) if v})
    else:
        b["factions"].append({"name": name, "aim": aim or "", "look": look or ""})
    save(sdir, b)


def thread_open(sdir, text, tid=None, chapter=None):
    b = load(sdir)
    text = _need(text, "thread text")
    if _find(b["threads"], "text", text):
        raise SagaError("that thread already exists")
    ids = {t["id"] for t in b["threads"]}
    tid = tid or "t" + str(max([int(t["id"][1:]) for t in b["threads"] if re.fullmatch(r"t\d+", t["id"])] or [0]) + 1)
    if tid in ids:
        raise SagaError(f"thread id {tid!r} already exists")
    b["threads"].append({"id": tid, "text": text, "opened": ch_name(chapter) if chapter else None, "status": "open", "closed_in": None})
    save(sdir, b)
    return tid


def thread_close(sdir, tid, chapter=None):
    b = load(sdir)
    t = next((x for x in b["threads"] if x["id"] == tid), None)
    if not t:
        raise SagaError(f"unknown thread {tid!r} (have: {', '.join(x['id'] for x in b['threads']) or 'none'})")
    if t["status"] == "closed":
        raise SagaError(f"thread {tid} is already closed in {t.get('closed_in')}")
    t["status"], t["closed_in"] = "closed", ch_name(chapter) if isinstance(chapter, int) else (chapter or ch_name(next_chapter(sdir) - 1))
    save(sdir, b)


def valid_crop(c):
    if not isinstance(c, (list, tuple)) or len(c) != 4 or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in c):
        return None
    x0, y0, x1, y1 = (float(v) for v in c)
    if not all(0 <= v <= 1 for v in (x0, y0, x1, y1)) or x1 <= x0 + 0.02 or y1 <= y0 + 0.02:
        return None
    return [round(v, 4) for v in (x0, y0, x1, y1)]


def setref(sdir, name, rel, crop=None, clear=False, root=None):
    sdir = Path(sdir)
    b = load(sdir)
    k = next((n for n in b["cast"] if _norm(n) == _norm(name)), None)
    if not k:
        raise SagaError(f"unknown cast member {name!r} (have: {', '.join(b['cast']) or 'none'})")
    e = b["cast"][k]
    if clear:
        e["ref"] = None
        e.pop("ref_crop", None)
        save(sdir, b)
        return k, None
    p = Path(rel)
    cand = p if p.is_absolute() else (Path(root or ROOT) / p if str(rel).replace("\\", "/").startswith("explore/") else sdir / p)
    if not cand.is_file():
        raise SagaError(f"no such picture: {cand}")
    try:
        out = cand.resolve().relative_to(Path(root or ROOT).resolve()).as_posix()
    except ValueError:
        raise SagaError("the reference must be inside the project")
    if crop is not None:
        c = valid_crop(crop)
        if not c:
            raise SagaError("--crop needs x0,y0,x1,y1 as fractions 0-1, at least 2% each way")
        e["ref_crop"] = c
    else:
        e.pop("ref_crop", None)
    e["ref"] = out
    save(sdir, b)
    return k, out


# ---------------------------------------------------------------------------------------------------------------- validation
def cast_names(bible):
    return list(bible.get("cast") or {})


def validate_shot(bible, shot, label="shot"):
    """-> (errors, warnings) for one saga shot (used by `chapter` and by explore_edit when it rewrites a saga chapter's unrendered shots)"""
    import explore_render as er
    errs, warns = [], []
    if not isinstance(shot, dict):
        return [f"{label}: not an object"], warns
    if not str(shot.get("prompt", "")).strip():
        errs.append(f"{label}: no prompt")
    try:
        er.aspect_name(shot.get("aspect"))
    except ValueError as e:
        errs.append(f"{label}: {e}")
    cast = cast_names(bible)
    with_ = shot.get("with") or []
    if not isinstance(with_, list):
        errs.append(f"{label}: `with` must be a list of cast names")
        with_ = []
    for w in with_:
        if w not in cast:
            hint = next((c for c in cast if _norm(c) == _norm(w) or _norm(w) in _norm(c)), None)
            errs.append(f"{label}: `with` names {w!r}, who is not in the cast" + (f" (did you mean {hint!r}?)" if hint else " (add them: saga.py cast)"))
    pl = shot.get("place")
    if pl and not _find(bible.get("places") or [], "name", pl):
        warns.append(f"{label}: place {pl!r} is not in the bible's places (add it: saga.py place), the text is used as given")
    dlg = shot.get("dialogue") or []
    if not isinstance(dlg, list):
        errs.append(f"{label}: dialogue must be a list of {{who, text}}")
        dlg = []
    if len(dlg) > MAX_DIALOGUE:
        errs.append(f"{label}: {len(dlg)} dialogue lines (max {MAX_DIALOGUE}); split the scene over two shots")
    for k, d in enumerate(dlg, 1):
        if not isinstance(d, dict) or not str(d.get("who", "")).strip() or not str(d.get("text", "")).strip():
            errs.append(f"{label}: dialogue #{k} needs who + text")
            continue
        if d["who"] not in with_ and not d.get("off"):
            errs.append(f"{label}: dialogue #{k}: {d['who']!r} is not in frame (`with`); mark an off-screen voice with \"off\": true")
        if d.get("off") is not True and d["who"] in with_ and d["who"] not in cast:
            errs.append(f"{label}: dialogue #{k}: unknown speaker {d['who']!r}")
    if not (str(shot.get("narration", "")).strip() or dlg or str(shot.get("caption", "")).strip()):
        errs.append(f"{label}: needs narration, dialogue or a caption (a silent picture still gets one line)")
    fc = shot.get("faces")
    if fc is not None and not isinstance(fc, dict):
        errs.append(f"{label}: faces must be {{cast name: expression}}")
    elif fc:
        for nm in fc:
            if nm not in with_:
                warns.append(f"{label}: faces names {nm!r}, who is not in frame (`with`)")
    if shot.get("nofigure") and with_:
        warns.append(f"{label}: nofigure with `with` {with_}: only non-human cast (a creature, an egg) should be named")
    return errs, warns


def normalize_shot(shot, n):
    """a shot as stored in episode.json: id eN, caption defaults to the narration / first line, dialogue cleaned"""
    s = {k: v for k, v in shot.items() if k not in ("id", "src")}
    dlg = [{k: v for k, v in {"who": d["who"].strip(), "text": d["text"].strip(), "off": True if d.get("off") else None}.items() if v is not None}
           for d in (shot.get("dialogue") or [])]
    cap = str(shot.get("caption", "")).strip() or str(shot.get("narration", "")).strip() or (dlg[0]["text"] if dlg else "")
    out = {"id": f"e{n}", "prompt": str(shot["prompt"]).strip(), "caption": cap, "aspect": shot.get("aspect") or "16:9", "hold": shot.get("hold") or 6,
           "with": list(shot.get("with") or []), "place": shot.get("place") or "", "narration": str(shot.get("narration", "")).strip(), "dialogue": dlg}
    for k in ("seed", "camera", "steer", "faces"):
        if shot.get(k):
            out[k] = shot[k]
    for k in ("noref", "nofigure"):
        if shot.get(k):
            out[k] = True
    return out


def write_chapter(sdir, spec, replace=False, steer=None, now=None, root=None):
    """validate chapter.json `spec` {title, summary, event?, opens, closes, status_changes {name: status}, shots} and write chNN/episode.json
    + update the bible (timeline, thread statuses, cast / place first_chapter, cast status). Raises SagaError (nothing written) on any problem."""
    sdir = Path(sdir)
    b = load(sdir)
    errs, warns = [], []
    title, summary = str(spec.get("title", "")).strip(), str(spec.get("summary", "")).strip()
    if not title:
        errs.append("chapter: no title")
    if not summary:
        errs.append("chapter: no summary (two sentences: what happens and what changes)")
    n = int(spec.get("chapter") or next_chapter(sdir))
    if replace and not spec.get("chapter"):  # --replace without a number = rewrite the newest chapter that has no pictures yet
        unrendered = sorted(int(d.name[2:]) for d in sdir.glob("ch[0-9][0-9]") if (d / "episode.json").exists() and not list(d.glob("e*.png")))
        if unrendered:
            n = unrendered[-1]
    cdir = sdir / ch_name(n)
    if cdir.exists():
        pngs = list(cdir.glob("e*.png"))
        if pngs:
            errs.append(f"{ch_name(n)} already has {len(pngs)} picture(s): write the next chapter (ch{next_chapter(sdir):02d}) or re-steer with explore_edit.py")
        elif not replace:
            errs.append(f"{ch_name(n)} already exists without pictures: pass --replace to overwrite it")
    shots = spec.get("shots")
    if not isinstance(shots, list) or not shots:
        errs.append("chapter: `shots` must be a non-empty list (12-20 shots)")
        shots = []
    elif not 8 <= len(shots) <= 24:
        warns.append(f"{len(shots)} shots (the rhythm is 12-20)")
    for i, s in enumerate(shots, 1):
        e, w = validate_shot(b, s, f"shot {i}")
        errs += e
        warns += w
    pace = pacing(shots) if shots else None
    if pace and (not pace["ok"] or len(pace["short"]) > len(shots) // 3):
        warns.append(f"pacing: shots read {pace['avg_s']} s on average, target {pace['target_s']} s ({int(PACE_SHARE * 100)}% of the {pace['render_s']} s median render); "
                     f"short: " + ", ".join(f"shot {i} {v}s" for i, v in pace["short"]) + " (add a dialogue exchange that moves the scene, rather than narration)")
    warns += story_lint(spec, shots, b, n)
    # threads
    ths = {t["id"]: t for t in b["threads"]}
    new_threads = []
    opens = []
    for o in spec.get("opens") or []:
        if isinstance(o, dict):
            tid, text = o.get("id"), str(o.get("text", "")).strip()
            if not text:
                errs.append("opens: a new thread needs text")
            elif _find(b["threads"], "text", text) or (tid and tid in ths):
                errs.append(f"opens: thread {tid or text!r} already exists (list its id as a plain string to attach it to this chapter)")
            else:
                new_threads.append({"id": tid, "text": text})
                opens.append(tid or "?")
            continue
        t = ths.get(o)
        if not t:
            errs.append(f"opens: unknown thread {o!r} (create it: saga.py thread {b['id']} open \"...\")")
        elif t["status"] != "open" or t.get("opened") not in (None, ch_name(n)):
            errs.append(f"opens: thread {o} is already {t['status']} (opened {t.get('opened')}); only a fresh thread can be opened here")
        else:
            opens.append(o)
    closes = []
    for c in spec.get("closes") or []:
        t = ths.get(c)
        if not t:
            errs.append(f"closes: unknown thread {c!r} (have: {', '.join(ths) or 'none'})")
        elif t["status"] == "closed" and t.get("closed_in") != ch_name(n):
            errs.append(f"closes: thread {c} was already closed in {t.get('closed_in')}")
        elif t.get("opened") is None and c not in opens:
            errs.append(f"closes: thread {c} was never opened (list it in `opens` of this or an earlier chapter)")
        else:
            closes.append(c)
    sc = spec.get("status_changes") or {}
    for who in sc:
        if who not in b["cast"]:
            errs.append(f"status_changes: {who!r} is not in the cast")
    if errs:
        raise SagaError("\n".join("- " + e for e in errs))
    # ---- commit
    for nt in new_threads:
        tid = nt["id"] or "t" + str(max([int(t["id"][1:]) for t in b["threads"] if re.fullmatch(r"t\d+", t["id"])] or [0]) + 1)
        b["threads"].append({"id": tid, "text": nt["text"], "opened": None, "status": "open", "closed_in": None})
        opens = [tid if x == "?" else x for x in opens]
    for t in b["threads"]:
        if t["id"] in opens:
            t["opened"] = ch_name(n)
        if t["id"] in closes:
            t["status"], t["closed_in"] = "closed", ch_name(n)
    norm = [normalize_shot(s, i) for i, s in enumerate(shots, 1)]
    for s in norm:
        for w in s["with"]:
            if b["cast"][w].get("first_chapter") is None:
                b["cast"][w]["first_chapter"] = ch_name(n)
        pl = _find(b["places"], "name", s["place"]) if s["place"] else None
        if pl and pl.get("first_chapter") is None:
            pl["first_chapter"] = ch_name(n)
    for who, st in sc.items():
        b["cast"][who]["status"] = st
    b["timeline"] = [t for t in b["timeline"] if t.get("chapter") != ch_name(n)] + [{"chapter": ch_name(n), "event": str(spec.get("event") or summary).strip()}]
    b["timeline"].sort(key=lambda t: chapter_num(t["chapter"]))
    if steer is None:
        try:
            import explore_state
            st = explore_state.state(Path(root or ROOT) / "feedback" / "explore.json")
            steer = {k: st.get(k) for k in ("presence", "emotion", "formality", "cores", "maturity") if st.get(k) is not None}
        except Exception:
            steer = {}
        if b.get("cores") is not None:   # the saga's own cores (with their history) are the source of truth for its chapters
            steer["cores"] = [{k: v for k, v in c.items() if k != "history"} for c in b["cores"]]
        if b.get("maturity"):
            steer["maturity"] = b["maturity"]
        elif "maturity" not in steer:
            import maturity as mt
            steer["maturity"] = mt.clean(mt.DEFAULT_STOP)
    ep = {"id": f"{b['id']}/{ch_name(n)}", "saga": b["id"], "chapter": n, "title": title, "topic": b["title"], "premise": summary, "summary": summary,
          "style": b["style"], "created": now or time.strftime("%Y-%m-%d %H:%M:%S"), "status": "draft", **steer, "steer_log": [],
          "opens": opens, "closes": closes, "shots": norm}
    for k in ("scenes", "choices", "hook"):   # the story plan travels with the chapter (the lint reads it; the bible shows it)
        if spec.get(k):
            ep[k] = spec[k]
    cdir.mkdir(exist_ok=True)
    (cdir / "episode.json.tmp").write_text(json.dumps(ep, indent=2, ensure_ascii=False), encoding="utf-8")
    (cdir / "episode.json.tmp").replace(cdir / "episode.json")
    save(sdir, b)
    return {"chapter": ch_name(n), "dir": cdir, "shots": len(norm), "opens": opens, "closes": closes, "warnings": warns, "pacing": pace}


# ---------------------------------------------------------------------------------------------------------------- emotional cores (per saga)
def _find_core(cores, key):
    k = _norm(key)
    hit = [c for c in cores if _norm(c.get("id", "")) == k or _norm(c.get("name", "")) == k]
    if not hit:
        hit = [c for c in cores if k and (k in _norm(c.get("id", "")) or k in _norm(c.get("name", "")))]
    if len(hit) != 1:
        raise SagaError(f"unknown or ambiguous core {key!r} (have: {', '.join(c['id'] + ' = ' + c['name'] for c in cores) or 'none'})")
    return hit[0]


def cores_set(sdir, cores=None, maturity=None, root=None):
    """save the deck's cores / maturity into saga.json (cores=None: read feedback/explore.json). History is kept by core id; returns the saved list"""
    import explore_state
    import maturity as mt
    b = load(sdir)
    if cores is None:
        st = explore_state.state(Path(root or ROOT) / "feedback" / "explore.json")
        cores = st.get("cores") or []
        if maturity is None:
            maturity = st.get("maturity")
    old = {c["id"]: c for c in b.get("cores") or []}
    new = explore_state.clean_cores(cores)
    for c in new:
        hist = (old.get(c["id"]) or {}).get("history") or []
        if hist and not c.get("history"):
            c["history"] = hist
    b["cores"] = new
    m = mt.clean(maturity)
    if m:
        b["maturity"] = m
    save(sdir, b)
    return new


def cores_log(sdir, core, chapter, beat, how=""):
    b = load(sdir)
    c = _find_core(b.get("cores") or [], core)
    entry = {"chapter": _need(chapter, "--chapter"), "beat": _need(beat, "--beat")}
    if how:
        entry["how"] = how
    c.setdefault("history", []).append(entry)
    save(sdir, b)
    return c


def cores_status(sdir, core, status):
    b = load(sdir)
    cs = b.get("cores") or []
    c = _find_core(cs, core)
    if status == "active" and c.get("status") != "active" and sum(1 for x in cs if x.get("status", "active") == "active") >= 5:
        raise SagaError("already 5 active cores: resolve one first")
    c["status"] = status
    save(sdir, b)
    return c


def cores_weight(sdir, core, weight):
    b = load(sdir)
    c = _find_core(b.get("cores") or [], core)
    c["weight"] = round(max(0.0, min(1.0, float(weight))), 2)
    save(sdir, b)
    return c


def cores_text(sdir):
    import explore_state
    import maturity as mt
    b = load(sdir)
    L = [f"maturity: {mt.describe(b.get('maturity')) if b.get('maturity') else 'not set (assume Teen; the hard ceiling always applies)'}", "emotional cores (the story's through-lines):"]
    cs = b.get("cores") or []
    if not cs:
        L.append("  none")
    for c in sorted(cs, key=lambda c: (c.get("status") == "resolved", -float(c.get("weight", 0.6)))):
        L.append(f"  - {c['id']}: {explore_state.cores_words([c], detail=True)}")
        for h in c.get("history") or []:
            L.append(f"      {h.get('chapter')}: {h.get('beat')}" + (f" ({h['how']})" if h.get("how") else ""))
    return "\n".join(L)


# ---------------------------------------------------------------------------------------------------------------- reading
def chapter_info(cdir):
    ep = json.loads((Path(cdir) / "episode.json").read_text(encoding="utf-8"))
    sh = ep.get("shots") or []
    return {"chapter": cdir.name, "title": ep.get("title", ""), "summary": ep.get("summary", ""), "status": ep.get("status", "draft"),
            "rendered": sum(1 for s in sh if (Path(cdir) / f"{s['id']}.png").is_file()), "shots": len(sh)}


def current(root=None):
    sdir = resolve(None, root)
    b = load(sdir)
    chs = [chapter_info(p) for p in chapter_dirs(sdir)]
    flight = next((c for c in reversed(chs) if c["status"] != "done"), None)
    return {"id": b["id"], "title": b["title"], "logline": b["logline"], "next_chapter": next_chapter(sdir), "next_name": ch_name(next_chapter(sdir)),
            "chapters": len(chs), "in_flight": flight, "dir": str(sdir)}


def bible_text(sdir, brief=False):
    b = load(sdir)
    L = [f"# {b['title']}  [{b['id']}]", b["logline"], f"STYLE (look only): {b['style']}"]
    w = b.get("world") or {}
    for k, label in (("setting", "Setting"), ("rules", "Rules"), ("tech_or_magic", "Tech / magic"), ("tone", "Tone")):
        if w.get(k):
            L.append(f"{label}: {w[k]}")
    if b.get("factions"):
        L.append("\n## Factions")
        L += [f"- {f['name']}: aim {f.get('aim', '')}; look {f.get('look', '')}" for f in b["factions"]]
    L.append("\n## Cast (looks are repeated verbatim in every shot they appear in)")
    for n, c in b["cast"].items():
        ref = f"ref {c['ref']}" + (f" crop {c['ref_crop']}" if c.get("ref_crop") else "") if c.get("ref") else "NO REF YET (saga.py setref after their clearest frontal shot)"
        L.append(f"- {n} [{c.get('status', 'alive')}] — {c.get('role', '')}; first {c.get('first_chapter') or 'not yet'}; {ref}")
        L.append(f"    look: {c.get('look', '')}")
        if not brief and c.get("voice"):
            L.append(f"    voice: {c['voice']}")
        elif brief and c.get("voice"):
            L.append(f"    voice: {c['voice'][:90]}")
    L.append("\n## Maturity + emotional cores (CLAUDE.md 'Nev Novel': heavy cores drive the main beats, light ones colour scenes; log served beats with saga.py cores <saga> log)")
    L.append(cores_text(sdir))
    L.append("\n## Places")
    L += [f"- {p['name']} (first {p.get('first_chapter') or 'not yet'}): {p.get('look', '')}" for p in b["places"]]
    L.append("\n## Lore")
    L += [f"- {x['topic']}: {x['text'] if not brief else x['text'][:200]}" for x in b["lore"]]
    ths = b["threads"]
    L.append("\n## Open threads (pay these off; close them with `closes`)")
    L += [f"- {t['id']}: {t['text']}  (opened {t.get('opened') or 'not yet'})" for t in ths if t["status"] == "open"] or ["- none"]
    cl = [t for t in ths if t["status"] == "closed"]
    if cl:
        L.append("Closed: " + "; ".join(f"{t['id']} ({t.get('closed_in')}): {t['text'][:60]}" for t in cl))
    tl = b["timeline"] if not brief else b["timeline"][-6:]
    L.append("\n## Timeline" + (" (last 6)" if brief and len(b["timeline"]) > 6 else ""))
    L += [f"- {t['chapter']}: {t['event']}" for t in tl] or ["- (nothing yet)"]
    chs = chapter_dirs(sdir)
    L.append("\n## Chapters" + (" (last 3)" if brief else ""))
    for p in (chs[-3:] if brief else chs):
        i = chapter_info(p)
        L.append(f"- {i['chapter']} {i['title']} [{i['status']} {i['rendered']}/{i['shots']}]: {i['summary']}")
    if not chs:
        L.append("- none yet")
    eng = engagement(sdir)
    if eng:
        L.append("\n## Reader engagement (from the player: where attention held or dropped; write the next chapter against it)")
        for c, e in eng.items():
            sk = ", ".join(f"{s['shot']}{' (narration only)' if s['nonly'] else ''}" for s in e["skipped"]) or "none"
            L.append(f"- {c}: {e['shots']} shots seen, skipped early {len(e['skipped'])} ({e['skip_pct']}%), went back {e['backs']}; skipped: {sk}")
    L.append(f"\nNEXT: {ch_name(next_chapter(sdir))}")
    return "\n".join(L)


def engagement(sdir, root=None):
    """feedback/engage.jsonl (the player's rows) for this saga -> {chNN: {shots, skipped [{shot, nonly}], skip_pct, backs}}: a shot counts as skipped when the reader
    moved on early on its LATEST viewing (so re-reading it later fixes the record)"""
    root = Path(root or ROOT)
    f = root / "feedback" / "engage.jsonl"
    if not f.is_file():
        return {}
    pre = f"explore/sagas/{Path(sdir).name}/"
    last, backs = {}, {}
    for line in f.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        src = str(r.get("src", ""))
        if not src.startswith(pre):
            continue
        m = re.match(re.escape(pre) + r"(ch\d+)/(e\d+)\.png$", src)
        if not m:
            continue
        last[(m.group(1), m.group(2))] = r
        if r.get("act") == "back":
            backs[m.group(1)] = backs.get(m.group(1), 0) + 1
    out = {}
    for (ch, shot), r in sorted(last.items(), key=lambda kv: (kv[0][0], int(kv[0][1][1:]))):
        e = out.setdefault(ch, {"shots": 0, "skipped": [], "backs": backs.get(ch, 0)})
        e["shots"] += 1
        if r.get("act") == "skip":
            ef = Path(sdir) / ch / "episode.json"
            ep = json.loads(ef.read_text(encoding="utf-8")) if ef.is_file() else {}
            s = next((x for x in ep.get("shots") or [] if x.get("id") == shot), {})
            e["skipped"].append({"shot": shot, "nonly": bool(s.get("narration")) and not s.get("dialogue")})
    for e in out.values():
        e["skip_pct"] = round(100 * len(e["skipped"]) / e["shots"]) if e["shots"] else 0
    return out


# ---------------------------------------------------------------------------------------------------------------- CLI
def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new")
    p.add_argument("title")
    p.add_argument("--logline", default="")
    p.add_argument("--style", default="")
    for k in ("setting", "rules", "tech", "tone"):
        p.add_argument("--" + k, default="")
    p = sub.add_parser("current")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("bible")
    p.add_argument("saga", nargs="?")
    p.add_argument("--brief", action="store_true")
    p = sub.add_parser("cast")
    p.add_argument("saga")
    p.add_argument("name")
    p.add_argument("--look", default="")
    p.add_argument("--role", default="")
    p.add_argument("--voice", default="")
    p.add_argument("--status", default="")
    p.add_argument("--update", action="store_true")
    p = sub.add_parser("place")
    p.add_argument("saga")
    p.add_argument("name")
    p.add_argument("--look", default="")
    p.add_argument("--update", action="store_true")
    p = sub.add_parser("lore")
    p.add_argument("saga")
    p.add_argument("topic")
    p.add_argument("--text", default="")
    p.add_argument("--update", action="store_true")
    p = sub.add_parser("faction")
    p.add_argument("saga")
    p.add_argument("name")
    p.add_argument("--aim", default="")
    p.add_argument("--look", default="")
    p.add_argument("--update", action="store_true")
    p = sub.add_parser("thread")
    p.add_argument("saga")
    p.add_argument("op", choices=["open", "close"])
    p.add_argument("arg")
    p.add_argument("--id", default=None)
    p.add_argument("--in", dest="chap", default=None)
    p = sub.add_parser("chapter")
    p.add_argument("saga")
    p.add_argument("file")
    p.add_argument("--replace", action="store_true")
    p = sub.add_parser("lint")  # the story lint (+ pacing) on a chapter dir (chNN) or a chapter.json, before it is registered
    p.add_argument("saga")
    p.add_argument("target", help="chNN or a chapter.json path")
    p = sub.add_parser("pace")  # reading time per shot vs PACE_SHARE of the median render; a chapter dir (chNN) or a chapter.json
    p.add_argument("saga")
    p.add_argument("target", help="chNN or a chapter.json path")
    p = sub.add_parser("setref")
    p.add_argument("saga")
    p.add_argument("name")
    p.add_argument("png", nargs="?")
    p.add_argument("--crop", default=None)
    p.add_argument("--clear", action="store_true")
    p = sub.add_parser("cores")
    p.add_argument("saga")
    p.add_argument("op", choices=["show", "set", "log", "resolve", "reopen", "weight"])
    p.add_argument("arg", nargs="?")
    p.add_argument("arg2", nargs="?")
    p.add_argument("--file", default=None)
    p.add_argument("--maturity", default=None)
    p.add_argument("--chapter", default=None)
    p.add_argument("--beat", default="")
    p.add_argument("--how", default="")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "new":
            sdir, warns = new(a.title, a.logline, a.style, world={"setting": a.setting, "rules": a.rules, "tech_or_magic": a.tech, "tone": a.tone})
            print(f"created {sdir.relative_to(ROOT).as_posix() if sdir.is_relative_to(ROOT) else sdir}  (next: saga.py cast / place / lore / thread, then a chapter)")
            for w in warns:
                print("WARN", w)
        elif a.cmd == "current":
            c = current()
            if a.json:
                print(json.dumps(c, indent=2, ensure_ascii=False))
            else:
                print(f"{c['id']}  {c['title']} — {c['logline']}\n  {c['chapters']} chapter(s); next = {c['next_name']}"
                      + (f"; in flight: {c['in_flight']['chapter']} {c['in_flight']['title']} [{c['in_flight']['status']} {c['in_flight']['rendered']}/{c['in_flight']['shots']}]" if c["in_flight"] else ""))
        else:
            sdir = resolve(a.saga)
            if a.cmd == "bible":
                print(bible_text(sdir, a.brief))
            elif a.cmd == "cast":
                print("cast:", add_cast(sdir, a.name, a.look, a.role, a.voice, a.status or ("" if a.update else "alive"), a.update))
            elif a.cmd == "place":
                add_place(sdir, a.name, a.look, a.update)
                print("place:", a.name)
            elif a.cmd == "lore":
                add_lore(sdir, a.topic, a.text, a.update)
                print("lore:", a.topic)
            elif a.cmd == "faction":
                add_faction(sdir, a.name, a.aim, a.look, a.update)
                print("faction:", a.name)
            elif a.cmd == "thread":
                if a.op == "open":
                    print("thread opened:", thread_open(sdir, a.arg, a.id, next_chapter(sdir)))
                else:
                    thread_close(sdir, a.arg, a.chap)
                    print("thread closed:", a.arg)
            elif a.cmd == "chapter":
                spec = json.loads(Path(a.file).read_text(encoding="utf-8"))
                r = write_chapter(sdir, spec, a.replace)
                for w in r["warnings"]:
                    print("WARN", w)
                if r.get("pacing"):
                    pc = r["pacing"]
                    print(f"pacing: {pc['avg_s']} s reading per shot on average (target {pc['target_s']} s = {int(PACE_SHARE * 100)}% of a {pc['render_s']} s render)")
                print(f"wrote {r['dir']}/episode.json: {r['shots']} shots; opens {r['opens'] or '-'}; closes {r['closes'] or '-'}\n"
                      f"render: python tools/explore_render.py explore/sagas/{sdir.name}/{r['chapter']}")
            elif a.cmd in ("lint",):
                tp = Path(a.target)
                f = tp if tp.suffix == ".json" else sdir / a.target / "episode.json"
                spec = json.loads(f.read_text(encoding="utf-8"))
                n = int(spec.get("chapter") or (a.target[2:] if a.target.startswith("ch") and a.target[2:].isdigit() else next_chapter(sdir)))
                ws = story_lint(spec, spec.get("shots") or [], load(sdir), n)
                pc = pacing(spec.get("shots") or [])
                print(f"pacing: {pc['avg_s']} s per shot (target {pc['target_s']} s)")
                print("\n".join(ws) if ws else "story: clean (scenes with goals, obstacles, turns and stakes; a costly choice; a hook; mostly shown, not told)")
            elif a.cmd == "pace":
                tp = Path(a.target)
                f = tp if tp.suffix == ".json" else sdir / a.target / "episode.json"
                shots = json.loads(f.read_text(encoding="utf-8")).get("shots") or []
                pc = pacing(shots)
                print(f"target {pc['target_s']} s per shot = {int(PACE_SHARE * 100)}% of the {pc['render_s']} s median render; average {pc['avg_s']} s "
                      + ("OK" if pc["ok"] else "SHORT"))
                for i, v in enumerate(pc["per_shot"], 1):
                    print(f"  shot {i:2d} {v:5.1f} s {'#' * int(v)}{'  <- short' if v < 0.8 * pc['target_s'] else ''}")
            elif a.cmd == "cores":
                if a.op == "show":
                    print(cores_text(sdir))
                elif a.op == "set":
                    cs = json.loads(Path(a.file).read_text(encoding="utf-8")) if a.file else None
                    got = cores_set(sdir, cs, a.maturity)
                    print(f"saved {len(got)} core(s) into {sdir.name}/saga.json\n" + cores_text(sdir))
                elif a.op == "log":
                    c = cores_log(sdir, _need(a.arg, "core"), a.chapter, a.beat, a.how)
                    print(f"logged for {c['id']}: {a.chapter} {a.beat}")
                elif a.op in ("resolve", "reopen"):
                    c = cores_status(sdir, _need(a.arg, "core"), "resolved" if a.op == "resolve" else "active")
                    print(f"{c['id']}: {c['status']}")
                else:
                    c = cores_weight(sdir, _need(a.arg, "core"), _need(a.arg2, "weight"))
                    print(f"{c['id']}: weight {c['weight']}")
            elif a.cmd == "setref":
                crop = [float(x) for x in a.crop.split(",")] if a.crop else None
                if not a.clear and not a.png:
                    raise SagaError("give the picture: chNN/eK.png")
                k, out = setref(sdir, a.name, a.png, crop, a.clear)
                print(f"{k}: reference " + (out + (f" crop {crop}" if crop else "") if out else "cleared"))
    except (SagaError, OSError, ValueError, json.JSONDecodeError) as e:
        sys.exit(f"saga: {e}")


if __name__ == "__main__":
    main()
