"""👄 EXPERIMENTAL. Lip-sync an existing clip to a vocal track with LatentSync 1.5. Needs two ComfyUI custom node packs
(not installed by this repo): ComfyUI-LatentSyncWrapper and ComfyUI-VideoHelperSuite.
  python tools/lipsync.py <clip.mp4> <vocals.wav> [--out <out.mp4>] [--lips 1.5] [--steps 20] [--seed N]
The clip's frames are re-mouthed to the audio (25 fps, as LatentSync expects) and saved WITH that audio.
Default output: <clip>__lipsync.mp4 (+ .json). In our tests LTX-2.3 image+audio gave better lip-sync than LatentSync over an
image-to-video clip. The clip and the audio are uploaded to ComfyUI over HTTP (POST /upload/image). Takes the GPU ticket like
every lab video job."""
import json
import mimetypes
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline  # noqa: E402
import run_version as rv  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def upload(path: Path, prefix="animestylelab_"):
    """POST /upload/image (it accepts any file, audio and video too) -> the name ComfyUI stored it under"""
    name = prefix + path.name.replace("@", "_").replace("~", "_")
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
    body = b"".join([
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\nContent-Type: {ctype}\r\n\r\n".encode(),
        path.read_bytes(), f"\r\n--{boundary}--\r\n".encode()])
    req = urllib.request.Request(rv.SERVER + "/upload/image", data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())["name"]


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def main():
    pos = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith("--") and not sys.argv[i - 1].startswith("--")]
    if len(pos) != 2:
        sys.exit(__doc__)
    clip, audio = (ROOT / pos[0]).resolve(), (ROOT / pos[1]).resolve()
    out = ROOT / arg("--out", str(clip.with_name(clip.stem + "__lipsync.mp4").relative_to(ROOT)))
    seed = int(arg("--seed", 1247))
    g = {
        "v": {"class_type": "VHS_LoadVideo", "inputs": {"video": upload(clip), "force_rate": 25, "custom_width": 0, "custom_height": 0,
                                                        "frame_load_cap": 0, "skip_first_frames": 0, "select_every_nth": 1}},
        "a": {"class_type": "VHS_LoadAudioUpload", "inputs": {"audio": upload(audio), "start_time": 0, "duration": 0}},
        "ls": {"class_type": "LatentSyncNode", "inputs": {"images": ["v", 0], "audio": ["a", 0], "seed": seed,
                                                           "lips_expression": float(arg("--lips", 1.5)), "inference_steps": int(arg("--steps", 20))}},
        "out": {"class_type": "VHS_VideoCombine", "inputs": {"images": ["ls", 0], "audio": ["ls", 1], "frame_rate": 25, "loop_count": 0,
                                                             "filename_prefix": "anime-style-lab/lipsync_" + out.stem, "format": "video/h264-mp4",
                                                             "pingpong": False, "save_output": True}},
    }
    rel = out.relative_to(ROOT).as_posix()
    job = pipeline.Job("lipsync", [{"kind": "video", "out": rel, "label": f"👄 {out.stem}"}])
    job.start(rel)
    t = time.time()
    try:
        hist = rv.submit_and_wait(g, timeout=5400, kind="video")
    except BaseException:
        job.finish(rel, ok=False)
        raise
    job.finish(rel)
    files = [f for o in hist["outputs"].values() for f in (o.get("gifs") or o.get("videos") or []) if str(f.get("filename", "")).endswith(".mp4")]
    if not files:
        sys.exit(f"no mp4 in outputs: {list(hist['outputs'].values())[:1]}")
    f = files[-1]
    q = urllib.parse.urlencode({k: f[k] for k in ("filename", "subfolder", "type")})
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(f"{rv.SERVER}/view?{q}") as r:
        out.write_bytes(r.read())
    out.with_suffix(".json").write_text(json.dumps({"engine": "latentsync", "source_clip": pos[0], "audio": pos[1], "seed": seed,
                                                    "lips_expression": float(arg("--lips", 1.5)), "steps": int(arg("--steps", 20)),
                                                    "render_seconds": round(time.time() - t, 1)}, indent=2), encoding="utf-8")
    import mv_audio  # the vocals drove the mouth; playback gets the full song mix
    mv_audio.song_under(out, mv_audio.frame_of(clip), at=float(arg("--song-at")) if arg("--song-at") else None)
    print("wrote", rel, flush=True)


if __name__ == "__main__":
    main()
