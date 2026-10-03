"""📖 Saga render bake-off (accuracy, consistency and speed of saga shots).

Renders ONE saga shot (same prompt, same seed) under several render-knob variants and reports the GPU time of each, so the best
likeness-per-second can become the saga's default (`saga.json` "render": {steps, ref_resolution, max_refs}).

  python tools/saga_bench.py explore/sagas/NNN-x/chNN e7 "A:" "B:ref_resolution=512" "C:steps=20" "D:max_refs=2" "E:steps=20,ref_resolution=512,max_refs=2"
      -> chNN/_bench/e7__A.png ... + chNN/_bench/e7_bench.json [{variant, over, gpu_s, wall_s, png}]  (a variant with no knobs = the saga's current settings)
  --dry-run   print the knobs and the reference count per variant, render nothing

Each render takes the normal GPU ticket (one lab job at a time). GPU time comes from ComfyUI's own execution_start / execution_success stamps."""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
KNOBS = {"steps": int, "ref_resolution": int, "max_refs": int, "megapixels": float, "upscaler": str, "up_scale": float}


def parse_variant(s):
    """'B:ref_resolution=512,steps=20' -> ('B', {'ref_resolution': 512, 'steps': 20}); unknown knobs raise"""
    name, _, rest = s.partition(":")
    over = {}
    for part in [p for p in rest.split(",") if p.strip()]:
        k, _, v = part.partition("=")
        k = k.strip()
        if k not in KNOBS:
            raise ValueError(f"unknown knob {k!r} (use {', '.join(KNOBS)})")
        over[k] = KNOBS[k](v)
    return name.strip() or "A", over


def gpu_seconds(hist):
    """ComfyUI history -> seconds between execution_start and execution_success (None if the stamps are missing)"""
    msgs = {m[0]: m[1] for m in (hist.get("status") or {}).get("messages") or [] if isinstance(m, list) and len(m) == 2}
    a, b = (msgs.get("execution_start") or {}).get("timestamp"), (msgs.get("execution_success") or {}).get("timestamp")
    return round((b - a) / 1000, 1) if a and b else None


def main(argv):
    pos = [a for a in argv if not a.startswith("--")]
    if len(pos) < 3:
        sys.exit(__doc__)
    edir = Path(pos[0]) if Path(pos[0]).is_absolute() else ROOT / pos[0]
    sid, variants = pos[1], [parse_variant(v) for v in pos[2:]]
    import explore_render as er
    import saga_render as sr
    ep = er.load(edir)
    idx = next((i for i, s in enumerate(ep.get("shots") or [], 1) if s.get("id") == sid), None)
    if idx is None:
        sys.exit(f"no shot {sid} in {edir}")
    shot = ep["shots"][idx - 1]
    out = edir / "_bench"
    out.mkdir(exist_ok=True)
    if "--dry-run" in argv:
        for name, over in variants:
            refs = sr.refs_of(sr.render_bible(edir, over), shot, sr.root_of(edir))
            print(f"{name}: {over or '(current settings)'} -> {len(refs)} reference image(s): {[w for _, w in refs]}")
        return
    import run_version as rv
    results = []
    for name, over in variants:
        g = sr.build(ep, shot, idx, edir, True, over=over)
        t0 = time.time()
        hist = rv.submit_and_wait(g, timeout=3600)
        wall = round(time.time() - t0, 1)
        ims = [im for o in hist["outputs"].values() for im in o.get("images", [])]
        png = out / f"{sid}__{name}.png"
        q = urllib.parse.urlencode({k: ims[0][k] for k in ("filename", "subfolder", "type")})
        with urllib.request.urlopen(f"{rv.SERVER}/view?{q}") as r:
            png.write_bytes(r.read())
        row = {"variant": name, "over": over, "gpu_s": gpu_seconds(hist), "wall_s": wall, "png": png.relative_to(ROOT).as_posix(),
               "refs": len(sr.refs_of(sr.render_bible(edir, over), shot, sr.root_of(edir)))}
        results.append(row)
        print(json.dumps(row), flush=True)
        (out / f"{sid}_bench.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print("bench done:", ", ".join(f"{r['variant']} {r['gpu_s']}s" for r in results), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
