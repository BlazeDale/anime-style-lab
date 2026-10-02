"""Stem-aware analysis of a 🎵 music video's separate tracks (a zip of the song's separate tracks lets a director match the beat and
find key moments to cut to different band members).

  python tools/mv_stems.py <musicvideos/NNN-slug> [--summary]

Reads audio/stems/* (+ audio/song.* and audio/analysis.json when present) -> audio/stems.json:
  {duration, tempo, beat_source (drums|mix|stems), beats, downbeats, sections, warnings, skipped,
   stems: [{name, file, role, duration, offset_s, offset_ok, activity_pct, segments [[t0,t1]], entrances [t], exits [t],
            share_by_section [0-1 per section span], lane [0-99 x ~1500 max-abs buckets over the SONG timeline]}],
   moments: [{t, t1?, kind, stems, note}]}    kinds: enter exit solo feature breakdown fill drop build
All times are SONG seconds (a stem whose start is shifted against the song is moved into place: offset_s, found by cross-correlating
onset envelopes of the first 90 s). --summary prints the compact table Claude reads when directing (runs the analysis first if needed).
Needs librosa + soundfile + numpy (pip install librosa soundfile numpy). mp3/flac/wav, mono/stereo, any sample rate (resampled to 22050).
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mv_analyze  # noqa: E402  (load() with the ffmpeg fallback, peaks, SR)

SR = mv_analyze.SR
WIN = 0.1            # activity / energy resolution (s)
HOP = 110            # onset envelope hop (~5 ms at 22050 Hz)
LANE = 1500
AUDIO_EXT = (".mp3", ".wav", ".flac", ".m4a", ".ogg", ".opus", ".aac")
ROLES = ("drums", "bass", "guitar", "keys", "vocals", "backing", "strings", "brass", "fx", "other")

# (role, substring words (>=4 letters), whole-token words): first hit wins, so "bass drum" is drums and "backing vocals" is backing
ROLE_RULES = [
    ("backing", ("backing", "harmon", "choir", "choral", "bvox"), ("bv", "bvs", "bgv", "bgvox")),
    ("vocals", ("vocal", "voice", "sing"), ("vox", "lv", "vx")),
    ("drums", ("drum", "kick", "snare", "perc", "cymbal", "hihat", "overhead", "clap"), ("hat", "hats", "tom", "toms", "oh")),
    ("bass", ("bass",), ("sub",)),
    ("guitar", ("guitar", "strum", "riff"), ("gtr", "gt", "gtrs")),
    ("keys", ("keys", "piano", "synth", "organ", "rhodes", "wurli", "mellotron"), ("key", "pad", "pads", "kbd")),
    ("strings", ("string", "violin", "cello", "viola", "orches"), ()),
    ("brass", ("brass", "horn", "trumpet", "trombone", "flute", "wind"), ("sax",)),
    ("fx", ("effect", "ambien", "riser", "noise", "sfx"), ("fx",)),
]


def guess_role(name):
    s = name.lower()
    toks = set(re.findall(r"[a-z]+", s))
    for role, subs, words in ROLE_RULES:
        if any(w in s for w in subs) or any(w in toks for w in words):
            return role
    return "other"


NOT_LEAD = ("double", "dbl", "adlib", "harm", "stack", "backing", "choir", "choral", "bv", "bvs", "bgv", "bvox", "dub", "whisper", "layer", "octave")
MIX_WORDS = ("mix", "mixdown", "fullmix", "master", "mastered", "premaster", "full", "bounce", "stereo", "final", "complete", "song", "print")
NOT_MIX = ("instrumental", "inst", "karaoke", "minus", "click", "guide", "ref", "reference", "demo", "acapella", "acappella", "stem", "stems")


def _toks(name):
    return set(re.findall(r"[a-z]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", name).lower()))


def pick_lead(names):
    """the stem that is the LEAD vocal, by its name (stem exports follow naming conventions): "Lead Vocals", "Lead Vox", "LV", "vox lead", "main vocal" win; backing/BV/harmony/double/ad-lib never; with no 'lead' a single
    plain vocal/vox stem is taken; None when it's ambiguous"""
    cands = []
    for n in names:
        s, toks = n.lower(), _toks(n)
        if guess_role(n) != "vocals" or any((w in toks) if len(w) <= 3 else (w in s) for w in NOT_LEAD):
            continue
        cands.append((0 if ("lead" in toks or "lv" in toks or "main" in toks or "lead" in s) else 1, len(n), n))
    if not cands:
        return None
    cands.sort()
    if cands[0][0] == 0:
        return cands[0][2]
    return cands[0][2] if len(cands) == 1 else None


