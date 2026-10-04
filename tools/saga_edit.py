"""🎞 the IMMERSION pass of tools/saga_assemble.py: pure editing decisions (no ffmpeg), so they can be unit-tested.

Options live in episode.json `reel.edit` {...} (every key optional, defaults below); the resolved set is recorded in the build's .json.
  title        "over" (default: the saga title + chapter fade in over the FIRST shot, darkened ~30 %) | "card" (a separate black card first)
  look         0-1, strength of the shared grade (warm / teal balance, soft contrast, fine grain, soft vignette); 0 = off. default 0.5
  trim         true: drop frozen heads / tails of clips (clip_motion) and the first ~0.15 s; never hold a frozen last frame
  beats        true: with music, snap every cut to the nearest beat (downbeats preferred) by trimming or slowing <= 1.2x
  kenburns     true: stills vary push-in / pull-out / lateral drift (deterministic by shot id, never the same move twice in a row)
  dip          true: a dip to black where the place changes AND the time of day jumps; otherwise dissolves
  dissolve     seconds, or null = automatic (~1 beat at slow tempos, clamped 0.8-1.2 s; 1.0 s without music)
  caption_delay seconds after the cut before an on-screen line appears (default 0.6)
  end_fade     seconds of the slow fade to black at the end (default 3.0); tail = seconds of black the music rings on after the picture (default 1.5, music only)
  letterbox    0 (off) or a ratio like 2.39: black bars over the picture
"""
import json
import math
import re
import subprocess
import sys
import zlib
from pathlib import Path

DEFAULTS = {"title": "over", "look": 0.5, "trim": True, "beats": True, "kenburns": True, "dip": True, "dissolve": None,
            "caption_delay": 0.6, "end_fade": 3.0, "tail": 1.5, "letterbox": 0}
MAX_SLOW = 1.2
MIN_CLIP = 1.5
DIP_D = 0.6
HEAD_CUT = 0.15


def _num(v, default, lo, hi):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def edit_opts(ep):
    """episode.json -> the resolved reel.edit options (defaults filled, junk ignored)"""
    e = ((ep or {}).get("reel") or {}).get("edit")
    e = e if isinstance(e, dict) else {}
    o = dict(DEFAULTS)
    if e.get("title") in ("over", "card"):
        o["title"] = e["title"]
    for k in ("trim", "beats", "kenburns", "dip"):
        if k in e:
            o[k] = bool(e[k])
    o["look"] = _num(e.get("look", o["look"]), DEFAULTS["look"], 0.0, 1.0)
    if e.get("dissolve") is not None:
        o["dissolve"] = _num(e["dissolve"], None, 0.2, 3.0)
    o["caption_delay"] = _num(e.get("caption_delay", o["caption_delay"]), 0.6, 0.0, 3.0)
    o["end_fade"] = _num(e.get("end_fade", o["end_fade"]), 3.0, 0.5, 8.0)
    o["tail"] = _num(e.get("tail", o["tail"]), 1.5, 0.0, 6.0)
    o["letterbox"] = _num(e.get("letterbox", 0), 0, 0, 3.0)
    if 0 < o["letterbox"] < 1.4:
        o["letterbox"] = 0
    return o


# ---------------------------------------------------------------- 4. dead parts of a clip
def trim_span(motion, fps, still=0.35, step=0.25, head_cut=HEAD_CUT, min_len=MIN_CLIP, min_still=0.5):
    """(ss, to) seconds to keep of a clip: motion = mean abs frame difference per frame (tools/clip_motion.motion). A frozen head / tail of
    >= min_still seconds is dropped, plus the first head_cut s; never leaves less than min_len (then only the head_cut is dropped)."""
    n = len(motion)
    if n == 0 or not fps:
        return 0.0, 0.0
    dur = n / fps
    w = max(1, int(round(step * fps)))
    wins = [sum(motion[i:i + w]) / len(motion[i:i + w]) for i in range(0, n, w)]
    h = 0
    while h < len(wins) and wins[h] < still:
        h += 1
    t = 0
    while t < len(wins) - h and wins[len(wins) - 1 - t] < still:
        t += 1
    head_s, tail_s = h * w / fps, min(dur, t * w / fps)
    ss = (head_s if head_s >= min_still else 0.0) + head_cut
    to = dur - (tail_s if tail_s >= min_still else 0.0)
    if to - ss < min_len:
        ss, to = head_cut, dur
    if to - ss < min_len:  # a very short clip: keep all of it
        ss = 0.0
    return round(ss, 3), round(to, 3)


