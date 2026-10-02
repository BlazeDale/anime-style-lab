#!/usr/bin/env python
"""🎞 Final-cut assembler for a music video (all the clips put together on the original full song file, with transitions
and overlays).

  python tools/mv_assemble.py musicvideos/NNN-x [--sb sb01] [--edit edit.json] [--draft] [--out cut/<slug>.mp4]
                                              [--plan] [--replan] [--keep]

edit.json (musicvideos/<id>/edit.json, made from the chapter + stems by --plan, then hand-edited; never overwritten without --replan):
  {"output": {w, h, fps, grain, vignette, lyrics: false|true|"all", preroll?}, "looks": {name: {eq, colorbalance, curves, glow, glow_sigma, grain}},
   "cuts": [{frame, t0, t1, clip: null|path, look: now|memory|none, in: {type, dur}, fx: [dust|lightleak|beatflash], why}],
   "overlays": [{type: dust|lyrics|beatflash, t0, t1, strength?}]}   (overlay / cut times are SONG seconds)
Timeline: video time = song time + preroll (s1's clip runs `preroll` s BEFORE the song); the audio is the ORIGINAL song.wav, continuous
(the first `preroll` s of s1's own audio crossfade into it). Every piece is placed by frame numbers: a transition of d frames extends the
OUTGOING piece by d (hold / continue) so each piece still starts at its song time; singing (ltxia2v) clips are never stretched, their frame 0
sits at sidecar song_audio.t0 (lip-sync stays exact). Pieces -> _assembly/ -> xfade units -> concat + grade/grain/lyrics -> cut/<slug>.mp4 (+ .json, _strip.jpg).
"""
import argparse, json, math, os, re, shutil, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FFMPEG, FFPROBE, find_font  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SING_ENGINES = {"ltxia2v", "s2v"}  # lip-synced to the song: placed at song_audio.t0, never stretched
XFADE = {"dissolve": "fade", "fade": "fade", "fadeblack": "fadeblack", "fadewhite": "fadewhite", "zoomin": "zoomin", "smoothleft": "smoothleft",
         "smoothright": "smoothright", "smoothup": "smoothup", "smoothdown": "smoothdown", "wipeleft": "wipeleft", "wiperight": "wiperight",
         "slideleft": "slideleft", "slideright": "slideright", "circleopen": "circleopen", "circleclose": "circleclose", "radial": "radial",
         "pixelize": "pixelize", "fadegrays": "fadegrays", "distance": "distance"}
NO_OVERLAP = {"cut", "flash"}  # hard cuts (flash = cut + a 3-frame white exposure fade-in)
FLASH_F = 3
DEFAULT_LOOKS = {
    "now": {"eq": "contrast=1.04:saturation=1.08", "colorbalance": "rs=0.02:bs=-0.02:rh=0.02:bh=-0.01"},
    "memory": {"eq": "contrast=0.94:saturation=0.80:brightness=0.02", "colorbalance": "rs=0.06:gs=0.01:bs=-0.06:rm=0.05:bm=-0.05:rh=0.04:bh=-0.04",
               "curves": "all='0/0.06 0.5/0.52 1/0.96'", "glow": 0.28, "glow_sigma": 14, "grain": 0.06},
}
DEFAULT_OUTPUT = {"w": 1920, "h": 1080, "fps": 24, "grain": 0.10, "vignette": 0.35, "lyrics": False}


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def F(t, fps):
    return int(round(t * fps))


def rel(p):
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(p).as_posix()


# ---------------------------------------------------------------- which clip belongs to a frame (the gallery's ❤ rule)
def has_act(m, a):
    return bool(m) and a in (m.get("actions") or ([m["action"]] if m.get("action") else []))


def clip_candidates(sbdir, sid):
    """<sid>__*.mp4 next to the frames, newest first; *__lipsync.mp4 (broken LatentSync output) is ignored"""
    c = [p for p in Path(sbdir).glob(sid + "__*.mp4") if p.name.split("__")[0] == sid and not p.stem.endswith("__lipsync")]
    return sorted(c, key=lambda p: p.stat().st_mtime, reverse=True)


def pick_clip(sbdir, sid, marks):
    """newest ❤ clip, else the newest non-👎 one (mvReel / sceneClips in the gallery template); None when there is none"""
    all_ = [p for p in clip_candidates(sbdir, sid) if not has_act(marks.get(rel(p)), "nope")]
    return next((p for p in all_ if has_act(marks.get(rel(p)), "love")), all_[0] if all_ else None)


def load_marks():
    return read_json(ROOT / "feedback" / "state.json", {}) or {}


# ---------------------------------------------------------------- the edit list
def classify(sc, memory_cast=()):
    """memory = a flashback (a scene `look` of "memory", or the prompt/place mention a flashback / memory, or a cast member listed in the
    chapter's `memory_cast` is in the scene); now = the performance + inserts. A scene `look` of "now" always wins."""
    if sc.get("look") in ("now", "memory"):
        return sc["look"]
    t = " ".join(str(sc.get(k) or "") for k in ("prompt", "place", "shot", "camera")).lower()
    who = {w.lower() for w in (sc.get("with") or [])}
    return "memory" if ("flashback" in t or "warm faded" in t or who & {m.lower() for m in memory_cast}) else "now"


def moments(stems, kind):
    return sorted(m["t"] for m in (stems or {}).get("moments", []) if m.get("kind") == kind)


