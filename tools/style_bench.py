"""🧪 Style-aware speed / quality bake-off: find the speed sweet spot without losing any style to a
limited upscaler. Runs a spread of styles from the evolutions under each variant and feeds a test page (bench_page.py) that compares the
results within each style and sums up the savings.

Re-renders one existing image per TARGET (a lab lineage or a saga shot: same prompt, same seed) under each VARIANT and records the GPU time and output size.
Nothing in the lineage / chapter folders changes: everything goes to bench/<run>/ (+ results.json), which tools/bench_page.py turns into gallery/bench.html.

  python tools/style_bench.py <run> <target>... [--variants "N:" "A:megapixels=0.8,upscaler=4x-AnimeSharp.pth" ...] [--dry-run]
    target = evolutions/NNN-slug[=Family label]                     (its newest version with a picture, its first picture)
           | explore/sagas/NNN-slug/chNN:eK[=Family label]
    default variants: N (native, today) · A (0.8 MP + 4x-AnimeSharp, net 2x) · R (0.8 MP + 4x_foolhardy_Remacri, net 2x)
Knobs: megapixels, upscaler (a file in ComfyUI/models/upscale_models), up_scale (default 0.5 of the 4x = 2x), steps."""
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
# order matters: L renders the 0.8 MP picture once; A and R then reuse it from ComfyUI's cache, so their time is the UPSCALE alone (the page adds L's);
# N (native) last. One warm-up render first so no variant pays the model load.
DEFAULT_VARIANTS = ["L:megapixels=0.8,upscaler=plain", "A:megapixels=0.8,upscaler=4x-AnimeSharp.pth", "R:megapixels=0.8,upscaler=4x_foolhardy_Remacri.pth", "N:"]
VARIANT_LABEL = {"N": "native (today)", "L": "0.8 MP + plain resize 2x", "A": "0.8 MP + AnimeSharp 2x", "R": "0.8 MP + Remacri 2x"}


def parse_target(s):
    """'evolutions/004-shinkai-film=Luminous anime film' -> {kind, path, shot?, family}"""
    path, _, fam = s.partition("=")
    if ":" in path and "/sagas/" in path:
        ch, _, shot = path.partition(":")
        return {"kind": "saga", "path": ch.strip("/"), "shot": shot, "family": fam or Path(ch).parent.name}
    return {"kind": "lineage", "path": path.strip("/"), "family": fam or Path(path).name}


def lineage_pick(lin):
    """newest vNN with a top-level picture -> (vdir, png name). Pictures named <subject>_seed<N>.png or seed<N>.png"""
    vs = sorted([d for d in (ROOT / lin).glob("v[0-9][0-9]") if d.is_dir() and any(d.glob("*.png"))], key=lambda d: d.name)
    if not vs:
        raise SystemExit(f"{lin}: no version with a picture")
    vdir = vs[-1]
    png = sorted(p for p in vdir.glob("*.png") if not p.name.startswith("_"))[0]
    return vdir, png.stem


def lineage_job(lin):
    """-> (graph-builder(over), title, source png, style text) for a lineage target, without touching its files"""
    import run_version as rv
    vdir, name = lineage_pick(lin)
    template = (vdir / "prompt.txt").read_text(encoding="utf-8").strip()
    params = {**rv.DEFAULTS, **json.loads((vdir / "params.json").read_text(encoding="utf-8"))}
    m = re.match(r"(?:(.+)_)?seed(\d+)$", name)
    subj, seed = (m.group(1), int(m.group(2))) if m else (None, params["seeds"][0])
    prompt = template.replace("{subject}", rv.SUBJECTS[subj]["text"]) if subj and "{subject}" in template else template

    def build(over, wf):
        import saga_render as sr
        p = {**params, **({"megapixels": over["megapixels"]} if over.get("megapixels") else {}), **({"steps": over["steps"]} if over.get("steps") else {})}
        g = rv.version_graph(vdir, p, name, prompt, seed, wf)
        return sr.add_upscale(g, over.get("upscaler"), float(over.get("up_scale") or 0.5))
    return build, f"{Path(lin).name} {vdir.name}", (vdir / f"{name}.png").relative_to(ROOT).as_posix(), template[:400], params.get("megapixels")


