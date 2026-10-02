"""Waveform + beats + sections of a song for the 🎵 music-video timeline.

  python tools/mv_analyze.py <audio file> <out analysis.json>

-> {duration, peaks: [[min, max], ...] (~3000 buckets, -1..1, mono), beats: [t...], tempo, sections: [t...]} (seconds).
Needs librosa + soundfile + numpy (pip install librosa soundfile numpy; config.json "comfy_python" can point at an interpreter that has them). mp3 that librosa can't decode is
re-decoded through ffmpeg to a temp wav.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import FFMPEG  # noqa: E402
BUCKETS = 3000
SR = 22050


def need_librosa():
    try:
        import librosa
        return librosa
    except ImportError:
        sys.exit("mv_analyze needs librosa + soundfile + numpy: pip install librosa soundfile numpy")


def load(path):
    librosa = need_librosa()
    try:
        return librosa.load(path, sr=SR, mono=True)
    except Exception:
        with tempfile.TemporaryDirectory() as td:
            wav = os.path.join(td, "in.wav")
            subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), wav], check=True)
            return librosa.load(wav, sr=SR, mono=True)


def peaks(y, n=BUCKETS):
    import numpy as np
    n = max(1, min(n, len(y)))
    edges = np.linspace(0, len(y), n + 1).astype(int)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        seg = y[a:max(b, a + 1)]
        out.append([round(float(seg.min()), 3), round(float(seg.max()), 3)])
    return out


def sections(y, sr, want=8):
    """~6-12 boundaries (seconds) from agglomerative clustering of beat-synchronous chroma + MFCC"""
    librosa = need_librosa()
    import numpy as np
    dur = len(y) / sr
    if dur < 20:
        return []
    k = int(max(6, min(12, round(dur / 25))))
    hop = 512
    feat = np.vstack([librosa.util.normalize(librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop), axis=1),
                      librosa.util.normalize(librosa.feature.mfcc(y=y, sr=sr, hop_length=hop, n_mfcc=13), axis=1)])
    b = librosa.segment.agglomerative(feat, k)
    t = librosa.frames_to_time(b, sr=sr, hop_length=hop)
    return [round(float(x), 2) for x in t if 1.0 < x < dur - 1.0]


def analyze(path):
    librosa = need_librosa()
    y, sr = load(path)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(tempo.item() if hasattr(tempo, "item") else tempo)
    return {"duration": round(len(y) / sr, 3), "peaks": peaks(y),
            "beats": [round(float(t), 2) for t in librosa.frames_to_time(beats, sr=sr)],
            "tempo": round(tempo, 1), "sections": sections(y, sr)}


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    out = Path(argv[2])
    res = analyze(argv[1])
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(res, separators=(",", ":")), encoding="utf-8")
    tmp.replace(out)
    print(f"{res['duration']}s, {len(res['beats'])} beats @ {res['tempo']} bpm, {len(res['sections'])} sections")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