def pick_mix(names, title=""):
    """the full mix / master among the stems' names ("Mix", "Master", "Full Mix", "Stereo Mix", "Bounce", or just the song title
    with no instrument word), None if there is none -> the server renders a mixdown of all stems instead"""
    tn = re.sub(r"[^a-z0-9]", "", title.lower())
    best = None
    for n in names:
        toks = _toks(n)
        if guess_role(n) != "other" or toks & set(NOT_MIX):
            continue
        nn = re.sub(r"[^a-z0-9]", "", n.lower())
        hit = toks & set(MIX_WORDS)
        rank = 0 if toks & {"master", "mastered", "premaster"} else 1 if hit else None
        if rank is None and len(tn) >= 3 and tn in nn:
            rest = nn.replace(tn, "")
            if not re.sub(r"\d+|" + "|".join(MIX_WORDS), "", rest):
                rank = 2
        if rank is not None and (best is None or rank < best[0]):
            best = (rank, n)
    return best[1] if best else None


def safe_name(member, taken):
    """zip member -> a flat, sanitized audio file name (zip-slip proof: folders, '..' and odd characters are dropped), None to skip
    (not audio, hidden, __MACOSX junk); `taken` = lowercase names already used (updated)"""
    parts = [p for p in re.split(r"[\\/]+", member) if p not in ("", ".", "..")]
    if not parts or any(p.startswith(".") or p == "__MACOSX" for p in parts):
        return None
    base = parts[-1]
    ext = Path(base).suffix.lower()
    if ext not in AUDIO_EXT:
        return None
    stem = re.sub(r"[^A-Za-z0-9 _.-]", "_", re.sub(r"[()\[\]]", "", base[:-len(ext)])).strip(" ._-") or "stem"
    name, k = stem[:80] + ext, 2
    while name.lower() in taken:
        name, k = "%s (%d)%s" % (stem[:76], k, ext), k + 1
    taken.add(name.lower())
    return name


def extract_audio_zip(zpath, outdir, max_total=6 << 30):
    """extract only the audio files of a zip into outdir (flattened, sanitized, deduped, streamed in chunks); -> [file names]"""
    import zipfile
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    taken, out, total = set(), [], 0
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = safe_name(info.filename, taken)
            if not name:
                continue
            with zf.open(info) as src, (outdir / name).open("wb") as dst:
                while True:
                    chunk = src.read(1 << 20)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_total:
                        raise ValueError("zip expands past %d GB" % (max_total >> 30))
                    dst.write(chunk)
            out.append(name)
    return out


def place(y, shift, n):
    """y moved `shift` samples later (earlier if negative) into a zero array of n samples"""
    import numpy as np
    out = np.zeros(n, dtype=np.float32)
    if shift >= 0:
        m = min(len(y), n - shift)
        if m > 0:
            out[shift:shift + m] = y[:m]
    else:
        m = min(len(y) + shift, n)
        if m > 0:
            out[:m] = y[-shift:-shift + m]
    return out