def saga_job(ch, sid):
    import explore_render as er
    import saga_render as sr
    edir = ROOT / ch
    ep = er.load(edir)
    idx = next(i for i, s in enumerate(ep["shots"], 1) if s.get("id") == sid)
    shot = ep["shots"][idx - 1]

    def build(over, wf):
        return sr.build(ep, shot, idx, edir, True, over=over)
    return build, f"{Path(ch).parent.name} {Path(ch).name} {sid}", f"{ch}/{sid}.png", ep.get("style", "")[:400], er.MEGAPIXELS


def sampler_cached(hist):
    """True when ComfyUI reused the sampled picture (only the upscale step ran)"""
    for m in (hist.get("status") or {}).get("messages") or []:
        if isinstance(m, list) and m and m[0] == "execution_cached":
            return any(str(n).endswith("458") for n in (m[1] or {}).get("nodes") or [])
    return False


def png_size(p):
    try:
        from PIL import Image
        with Image.open(p) as im:
            return list(im.size)
    except Exception:
        return None


def main(argv):
    import saga_bench as sb
    dry = "--dry-run" in argv
    argv = [a for a in argv if a != "--dry-run"]
    vs = DEFAULT_VARIANTS
    if "--variants" in argv:
        i = argv.index("--variants")
        vs, argv = argv[i + 1:], argv[:i]
    if len(argv) < 2:
        sys.exit(__doc__)
    run, targets = argv[0], [parse_target(t) for t in argv[1:]]
    variants = [sb.parse_variant(v) for v in vs]
    out = ROOT / "bench" / run
    out.mkdir(parents=True, exist_ok=True)
    rf = out / "results.json"
    res = json.loads(rf.read_text(encoding="utf-8")) if rf.is_file() else {"run": run, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "rows": []}
    res["variants"] = {n: {"over": o, "label": VARIANT_LABEL.get(n, n)} for n, o in variants}
    done = {(r["target"], r["variant"]) for r in res["rows"]}
    import run_version as rv
    if not dry and targets:   # warm-up: load the model once, outside the measurements
        b0 = (lineage_job(targets[0]["path"]) if targets[0]["kind"] == "lineage" else saga_job(targets[0]["path"], targets[0]["shot"]))[0]
        rv.submit_and_wait(b0({"megapixels": 0.5}, out / "_warmup.workflow.json"), timeout=3600)
    for t in targets:
        build, title, source, style, native_mp = lineage_job(t["path"]) if t["kind"] == "lineage" else saga_job(t["path"], t["shot"])
        key = t["path"] + (":" + t["shot"] if t.get("shot") else "")
        slug = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")
        for name, over in variants:
            if (key, name) in done:
                continue
            if dry:
                print(f"would render {title} [{t['family']}] {name} {over or '(native)'}")
                continue
            g = build(over, out / f"_{slug}__{name}.workflow.json")
            t0 = time.time()
            hist = rv.submit_and_wait(g, timeout=3600)
            ims = [im for o in hist["outputs"].values() for im in o.get("images", [])]
            png = out / f"{slug}__{name}.png"
            q = urllib.parse.urlencode({k: ims[0][k] for k in ("filename", "subfolder", "type")})
            with urllib.request.urlopen(f"{rv.SERVER}/view?{q}") as r:
                png.write_bytes(r.read())
            row = {"target": key, "kind": t["kind"], "title": title, "family": t["family"], "style": style, "source": source, "native_mp": native_mp,
                   "variant": name, "over": over, "gpu_s": sb.gpu_seconds(hist), "wall_s": round(time.time() - t0, 1), "sampler_cached": sampler_cached(hist),
                   "png": png.relative_to(ROOT).as_posix(), "size": png_size(png)}
            res["rows"].append(row)
            disk = json.loads(rf.read_text(encoding="utf-8")) if rf.is_file() else {}   # merge: another run may have added rows meanwhile
            seen = {(r["target"], r["variant"]) for r in res["rows"]}
            res["rows"] += [r for r in disk.get("rows") or [] if (r["target"], r["variant"]) not in seen]
            for k in ("verdicts", "summary"):
                if disk.get(k) and not res.get(k):
                    res[k] = disk[k]
            rf.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
            print(json.dumps({k: row[k] for k in ("title", "variant", "gpu_s", "size")}), flush=True)
            try:   # the page fills in as the run goes
                import bench_page
                bench_page.main([run])
            except Exception as e:
                print("bench page rebuild failed:", e, flush=True)
    if not dry:
        import bench_page
        bench_page.main([run])
        print("bench done ->", (ROOT / "gallery" / "bench.html").as_posix(), flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