def plan_edit(chapter, stems, preroll=None):
    scenes = sorted(chapter["scenes"], key=lambda s: s["t0"])
    tempo = float((stems or {}).get("tempo") or 100)
    dissolve = min(1.0, max(0.6, round(2 * 60.0 / tempo * 24) / 24))
    drops, breaks = moments(stems, "drop"), moments(stems, "breakdown")
    near = lambda ts, t, tol: any(abs(x - t) <= tol for x in ts)
    cuts, prev = [], None
    memory_cast = chapter.get("memory_cast") or []
    for i, sc in enumerate(scenes):
        look = classify(sc, memory_cast)
        why = sc.get("cut_why") or sc.get("lyric") or ""
        tr, reason = {"type": "cut", "dur": 0.0}, "hard cut on the beat"
        if i and near(drops, sc["t0"], 0.3):
            tr, reason = {"type": "flash", "dur": round(FLASH_F / 24, 3)}, "the drop: a 3-frame white flash"
        elif i and near(breaks, sc["t0"], 0.35):
            tr, reason = {"type": "fadeblack", "dur": 0.8}, "the band drops out: dip through black"
        elif i and "hard cut" in why:
            reason = "the band slams back: hard cut"
        elif i and look != prev:
            tr, reason = {"type": "dissolve", "dur": dissolve}, ("NOW -> MEMORY" if look == "memory" else "MEMORY -> NOW") + ": dissolve (~2 beats)"
        cut = {"frame": sc["id"], "t0": sc["t0"], "t1": sc["t1"], "clip": None, "look": look, "in": tr, "fx": [],
               "why": f"{reason} · {why}" if why else reason}
        cuts.append(cut)
        prev = look
    if cuts:  # dust on the first and last frame
        cuts[0]["fx"].append("dust")
        if len(cuts) > 1:
            cuts[-1]["fx"].append("dust")
    overlays = []
    if drops:  # chorus after the drop: a subtle exposure pulse on the downbeats, until the last sung frame
        sung = [s["t1"] for s in scenes if s["t0"] >= drops[0] and "instrumental" not in str(s.get("lyric", "")).lower()]
        if sung:
            overlays.append({"type": "beatflash", "t0": drops[0], "t1": max(sung), "strength": 0.06})
    pr = preroll if preroll is not None else max([float(s.get("preroll") or 0) for s in scenes] or [0])
    return {"output": {**DEFAULT_OUTPUT, "preroll": pr}, "looks": DEFAULT_LOOKS, "cuts": cuts, "overlays": overlays}