# ---------------------------------------------------------------- 5. rhythm
def beat_grid(beats, downbeats_every=4, offset=0.0, total=0.0, tempo=None):
    """song beat times -> (beats_out, downs_out) in OUTPUT seconds (song time - offset), extended periodically past the last beat up to `total`.
    The first beat of the song is taken as a bar start, every `downbeats_every`-th beat after it is a downbeat."""
    b = sorted(float(x) for x in (beats or []))
    if len(b) < 4:
        return [], []
    iv = sorted(y - x for x, y in zip(b, b[1:]))
    period = iv[len(iv) // 2]
    if tempo and 40 < tempo < 220:
        period = min(period, 60.0 / tempo) if abs(period - 60.0 / tempo) / period < 0.2 else period
    idx = list(range(len(b)))
    allb = list(b)
    while allb[-1] - offset < total + period and len(allb) < 5000:
        allb.append(allb[-1] + period)
        idx.append(idx[-1] + 1)
    beats_out, downs = [], []
    for i, t in zip(idx, allb):
        o = t - offset
        if o < 0:
            continue
        beats_out.append(round(o, 3))
        if i % downbeats_every == 0:
            downs.append(round(o, 3))
    return beats_out, downs


def beat_period(beats):
    b = sorted(beats or [])
    if len(b) < 3:
        return None
    iv = sorted(y - x for x, y in zip(b, b[1:]))
    return iv[len(iv) // 2]


def dissolve_len(period, opt=None):
    """the dissolve length in seconds: reel.edit.dissolve, else ~1 beat (2 beats at fast tempos) clamped to 0.8-1.2 s; 1.0 s without music"""
    if opt:
        return float(opt)
    if not period:
        return 1.0
    d = period if period >= 0.8 else 2 * period
    return round(max(0.8, min(1.2, d)), 3)


def snap_lengths(bounds, ds, beats, downs, start=0.0, prefer=0.3):
    """output lengths of the pieces so that every cut lands on a beat. bounds = [(lo, hi, natural)] per piece, ds = the transition length between
    piece k and k+1 (len n-1); the cut MOMENT of a transition is its middle (piece k's end minus d/2). Greedy from the first piece: the beat whose
    implied length is closest to the natural one (relative), downbeats get a bonus of `prefer`; a piece with no beat inside [lo, hi] keeps its
    natural length. The last piece is never snapped."""
    n = len(bounds)
    lens, s = [], float(start)
    dset = set(round(x, 3) for x in (downs or []))
    for k in range(n):
        lo, hi, nat = bounds[k]
        if k == n - 1 or not beats:
            lens.append(round(nat, 3))
            continue
        d = ds[k]
        best, bc = None, None
        for m in beats:
            ln = m - s + d / 2
            if ln < lo - 1e-6 or ln > hi + 1e-6:
                continue
            c = abs(ln - nat) / max(nat, 0.1) - (prefer if round(m, 3) in dset else 0.0)
            if bc is None or c < bc:
                best, bc = ln, c
        ln = best if best is not None else nat
        lens.append(round(ln, 3))
        s += ln - d
    return lens


def clip_bounds(avail):
    """(lo, hi, natural) output length of a clip with `avail` seconds of good footage: trim down to MIN_CLIP, slow up to 1.2x"""
    return (min(MIN_CLIP, avail), avail * MAX_SLOW, avail)


def still_bounds(hold):
    return (max(2.0, hold * 0.6), hold * 1.5, hold)


# ---------------------------------------------------------------- transitions: dissolve, or a dip to black on a place + time-of-day jump
_TOD = [("night", r"\b(night|midnight|moonlit|moonlight|starlit|starry|after dark)\b"), ("dusk", r"\b(dusk|sunset|evening|twilight|golden hour)\b"),
        ("dawn", r"\b(dawn|sunrise|daybreak|first light|morning)\b"), ("day", r"\b(noon|midday|daylight|afternoon|bright day|sunny)\b")]


def tod(text):
    """a coarse time of day named in a prompt (night | dusk | dawn | day), or None"""
    t = (text or "").lower()
    for name, rx in _TOD:
        if re.search(rx, t):
            return name
    return None


def transitions(pieces, period=None, opt=None, dip=True):
    """[{kind: dissolve|dip, d}] between consecutive pieces. A dip (0.6 s) where the place changes AND the time of day jumps (both named, different)."""
    d = dissolve_len(period, opt)
    out = []
    for a, b in zip(pieces, pieces[1:]):
        pa, pb = (a.get("place") or "").strip().lower(), (b.get("place") or "").strip().lower()
        ta, tb = a.get("tod"), b.get("tod")
        if dip and pa and pb and pa != pb and ta and tb and ta != tb:
            out.append({"kind": "dip", "d": DIP_D})
        else:
            out.append({"kind": "dissolve", "d": d})
    return out


def clamp_transitions(trs, lens):
    """no transition longer than 40 % of either neighbour"""
    out = []
    for i, t in enumerate(trs):
        lim = 0.4 * min(lens[i], lens[i + 1])
        out.append({**t, "d": round(min(t["d"], lim), 3)})
    return out


# ---------------------------------------------------------------- 6. Ken Burns variety
KB_MOVES = ("push", "pull", "left", "right")


def kb_moves(ids):
    """a move per still shot id: deterministic (crc32 of the id), never the same move twice in a row"""
    out, prev = [], None
    for sid in ids:
        i = zlib.crc32(str(sid).encode()) % len(KB_MOVES)
        if KB_MOVES[i] == prev:
            i = (i + 1) % len(KB_MOVES)
        out.append(KB_MOVES[i])
        prev = KB_MOVES[i]
    return out


def kb_filter(move, frames, w, h):
    """zoompan for a still pre-scaled to 2w x 2h"""
    f = max(1, frames)
    cy = "y='ih/2-(ih/zoom/2)'"
    if move == "pull":
        zx = f"z='1.08-0.08*on/{f}':x='iw/2-(iw/zoom/2)':{cy}"
    elif move == "left":
        zx = f"z='1.07':x='(iw-iw/zoom)*(1-on/{f})':{cy}"
    elif move == "right":
        zx = f"z='1.07':x='(iw-iw/zoom)*on/{f}':{cy}"
    else:
        zx = f"z='1+0.08*on/{f}':x='iw/2-(iw/zoom/2)':{cy}"
    return f"zoompan={zx}:d={f}:s={w}x{h}:fps=24"


# ---------------------------------------------------------------- 1. captions that do not break the spell
def caption_times(dur, d_in, d_out, delay=0.6, after=0.0, fade=0.5, min_show=1.2):
    """(t0, t1) seconds INSIDE a piece between which its on-screen line is fully visible-or-fading: it appears `delay` s after the incoming
    dissolve ended (d_in; 0 for the first piece) and is gone before the outgoing one starts (d_out). `after` = a time the line must not start
    before (the title). None when there is no room (< min_show s)."""
    t0 = max(d_in + delay, after)
    t1 = dur - d_out - 0.15
    if t1 - t0 < min_show:
        return None
    return round(t0, 3), round(t1, 3)


def fade_alpha(t0, t1, f=0.5):
    """a drawtext alpha expression: 0 before t0, fades in over f, holds, fades out ending at t1"""
    return (f"if(lt(t,{t0:.2f}),0,if(lt(t,{t0 + f:.2f}),(t-{t0:.2f})/{f},if(lt(t,{t1 - f:.2f}),1,if(lt(t,{t1:.2f}),({t1:.2f}-t)/{f},0))))")


# ---------------------------------------------------------------- 3. one look for the chapter
def look_filter(look):
    """a gentle shared grade: slight warm highlights / teal shadows, soft contrast, fine grain, soft vignette; '' when look <= 0"""
    L = max(0.0, min(1.0, float(look or 0)))
    if L <= 0:
        return ""
    return (f"eq=contrast={1 + 0.05 * L:.3f}:saturation={1 - 0.06 * L:.3f},"
            f"colorbalance=rs={-0.05 * L:.3f}:bs={0.06 * L:.3f}:rh={0.05 * L:.3f}:bh={-0.05 * L:.3f},"
            f"noise=alls={max(1, round(7 * L))}:allf=t,"
            f"vignette=angle={1.5 - 0.25 * L:.3f}")  # a very soft vignette: edges only, brightness-neutral


def letterbox_filter(ratio):
    if not ratio:
        return ""
    bar = f"(ih-iw/{ratio})/2"
    return f"drawbox=x=0:y=0:w=iw:h={bar}:color=black:t=fill,drawbox=x=0:y=ih-{bar}:w=iw:h={bar}:color=black:t=fill"


def title_alpha(piece_len, start=0.7, fade_in=0.9, hold_end=4.2, fade_out=1.0):
    """(alpha expr, dim expr, t_end) for the title over the first shot; shrinks to fit a short first piece"""
    end = min(hold_end + fade_out, max(2.2, piece_len - 0.4))
    out_s = max(start + fade_in + 0.4, end - fade_out)
    a = (f"if(lt(t,{start:.2f}),0,if(lt(t,{start + fade_in:.2f}),(t-{start:.2f})/{fade_in},if(lt(t,{out_s:.2f}),1,if(lt(t,{end:.2f}),({end:.2f}-t)/{fade_out},0))))")
    # the picture darkens ~30 % (brightness -0.14) while the title is up
    dim = f"-0.14*min(1,t/0.6)*max(0,min(1,({end:.2f}-t)/{fade_out}))"
    return a, dim, round(end, 3)


# ---------------------------------------------------------------- beats of the uploaded song (librosa lives in ComfyUI's python: config comfy_python)
def _comfy_python():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from config import COMFY_PYTHON
    return str(COMFY_PYTHON)


def music_beats(music_path, root, cache_dir=None):
    """{beats, tempo} of the song, cached next to it (<song>.beats.json keyed by mtime + size); None when it can't be analysed"""
    p = Path(music_path)
    cache = Path(cache_dir or p.parent) / "music.beats.json"
    st = p.stat()
    key = {"mtime": int(st.st_mtime), "size": st.st_size}
    try:
        c = json.loads(cache.read_text(encoding="utf-8"))
        if c.get("key") == key:
            return {"beats": c["beats"], "tempo": c.get("tempo")}
    except (OSError, ValueError, KeyError):
        pass
    py = _comfy_python()
    py = py if Path(py).is_file() else None
    if not py:
        return None
    tmp = cache.with_name("music.analysis.tmp")
    r = subprocess.run([py, str(Path(root) / "tools" / "mv_analyze.py"), str(p), str(tmp)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        if r.returncode:
            return None
        a = json.loads(tmp.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    finally:
        tmp.unlink(missing_ok=True)
    slim = {"key": key, "beats": a.get("beats", []), "tempo": a.get("tempo"), "duration": a.get("duration")}
    cache.write_text(json.dumps(slim), encoding="utf-8")
    return {"beats": slim["beats"], "tempo": slim["tempo"]}


# ---------------------------------------------------------------- the saga-level 🎞 music video: one song over a chapter range, UNIFORM speed
SPEED_MIN, SPEED_MAX = 0.7, 1.4


def parse_length(v):
    """'4:05' | '1:02:03' | '245' | 245 -> seconds (float), None when unusable"""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v) if v > 0 else None
    parts = str(v).strip().split(":")
    try:
        nums = [float(x) for x in parts]
    except ValueError:
        return None
    if not 1 <= len(nums) <= 3 or any(x < 0 for x in nums):
        return None
    sec = 0.0
    for x in nums:
        sec = sec * 60 + x
    return sec if sec > 0 else None


def fmt_len(sec):
    sec = int(round(float(sec or 0)))
    return f"{sec // 60}:{sec % 60:02d}"


def parse_range(spec, available):
    """'ch01-ch03' | 'ch02' | 'ch01..ch03' | 'ch01,ch03' -> the chapter ids of `available` (sorted ids like ch01) inside it; [] when nothing matches"""
    av = sorted(available)
    spec = str(spec or "").strip().lower()
    nums = [int(x) for x in re.findall(r"\d+", spec)]
    if not nums:
        return []
    if "," in spec:
        want = set(nums)
        return [a for a in av if int(re.sub(r"\D", "", a) or 0) in want]
    lo, hi = nums[0], nums[-1]
    if lo > hi:
        lo, hi = hi, lo
    return [a for a in av if lo <= int(re.sub(r"\D", "", a) or 0) <= hi]


def fit_report(nats, ds_total, target_pic, lo=SPEED_MIN, hi=SPEED_MAX):
    """the uniform speed factor that makes the picture target_pic seconds long: output = sum(nats) / f - ds_total (the dissolves overlap).
    f < 1 slows, f > 1 speeds up. Clamped to lo..hi: outside it `ok` is False and `message` says how many cells to add / drop instead."""
    tot = float(sum(nats))
    n = max(1, len(nats))
    avg = tot / n if tot else 5.0
    want = target_pic + ds_total
    raw = tot / want if want > 0 else hi
    out = {"factor_raw": round(raw, 4), "factor": round(max(lo, min(hi, raw)), 4), "ok": lo <= raw <= hi, "cells": len(nats), "natural": round(tot - ds_total, 2),
           "target": round(target_pic, 2), "cells_needed": 0, "message": ""}
    if raw < lo:
        add = math.ceil((lo * want - tot) / avg)
        out["cells_needed"] = add
        out["message"] = f"song is {fmt_len(target_pic)}, natural {fmt_len(tot - ds_total)}: needs ~{add} more cell{'s' if add != 1 else ''}, or {raw:.2f}x is too slow"
    elif raw > hi:
        drop = math.ceil((tot - hi * want) / avg)
        out["cells_needed"] = -drop
        out["message"] = f"song is {fmt_len(target_pic)}, natural {fmt_len(tot - ds_total)}: drop ~{drop} cell{'s' if drop != 1 else ''}, or {raw:.2f}x is too fast"
    return out