def find_offset(song, y):
    """(offset_s, ok): add offset_s to the stem's time to get song time; ok = the correlation peak was clear enough to trust"""
    import librosa
    import numpy as np
    n = int(90 * SR)
    if len(song) < SR or len(y) < SR:
        return 0.0, False
    a = librosa.onset.onset_strength(y=song[:n], sr=SR, hop_length=HOP)
    b = librosa.onset.onset_strength(y=y[:n], sr=SR, hop_length=HOP)
    if a.std() < 1e-9 or b.std() < 1e-9:
        return 0.0, False
    a, b = a - a.mean(), b - b.mean()
    size = 1 << int(np.ceil(np.log2(len(a) + len(b))))
    c = np.fft.irfft(np.conj(np.fft.rfft(a, size)) * np.fft.rfft(b, size), size)  # c[lag] = sum song[n] * stem[n + lag]
    mx = min(int(5 * SR / HOP), size // 2 - 1)
    cc = np.r_[c[:mx + 1], c[size - mx:]]
    lags = np.r_[np.arange(0, mx + 1), np.arange(-mx, 0)]
    k = int(np.argmax(cc))
    conf = float(cc[k] / (cc.std() + 1e-12))
    rest = cc.copy()
    rest[[(k + j) % len(cc) for j in range(-6, 7)]] = -1e9  # the runner-up away from the peak: a steady click track matches at every beat
    ok = conf >= 5.0 and float(rest.max()) <= 0.85 * float(cc[k])
    return (round(float(-lags[k] * HOP / SR), 3) if ok else 0.0), ok


def segments_from(act, nw):
    """active-window mask -> [[t0,t1]] with gaps < 0.6 s merged and blips < 0.4 s dropped"""
    segs, i = [], 0
    while i < nw:
        if act[i]:
            j = i
            while j < nw and act[j]:
                j += 1
            segs.append([i * WIN, j * WIN])
            i = j
        else:
            i += 1
    merged = []
    for s in segs:
        if merged and s[0] - merged[-1][1] < 0.6:
            merged[-1][1] = s[1]
        else:
            merged.append(s)
    return [[round(a, 2), round(b, 2)] for a, b in merged if b - a >= 0.4]


def mask_from(segs, nw):
    import numpy as np
    m = np.zeros(nw, dtype=bool)
    for a, b in segs:
        m[int(round(a / WIN)):int(round(b / WIN))] = True
    return m


def runs(mask, min_len):
    """[(i, j)) of True runs of at least min_len"""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if j - i >= min_len:
                out.append((i, j))
            i = j
        else:
            i += 1
    return out


def merge_moments(ms):
    """same kind within 0.5 s (and same span end) = one moment with several stems"""
    out = []
    for m in sorted(ms, key=lambda x: (x["kind"], x["t"])):
        p = out[-1] if out else None
        if p and p["kind"] == m["kind"] and abs(p["t"] - m["t"]) < 0.5 and p.get("t1") == m.get("t1") and p["kind"] in ("enter", "exit"):
            p["stems"] = p["stems"] + [s for s in m["stems"] if s not in p["stems"]]
        else:
            out.append(dict(m))
    for m in out:
        if m["kind"] in ("enter", "exit") and len(m["stems"]) > 1:
            m["note"] = "%s %s" % (", ".join(m["stems"]), "come in" if m["kind"] == "enter" else "drop out")
    return sorted(out, key=lambda x: (x["t"], x["kind"]))


def analyze(d):
    import librosa
    import numpy as np
    d = Path(d)
    mv = json.loads((d / "mv.json").read_text(encoding="utf-8")) if (d / "mv.json").exists() else {}
    ana = {}
    if (d / "audio" / "analysis.json").exists():
        try:
            ana = json.loads((d / "audio" / "analysis.json").read_text(encoding="utf-8"))
        except ValueError:
            pass
    song = None
    root = d.parent.parent
    cand = [root / mv["audio"]] if mv.get("audio") else []
    cand += sorted((d / "audio").glob("song.*"))
    for p in cand:
        if p.is_file() and p.suffix.lower() in AUDIO_EXT:
            try:
                song, _ = mv_analyze.load(p)
                break
            except Exception:
                song = None
    files = sorted(p for p in (d / "audio" / "stems").glob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXT) \
        if (d / "audio" / "stems").is_dir() else []
    raw, skipped, warnings = [], [], []
    for p in files:
        try:
            y, _ = mv_analyze.load(p)
            if len(y) < SR // 4:
                raise ValueError("under a quarter second of audio")
            raw.append((p, y.astype(np.float32)))
        except Exception as e:
            skipped.append({"file": p.name, "error": str(e)[:160]})
    if not raw:
        raise SystemExit("no readable stems in %s" % (d / "audio" / "stems"))
    T = float(ana.get("duration") or (len(song) / SR if song is not None else max(len(y) for _, y in raw) / SR))
    Ns = int(T * SR)
    nw = Ns // int(SR * WIN)
    W = int(SR * WIN)
    stems, E, placed_drums, placed_all = [], [], [], []
    for p, y in raw:
        off, ok = find_offset(song, y) if song is not None else (0.0, False)
        if ok and abs(off) > 0.005:
            y_song = place(y, int(round(off * SR)), Ns)
            if abs(off) > 0.02:
                warnings.append("%s is %.3f s %s the song: shifted into place" % (p.stem, abs(off), "behind" if off < 0 else "ahead of"))
        else:
            off = 0.0 if ok else off
            y_song = place(y, 0, Ns)
        role = guess_role(p.stem)
        rms = np.sqrt((y_song[:nw * W].reshape(nw, W) ** 2).mean(axis=1))
        live = rms[rms > 1e-4]
        gate = max(float(np.percentile(live, 95)) * 0.1, 1e-4) if len(live) else 1e9
        segs = segments_from(rms > gate, nw)
        act = mask_from(segs, nw)
        ent = [s[0] for i, s in enumerate(segs) if (s[0] - (segs[i - 1][1] if i else 0.0)) >= 2.0 and (i or s[0] >= 2.0)]
        ext = [s[1] for i, s in enumerate(segs) if ((segs[i + 1][0] if i + 1 < len(segs) else T) - s[1]) >= 2.0]
        peak = float(np.abs(y_song).max()) or 1.0
        nb = min(LANE, Ns)
        edges = np.linspace(0, Ns, nb + 1).astype(int)
        edges[-1] = Ns
        lane = np.maximum.reduceat(np.abs(y_song), edges[:-1]) / peak
        lane = [int(round(99 * float(v))) for v in lane]
        stems.append({"name": p.stem, "file": p.name, "role": role, "duration": round(len(y) / SR, 2), "offset_s": off,
                      "offset_ok": bool(ok), "activity_pct": round(100 * sum(b - a for a, b in segs) / T, 1) if T else 0.0,
                      "segments": segs, "entrances": ent, "exits": ext, "lane": lane})
        E.append(rms ** 2)
        placed_all.append(y_song if role != "drums" else None)
        if role == "drums":
            placed_drums.append(y_song)
    E = np.array(E)
    acts = [mask_from(s["segments"], nw) for s in stems]
    names = [s["name"] for s in stems]
    roles = [s["role"] for s in stems]

    # sections + per-stem energy share per section
    secs = [float(x) for x in (ana.get("sections") or []) if 0 < x < T]
    bounds = [0.0] + secs + [T]
    tot = E.sum(axis=0)
    for i, s in enumerate(stems):
        share = []
        for a, b in zip(bounds[:-1], bounds[1:]):
            ia, ib = int(a / WIN), max(int(a / WIN) + 1, int(b / WIN))
            den = float(tot[ia:ib].sum())
            share.append(round(float(E[i][ia:ib].sum()) / den, 2) if den > 0 else 0.0)
        s["share_by_section"] = share

    moments = []
    # enter / exit (stems with < 3 s of activity are noise)
    for i, s in enumerate(stems):
        if sum(b - a for a, b in s["segments"]) < 3.0:
            continue
        for t in s["entrances"]:
            moments.append({"t": t, "kind": "enter", "stems": [s["name"]], "note": "%s comes in (%s)" % (s["name"], s["role"])})
        for t in s["exits"]:
            moments.append({"t": t, "kind": "exit", "stems": [s["name"]], "note": "%s drops out (%s)" % (s["name"], s["role"])})

    # solo / feature: one non-drum, non-vocal stem carrying >= 45 % of the non-vocal energy for >= 3 s with the vocals silent,
    # or clearly dominant (>= 60 % and >= 2x the next stem) while they sing
    nb5 = nw // 5
    if nb5 >= 6:
        Eb = E[:, :nb5 * 5].reshape(len(stems), nb5, 5).sum(axis=2)
        Ab = np.array([a[:nb5 * 5].reshape(nb5, 5).any(axis=1) for a in acts])
        vox = [i for i, r in enumerate(roles) if r in ("vocals", "backing")]
        nonv = [i for i, r in enumerate(roles) if r not in ("vocals", "backing")]
        cands = [i for i, r in enumerate(roles) if r not in ("vocals", "backing", "drums", "fx")]
        vox_on = Ab[vox].any(axis=0) if vox else np.zeros(nb5, dtype=bool)
        if nonv and cands:
            den = Eb[nonv].sum(axis=0)
            okbin = den > 0.01 * max(float(den.max()), 1e-12)
            lab = np.full(nb5, -1)
            kinds = np.zeros(nb5, dtype=bool)  # True = feature (vocals present)
            for b in range(nb5):
                if not okbin[b]:
                    continue
                sh = {i: float(Eb[i, b] / den[b]) for i in nonv}
                best = max(cands, key=lambda i: sh[i])
                others = sorted([v for i, v in sh.items() if i != best], reverse=True)
                if not Ab[best, b]:
                    continue
                if not vox_on[b] and sh[best] >= 0.45:
                    lab[b] = best
                elif sh[best] >= 0.6 and sh[best] >= 2 * (others[0] if others else 0):
                    lab[b], kinds[b] = best, bool(vox_on[b])
            for b in range(1, nb5 - 1):  # a one-bin hole inside a stem's run doesn't end it
                if lab[b] < 0 and lab[b - 1] >= 0 and lab[b - 1] == lab[b + 1]:
                    lab[b], kinds[b] = lab[b - 1], kinds[b - 1]
            b = 0
            while b < nb5:
                if lab[b] < 0:
                    b += 1
                    continue
                e = b
                while e < nb5 and lab[e] == lab[b]:
                    e += 1
                if (e - b) * 0.5 >= 3.0:
                    i = int(lab[b])
                    feat = bool(kinds[b:e].any())
                    pct = int(round(100 * float(Eb[i, b:e].sum() / max(den[b:e].sum(), 1e-12))))
                    alone = pct >= 97
                    moments.append({"t": round(b * 0.5, 2), "t1": round(e * 0.5, 2), "kind": "feature" if feat else "solo", "stems": [names[i]],
                                    "note": "%s %s (%s, %d%% of the non-vocal energy%s)" % (
                                        names[i], "plays alone" if alone and not feat else ("leads while the vocals sing" if feat else "takes the spotlight"),
                                        roles[i], pct, "" if feat else ", vocals silent")})
                b = e

    # breakdown: the drums (union of drum stems) or the bass silent >= 2 s inside their own playing time, others still going
    for grp in ("drums", "bass"):
        idx = [i for i, r in enumerate(roles) if r == grp]
        if not idx:
            continue
        on = np.any([acts[i] for i in idx], axis=0)
        if not on.any():
            continue
        first, last = int(np.argmax(on)), nw - int(np.argmax(on[::-1]))
        gap = ~on.copy()
        gap[:first] = False
        gap[last:] = False
        rest = [acts[i] for i in range(len(stems)) if i not in idx and roles[i] != "fx"]
        for a, b in runs(gap, 20):
            if rest and np.any(rest, axis=0)[a:b].mean() >= 0.5:
                moments.append({"t": round(a * WIN, 2), "t1": round(b * WIN, 2), "kind": "breakdown", "stems": [names[i] for i in idx],
                                "note": "%s silent for %.1f s, the rest keeps playing (back at %.1f s)" % (grp, (b - a) * WIN, b * WIN)})

    # drum fills + section-boundary energy jumps
    beat_src, beats, downbeats, tempo = "mix", [], [], float(ana.get("tempo") or 0)
    sig = None
    if placed_drums:
        sig, beat_src = np.sum(placed_drums, axis=0), "drums"
    elif song is not None:
        sig = song
    else:
        sig, beat_src = np.sum([y for y in placed_all if y is not None] or [raw[0][1]], axis=0), "stems"
    try:
        tp, bf = librosa.beat.beat_track(y=sig, sr=SR)
        tempo = float(tp.item() if hasattr(tp, "item") else tp)
        beats = [round(float(t), 2) for t in librosa.frames_to_time(bf, sr=SR)]
        if len(bf) >= 8:
            st = librosa.onset.onset_strength(y=sig, sr=SR)
            ph = int(np.argmax([float(np.mean(st[np.minimum(bf[p::4], len(st) - 1)])) for p in range(4)]))
            downbeats = beats[ph::4]
    except Exception as e:
        warnings.append("beat tracking failed: %s" % str(e)[:100])
    if placed_drums and secs:
        dsum = np.sum(placed_drums, axis=0)
        env = librosa.onset.onset_strength(y=dsum, sr=SR, hop_length=HOP)
        hits = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=HOP, units="time")
        didx = [i for i, r in enumerate(roles) if r == "drums"]
        don = np.any([acts[i] for i in didx], axis=0)
        dsecs = float(don.sum()) * WIN
        if dsecs > 4 and len(hits):
            avg = float(((hits >= 0) & don[np.minimum((hits / WIN).astype(int), nw - 1)]).sum()) / dsecs
            for b in secs:
                n2 = int(((hits >= b - 2) & (hits < b)).sum())
                if b >= 2 and n2 >= 4 and n2 / 2 >= 1.7 * avg and don[min(int((b - 1) / WIN), nw - 1)]:
                    moments.append({"t": round(b, 2), "kind": "fill", "stems": [names[i] for i in didx],
                                    "note": "drum fill into the section at %.1f s (%d hits in 2 s, %.1fx the average)" % (b, n2, n2 / 2 / avg)})
    db = lambda a, b: 10 * np.log10((b + 1e-9) / (a + 1e-9))
    for b in secs:
        ia, ib, ic = int(b / WIN), int(b / WIN), min(nw, int((b + 4) / WIN))
        ia = max(0, ia - 40)
        if ib - ia < 10 or ic - ib < 10:
            continue
        jump = db(float(tot[ia:ib].mean()), float(tot[ib:ic].mean()))
        ents = [n for s, n in zip(stems, names) if any(abs(t - b) <= 1.5 for t in s["entrances"])]
        if jump >= 6:
            moments.append({"t": round(b, 2), "kind": "drop", "stems": ents, "note": "energy +%.1f dB into the section at %.1f s%s" % (
                jump, b, ("; %s enter" % ", ".join(ents)) if ents else "")})
            if ib - 80 >= 0 and db(float(tot[ib - 80:ib - 40].mean()), float(tot[ib - 40:ib].mean())) >= 3:
                moments.append({"t": round(b - 8, 2), "t1": round(b, 2), "kind": "build", "stems": [], "note": "energy climbs for 8 s into the drop at %.1f s" % b})
        elif jump <= -6:
            moments.append({"t": round(b, 2), "kind": "breakdown", "stems": [], "note": "energy %.1f dB into the section at %.1f s" % (jump, b)})

    lead = pick_lead(names)
    for s in stems:
        s["lead"] = s["name"] == lead
    return {"version": 1, "generated": time.strftime("%Y-%m-%d %H:%M:%S"), "duration": round(T, 2), "tempo": round(tempo, 1),
            "beat_source": beat_src, "beats": beats, "downbeats": downbeats, "sections": [round(x, 2) for x in secs],
            "song": bool(song is not None), "warnings": warnings, "skipped": skipped, "stems": stems, "moments": merge_moments(moments)}