# ---------------------------------------------------------------- probing
def probe(path):
    """{frames, fps, w, h, dur, audio}: the video stream's frame count (counted when the container has none)"""
    r = subprocess.run([FFPROBE, "-v", "error", "-count_packets", "-show_entries", "stream=codec_type,width,height,r_frame_rate,nb_read_packets,duration",
                        "-of", "json", str(path)], capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    n, fr = int(v.get("nb_read_packets") or 0), v.get("r_frame_rate", "24/1").split("/")
    fps = float(fr[0]) / float(fr[1] or 1) if len(fr) == 2 and float(fr[1] or 0) else 24.0
    return {"frames": n, "fps": fps, "w": v.get("width"), "h": v.get("height"), "dur": n / fps if fps else 0.0,
            "audio": any(s.get("codec_type") == "audio" for s in d.get("streams", []))}


def audio_len(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


# ---------------------------------------------------------------- fitting the clips to the song timeline (pure: frame arithmetic)
def resolve(edit, chapter, mvdir, marks, probe_fn=probe, song_dur=None, draft=False, sb="sb01"):
    """-> {fps, w, h, preroll, total_f, pieces: [...]}. Every piece: frame, kind sing|clip|still, clip, fit (how it was fitted), speed, a_f/b_f (its own
    window in video frames), ext_f (frames borrowed by the NEXT transition), n_f (= b_f - a_f + ext_f frames rendered), in (type, d_f), look, fx, why."""
    mvdir, out = Path(mvdir), {**DEFAULT_OUTPUT, **(edit.get("output") or {})}
    fps, P = int(out["fps"]), float(out.get("preroll") or 0)
    w, h = (1280, 720) if draft else (int(out["w"]), int(out["h"]))
    sbdir = mvdir / sb
    scenes = {s["id"]: s for s in chapter.get("scenes", [])}
    cuts = sorted(edit["cuts"], key=lambda c: c.get("t0", scenes.get(c["frame"], {}).get("t0", 0)))
    for c in cuts:
        s = scenes.get(c["frame"], {})
        c.setdefault("t0", s.get("t0", 0)); c.setdefault("t1", s.get("t1", c["t0"]))
    total_f = F(P + (song_dur if song_dur is not None else cuts[-1]["t1"]), fps)
    bounds = [0] + [F(P + c["t0"], fps) for c in cuts[1:]] + [total_f]
    # transitions first: how many frames the incoming piece's blend borrows from the outgoing one
    dfs = []
    for i, c in enumerate(cuts):
        tr = c.get("in") or {"type": "cut", "dur": 0}
        typ = tr.get("type", "cut")
        if typ not in NO_OVERLAP and typ not in XFADE:
            typ = "cut"
        d = 0 if typ in NO_OVERLAP or not i else max(1, F(float(tr.get("dur") or 0), fps))
        if d:
            d = min(d, (bounds[i + 1] - bounds[i]) - 1, (bounds[i] - bounds[i - 1]) - 1)
            d = max(d, 0)
            if not d:
                typ = "cut"
        dfs.append((typ if i else "cut", d))
    pieces = []
    for i, c in enumerate(cuts):
        sid, A, B = c["frame"], bounds[i], bounds[i + 1]
        ext = dfs[i + 1][1] if i + 1 < len(cuts) else 0
        n = B - A + ext
        clip = None
        if c.get("clip"):
            for base in (ROOT, mvdir, sbdir):
                if (base / c["clip"]).is_file():
                    clip = base / c["clip"]; break
        else:
            clip = pick_clip(sbdir, sid, marks)
        meta = read_json(clip.with_suffix(".json"), {}) if clip else {}
        still = sbdir / f"{sid}.png"
        p = {"frame": sid, "a_f": A, "b_f": B, "ext_f": ext, "n_f": n, "in": {"type": dfs[i][0], "d_f": dfs[i][1]}, "look": c.get("look", "none"),
             "fx": list(c.get("fx") or []), "why": c.get("why", ""), "t0": c["t0"], "t1": c["t1"],
             "still": still.as_posix() if still.is_file() else None, "clip": rel(clip) if clip else None, "clip_abs": clip.as_posix() if clip else None,
             "engine": meta.get("engine"), "reversed": bool(meta.get("reversed")), "play_reverse": bool(c.get("reverse")), "label": c.get("label") or sid}
        # edit.json per cut: reverse (play the clip backwards; a borrowed "stolen" dance shot), label (draft corner text), unsync, clip_from, max_slow
        if clip:
            pr = probe_fn(clip)
            # length in OUTPUT frames: the piece chain resamples with fps=<out fps> first (Wan is 16 fps, the cut 24)
            Dn = F(pr["dur"], fps) if pr.get("fps") and abs(pr["fps"] - fps) > 0.01 and pr.get("dur") else pr["frames"]
            if c.get("clip_len") and meta.get("engine") not in SING_ENGINES:  # use only the first N s (Wan rolls back to its start pose after ~5 s)
                Dn = max(1, min(Dn, F(float(c["clip_len"]), fps)))
            sa = meta.get("song_audio") or {}
            if meta.get("engine") in SING_ENGINES and sa.get("t0") is not None and not c.get("unsync"):  # lip-synced: frame 0 belongs at song time sa.t0
                # (edit.json unsync: true = a silent LTX take, fit it like any clip: trim / slow / hold)
                c0 = F(P + float(sa["t0"]), fps)
                s0 = max(0, A - c0); pre = max(0, c0 - A)
                s0 = min(s0, Dn - 1)
                post = max(0, (A + n) - (c0 + Dn))
                fit = "sing-placed" + ("+hold-first" if pre else "") + ("+hold-last" if post else "") + ("+trim-head" if A - c0 > 0 else "")
                p.update(kind="sing", s0=s0, pre_f=pre, speed=1.0, fit=fit, clip_f0=c0, clip_frames=Dn, sync_t=c0 / fps, song_t0=float(sa["t0"]))
            else:
                W = B - A
                rev = p["reversed"]
                if Dn >= W:
                    s0 = max(0, Dn - W) if rev else 0  # a reversed entrance must END on the next frame: keep its tail (the extension holds that last frame)
                    if c.get("clip_from") is not None:  # edit.json override: start the clip at this second (e.g. skip a bad stretch at its end)
                        s0 = min(max(0, F(float(c["clip_from"]), fps)), Dn - W)
                    p.update(kind="clip", s0=s0, pre_f=0, speed=1.0, fit="trim" if Dn >= n else "trim+hold-last", clip_frames=Dn)
                else:
                    f = min(W / Dn, float(c.get("max_slow") or 1.25))  # edit.json max_slow: allow more slow-mo for this cut
                    slowed = Dn * f
                    p.update(kind="clip", s0=0, pre_f=0, speed=round(f, 4), clip_frames=Dn,
                             fit=("slow" if abs(slowed - W) < 1.5 and f > 1.0001 else "slow+hold-last") if f > 1.0001 else "hold-last")
        else:
            p.update(kind="still", s0=0, pre_f=0, speed=1.0, fit="still-kenburns" if p["still"] else "black")
        pieces.append(p)
    return {"fps": fps, "w": w, "h": h, "preroll": P, "total_f": total_f, "pieces": pieces, "output": out}


# ---------------------------------------------------------------- ffmpeg graphs
def q(s):
    return str(s).replace("\\", "/")


def look_chain(look):
    """ffmpeg filters (list) for a look dict; glow needs a split so it comes back as a graph fragment"""
    ch = []
    if look.get("eq"):
        ch.append("eq=" + look["eq"])
    if look.get("colorbalance"):
        ch.append("colorbalance=" + look["colorbalance"])
    if look.get("curves"):
        ch.append("curves=" + look["curves"])
    return ch


def piece_graph(p, fps, w, h, look, secs, extra):
    """filter_complex for one piece -> label [v]. extra = list of lavfi input sources appended after the clip / still (inputs 1..)"""
    norm = f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},setsar=1,fps={fps},format=yuv420p"
    n = p["n_f"]
    if p["kind"] == "still":
        if p["still"]:
            zi = f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase:flags=lanczos,crop={w * 2}:{h * 2}"
            src = f"[0:v]{zi},zoompan=z='1+0.10*on/{max(n, 1)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={w}x{h}:fps={fps},setsar=1,format=yuv420p"
        else:
            src = "[0:v]null"
        g = [f"{src}[b]"]
    else:
        s0 = p["s0"]
        ch = [f"fps={fps}"] + (["reverse", "setpts=PTS-STARTPTS"] if p.get("play_reverse") else []) + [f"trim=start_frame={s0}", "setpts=PTS-STARTPTS"]
        if p["speed"] != 1.0:
            ch += [f"setpts={p['speed']}*PTS", f"fps={fps}"]
        ch.append(f"tpad=start={p['pre_f']}:start_mode=clone:stop={n}:stop_mode=clone")
        g = [f"[0:v]{','.join(ch)},{norm}[b]"]
    cur = "b"
    if p["in"]["type"] == "flash":
        g.append(f"[{cur}]fade=t=in:st=0:n={FLASH_F}:color=white[f]"); cur = "f"
    lc = look_chain(look)
    if lc:
        g.append(f"[{cur}]{','.join(lc)}[l]"); cur = "l"
    if look.get("glow"):
        g.append(f"[{cur}]split[ga][gb];[gb]gblur=sigma={look.get('glow_sigma', 14)}[gc];[ga][gc]blend=all_mode=screen:all_opacity={look['glow']}[gg]"); cur = "gg"
    if look.get("grain"):
        g.append(f"[{cur}]noise=alls={int(look['grain'] * 100)}:allf=t+u[gn]"); cur = "gn"
    for k, (kind, _) in enumerate(extra):
        idx = 1 + k
        g.append(f"[{idx}:v]format=yuv420p[x{k}]")
        g.append(f"[{cur}][x{k}]blend=all_mode={'overlay' if kind == 'dust' else 'screen'}:all_opacity={'0.9' if kind == 'dust' else '0.75'}[y{k}]"); cur = f"y{k}"
    g.append(f"[{cur}]null[v]")
    return ";\n".join(g)


def make_dust(path, w, h, fps, secs, seed=7):
    """film dust on MID-GREY (blended with 'overlay': grey = no change, dark specks darken, light flecks lighten): a few soft specks a
    frame (mostly dark dirt), the odd bigger blob, hairs that stay 2-4 frames, a faint drifting vertical scratch now and then.
    (per-frame random white pixels would read as TV static)"""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
    path = Path(path)
    if path.exists():
        return path
    rng, n = np.random.default_rng(seed), max(1, int(round(secs * fps)))
    k = max(1.0, w / 1920)  # sizes scale with the output
    hairs, scratch = [], None
    proc = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                             "-c:v", "libx264", "-crf", "12", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)
    for f in range(n):
        im = Image.new("L", (w, h), 128)
        d = ImageDraw.Draw(im)
        for _ in range(rng.poisson(2.2)):  # specks
            x, y = rng.uniform(0, w), rng.uniform(0, h)
            r = (rng.uniform(3, 6) if rng.random() < 0.06 else rng.uniform(0.8, 2.4)) * k
            v = int(rng.uniform(40, 95)) if rng.random() < 0.75 else int(rng.uniform(175, 215))
            d.ellipse([x - r, y - r * rng.uniform(0.6, 1.0), x + r, y + r * rng.uniform(0.6, 1.0)], fill=v)
        if rng.random() < 0.035:  # a hair / fibre that stays a few frames
            x, y, a, L = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0, 6.28), rng.uniform(25, 70) * k
            pts = [(x + i / 8 * L * np.cos(a + 0.9 * np.sin(i / 3)), y + i / 8 * L * np.sin(a + 0.9 * np.sin(i / 3))) for i in range(9)]
            hairs.append([pts, int(rng.integers(2, 5))])
        for hr in hairs:
            d.line(hr[0], fill=70, width=max(1, int(k)))
            hr[1] -= 1
        hairs = [hr for hr in hairs if hr[1] > 0]
        if scratch is None and rng.random() < 0.012:  # a faint vertical scratch that drifts for ~0.5 s
            scratch = [rng.uniform(0.1, 0.9) * w, int(rng.integers(8, 16)), rng.uniform(0.3, 1.0) * h]
        if scratch:
            scratch[0] += rng.normal(0, 1.2 * k)
            y0 = rng.uniform(0, h - scratch[2])
            d.line([(scratch[0], y0), (scratch[0], y0 + scratch[2])], fill=160, width=1)
            scratch[1] -= 1
            if scratch[1] <= 0:
                scratch = None
        proc.stdin.write(im.filter(ImageFilter.GaussianBlur(0.6 * k)).tobytes())
    proc.stdin.close()
    proc.wait()
    return path


