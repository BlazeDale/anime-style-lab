#!/usr/bin/env python
"""🎞 NevNovella chapter final cut (the draft / YouTube / Suno / hooks build buttons on saga chapters).

  python tools/saga_assemble.py explore/sagas/NNN-x/chNN --target draft|youtube|suno|hooks [--captions] [--keep] [--dry-run] [--no-gallery]

One piece per shot, in order: the shot's clip by the gallery rule (newest ❤ clip, else newest non-👎; same helpers as the music-video cut),
else the still eN.png with a slow Ken Burns push for its `hold` seconds (silent). Clips keep their own audio. ~0.5 s dissolves between pieces,
every piece fitted (scaled + padded) to 16:9: 1920x1080 for the master, 960x540 for the draft. An opening title card (saga title + "Chapter N · title",
3 s, fades) and a short fade-out at the end. Optional burned-in captions (--captions, off by default).
Outputs in chNN/cut/: draft = <saga>-chNN-draft.mp4 | youtube = the master <saga>-chNN.mp4 | suno = the master re-encoded under 200 MB (-suno.mp4;
builds the master first when it is not current) | hooks = 10-30 s segments cut at shot boundaries -> cut/hooks/NN-eA-eB.mp4 + hooks.json.
Each build writes <name>.json (the resolved timeline) and cut/_status.json {target, state running|done|error, stage, ts, out, msg}.
Filter graphs go through `-/filter_complex file` (Windows 32k command-line limit)."""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mv_assemble as MA  # the clip rule, ffmpeg paths, atomic publish, suno bitrate
import saga_edit as E  # the immersion pass: trims, beat snapping, Ken Burns, captions timing, look

ROOT = MA.ROOT
FFMPEG, FFPROBE = MA.FFMPEG, MA.FFPROBE
TARGETS = ("draft", "youtube", "suno", "hooks")
DISSOLVE = 0.5
TITLE_S = 3.0
FADE_OUT = 0.8
FPS = 24
SIZES = {"draft": (960, 540), "youtube": (1920, 1080)}
HOOK_MIN, HOOK_MAX, HOOK_AIM = 10.0, 30.0, 20.0


def read_json(p, default=None):
    return MA.read_json(p, default)


def slug_of(chdir):
    return re.sub(r"^\d+-", "", Path(chdir).parent.name)


def out_paths(chdir, target, mv_tag=None):
    """chNN/cut/<saga>-chNN[-draft|-suno].mp4 + hooks/; the saga-level music video (chdir = the saga dir, mv_tag "ch01-ch03"): cut/<saga>-ch01-ch03... + hooks-ch01-ch03/"""
    chdir = Path(chdir)
    base = f"{re.sub(r'^[0-9]+-', '', chdir.name)}-{mv_tag}" if mv_tag else f"{slug_of(chdir)}-{chdir.name}"
    cut = chdir / "cut"
    return {"draft": cut / f"{base}-draft.mp4", "youtube": cut / f"{base}.mp4", "suno": cut / f"{base}-suno.mp4", "hooks": cut / (f"hooks-{mv_tag}" if mv_tag else "hooks")}[target]


def set_status(chdir, **kw):
    cut = Path(chdir) / "cut"
    cut.mkdir(exist_ok=True)
    st = read_json(cut / "_status.json", {}) or {}
    st.update(kw, ts=int(time.time()))
    (cut / "_status.json").write_text(json.dumps(st), encoding="utf-8")


# ---------------------------------------------------------------- what plays for each shot (pure-ish: reads the folder + the marks)
def resolve(chdir, marks=None):
    """[{id, kind clip|still, src, clip (rel path or None), hold, text}] in shot order; a shot with neither clip nor picture is skipped"""
    chdir = Path(chdir)
    ep = read_json(chdir / "episode.json", {}) or {}
    marks = MA.load_marks() if marks is None else marks
    out = []
    for i, sh in enumerate(ep.get("shots") or [], 1):
        sid = sh.get("id") or f"e{i}"
        # `overview` = the cut's on-screen story line (short enough to read while the clip
        # runs); without one, the narration / dialogue / caption as before
        text = (sh.get("overview") or sh.get("narration") or " ".join(d.get("text", "") for d in sh.get("dialogue") or []) or sh.get("caption") or "").strip()
        clip = MA.pick_clip(chdir, sid, marks)
        png = chdir / f"{sid}.png"
        if clip:
            out.append({"id": sid, "kind": "clip", "src": str(clip), "clip": MA.rel(clip), "hold": None, "text": text, "place": sh.get("place") or "", "tod": E.tod(sh.get("prompt"))})
        elif png.is_file():
            out.append({"id": sid, "kind": "still", "src": str(png), "clip": None, "hold": float(sh.get("hold") or 6), "text": text, "place": sh.get("place") or "", "tod": E.tod(sh.get("prompt"))})
    return out


CLIP_SOUNDS = ("off", "low", "full")
LOW_VOL = 0.15
MUSIC_FADE_IN, MUSIC_FADE_OUT, MUSIC_XFADE = 1.0, 2.5, 1.5


def music_info(chdir):
    """the chapter's uploaded song + options (episode.json reel.music {file, name, ts, clip_sound, offset}); None without a usable file.
    Adds `path` (the file in chNN/cut/) and `mtime`."""
    chdir = Path(chdir)
    m = ((read_json(chdir / "episode.json", {}) or {}).get("reel") or {}).get("music")
    return music_from(chdir, m, (m or {}).get("clip_sound") if isinstance(m, dict) else None, (m or {}).get("offset") if isinstance(m, dict) else None)


