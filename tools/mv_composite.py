"""Chroma-key an LTX ia2v lip-sync clip (rendered from a start frame cut out over green, see mv_plates.py) over a moving Wan plate.
EXPERIMENTAL. Needs opencv-python + numpy and ffmpeg.

    python tools/mv_composite.py <ltx_on_green.mp4> <wan_clean.mp4>
        [--out path] [--preview out.jpg] [--max-slow 1.7] [--tmin 14] [--tmax 46] [--key R,G,B]

The key colour is measured from the clip's own first frame (LTX shifts the green a little), keyed on CbCr distance with a soft
alpha, spill suppressed on the edge band. Wan is resized to the LTX size, slowed up to --max-slow to cover the LTX duration, then
ping-ponged (no freeze, no jump). The LTX clip's audio is muxed in. Sidecar .json = LTX json + "composite"; .genaudio.m4a copied.
Default out: the LTX name with its tag segment replaced by "comp" (s10__ltxia2v-talk_seed1001.mp4 -> s10__ltxia2v-comp_seed1001.mp4).
"""
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:  # checked in main()
    cv2 = np = None

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from config import FFMPEG  # noqa: E402


def arg(flag, default=None):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


def cbcr(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return np.stack([-0.1687 * r - 0.3313 * g + 0.5 * b, 0.5 * r - 0.4187 * g - 0.0813 * b], -1)


def measure_key(frame_rgb):
    """key colour = median of the green-dominant pixels (the person is never green-dominant)"""
    f = frame_rgb.astype(np.float32)
    m = (f[..., 1] > f[..., 0] + 40) & (f[..., 1] > f[..., 2] + 40)
    if m.sum() < 500:
        raise SystemExit("no green background found in the LTX clip's first frame")
    return np.median(f[m], axis=0)


def key_alpha(rgb, key, tmin, tmax):
    """(alpha of the FOREGROUND, spill-suppressed float rgb); alpha 1 = keep the LTX pixel"""
    f = rgb.astype(np.float32)
    kc = cbcr(np.asarray(key, np.float32).reshape(1, 1, 3))[0, 0]
    d = np.linalg.norm(cbcr(f) - kc, axis=-1)
    a = np.clip((d - tmin) / (tmax - tmin), 0, 1)
    a = a * a * (3 - 2 * a)
    dom = (f[..., 1] - np.maximum(f[..., 0], f[..., 2])) / 255.0  # green-dominant leftovers (compression speckle) -> background
    a = np.where(dom > 0.25, 0, a)
    band = cv2.dilate((a < 0.98).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool) & (a > 0)
    out = f.copy()
    out[..., 1] = np.where(band, np.minimum(f[..., 1], np.maximum(f[..., 0], f[..., 2])), f[..., 1])  # despill: cap green at max(r, b)
    return a, out


class WanPlate:
    def __init__(self, path, size, n_out, fps_out, max_slow):
        cap = cv2.VideoCapture(str(path))
        self.fps = cap.get(cv2.CAP_PROP_FPS) or 16.0
        fr = []
        while True:
            ok, f = cap.read()
            if not ok:
                break
            fr.append(cv2.resize(f, size, interpolation=cv2.INTER_AREA if f.shape[1] > size[0] else cv2.INTER_CUBIC))
        cap.release()
        if not fr:
            raise SystemExit(f"cannot read {path}")
        self.frames = fr
        self.n_w = len(fr)
        need = n_out * self.fps / fps_out  # source frames needed at native speed
        self.speed = min(max_slow, need / self.n_w) if need > self.n_w else 1.0  # slow factor (>1 = slower)
        self.step = self.fps / fps_out / self.speed  # source frames advanced per output frame
        self.pingpong = (n_out - 1) * self.step > self.n_w - 1

    def pos(self, i):
        L = self.n_w - 1
        if L == 0:
            return 0.0
        p = i * self.step
        if not self.pingpong:
            return min(p, L)
        p = p % (2 * L)
        return p if p <= L else 2 * L - p

    def frame(self, i):
        p = self.pos(i)
        a = int(np.floor(p))
        b = min(a + 1, self.n_w - 1)
        t = p - a
        if t < 1e-3 or a == b:
            return self.frames[a]
        return cv2.addWeighted(self.frames[a], 1 - t, self.frames[b], t, 0)


def default_out(ltx):
    n = re.sub(r"(__[a-z0-9]+)-[a-z0-9]+(_seed\d+)", r"\1-comp\2", ltx.name)
    return ltx.with_name(n if n != ltx.name else ltx.stem + "_comp.mp4")


def rel(p):
    try:
        return Path(p).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def main():
    if cv2 is None:
        sys.exit("mv_composite needs opencv + numpy: pip install opencv-python numpy")
    ltx, wan = Path(sys.argv[1]), Path(sys.argv[2])
    out = Path(arg("--out")) if arg("--out") else default_out(ltx)
    tmin, tmax = float(arg("--tmin", 14)), float(arg("--tmax", 46))
    max_slow = float(arg("--max-slow", 1.7))
    t_start = time.time()
    cap = cv2.VideoCapture(str(ltx))
    fps = cap.get(cv2.CAP_PROP_FPS)
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    plate = WanPlate(wan, (W, H), n, fps, max_slow)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + "._v.mp4")
    enc = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", f"{fps}", "-i", "-",
                            "-c:v", "libx264", "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    key = np.array([float(v) for v in arg("--key").split(",")]) if arg("--key") else None
    keep_idx = {round(k * (n - 1) / 5) for k in range(6)}
    shots = []
    i = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        if key is None:
            key = measure_key(rgb)
        a, fg = key_alpha(rgb, key, tmin, tmax)
        a = cv2.GaussianBlur(a, (0, 0), 0.8)
        bg = cv2.cvtColor(plate.frame(i), cv2.COLOR_BGR2RGB).astype(np.float32)
        res = fg * a[..., None] + bg * (1 - a[..., None])
        res_bgr = cv2.cvtColor(np.clip(res, 0, 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
        enc.stdin.write(res_bgr.tobytes())
        if i in keep_idx:
            shots.append((res_bgr, (a * 255).astype(np.uint8)))
        i += 1
    cap.release()
    enc.stdin.close()
    enc.wait()
    subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(tmp), "-i", str(ltx), "-map", "0:v", "-map", "1:a?", "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    tmp.unlink(missing_ok=True)
    side = ltx.with_suffix(".json")
    meta = json.loads(side.read_text(encoding="utf-8")) if side.exists() else {}
    meta["composite"] = {"ltx": rel(ltx), "wan": rel(wan), "settings": {
        "key_rgb": [round(float(v), 1) for v in key], "tmin": tmin, "tmax": tmax, "max_slow": max_slow,
        "wan_speed": round(plate.speed, 3), "pingpong": plate.pingpong, "wan_fps": plate.fps}}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    ga = ltx.with_name(ltx.stem + ".genaudio.m4a")
    if ga.exists():
        shutil.copyfile(ga, out.with_name(out.stem + ".genaudio.m4a"))
    pv = arg("--preview")
    if pv and shots:
        th = 240
        tw = round(W * th / H)
        row1 = np.hstack([cv2.resize(f, (tw, th)) for f, _ in shots])
        row2 = np.hstack([cv2.cvtColor(cv2.resize(m, (tw, th)), cv2.COLOR_GRAY2BGR) for _, m in shots])
        cv2.imwrite(pv, np.vstack([row1, row2]), [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(json.dumps({"out": str(out), "frames": i, "fps": fps, "wan_speed": round(plate.speed, 3), "pingpong": plate.pingpong,
                      "seconds": round(time.time() - t_start, 1)}))


if __name__ == "__main__":
    main()