def tc(t):
    return "%d:%04.1f" % (int(t // 60), t % 60)


def summary(res):
    L = ["song %s | %.1f bpm (beats from %s; %d beats, %d downbeats) | %d stems%s" % (
        tc(res["duration"]), res["tempo"], res["beat_source"], len(res["beats"]), len(res["downbeats"]), len(res["stems"]),
        "" if res.get("song") else " | no song file: offsets not checked")]
    for w in res.get("warnings") or []:
        L.append("WARNING: " + w)
    for s in res.get("skipped") or []:
        L.append("SKIPPED %s: %s" % (s["file"], s["error"]))
    L.append("")
    L.append("%-22s %-8s %6s %8s  entrances" % ("stem", "role", "active", "offset"))
    for s in res["stems"]:
        off = "%+.3fs" % s["offset_s"] if s["offset_ok"] else "?"
        L.append("%-22s %-8s %5.0f%% %8s  %s" % ((s["name"] + (" *" if s.get("lead") else ""))[:22], s["role"], s["activity_pct"], off, ", ".join(tc(t) for t in s["entrances"][:8]) or "-"))
    L.append("")
    L.append("%-15s %-10s %-20s note" % ("time", "kind", "stems"))
    for m in res["moments"]:
        t = tc(m["t"]) + ("-" + tc(m["t1"]) if m.get("t1") else "")
        L.append("%-15s %-10s %-20s %s" % (t, m["kind"], ",".join(m["stems"])[:20], m["note"]))
    if res["downbeats"]:
        L.append("")
        L.append("downbeats: " + " ".join("%.1f" % t for t in res["downbeats"][:16]) + (" ..." if len(res["downbeats"]) > 16 else ""))
    return "\n".join(L)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        print(__doc__)
        return 2
    d = Path(args[0])
    out = d / "audio" / "stems.json"
    if "--summary" in argv and out.exists() and "--force" not in argv:
        res = json.loads(out.read_text(encoding="utf-8"))
    else:
        try:
            res = analyze(d)
        except ImportError as e:
            sys.exit("mv_stems needs librosa + soundfile + numpy (pip install librosa soundfile numpy): %s" % e)
        tmp = out.with_suffix(".tmp")
        tmp.write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
        tmp.replace(out)
    if "--summary" in argv:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(summary(res))
    else:
        print("%d stems, %d moments, %.1f bpm (%s)" % (len(res["stems"]), len(res["moments"]), res["tempo"], res["beat_source"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