def fx_source(kind, w, h, fps, secs):
    # lightleak: a warm orange glow drifting across the frame, peaking mid-piece
    d = max(secs, 0.1)
    k = f"max(0,1-hypot(X-W*(0.05+0.4*T/{d:.3f}),Y-H*0.25)/(W*0.75))*pow(sin(PI*T/{d:.3f}),2)"
    return f"color=c=black:s={w // 4}x{h // 4}:r={fps}:d={secs:.3f},format=gbrp,geq=r='255*{k}':g='120*{k}':b='35*{k}',scale={w}:{h}:flags=bicubic,gblur=sigma=8"


class Runner:
    def __init__(self, cwd, log=None):
        self.cwd, self.log = Path(cwd), log

    def ff(self, args, graph=None, name="g"):
        cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostdin"]
        if graph is not None:
            gp = self.cwd / f"{name}.txt"
            gp.write_text(graph, encoding="utf-8")
            args = list(args)
            i = args.index("@graph")
            args[i:i + 1] = ["-/filter_complex", gp.name]
        r = subprocess.run(cmd + args, cwd=self.cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            raise RuntimeError("ffmpeg failed: " + (r.stderr or "")[-1500:])


def render_piece(run, p, tl, looks, draft, path):
    fps, w, h = tl["fps"], tl["w"], tl["h"]
    look = looks.get(p["look"]) or {}
    secs = p["n_f"] / fps
    extra = [(k, str(make_dust(run.cwd / f"dust_{w}x{h}_{p['n_f']}.mp4", w, h, fps, secs)) if k == "dust" else fx_source(k, w, h, fps, secs))
             for k in p["fx"] if k in ("dust", "lightleak")]
    args = []
    if p["kind"] == "still" and p["still"]:
        args += ["-i", p["still"]]
    elif p["kind"] != "still":
        args += ["-i", p["clip_abs"]]
    else:
        args += ["-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r={fps}:d={secs:.3f}"]
    for kind, src in extra:
        args += ["-i", src] if kind == "dust" else ["-f", "lavfi", "-i", src]
    g = piece_graph(p, fps, w, h, look, secs, extra)
    run.ff(args + ["@graph", "-map", "[v]", "-frames:v", str(p["n_f"]), "-r", str(fps), "-an", "-c:v", "libx264", "-crf", "16" if not draft else "20",
                   "-preset", "ultrafast" if draft else "veryfast", "-bf", "0", "-pix_fmt", "yuv420p", "-g", "48", str(path)], g, name=f"g_{path.stem}")


def make_units(pieces):
    """consecutive pieces joined by an xfade form one unit (rendered together); hard cuts separate units -> [[piece idx...], ...]"""
    units = []
    for i, p in enumerate(pieces):
        if i and p["in"]["d_f"]:
            units[-1].append(i)
        else:
            units.append([i])
    return units


def render_unit(run, pieces, idxs, fps, files, path, draft):
    args, g, cur, a0 = [], [], "[0:v]", pieces[idxs[0]]["a_f"]
    for k, i in enumerate(idxs):
        args += ["-i", files[i].name]
    for k, i in enumerate(idxs[1:], start=1):
        p = pieces[i]
        x = XFADE[p["in"]["type"]]
        g.append(f"{cur}[{k}:v]xfade=transition={x}:duration={p['in']['d_f'] / fps:.6f}:offset={(p['a_f'] - a0) / fps:.6f}[u{k}]")
        cur = f"[u{k}]"
    g.append(f"{cur}null[v]")
    n = pieces[idxs[-1]]["a_f"] + pieces[idxs[-1]]["n_f"] - a0
    run.ff(args + ["@graph", "-map", "[v]", "-frames:v", str(n), "-r", str(fps), "-an", "-c:v", "libx264", "-crf", "16" if not draft else "20",
                   "-preset", "ultrafast" if draft else "veryfast", "-bf", "0", "-pix_fmt", "yuv420p", "-g", "48", str(path)], ";\n".join(g), name=f"g_{path.stem}")


def beat_windows(stems, t0, t1, P, strength):
    db = [t for t in (stems or {}).get("downbeats", []) if t0 <= t <= t1]
    return [(P + t, P + t + 0.10) for t in db]


def publish_cut(part, out_path, keep=1):
    """swap the finished build in atomically; the previous one moves to cut/_old/<stem>__<mtime>.mp4 (last `keep` kept) so a player
    still on the old ?v=<mtime> URL gets the old bytes from serve_gallery.pinned_cut instead of a half-new file"""
    out_path = Path(out_path)
    if out_path.is_file():
        old = out_path.parent / "_old"
        old.mkdir(exist_ok=True)
        shutil.copy2(out_path, old / f"{out_path.stem}__{int(out_path.stat().st_mtime)}{out_path.suffix}")
        for f in sorted(old.glob(f"{out_path.stem}__*{out_path.suffix}"), key=lambda q: q.stat().st_mtime)[:-keep]:
            f.unlink()
    for i in range(120):  # Windows: a player's open handle blocks the swap for a moment; retry up to ~2 min
        try:
            os.replace(part, out_path)
            return
        except PermissionError:
            if i == 119:
                raise
            time.sleep(1)


def final_pass(run, mvdir, tl, edit, units_files, stems, lyr, audio_path, intro, out_path, draft, total_s, heads=()):
    """concat the units + vignette, grain, dust/beat-flash overlays, lyrics, end fade; audio = intro crossfaded into the full song; one encode"""
    fps, w, h, P, out = tl["fps"], tl["w"], tl["h"], tl["preroll"], tl["output"]
    lst = run.cwd / "concat.txt"
    lst.write_text("".join(f"file '{f.name}'\n" for f in units_files), encoding="utf-8")
    args = ["-f", "concat", "-safe", "0", "-i", "concat.txt", "-i", str(audio_path)]
    nxt = 2
    if intro:
        args += ["-i", str(intro)]; intro_idx, nxt = nxt, nxt + 1
    g, cur = [], "[0:v]"
    ov = list(edit.get("overlays") or [])
    dust = [o for o in ov if o["type"] == "dust"]
    if dust:
        args += ["-i", str(make_dust(run.cwd / f"dust_{w}x{h}_all.mp4", w, h, fps, total_s))]
        en = "+".join(f"between(t,{P + o['t0']:.3f},{P + o['t1']:.3f})" for o in dust)
        g.append(f"[{nxt}:v]format=yuv420p[dv];{cur}[dv]blend=all_mode=overlay:all_opacity=0.9:enable='{en}'[d0]"); cur = "[d0]"; nxt += 1
    flashes, strength = [], 0.06
    for o in ov:
        if o["type"] == "beatflash":
            strength = float(o.get("strength", strength)); flashes += beat_windows(stems, o["t0"], o["t1"], P, strength)
    for c in edit["cuts"]:
        if "beatflash" in (c.get("fx") or []):
            flashes += beat_windows(stems, c["t0"], c["t1"], P, strength)
    if flashes:
        en = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in sorted(set(flashes)))
        g.append(f"{cur}drawbox=x=0:y=0:w=iw:h=ih:color=white@{strength}:t=fill:enable='{en}'[bf]"); cur = "[bf]"
    if out.get("vignette"):
        ang = math.pi / 2 - float(out["vignette"]) * (math.pi / 2 - math.pi / 6)
        g.append(f"{cur}vignette=angle={ang:.4f}:eval=init[vg]"); cur = "[vg]"
    if out.get("grain"):
        g.append(f"{cur}noise=alls={int(float(out['grain']) * 100)}:allf=t+u[gr]"); cur = "[gr]"
    for k, (t0, t1, txt) in enumerate(lyr):
        (run.cwd / f"lyr{k}.txt").write_text(txt, encoding="utf-8")
        a, b = P + t0, P + t1
        g.append(f"{cur}drawtext=fontfile={out_font(run.cwd, out)}:textfile=lyr{k}.txt:fontsize=h/24:fontcolor=white:borderw=2:bordercolor=black@0.55:"
                 f"x=(w-tw)/2:y=h*{0.72 if heads else 0.84}:enable='between(t,{a:.3f},{b:.3f})':alpha='max(0,min(1,min((t-{a:.3f})/0.3,({b:.3f}-t)/0.3)))'[lt{k}]"); cur = f"[lt{k}]"
    hf, cur = headline_filters(run.cwd, heads, w, h, cur, out)  # 📰 news-style lower thirds
    g += hf
    if out.get("labels", draft):  # draft: frame id in the lower-left corner (top-left when headlines are on), so notes can refer to "s7"
        ps = tl["pieces"]
        for k, pc in enumerate(ps):
            a, b = pc["a_f"] / fps, (ps[k + 1]["a_f"] / fps if k + 1 < len(ps) else total_s)
            g.append(f"{cur}drawtext=fontfile={out_font(run.cwd, out)}:text='{str(pc.get("label") or pc["frame"]).replace(":", " ").replace("'", "")}':fontsize=h/22:fontcolor=white@0.85:borderw=2:bordercolor=black@0.6:"
                     f"x=h*0.03:y={'h*0.03' if heads else 'h*0.95-th'}:enable='between(t,{a:.3f},{b:.3f})'[sl{k}]"); cur = f"[sl{k}]"
    g.append(f"{cur}fade=t=out:st={max(0, total_s - 1.5):.3f}:d=1.5,format=yuv420p[v]")
    sr = "aresample=48000,aformat=channel_layouts=stereo"
    ag = [f"[1:a]{sr},adelay=delays={int(P * 1000)}:all=1[s]"] if P else [f"[1:a]{sr}[s]"]
    if intro and P:
        mute = min(float(edit.get("output", {}).get("intro_mute") or 0), P)  # silence the clip's first N s (e.g. a model ping)
        fin = f",afade=t=in:st={mute:.3f}:d=0.3" if mute else ""
        ag.append(f"[{intro_idx}:a]{sr},atrim=0:{P + 0.2:.3f},asetpts=PTS-STARTPTS{fin},afade=t=out:st={max(0, P - 0.1):.3f}:d=0.3[i]")
        ag.append("[i][s]amix=inputs=2:duration=longest:normalize=0[a]")
    else:
        ag.append("[s]anull[a]")
    run.ff(args + ["@graph", "-map", "[v]", "-map", "[a]", "-t", f"{total_s:.3f}", "-r", str(fps), "-c:v", "libx264", "-crf", "23" if draft else "18", *([] if draft else ["-maxrate", str(out.get("maxrate", "16M")), "-bufsize", str(out.get("bufsize", "32M"))]),
                   "-preset", "veryfast" if draft else "slow", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", "-f", "mp4", str(out_path)],
           ";\n".join(g + ag), name="final")


def headline_plan(tl, chapter, mv, edit):
    """[(a, b, text, tag)] in VIDEO seconds for every piece whose own `frame` scene has a `headline` (a cut that reuses another scene's clip
    still shows the headline of its frame). output.headlines: true/false (default: on when any scene has one); output.headline_tag > scene
    headline_tag > mv.json headline_tag > BREAKING."""
    out = tl["output"]
    scenes = {s["id"]: s for s in (chapter or {}).get("scenes", [])}
    on = out.get("headlines")
    if on is None:
        on = any(s.get("headline") for s in scenes.values())
    if not on:
        return []
    fps, ps, res = tl["fps"], tl["pieces"], []
    for k, pc in enumerate(ps):
        sc = scenes.get(pc["frame"]) or {}
        if not sc.get("headline"):
            continue
        a = pc["a_f"] / fps
        b = ps[k + 1]["a_f"] / fps if k + 1 < len(ps) else tl["total_f"] / fps
        tag = out.get("headline_tag") or sc.get("headline_tag") or (mv or {}).get("headline_tag") or "BREAKING"
        res.append((a, b, str(sc["headline"]).strip(), str(tag).strip()))
    return res


def headline_filters(cwd, heads, w, h, cur, out):
    """drawbox/drawtext chain (text via textfile=, so no escaping): a hot-pink tag box + a navy bar with the headline in bold white caps at the
    bottom-left (85% wide, ~11.5% tall). drawbox cannot take `t`, so each box is 3 stacked layers switched on 0.08 s apart (a 0.25 s stepped
    fade in at the start of the cut and out at its end); the text fades with an alpha expression like the lyrics."""
    if not heads:
        return [], cur
    font = out_font(cwd, out, "headline_font", "hlfont.ttf")
    x0, bw, bh = round(w * 0.03), round(w * 0.85), round(h * 0.115)
    y0 = round(h * 0.95) - bh
    tw_, pad, line = round(w * 0.13), round(w * 0.015), max(2, h // 150)
    avail = bw - tw_ - 2 * pad

    def boxes(x, y, bw_, bh_, color, f, a, b):  # stepped-alpha stack: cumulative opacity f/3, 2f/3, f
        res, step = [], 0.08
        cum = [f / 3, 2 * f / 3, f]
        prev = 0.0
        for n, c in enumerate(cum):
            al = 1 - (1 - c) / (1 - prev) if prev < 1 else 1
            prev = c
            res.append(f"drawbox=x={x}:y={y}:w={bw_}:h={bh_}:color={color}@{al:.3f}:t=fill:enable='between(t,{a + n * step:.3f},{b - n * step:.3f})'")
        return res
    g = []
    for k, (a, b, txt, tag) in enumerate(heads):
        txt = txt.upper()
        (Path(cwd) / f"hl{k}.txt").write_text(txt, encoding="utf-8")
        (Path(cwd) / f"hlt{k}.txt").write_text(tag.upper(), encoding="utf-8")
        fs = max(round(h / 34), min(round(h / 19), int(avail / (max(len(txt), 1) * 0.69))))
        tfs = round(min(h / 34, tw_ / (max(len(tag), 1) * 0.75)))
        al = f"alpha='max(0,min(1,min((t-{a:.3f})/0.25,({b:.3f}-t)/0.25)))':enable='between(t,{a:.3f},{b:.3f})'"
        chain = (boxes(x0, y0 - line, bw, line, "white", 0.9, a, b) + boxes(x0 + tw_, y0, bw - tw_, bh, "0x081642", 0.9, a, b)
                 + boxes(x0, y0, tw_, bh, "0xe8358f", 1.0, a, b)
                 + [f"drawtext=fontfile={font}:textfile=hlt{k}.txt:expansion=none:fontsize={tfs}:fontcolor=white:x={x0}+({tw_}-tw)/2:y={y0}+({bh}-th)/2:{al}",
                    f"drawtext=fontfile={font}:textfile=hl{k}.txt:expansion=none:fontsize={fs}:fontcolor=white:x={x0 + tw_ + pad}:y={y0}+({bh}-th)/2:{al}"])
        g.append(cur + ",".join(chain) + f"[hl{k}]")
        cur = f"[hl{k}]"
    return g, cur


def out_font(cwd, out, key="font", name="font.ttf"):
    """copy the font next to the filter script (ffmpeg's drawtext fontfile= wants a plain relative name): edit.json output[key],
    else config.find_font() (config.json "font" / "headline_font", else a common system font)"""
    src = Path(out.get(key) or find_font("headline_font" if key == "headline_font" else "font") or "")
    if not src.is_file():
        raise RuntimeError("no usable font for text overlays: set \"font\" / \"headline_font\" in config.json or output.%s in edit.json" % key)
    dst = Path(cwd) / name
    if not dst.exists():
        shutil.copy(src, dst)
    return name


def lyric_lines(edit, mvdir, tl_out):
    lt = read_json(Path(mvdir) / "audio" / "lyrics_timing.json", {}) or {}
    mode = tl_out.get("lyrics")
    ovs = [o for o in (edit.get("overlays") or []) if o["type"] == "lyrics"]
    if not mode and not ovs:
        return []
    out = []
    for ln in lt.get("lines", []):
        if mode != "all" and float(ln.get("conf", 1)) < 0.5:
            continue
        a, b = float(ln["t0"]), float(ln["t1"]) + 0.3
        if ovs and not any(o["t0"] <= a <= o["t1"] for o in ovs) and not mode:
            continue
        out.append((a, b, str(ln["text"]).strip()))
    return out


def strip_sheet(video, tl, pieces, out_jpg, run):
    from PIL import Image, ImageDraw
    tiles = []
    for i, p in enumerate(pieces):
        t = (p["a_f"] + p["b_f"]) / 2 / tl["fps"]
        tmp = run.cwd / f"strip{i}.jpg"
        run.ff(["-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", "scale=320:-2", str(tmp)])
        im = Image.open(tmp).convert("RGB")
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, im.width, 14], fill=(0, 0, 0))
        d.text((3, 1), f"#{i + 1} {p['frame']} {p['kind']} {p['in']['type']} {p['look']}", fill=(255, 255, 255))
        tiles.append(im)
    cols = 6
    tw, th = tiles[0].size
    sheet = Image.new("RGB", (cols * tw, ((len(tiles) + cols - 1) // cols) * th), (20, 20, 20))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % cols) * tw, (i // cols) * th))
    sheet.save(out_jpg, quality=85)


def set_status(cutdir, **kw):
    cutdir.mkdir(exist_ok=True)
    st = read_json(cutdir / "_status.json", {}) or {}
    st.update(kw, ts=int(time.time()))
    (cutdir / "_status.json").write_text(json.dumps(st), encoding="utf-8")


def assemble(mvdir, sb="sb01", edit_path=None, draft=False, out=None, keep=False, plan_only=False, replan=False):
    mvdir = Path(mvdir)
    mv = read_json(mvdir / "mv.json", {})
    chapter = read_json(mvdir / sb / "chapter.json")
    stems = read_json(mvdir / "audio" / "stems.json")
    ep = Path(edit_path) if edit_path else mvdir / "edit.json"
    if not ep.is_absolute() and not ep.exists():
        ep = mvdir / ep
    if replan or not ep.exists():
        edit = plan_edit(chapter, stems)
        ep.write_text(json.dumps(edit, indent=1, ensure_ascii=False), encoding="utf-8")
        print("wrote", rel(ep), "-", len(edit["cuts"]), "cuts")
    elif plan_only:
        print(rel(ep), "exists: use --replan to overwrite it")
    if plan_only:
        return None
    edit = read_json(ep)
    slug = re.sub(r"^\d+-", "", mvdir.name) + ("-draft" if draft else "")
    cutdir = mvdir / "cut"
    out_path = Path(out) if out else cutdir / f"{slug}.mp4"
    if not out_path.is_absolute():
        out_path = mvdir / out_path if str(out).startswith("cut/") or not out else ROOT / out_path
    cutdir.mkdir(exist_ok=True)
    audio = ROOT / mv["audio"]
    song_dur = audio_len(audio)
    t_start = time.time()
    set_status(cutdir, state="running", draft=draft, stage="planning the timeline", started=int(t_start), out=rel(out_path))
    tmp = mvdir / "_assembly"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    run = Runner(tmp)
    try:
        tl = resolve(edit, chapter, mvdir, load_marks(), song_dur=song_dur, draft=draft, sb=sb)
        looks = {**DEFAULT_LOOKS, **(edit.get("looks") or {}), "none": {}}
        P, fps, pcs = tl["preroll"], tl["fps"], tl["pieces"]
        files = []
        for i, p in enumerate(pcs):
            set_status(cutdir, stage=f"rendering piece {i + 1}/{len(pcs)} ({p['frame']})")
            f = tmp / f"p{i:02d}.mp4"
            render_piece(run, p, tl, looks, draft, f)
            files.append(f)
        units, ufiles = make_units(pcs), []
        for k, u in enumerate(units):
            set_status(cutdir, stage=f"transitions {k + 1}/{len(units)}")
            if len(u) == 1:
                ufiles.append(files[u[0]])
            else:
                uf = tmp / f"u{k:02d}.mp4"
                render_unit(run, pcs, u, fps, files, uf, draft)
                ufiles.append(uf)
        set_status(cutdir, stage="final pass: grade, overlays, audio")
        first = pcs[0]
        intro = None
        if P and first.get("clip_abs"):
            c = Path(first["clip_abs"])
            g = c.with_suffix(".genaudio.m4a")
            intro = g if g.exists() else (c if probe(c)["audio"] else None)
        total_s = tl["total_f"] / fps
        lyr = lyric_lines(edit, mvdir, tl["output"])
        part = out_path.with_name(out_path.name + ".part")  # never write over the file a player may be streaming
        final_pass(run, mvdir, tl, edit, ufiles, stems, lyr, audio, intro, part, draft, total_s, headline_plan(tl, chapter, mv, edit))
        publish_cut(part, out_path)
        set_status(cutdir, stage="contact sheet")
        strip = out_path.with_name(out_path.stem + "_strip.jpg")
        strip_sheet(out_path, tl, pcs, strip, run)
        res = {"mv": mvdir.name, "video": rel(out_path), "strip": rel(strip), "draft": draft, "w": tl["w"], "h": tl["h"], "fps": fps, "preroll": P,
               "duration": total_s, "song": rel(audio), "intro_audio": rel(intro) if intro else None, "built": int(time.time()), "build_seconds": round(time.time() - t_start, 1),
               "counts": count_types(pcs), "cuts": [
                   {"n": i + 1, "frame": p["frame"], "clip": p["clip"], "engine": p["engine"], "kind": p["kind"], "fit": p["fit"], "speed": p["speed"],
                    "t0": round(p["a_f"] / fps, 3), "t1": round(p["b_f"] / fps, 3), "song_t0": p["t0"], "song_t1": p["t1"], "frames": p["n_f"],
                    "in": p["in"]["type"], "in_dur": round(p["in"]["d_f"] / fps, 3), "look": p["look"], "fx": p["fx"], "why": p["why"],
                    **({"sync_t": round(p["sync_t"], 4)} if p["kind"] == "sing" else {})} for i, p in enumerate(pcs)]}
        out_path.with_suffix(".json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
        set_status(cutdir, state="done", stage="done", video=rel(out_path), finished=int(time.time()), error="")
        # the page asks for the cut as ?v=<mtime from data.json>: without a rebuild it keeps asking for (and, via cut/_old,
        # getting) the previous build
        bg = Path(__file__).resolve().parent / "build_gallery.py"
        if bg.is_file() and mvdir.resolve().is_relative_to(Path(__file__).resolve().parents[1]):  # (a test tree elsewhere never rebuilds the repo's gallery)
            subprocess.run([sys.executable, str(bg)], cwd=ROOT, capture_output=True)
    except Exception as e:  # keep _assembly for a look at what broke
        set_status(cutdir, state="error", stage="failed", error=str(e)[-600:])
        raise
    if not keep:
        shutil.rmtree(tmp, ignore_errors=True)
    return res


def count_types(pcs):
    c = {}
    for p in pcs:
        c[p["in"]["type"]] = c.get(p["in"]["type"], 0) + 1
    return c


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("mv")
    ap.add_argument("--sb", default="sb01")
    ap.add_argument("--edit")
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--plan", action="store_true", help="write the default edit list and stop")
    ap.add_argument("--replan", action="store_true", help="overwrite an existing edit.json with a fresh plan")
    ap.add_argument("--keep", action="store_true", help="keep _assembly/")
    a = ap.parse_args()
    d = Path(a.mv)
    d = d if d.is_absolute() else (ROOT / d if (ROOT / d).exists() else ROOT / "musicvideos" / d)
    r = assemble(d, a.sb, a.edit, a.draft, a.out, a.keep, a.plan, a.replan)
    if r:
        print(f"{r['video']}  {r['duration']:.1f}s  {r['w']}x{r['h']}  pieces={len(r['cuts'])}  {r['counts']}  built in {r['build_seconds']}s")


if __name__ == "__main__":
    main()
