"""🎤 Place the lyrics on the song's timeline (sung lines timed automatically): transcribe the isolated vocals (else the song)
with faster-whisper word timestamps, then align the USER'S lyric
lines to the recognised words, so a misheard word never matters: only timing comes from the recogniser.
  python tools/mv_lyrics.py musicvideos/NNN-x [--model medium.en] [--lang en] [--summary]
Output: musicvideos/NNN-x/audio/lyrics_timing.json {model, source, lines: [{i, text, t0, t1, conf}], words: [[w, t0, t1, p]]}
conf = share of the line's words matched exactly; lines under 0.5 are spread over the audible vocal time between their
confident neighbours ("spread": true, '~' in --summary).
Runs on the CPU (int8), so it never competes with ComfyUI for the GPU. Needs faster-whisper (pip install faster-whisper; optional:
only this tool uses it) and numpy."""
import difflib
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FFMPEG  # noqa: E402
HEADER = re.compile(r"^\s*\[.*\]\s*$")  # [Verse 2], [Chorus]


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower().replace("’", "'").replace("'", ""))


def lyric_lines(text):
    return [ln.strip() for ln in str(text or "").splitlines() if ln.strip() and not HEADER.match(ln)]


def align(lines, words):
    """lines: [str]; words: [(w, t0, t1, p)] -> [{i, text, t0, t1, conf}]. Exact token matches (difflib opcodes on normalised
    tokens) pin times; tokens inside replace/delete runs are spread evenly across the time between their pinned neighbours."""
    toks = [(li, norm(w)) for li, ln in enumerate(lines) for w in ln.split() if norm(w)]
    asr = [norm(w[0]) for w in words]
    tt = [None] * len(toks)  # (t0, t1) per lyric token
    exact = [False] * len(toks)
    sm = difflib.SequenceMatcher(None, [t for _, t in toks], asr, autojunk=False)
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal":
            for k in range(a1 - a0):
                tt[a0 + k] = (words[b0 + k][1], words[b0 + k][2]); exact[a0 + k] = True
        elif op == "replace" and b1 > b0:  # misheard: spread the lyric tokens over the recognised words' span
            s, e = words[b0][1], words[b1 - 1][2]
            n = a1 - a0
            for k in range(n):
                tt[a0 + k] = (s + (e - s) * k / n, s + (e - s) * (k + 1) / n)
    # fill the rest (deleted runs) by interpolating between pinned neighbours
    for k in range(len(toks)):
        if tt[k] is None:
            p = next((tt[j][1] for j in range(k - 1, -1, -1) if tt[j]), 0.0)
            q = next((tt[j][0] for j in range(k + 1, len(toks)) if tt[j]), p)
            tt[k] = (p, max(p, q))
    out = []
    for li, text in enumerate(lines):
        ks = [k for k, (l, _) in enumerate(toks) if l == li]
        if not ks:
            continue
        out.append({"i": li, "text": text, "t0": round(tt[ks[0]][0], 2), "t1": round(tt[ks[-1]][1], 2),
                    "conf": round(sum(exact[k] for k in ks) / len(ks), 2)})
    return out


def voiced(pcm, sr=16000, hop=800):
    """[[t0, t1]] where the vocal track is audible (RMS gate, gaps < 0.45 s merged, blips < 0.25 s dropped)"""
    import numpy as np
    n = len(pcm) // hop
    rms = np.sqrt((pcm[:n * hop].reshape(n, hop) ** 2).mean(1)) if n else np.zeros(0)
    th = max(0.02, float(np.percentile(rms, 60)) * 0.35) if n else 1
    segs, st = [], None
    for i, on in enumerate(rms > th):
        t = i * hop / sr
        if on and st is None:
            st = t
        if not on and st is not None:
            segs.append([st, t]); st = None
    if st is not None:
        segs.append([st, n * hop / sr])
    out = []
    for a in segs:
        if out and a[0] - out[-1][1] < 0.45:
            out[-1][1] = a[1]
        else:
            out.append(a)
    return [a for a in out if a[1] - a[0] > 0.25]