def music_from(folder, m, clip_sound=None, offset=None):
    """music_info for any folder (a chapter, or the saga for its music video): m = {file, name}; the file lives in <folder>/cut/"""
    folder = Path(folder)
    if not isinstance(m, dict) or not m.get("file"):
        return None
    f = folder / "cut" / m["file"]
    if not f.is_file():
        return None
    cs = clip_sound if clip_sound in CLIP_SOUNDS else "off"
    try:
        off = max(0.0, float(offset or 0))
    except (TypeError, ValueError):
        off = 0.0
    return {"file": m["file"], "name": m.get("name") or m["file"], "clip_sound": cs, "offset": off, "path": str(f), "mtime": int(f.stat().st_mtime)}


def music_key(mi):
    return None if not mi else {"file": mi["file"], "mtime": mi["mtime"], "clip_sound": mi["clip_sound"], "offset": mi["offset"]}


# ---------------------------------------------------------------- pure timeline arithmetic
def timeline(durs, d=DISSOLVE):
    """piece durations -> ([start of each piece in the output], total); consecutive pieces overlap by d seconds (a dissolve; d may be a list, one per transition)"""
    starts, t = [], 0.0
    for i, x in enumerate(durs):
        starts.append(round(t, 3))
        t += x - ((d[i] if isinstance(d, (list, tuple)) else d) if i < len(durs) - 1 else 0)
    return starts, round(t, 3)


def plan_hooks(starts, total, lo=HOOK_MIN, hi=HOOK_MAX, aim=HOOK_AIM):
    """segments [(t0, t1)] of lo..hi seconds whose edges are shot starts (starts[0] opens the first hook, total ends the last).
    Picks the boundary closest to `aim`, never leaving a tail shorter than lo; one that can't fit (a long shot) takes the next boundary"""
    bounds = sorted(set([round(x, 3) for x in starts] + [round(total, 3)]))
    out, i = [], 0
    while i < len(bounds) - 1:
        s = bounds[i]
        cands = [j for j in range(i + 1, len(bounds)) if lo <= bounds[j] - s <= hi and (bounds[-1] - bounds[j] >= lo or j == len(bounds) - 1)]
        if bounds[-1] - s <= hi:
            cands = [len(bounds) - 1]
        if not cands:  # nothing in range: the first boundary past lo (a long shot), else the end
            cands = [next((j for j in range(i + 1, len(bounds)) if bounds[j] - s >= lo), len(bounds) - 1)]
        j = min(cands, key=lambda k: abs((bounds[k] - s) - aim))
        out.append((s, bounds[j]))
        i = j
    return out


# ---------------------------------------------------------------- ffmpeg
def run(args, what, cwd=None):
    r = subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostdin", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(f"{what} failed: {(r.stderr or '').strip()[-500:]}")