def spread(lines, segs, end):
    """lines the recogniser missed (conf < 0.5, e.g. a repeated chorus it skipped) are laid over the AUDIBLE vocal time between
    their confident neighbours, sized by word count, instead of collapsing to one instant (a skipped chorus repeat otherwise
    squeezes several lines into a second or two)"""
    for ln in lines:  # a line far longer than its words can take matched a later repeat of the same word: re-spread it
        if ln["t1"] - ln["t0"] > 2.5 + 1.0 * len(ln["text"].split()):
            ln["conf"] = min(ln["conf"], 0.49)
    good = [k for k, ln in enumerate(lines) if ln["conf"] >= 0.5]
    k = 0
    while k < len(lines):
        if lines[k]["conf"] >= 0.5:
            k += 1; continue
        e = k
        while e < len(lines) and lines[e]["conf"] < 0.5:
            e += 1
        lo = max([lines[g]["t1"] for g in good if g < k] or [0.0])
        hi = min([lines[g]["t0"] for g in good if g >= e] or [end])
        spans = [[max(a, lo), min(b, hi)] for a, b in segs if b > lo and a < hi]
        total = sum(b - a for a, b in spans)
        if total > 0.5:
            weights = [max(1, len(lines[j]["text"].split())) for j in range(k, e)]
            acc, W = 0.0, sum(weights)

            def at(x):  # x seconds of voiced time after lo -> song time
                for a, b in spans:
                    if x <= b - a:
                        return a + x
                    x -= b - a
                return spans[-1][1]
            for j, w in zip(range(k, e), weights):
                lines[j]["t0"], lines[j]["t1"] = round(at(acc), 2), round(at(acc + total * w / W), 2)
                lines[j]["spread"] = True
                acc += total * w / W
        k = e
    return lines


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    d = ROOT / args[0]
    out = d / "audio" / "lyrics_timing.json"
    if "--summary" in sys.argv and out.exists():
        r = json.loads(out.read_text(encoding="utf-8"))
        for ln in r["lines"]:
            print(f"{ln['t0']:7.2f}-{ln['t1']:7.2f}  {'~' if ln.get('spread') else '!' if ln['conf'] < 0.5 else ' '} {ln['text']}")
        return
    m = json.loads((d / "mv.json").read_text(encoding="utf-8"))
    lines = lyric_lines(m.get("lyrics"))
    if not lines:
        sys.exit("no lyrics in mv.json")
    src = ROOT / (m.get("vocals") or m.get("audio") or "")
    if not src.is_file():
        sys.exit("no vocals or song uploaded")
    model_name = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "medium.en"
    try:
        from faster_whisper import WhisperModel
        import numpy as np
    except ImportError as e:
        sys.exit("mv_lyrics needs faster-whisper and numpy: pip install faster-whisper numpy  (%s)" % e)
    lang = sys.argv[sys.argv.index("--lang") + 1] if "--lang" in sys.argv else "en"
    t = time.time()
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    # decode with ffmpeg ourselves: faster-whisper 1.2.1's own decoder calls av.open(metadata_errors=...), which PyAV 19 removed
    import subprocess
    pcm = subprocess.run([FFMPEG, "-v", "error", "-i", str(src), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True, check=True).stdout
    segs, _ = model.transcribe(np.frombuffer(pcm, np.float32), language=lang, word_timestamps=True, vad_filter=True, beam_size=5,
                               initial_prompt=" ".join(lines)[:600])  # the lyrics bias the vocabulary (names, slang)
    words = [(w.word.strip(), round(w.start, 2), round(w.end, 2), round(w.probability, 2)) for s in segs for w in (s.words or [])]
    pcm_f = np.frombuffer(pcm, np.float32)
    vseg = voiced(pcm_f)
    res = {"model": model_name, "source": src.relative_to(ROOT).as_posix(), "seconds": round(time.time() - t, 1),
           "lines": spread(align(lines, words), vseg, len(pcm_f) / 16000), "voiced": vseg, "words": words}
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(out)
    good = sum(ln["conf"] >= 0.5 for ln in res["lines"])
    print(f"wrote {out.relative_to(ROOT).as_posix()}: {len(res['lines'])} lines ({good} matched well), {len(words)} words, {res['seconds']} s",
          flush=True)


if __name__ == "__main__":
    main()