def dur_of(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def has_audio(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return "audio" in r.stdout


def font_file(work):
    src = Path("C:/Windows/Fonts/georgia.ttf")
    if not src.is_file():
        src = Path("C:/Windows/Fonts/arial.ttf")
    dst = Path(work) / "font.ttf"
    if src.is_file() and not dst.exists():
        shutil.copy(src, dst)
    return "font.ttf" if dst.exists() else None


def enc_args(draft):
    return ["-c:v", "libx264", "-preset", "ultrafast" if draft else "veryfast", "-crf", "26" if draft else "14", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "128k" if draft else "192k", "-ar", "48000", "-ac", "2"]


READ_WPS = 2.5  # comfortable on-screen reading speed (words per second)


def read_budget(dur):
    """how many words of on-screen text a viewer can read in a piece of `dur` seconds (the fades take ~1.2 s)"""
    return max(4, int((dur - 1.2) * READ_WPS))


def caption_vf(work, text, w, h, n, window=None):
    """drawtext (textfile in the work dir) for an on-screen line, immersion style: no box, a soft shadow + faint outline, serif, lower third at a fixed
    position, fading in and out between window=(t0, t1) seconds of the piece (saga_edit.caption_times). '' when there is no font, text or window"""
    ff = font_file(work)
    if not ff or not text or not window:
        return ""
    tf = Path(work) / f"cap{n}.txt"
    tf.write_text(re.sub(r"(.{1,46})(\s+|$)", r"\1\n", text).strip(), encoding="utf-8")
    alpha = f":alpha='{E.fade_alpha(window[0], window[1])}'"
    return (f",drawtext=fontfile={ff}:textfile={tf.name}:fontcolor=white:fontsize={max(16, h // 20)}:line_spacing={h // 120}"
            f":x=(w-text_w)/2:y=h*0.76:borderw=2:bordercolor=black@0.55:shadowcolor=black@0.9:shadowx=3:shadowy=3{alpha}")


def title_vf(work, saga, sub, w, h, piece_len):
    """the saga title + chapter faded in over the first shot (which darkens ~30 % meanwhile): -> (vf suffix, time the title is gone)"""
    ff = font_file(work)
    a, dim, end = E.title_alpha(piece_len)
    (Path(work) / "t1.txt").write_text(saga, encoding="utf-8")
    (Path(work) / "t2.txt").write_text(sub, encoding="utf-8")
    vf = f",eq=brightness='{dim}':eval=frame"
    if ff:
        vf += (f",drawtext=fontfile={ff}:textfile=t1.txt:fontcolor=white:fontsize={h // 11}:x=(w-text_w)/2:y=h*0.42-text_h/2:shadowcolor=black@0.85:shadowx=3:shadowy=3:alpha='{a}'"
               f",drawtext=fontfile={ff}:textfile=t2.txt:fontcolor=0xe6d8b0:fontsize={h // 22}:x=(w-text_w)/2:y=h*0.42+{h // 11}:shadowcolor=black@0.85:shadowx=2:shadowy=2:alpha='{a}'")
    return vf, end


def title_piece(work, saga, sub, w, h, draft, path):
    """the old separate black title card (reel.edit.title = "card")"""
    ff = font_file(work)
    (Path(work) / "t1.txt").write_text(saga, encoding="utf-8")
    (Path(work) / "t2.txt").write_text(sub, encoding="utf-8")
    vf = "format=yuv420p"
    if ff:
        vf = (f"drawtext=fontfile={ff}:textfile=t1.txt:fontcolor=white:fontsize={h // 11}:x=(w-text_w)/2:y=h*0.40-text_h/2,"
              f"drawtext=fontfile={ff}:textfile=t2.txt:fontcolor=0xd8c9a3:fontsize={h // 20}:x=(w-text_w)/2:y=h*0.40+{h // 12},format=yuv420p")
    vf += f",fade=t=in:st=0:d=0.7,fade=t=out:st={TITLE_S - 0.7}:d=0.7"
    run(["-f", "lavfi", "-i", f"color=c=0x0b0b10:s={w}x{h}:r={FPS}:d={TITLE_S}", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo", "-t", str(TITLE_S),
         "-vf", vf, *enc_args(draft), "-shortest", str(path)], "title card", cwd=work)


def clip_trim(p, trim=True):
    """(ss, avail): the good part of a clip. Motion analysis (tools/clip_motion) drops frozen heads / tails + the first 0.15 s."""
    full = dur_of(p["src"])
    if not trim:
        return 0.0, full
    try:
        import clip_motion
        m, fps = clip_motion.motion(p["src"])
        ss, to = E.trim_span(list(map(float, m)), fps)
        if to > ss:
            return ss, to - ss
    except Exception as e:  # numpy / decode trouble: keep the whole clip
        print("clip motion skipped for", p["id"], "-", str(e)[:80])
    return 0.0, full


def shot_piece(work, p, w, h, draft, path, n, extra_vf=""):
    """render one piece of length p['len']: a clip (trimmed from p['ss'], slowed up to 1.2x when it is shorter than asked) or a still with its Ken Burns move"""
    ln = float(p["len"])
    if p["kind"] == "clip":
        avail, ss = float(p["avail"]), float(p["ss"])
        srcdur = min(avail, ln * float(p.get("rate") or 1.0))  # a uniform-speed video consumes rate x the length; otherwise a short clip slows (<= 1.2x) rather than freezes
        sp = srcdur / ln  # < 1 = slowed
        vf = (f"setpts=(PTS-STARTPTS)/{sp:.5f},scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS},format=yuv420p{extra_vf}")
        af = "aresample=48000,aformat=channel_layouts=stereo" + (f",atempo={sp:.5f}" if abs(sp - 1) > 1e-3 else "") + f",apad,atrim=0:{ln:.3f}"
        if has_audio(p["src"]):
            run(["-ss", f"{ss:.3f}", "-t", f"{srcdur:.3f}", "-i", p["src"], "-vf", vf, "-af", af, "-t", f"{ln:.3f}", *enc_args(draft), str(path)], f"piece {p['id']}", cwd=work)
        else:
            run(["-ss", f"{ss:.3f}", "-t", f"{srcdur:.3f}", "-i", p["src"], "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", vf, "-t", f"{ln:.3f}", "-map", "0:v", "-map", "1:a",
                 *enc_args(draft), str(path)], f"piece {p['id']}", cwd=work)
        return ln
    frames = int(round(ln * FPS))
    kb = E.kb_filter(p.get("move") or "push", frames, w, h)
    vf = f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=decrease,pad={w * 2}:{h * 2}:(ow-iw)/2:(oh-ih)/2,setsar=1,{kb},format=yuv420p{extra_vf}"
    run(["-loop", "1", "-i", p["src"], "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-vf", vf, "-t", f"{ln:.3f}", "-map", "0:v", "-map", "1:a", *enc_args(draft), str(path)],
        f"still {p['id']}", cwd=work)
    return ln


def join_graph(durs, d=DISSOLVE, music=None, kinds=None, end_fade=FADE_OUT, tail=0.0, post="", silent_T=None, exact=False):
    """filter_complex joining n inputs (each with v + a) with dissolves (d = one length or a list; kinds[k] "dissolve" | "dip") + the shared look / letterbox
    (post) + a slow closing fade of the picture (end_fade s) + `tail` s of black while the music rings on: -> [vout] [aout].
    music = the clip-sound option ("off" | "low" | "full") when input n is the prepared song track (already as long as video + tail, faded): it is mixed in"""
    n = len(durs)
    ds = list(d) if isinstance(d, (list, tuple)) else [d] * max(0, n - 1)
    starts, total = timeline(durs, ds)
    lines, vl, al = [], "0:v", "0:a"
    for k in range(1, n):
        tr = "fadeblack" if kinds and kinds[k - 1] == "dip" else "fade"
        lines.append(f"[{vl}][{k}:v]xfade=transition={tr}:duration={ds[k - 1]}:offset={starts[k]:.3f}[v{k}]")
        if music != "off":  # clip sound off: the clips' own audio is never used
            lines.append(f"[{al}][{k}:a]acrossfade=d={ds[k - 1]}[a{k}]")
        vl, al = f"v{k}", f"a{k}"
    fs = max(0, total - end_fade)
    v = f"[{vl}]" + (post + "," if post else "") + f"fade=t=out:st={fs:.3f}:d={end_fade}"
    if tail:
        v += f",tpad=stop_mode=add:stop_duration={tail}:color=black"
    if exact:  # a fitted cut: a hair of clone (black by then) so the picture is never shorter than the target; the encode is cut at T
        v += ",tpad=stop_mode=clone:stop_duration=0.5"
    lines.append(v + ",format=yuv420p[vout]")
    T = total + tail
    if music is None:
        lines.append(f"[{al}]afade=t=out:st={fs:.3f}:d={end_fade}[aout]")
    elif silent_T:  # fitted to a typed song length, no song file: silent AAC (the user attaches the video to the song elsewhere), or the clips' own sound
        if music == "off":
            lines.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{silent_T:.3f},asetpts=PTS-STARTPTS[aout]")
        else:
            vol = LOW_VOL if music == "low" else 1.0
            lines.append(f"[{al}]volume={vol},afade=t=out:st={fs:.3f}:d={end_fade},apad,atrim=0:{silent_T:.3f}[aout]")
    elif music == "off":
        lines.append(f"[{n}:a]atrim=0:{T:.3f},asetpts=PTS-STARTPTS[aout]")
    else:
        vol = LOW_VOL if music == "low" else 1.0
        lines.append(f"[{al}]volume={vol},afade=t=out:st={fs:.3f}:d={end_fade}[cl]")
        lines.append(f"[cl][{n}:a]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95,atrim=0:{T:.3f}[aout]")
    return ";\n".join(lines)


def prepare_music(work, mi, total, draft, fout=MUSIC_FADE_OUT):
    """the song as a track exactly `total` s long (work/music.wav): from the start offset, fade in 1 s, fade out `fout` s at the end.
    A song shorter than the video LOOPS (from its start, 1.5 s crossfade at each seam) rather than ending early, so the chapter never goes silent."""
    path, off = mi["path"], eff_offset(mi)
    L = dur_of(path)
    fin, fout = MUSIC_FADE_IN, min(fout, total / 2)
    tail = f"atrim=0:{total:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d={fin},afade=t=out:st={max(0, total - fout):.3f}:d={fout}"
    fmt = "aresample=48000,aformat=channel_layouts=stereo"
    avail = L - off
    ins, lines = ["-ss", f"{off:.3f}", "-i", path], []
    if avail >= total + 0.05 or L <= MUSIC_XFADE + 0.2:
        lines.append(f"[0:a]{fmt},{tail}[m]")
    else:
        n, got = 1, avail
        while got < total + MUSIC_XFADE and n < 40:
            ins += ["-i", path]
            got += L - MUSIC_XFADE
            n += 1
        cur = "0:a"
        for k in range(1, n):
            lines.append(f"[{cur}][{k}:a]acrossfade=d={MUSIC_XFADE}[x{k}]")
            cur = f"x{k}"
        lines.append(f"[{cur}]{fmt},{tail}[m]")
    (Path(work) / "music_graph.txt").write_text(";\n".join(lines), encoding="utf-8")
    run([*ins, "-/filter_complex", "music_graph.txt", "-map", "[m]", "-c:a", "pcm_s16le", "-ar", "48000", "music.wav"], "music track", cwd=work)
    return Path(work) / "music.wav"


def eff_offset(mi):
    """the start offset actually used (a song shorter than offset + 2 s starts from 0)"""
    L = dur_of(mi["path"])
    return 0.0 if mi["offset"] >= L - 2.0 else mi["offset"]


# ---------------------------------------------------------------- the builds
def plan_cut(pieces, edit, mi, beats, target_pic=None):
    """everything the immersion pass decides, before any rendering: per piece ss / avail / len / rate / move, the transitions, totals.
    target_pic (the 🎞 music video): fit the picture to that many seconds by a UNIFORM speed factor (every piece the same), then snap each cut to a beat
    within +-0.4 s on top; the last piece absorbs the rest so the picture is exactly target_pic long.
    Returns dict(pieces, trs, lens, starts, total, snapped, factor, fit)."""
    for p in pieces:
        if p["kind"] == "clip":
            p["ss"], p["avail"] = clip_trim(p, edit["trim"])
        else:
            p["ss"], p["avail"] = 0.0, float(p["hold"])
        p["rate"] = 1.0
    stills = [p for p in pieces if p["kind"] == "still"]
    mv = dict(zip([p["id"] for p in stills], E.kb_moves([p["id"] for p in stills]))) if edit["kenburns"] else {}
    for p in pieces:
        p["move"] = mv.get(p["id"], "push")
    period = E.beat_period(beats["beats"]) if beats else None
    nat = [p["avail"] for p in pieces]
    trs = E.clamp_transitions(E.transitions(pieces, period, edit["dissolve"], edit["dip"]), nat) if len(pieces) > 1 else []
    ds = [t["d"] for t in trs]
    factor, fit = 1.0, None
    if target_pic:
        fit = E.fit_report(nat, sum(ds), target_pic)
        if not fit["ok"]:
            raise RuntimeError(fit["message"])
        factor = fit["factor"]
        for p in pieces:
            p["rate"] = factor
        nat = [x / factor for x in nat]
        trs = E.clamp_transitions(trs, nat) if len(pieces) > 1 else []
        ds = [t["d"] for t in trs]
    snapped = False
    lens = [round(x, 3) for x in nat]
    if beats and len(pieces) > 1:
        eo = eff_offset(mi)
        bo, dn = E.beat_grid(beats["beats"], 4, eo, (target_pic or sum(nat) * 1.25) + 5, beats.get("tempo"))
        bounds = []
        for k, p in enumerate(pieces):
            need = 2 * max([ds[k - 1] if k else 0, ds[k] if k < len(ds) else 0])
            if target_pic:  # a uniform-speed video: only a small nudge onto the beat
                lo, hi, nt = max(MIN_SNAP, nat[k] - 0.4), nat[k] + 0.4, nat[k]
            else:
                lo, hi, nt = E.clip_bounds(p["avail"]) if p["kind"] == "clip" else E.still_bounds(p["avail"])
            bounds.append((max(lo, need), max(hi, need), nt))
        lens = E.snap_lengths(bounds, ds, bo, dn)
        snapped = lens != [round(x, 3) for x in nat]
    if target_pic and len(pieces) > 1:  # the last piece absorbs what the snaps left over: the picture is exactly target_pic long
        _, tot = timeline(lens[:-1] + [0.0], ds)
        start_last = timeline(lens, ds)[0][-1]
        lens[-1] = round(max(2.0, target_pic - start_last), 3)
    starts, total = timeline(lens, ds)
    for p, ln in zip(pieces, lens):
        p["len"] = ln
    return {"pieces": pieces, "trs": trs, "lens": lens, "starts": starts, "total": total, "snapped": snapped, "factor": round(factor, 4), "fit": fit}


MIN_SNAP = 1.5


# ---------------------------------------------------------------- what is being built: one chapter, or the saga-level 🎞 music video over a chapter range
def chapter_dirs(sagadir):
    return sorted(p for p in Path(sagadir).glob("ch[0-9][0-9]*") if (p / "episode.json").is_file())


def mv_cfg(sagadir):
    """saga.json `mv` {music {file, name, ts}, chapters "ch01-ch03", length (s), clip_sound, offset, edit}"""
    m = (read_json(Path(sagadir) / "saga.json", {}) or {}).get("mv")
    return m if isinstance(m, dict) else {}


def make_ctx(d, target, marks=None, mv=None, length=None):
    """the build context. mv=None: d is a chapter dir. mv={"range": "ch01-ch03", "length": "4:05"|None}: d is the saga dir and the pieces are every shot of those chapters"""
    d = Path(d)
    if not mv:
        saga = read_json(d.parent / "saga.json", {}) or {}
        ep = read_json(d / "episode.json", {}) or {}
        n = int(re.sub(r"\D", "", d.name) or 0)
        pieces = resolve(d, marks)
        for i, p in enumerate(pieces):
            p["chapter_first"] = False
        reel = ep.get("reel") if isinstance(ep.get("reel"), dict) else {}
        lg = length if length not in (None, "") else reel.get("length")  # fit this one chapter to a song of that length (mm:ss)
        cs = reel.get("clip_sound") if reel.get("clip_sound") in CLIP_SOUNDS else "off"
        return {"dir": d, "mv": None, "pieces": pieces, "edit": E.edit_opts(ep), "mi": music_info(d), "saga_title": saga.get("title") or d.parent.name,
                "title_sub": f"Chapter {n} · {ep.get('title') or d.name}", "out": out_paths(d, target), "target_len": E.parse_length(lg), "has_text": has_overview(d),
                "clip_sound": cs, "deps": [d / "episode.json", *d.glob("e*.png"), *d.glob("e*__*.mp4")],
                "meta": {"saga": d.parent.name, "chapter": d.name, "length_arg": lg}, "label": d.name}
    cfg = mv_cfg(d)
    saga = read_json(d / "saga.json", {}) or {}
    avail = chapter_dirs(d)
    names = E.parse_range(mv.get("range") or cfg.get("chapters") or "", [c.name for c in avail])
    if not names:
        raise RuntimeError("pick a chapter range that exists (e.g. ch01-ch03)")
    tag = "-".join([names[0], names[-1]]) if len(names) > 1 else names[0]
    pieces, deps, chapters, text = [], [], [], False
    for nm in names:
        cd = d / nm
        ep = read_json(cd / "episode.json", {}) or {}
        ps = resolve(cd, marks)
        n = int(re.sub(r"\D", "", nm) or 0)
        for k, p in enumerate(ps):
            p["chapter"], p["chapter_first"] = nm, k == 0
            p["chapter_label"] = f"Chapter {n} · {ep.get('title') or nm}"
        chapters.append({"chapter": nm, "title": ep.get("title") or nm, "cells": len(ps)})
        pieces += ps
        deps += [cd / "episode.json", *cd.glob("e*.png"), *cd.glob("e*__*.mp4")]
        text = text or has_overview(cd)
    mi = music_from(d, cfg.get("music"), cfg.get("clip_sound"), cfg.get("offset"))
    typed = mv.get("length") if mv.get("length") not in (None, "") else None  # an explicit length wins over the song's own
    tl_arg = typed if typed is not None else cfg.get("length")
    length = E.parse_length(tl_arg)
    if mi and typed is None:
        length = max(1.0, dur_of(mi["path"]) - eff_offset(mi))
    edit = E.edit_opts({"reel": {"edit": cfg.get("edit")}})
    if pieces:
        pieces[0]["chapter_first"] = False  # the first shot carries the saga title (and chapter 1's name) instead
    n1 = int(re.sub(r"\D", "", names[0]) or 0)
    first_ep = read_json(d / names[0] / "episode.json", {}) or {}
    return {"dir": d, "mv": {"range": tag, "names": names, "length_arg": tl_arg}, "pieces": pieces, "edit": edit, "mi": mi, "saga_title": saga.get("title") or d.name,
            "title_sub": f"Chapter {n1} · {first_ep.get('title') or names[0]}", "out": out_paths(d, target, tag), "target_len": length, "has_text": text, "deps": deps,
            "clip_sound": cfg.get("clip_sound") if cfg.get("clip_sound") in CLIP_SOUNDS else "off",
            "meta": {"saga": d.name, "range": tag, "chapters": chapters, "length_arg": tl_arg}, "label": tag}


def master_current(chdir, marks=None, mv=None, length=None):
    """(True, "") when the master (cut/<saga>-chNN.mp4, or the music video's) still matches what a new build would make (nothing it depends on is newer,
    same clips, same options / song / length); else (False, why)"""
    chdir = Path(chdir)
    try:
        ctx = make_ctx(chdir, "youtube", marks, mv, length)
    except RuntimeError as e:
        return False, str(e)
    m = ctx["out"]
    j = read_json(m.with_suffix(".json"), None) if m.exists() else None
    if not j:
        return False, "no full build yet"
    built = m.stat().st_mtime
    deps = ctx["deps"] + [Path(__file__), Path(__file__).with_name("saga_edit.py")]
    newer = [p for p in deps if p.is_file() and p.stat().st_mtime > built + 1]
    if newer:
        return False, f"{newer[0].name} changed after the last full build"
    if ctx["edit"] != j.get("edit"):
        return False, "the edit options (reel.edit) changed"
    if music_key(ctx["mi"]) != j.get("music"):
        return False, "the music (file or options) changed"
    if mv and j.get("range") != ctx["mv"]["range"]:
        return False, "the chapter range changed"
    if j.get("length_arg") != (ctx["mv"]["length_arg"] if mv else ctx["meta"].get("length_arg")) or j.get("target_len") != ctx["target_len"]:
        return False, "the song length changed"
    now = [(p["id"], p["clip"]) for p in ctx["pieces"]]
    if now != [(p["id"], p.get("clip")) for p in j.get("pieces", [])]:
        return False, "a different clip is picked now (❤ / 👎 / new clip)"
    return True, ""


def chapter_vf(work, text, w, h, n, window):
    """a small elegant chapter name over the first shot of a chapter (the music video has no title cards): top centre, serif, soft shadow, fades in and out"""
    ff = font_file(work)
    if not ff or not text or not window:
        return ""
    tf = Path(work) / f"chap{n}.txt"
    tf.write_text(text, encoding="utf-8")
    return (f",drawtext=fontfile={ff}:textfile={tf.name}:fontcolor=0xefe3c0:fontsize={max(13, h // 30)}:x=(w-text_w)/2:y=h*0.08:shadowcolor=black@0.85:shadowx=2:shadowy=2"
            f":alpha='{E.fade_alpha(window[0], window[1], 0.8)}'")


def build_master(chdir, target, captions=False, keep=False, dry_run=False, marks=None, status_target=None, mv=None, length=None):
    """target draft | youtube -> the cut mp4 + .json; returns the timeline dict. mv = the saga-level music video (see make_ctx)"""
    chdir = Path(chdir)
    draft = target == "draft"
    w, h = SIZES[target]
    ctx = make_ctx(chdir, target, marks, mv, length)
    pieces, edit, mi, out = ctx["pieces"], ctx["edit"], ctx["mi"], ctx["out"]
    if not pieces:
        raise RuntimeError("this chapter has no rendered pictures or clips yet")
    if ctx["mv"] and not ctx["target_len"]:
        raise RuntimeError("the music video needs a song (upload one) or a song length (mm:ss)")
    if length not in (None, "") and not ctx["target_len"]:
        raise RuntimeError(f"can't read the length {length!r} (use mm:ss)")
    tail = edit["tail"] if mi else 0.0
    target_pic = round(ctx["target_len"] - tail, 3) if ctx["target_len"] else None
    if dry_run:
        print(f"{target}: {w}x{h}  ->  {MA.rel(out)}")
        print(f"  title {edit['title']}: {ctx['saga_title']} / {ctx['title_sub']}")
        print(f"  edit: {json.dumps(edit)}" + (f"  music: {mi['name']} (clip sound {mi['clip_sound']}, from {mi['offset']:g}s)" if mi else "  (no music" + (f": a SILENT track, fitted to {E.fmt_len(ctx['target_len'])})" if ctx["target_len"] else ")")))
        for p in pieces:
            print(f"  {p['id']:>4}  " + (f"[{p['chapter']}] " if ctx["mv"] else "") + (f"clip {Path(p['src']).name}" if p["kind"] == "clip" else f"still, Ken Burns {p['hold']:g}s, silent"))
        if target_pic:
            nat = [(dur_of(p["src"]) - 0.15) if p["kind"] == "clip" else float(p["hold"]) for p in pieces]
            fit = E.fit_report(nat, max(0, len(nat) - 1) * E.dissolve_len(None, edit["dissolve"]), target_pic)
            print(f"  fit to the song length: {len(pieces)} cells, natural {E.fmt_len(fit['natural'])} -> {E.fmt_len(ctx['target_len'])}: speed {fit['factor_raw']:.2f}x " + ("(ok)" if fit["ok"] else "-> " + fit["message"]))
        return None
    t0 = time.time()
    work = Path(tempfile.mkdtemp(prefix="sagaasm_", dir=(chdir / "cut") if (chdir / "cut").is_dir() else None))
    (chdir / "cut").mkdir(exist_ok=True)
    set_status(chdir, state="running", target=status_target or target, stage="analysing the clips", out=MA.rel(out), msg="", started=int(t0))
    try:
        beats = None
        if mi and edit["beats"]:  # (no song file = no beats to snap to: a typed length only fits the speed)
            set_status(chdir, stage="finding the beats")
            beats = E.music_beats(mi["path"], ROOT, chdir / "cut")
            if not beats or len(beats.get("beats") or []) < 8:
                print("no usable beat grid for the song: cuts keep their natural lengths")
                beats = None
        pl = plan_cut(pieces, edit, mi, beats, target_pic)
        pieces, trs, lens, starts, total = pl["pieces"], pl["trs"], pl["lens"], pl["starts"], pl["total"]
        card = edit["title"] == "card" and not ctx["mv"]
        captions = bool(captions) if captions is not None else ctx["has_text"]
        files, durs, ds, kinds, off = [], [], [t["d"] for t in trs], [t["kind"] for t in trs], 0
        if card:  # a separate black card first, 0.5 s dissolve into the first shot
            tp = work / "p00.mp4"
            title_piece(work, ctx["saga_title"], ctx["title_sub"], w, h, draft, tp)
            files.append(tp)
            durs.append(dur_of(tp))
            ds.insert(0, DISSOLVE)
            kinds.insert(0, "dissolve")
            off = 1
        n_p = len(pieces)
        for i, p in enumerate(pieces):
            set_status(chdir, stage=f"piece {i + 1}/{n_p} ({p['id']})")
            d_in = trs[i - 1]["d"] if i > 0 else (DISSOLVE if card else 0.0)
            d_out = trs[i]["d"] if i < n_p - 1 else edit["end_fade"]
            extra, after = "", 0.0
            if i == 0 and not card:
                extra, after = title_vf(work, ctx["saga_title"], ctx["title_sub"], w, h, p["len"])
            elif p.get("chapter_first"):
                cw = (round(d_in + 0.4, 3), round(min(d_in + 4.4, p["len"] - d_out - 0.2), 3))
                extra = chapter_vf(work, p["chapter_label"], w, h, i + 1, cw if cw[1] - cw[0] >= 1.5 else None)
            win = E.caption_times(p["len"], d_in, d_out, edit["caption_delay"], after) if captions else None
            p["caption"] = list(win) if win else None
            extra += caption_vf(work, p["text"], w, h, i + 1, win)
            fp = work / f"p{i + 1:02d}.mp4"
            shot_piece(work, p, w, h, draft, fp, i + 1, extra)
            files.append(fp)
            durs.append(dur_of(fp))
        starts_all, total = timeline(durs, ds)
        set_status(chdir, stage="joining + encoding")
        extra_in = []
        if mi:
            set_status(chdir, stage="preparing the music")
            extra_in = ["-i", str(prepare_music(work, mi, total + tail, draft, 4.0 if tail else MUSIC_FADE_OUT).name)]
        post = ",".join(x for x in (E.look_filter(edit["look"]), E.letterbox_filter(edit["letterbox"])) if x)
        silent_T = ctx["target_len"] if (target_pic and not mi) else None
        mode = mi["clip_sound"] if mi else (ctx["clip_sound"] if silent_T else None)
        (work / "graph.txt").write_text(join_graph(durs, ds, mode, kinds, edit["end_fade"], tail, post, silent_T, bool(target_pic)), encoding="utf-8")
        part = out.with_name(out.name + ".part")
        ins = [x for f in files for x in ("-i", f.name)] + extra_in
        run_args = [*ins, "-/filter_complex", "graph.txt", "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "veryfast" if draft else "medium",
                    "-crf", "26" if draft else "17", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "128k" if draft else "192k", "-movflags", "+faststart", "-f", "mp4",
                    *(["-t", f"{ctx['target_len']:.3f}"] if target_pic else []), str(part.resolve())]
        r = subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-nostdin", *run_args], cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if r.returncode:
            raise RuntimeError("join failed: " + (r.stderr or "").strip()[-500:])
        MA.publish_cut(part, out)
        tl = {"target": target, "draft": draft, "video": MA.rel(out), "w": w, "h": h, "fps": FPS, "duration": round(ctx["target_len"] if target_pic else total + tail, 3), "picture_s": total,
              **ctx["meta"], "title_s": TITLE_S if card else None, "edit": edit, "transitions": [{"kind": k, "d": d_} for k, d_ in zip(kinds, ds)], "beat_snapped": pl["snapped"],
              "speed_factor": pl["factor"] if target_pic else None, "target_len": ctx["target_len"], "silent": bool(silent_T and mode == "off"),
              "captions": captions, "music": music_key(mi), "built": int(time.time()), "build_seconds": round(time.time() - t0, 1),
              "pieces": [{"id": p["id"], "kind": p["kind"], "clip": p["clip"], "t0": starts_all[i + off], "dur": round(durs[i + off], 3), "ss": round(p["ss"], 3),
                          **({"chapter": p["chapter"]} if ctx["mv"] else {}), "move": p["move"] if p["kind"] == "still" else None, "caption": p["caption"]} for i, p in enumerate(pieces)]}
        out.with_suffix(".json").write_text(json.dumps(tl, indent=1, ensure_ascii=False), encoding="utf-8")
        return tl
    finally:
        if not keep:
            shutil.rmtree(work, ignore_errors=True)


def build_suno(chdir, cap_mb=None, mv=None):
    master = out_paths(chdir, "youtube", (mv or {}).get("tag"))
    mj = read_json(master.with_suffix(".json"), {})
    out = out_paths(chdir, "suno", (mv or {}).get("tag"))
    cap = float(cap_mb or MA.SUNO_MB)
    set_status(chdir, stage=f"encoding for Suno (<= {cap:g} MB)")
    part = out.with_name(out.name + ".part")
    if master.stat().st_size <= cap * 1e6 * 0.97:
        shutil.copy2(master, part)
    else:
        vk, ak = MA.suno_rates(mj["duration"], cap)
        run(["-i", str(master), "-c:v", "libx264", "-preset", "slow", "-b:v", f"{vk}k", "-maxrate", f"{int(vk * 1.5)}k", "-bufsize", f"{vk * 2}k", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", f"{ak}k", "-movflags", "+faststart", "-f", "mp4", str(part)], "suno encode")
    MA.publish_cut(part, out)
    res = {**mj, "video": MA.rel(out), "target": "suno", "from": master.name, "mb": round(out.stat().st_size / 1e6, 1), "cap_mb": cap, "built": int(time.time())}
    out.with_suffix(".json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    return res


def build_hooks(chdir, mv=None):
    tag = (mv or {}).get("tag")
    master = out_paths(chdir, "youtube", tag)
    mj = read_json(master.with_suffix(".json"), {})
    pieces = mj.get("pieces") or []
    starts = [p["t0"] for p in pieces]
    plan = plan_hooks(starts, float(mj["duration"]))
    hd = out_paths(chdir, "hooks", tag)
    if hd.is_dir():
        for f in hd.glob("*.mp4"):
            f.unlink()
    hd.mkdir(parents=True, exist_ok=True)
    hooks = []
    for n, (a, b) in enumerate(plan, 1):
        ids = [p["id"] for p in pieces if a - 1e-3 <= p["t0"] < b - 1e-3]
        name = f"{n:02d}-{ids[0]}-{ids[-1]}.mp4" if ids else f"{n:02d}.mp4"
        set_status(chdir, stage=f"hook {n}/{len(plan)}")
        out = hd / name
        run(["-ss", f"{a:.3f}", "-i", str(master), "-t", f"{b - a:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], f"hook {n}")
        hooks.append({"n": n, "file": name, "t0": a, "t1": b, "shots": [ids[0], ids[-1]] if ids else [], "mb": round(out.stat().st_size / 1e6, 1)})
    (hd / "hooks.json").write_text(json.dumps({"from": master.name, "hooks": hooks}, indent=1, ensure_ascii=False), encoding="utf-8")
    return {"video": MA.rel(master), "target": "hooks", "hooks": hooks}


def has_overview(chdir):
    return any((sh.get("overview") or "").strip() for sh in (read_json(Path(chdir) / "episode.json", {}) or {}).get("shots") or [])


def overview_check(chdir, marks=None):
    """[(shot id, words, budget)] for overview lines longer than a viewer can read while that piece plays"""
    shots = {sh.get("id"): sh for sh in (read_json(Path(chdir) / "episode.json", {}) or {}).get("shots") or []}
    out = []
    for p in resolve(chdir, marks):
        ov = (shots.get(p["id"], {}).get("overview") or "").strip()
        if ov:
            dur = dur_of(p["src"]) if p["kind"] == "clip" else float(p["hold"])
            if len(ov.split()) > read_budget(dur):
                out.append((p["id"], len(ov.split()), read_budget(dur)))
    return out


def build(chdir, target, captions=None, keep=False, dry_run=False, marks=None, gallery=True, mv=None, length=None):
    """captions None = on when the chapter has `overview` lines (the story told on screen), else off. mv = {"range", "length"}: chdir is the SAGA dir and the
    cut is the saga-level 🎞 music video over that chapter range (uniform speed to the song / typed length)"""
    chdir = Path(chdir)
    mvk = None
    if mv:
        ctx0 = make_ctx(chdir, "youtube", marks, mv, length)
        mvk = {"tag": ctx0["mv"]["range"]}
        mv = {**mv, "range": ctx0["mv"]["range"]}
    elif captions is None:
        captions = has_overview(chdir)
        for sid, n, b in overview_check(chdir, marks) if captions else []:
            print(f"WARNING {sid}: overview is {n} words, about {b} can be read while it plays: shorten it")
    if target in ("draft", "youtube"):
        if dry_run:
            return build_master(chdir, target, captions, keep, True, marks, mv=mv, length=length)
        try:
            tl = build_master(chdir, target, captions, keep, False, marks, mv=mv, length=length)
            set_status(chdir, state="done", target=target, stage="done", out=tl["video"], msg="", finished=int(time.time()))
            res = tl
        except Exception as e:
            set_status(chdir, state="error", target=target, stage="failed", msg=str(e)[-600:])
            raise
    else:
        if dry_run:
            ok_, why = master_current(chdir, marks, mv, length)
            print(f"{target}: " + ("reuses the current master" if ok_ else f"builds the master first ({why})"))
            if target == "hooks" and ok_:
                mj = read_json(out_paths(chdir, "youtube", (mvk or {}).get("tag")).with_suffix(".json"), {})
                print("  hooks:", plan_hooks([p["t0"] for p in mj.get("pieces", [])], float(mj["duration"])))
            return None
        set_status(chdir, state="running", target=target, stage="checking the full build", out="", msg="", started=int(time.time()))
        try:
            ok_, why = master_current(chdir, marks, mv, length)
            if not ok_:
                print("building the full master first:", why)
                build_master(chdir, "youtube", captions, keep, False, marks, status_target=target, mv=mv, length=length)
            res = build_suno(chdir, mv=mvk) if target == "suno" else build_hooks(chdir, mv=mvk)
            set_status(chdir, state="done", target=target, stage="done", out=res["video"] if target != "hooks" else MA.rel(out_paths(chdir, "hooks", (mvk or {}).get("tag"))), msg="", finished=int(time.time()))
        except Exception as e:
            set_status(chdir, state="error", target=target, stage="failed", msg=str(e)[-600:])
            raise
    if gallery:
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_gallery.py")], cwd=ROOT, capture_output=True)
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("chapter", help="explore/sagas/NNN-slug/chNN (one chapter) or explore/sagas/NNN-slug with --chapters (the saga-level music video)")
    ap.add_argument("--target", choices=TARGETS, required=True)
    ap.add_argument("--chapters", help="the saga-level music video over a range like ch01-ch03 (saga.json mv.chapters when omitted but the folder is a saga)")
    ap.add_argument("--length", help="song length mm:ss: fit the cut to exactly that long by ONE uniform speed factor (a silent track unless there is a song file; works for one chapter too; saga.json mv.length / episode reel.length otherwise)")
    ap.add_argument("--captions", action="store_true", default=None, help="burn text into each piece: the shot's `overview` line, else narration / dialogue (default: on when the chapter has overview lines)")
    ap.add_argument("--no-captions", dest="captions", action="store_false")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-gallery", action="store_true", help="don't rebuild the gallery afterwards")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    d = Path(a.chapter)
    d = d if d.is_absolute() else ROOT / d
    mv = {"range": a.chapters or mv_cfg(d).get("chapters") or "", "length": a.length} if (a.chapters or (d / "saga.json").is_file()) else None
    r = build(d, a.target, a.captions, a.keep, a.dry_run, gallery=not a.no_gallery, mv=mv, length=None if mv else a.length)
    if r:
        print(r.get("video"), f"{len(r['hooks'])} hooks" if a.target == "hooks" else (f"{r.get('duration')}s" if r.get("duration") else ""),
              f"speed {r['speed_factor']}x" if r.get("speed_factor") else "")


if __name__ == "__main__":
    main()
