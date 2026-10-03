"""🧪 gallery/bench.html: the results page of the speed / quality bake-offs (style_bench.py runs + saga_bench.py reference tests).

  python tools/bench_page.py [run ...]      (default: every bench/<run>/results.json, newest first) -> gallery/bench.html
Served by serve_gallery at /gallery/bench.html. results.json may carry "verdicts" {target: {pick, note}} (the author's call per style)
and "summary" (a paragraph) — both are shown. Pure HTML + a little JS (wipe compare, zoom, lightbox), no build step."""
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPTER = 15  # shots in a typical chapter, for the "per chapter" estimate


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def effective(rows):
    """an upscale variant that reused L's sampled picture (sampler_cached) only timed its upscale: its real cost = L's time + its own. Sets r['eff_s']"""
    by = {}
    for r in rows:
        by.setdefault(r["target"], {})[r["variant"]] = r
    for d in by.values():
        base = d.get("L")
        for r in d.values():
            r["up_s"] = r["gpu_s"] if r.get("sampler_cached") else None
            r["eff_s"] = round(r["gpu_s"] + base["gpu_s"], 1) if r.get("sampler_cached") and base and base.get("gpu_s") and r.get("gpu_s") is not None else r.get("gpu_s")
    return rows


def stats(rows, variants):
    """-> per variant {n, avg_gpu, vs_native % (paired by target), size}  (times = effective seconds)"""
    rows = [{**r, "gpu_s": r.get("eff_s", r.get("gpu_s"))} for r in effective([dict(r) for r in rows])]
    by = {}
    for r in rows:
        by.setdefault(r["target"], {})[r["variant"]] = r
    out = {}
    for v in variants:
        pairs = [(t[v]["gpu_s"], t["N"]["gpu_s"]) for t in by.values() if v in t and "N" in t and t[v].get("gpu_s") and t["N"].get("gpu_s")]
        own = [t[v]["gpu_s"] for t in by.values() if v in t and t[v].get("gpu_s")]
        sizes = [tuple(t[v]["size"]) for t in by.values() if v in t and t[v].get("size")]
        out[v] = {"n": len(own), "avg": round(sum(own) / len(own), 1) if own else None,
                  "vs": round(100 * (1 - sum(a for a, _ in pairs) / sum(b for _, b in pairs)), 1) if pairs else None,
                  "size": max(set(sizes), key=sizes.count) if sizes else None}
    return out, by


def section_run(res):
    rows, vmeta = res.get("rows") or [], res.get("variants") or {}
    vs = list(vmeta) or sorted({r["variant"] for r in rows})
    st, by = stats(rows, vs)
    verdicts = res.get("verdicts") or {}
    nat = st.get("N", {}).get("avg")
    cards = []
    for v in vs:
        s = st[v]
        per = f"{s['avg'] * CHAPTER / 60:.1f} min" if s["avg"] else "–"
        save = ""
        if v != "N" and nat and s["avg"]:
            save = f"<div class='save'>{'saves' if s['avg'] < nat else 'costs'} {abs(nat - s['avg']) * CHAPTER / 60:.1f} min per {CHAPTER}-shot chapter</div>"
        label = esc(vmeta.get(v, {}).get("label", v))
        rel = ("%+.0f%% vs native" % -s["vs"]) if s["vs"] is not None and v != "N" else ("baseline" if v == "N" else "")
        size = f"<div>output {s['size'][0]}×{s['size'][1]}</div>" if s["size"] else ""
        avg = f"{s['avg']} s" if s["avg"] else "–"
        cards.append(f"<div class='card'><b>{esc(v)}</b> <span>{label}</span><div class='big'>{avg}</div><div>avg GPU time · {s['n']} image(s)</div>"
                     f"<div>{rel}</div>{size}<div>≈ {per} per chapter</div>{save}</div>")
    trs = []
    for t, d in by.items():
        r0 = next(iter(d.values()))
        cells = []
        for v in vs:
            r = d.get(v)
            if not r:
                cells.append("<td class='dim'>…</td>")
                continue
            dv = f" <i>{100 * (r['gpu_s'] / d['N']['gpu_s'] - 1):+.0f}%</i>" if v != "N" and "N" in d and r.get("gpu_s") and d["N"].get("gpu_s") else ""
            cells.append(f"<td>{r['gpu_s']} s{dv}</td>")
        vd = verdicts.get(t) or {}
        trs.append(f"<tr><td><a href='#t-{esc(t)}'>{esc(r0['family'])}</a><div class='dim'>{esc(r0['title'])}</div></td>{''.join(cells)}"
                   f"<td class='pick'>{esc(vd.get('pick', '–'))}</td><td class='note'>{esc(vd.get('note', ''))}</td></tr>")
    heads = "".join(f"<th>{esc(v)} · {esc(vmeta.get(v, {}).get('label', v))}</th>" for v in vs)
    table = f"<table><tr><th>Style</th>{heads}<th>Pick</th><th>Why</th></tr>{''.join(trs)}</table>"
    secs = []
    for t, d in by.items():
        r0 = next(iter(d.values()))
        imgs = "".join(f"<figure><img loading='lazy' src='../{esc(r['png'])}' data-full='../{esc(r['png'])}' alt=''><figcaption><b>{esc(v)}</b> {esc(vmeta.get(v, {}).get('label', v))}"
                       f" · {r['gpu_s']} s · {r['size'][0]}×{r['size'][1] if r.get('size') else ''}</figcaption>"
                       f"<div class='zooms'>{''.join(f'<div class=z style=\"background-image:url(../{esc(r[chr(112) + chr(110) + chr(103)])});background-position:{p}\"></div>' for p in ('50% 30%', '25% 70%', '78% 55%'))}</div></figure>"
                       for v in vs for r in [d.get(v)] if r)
        others = [v for v in vs if v != "N" and v in d]
        wipe = ""
        if "N" in d and others:
            wipe = (f"<div class='wipe' data-a='../{esc(d['N']['png'])}'><select>{''.join(f'<option value=\"../{esc(d[v][chr(112) + chr(110) + chr(103)])}\">N vs {esc(v)}</option>' for v in others)}</select>"
                    f"<div class='wbox'><img class='wa' src='../{esc(d['N']['png'])}'><img class='wb' src='../{esc(d[others[0]]['png'])}'><div class='wl'></div></div>"
                    f"<input type='range' min='0' max='100' value='50'></div>")
        vd = verdicts.get(t) or {}
        secs.append(f"<section id='t-{esc(t)}'><h3>{esc(r0['family'])} <span class='dim'>{esc(r0['title'])}</span></h3>"
                    f"<p class='dim style'>{esc(r0.get('style', ''))}</p>{('<p class=verdict><b>Pick: ' + esc(vd.get('pick', '')) + '</b> ' + esc(vd.get('note', '')) + '</p>') if vd else ''}"
                    f"<div class='row'>{imgs}</div>{wipe}<p class='dim'>Zoom strips: the same three spots of every version (face height, lower left, right side) at 4x, to judge lines, texture and grain.</p></section>")
    return (f"<h2>{esc(res.get('run'))} <span class='dim'>{esc(res.get('created', ''))} · {len(rows)} renders</span></h2>"
            + (f"<p class='summary'>{esc(res['summary'])}</p>" if res.get("summary") else "")
            + f"<div class='cards'>{''.join(cards)}</div>{table}{''.join(secs)}")


def section_refs():
    """saga_bench.py results (reference-image settings on a crowded shot)"""
    out = []
    for f in sorted(ROOT.glob("explore/sagas/*/ch*/_bench/*_bench.json")):
        rows = json.loads(f.read_text(encoding="utf-8"))
        if not rows:
            continue
        base = next((r for r in rows if r["variant"] == "A"), rows[0])
        figs = "".join(f"<figure><img loading='lazy' src='../{esc(r['png'])}' data-full='../{esc(r['png'])}'><figcaption><b>{esc(r['variant'])}</b> {esc(json.dumps(r['over']) if r['over'] else 'current')}"
                       f" · {r['gpu_s']} s{(' (%+.0f%%)' % (100 * (r['gpu_s'] / base['gpu_s'] - 1))) if r is not base and r.get('gpu_s') and base.get('gpu_s') else ''} · {r.get('refs', '?')} refs</figcaption></figure>" for r in rows)
        nf = f.with_name(f.stem.replace("_bench", "") + "_notes.txt")
        notes = f"<p class='summary'>{esc(nf.read_text(encoding='utf-8'))}</p>" if nf.is_file() else ""
        out.append(f"<section><h3>Reference settings · {esc(f.parent.parent.parent.name)} {esc(f.parent.parent.name)} {esc(f.stem.replace('_bench', ''))}</h3>{notes}<div class='row'>{figs}</div></section>")
    return ("<h2>Reference-image settings (crowded saga shot)</h2>" + "".join(out)) if out else ""


CSS = """:root{--bg:#0f1117;--panel:#171a23;--ink:#e8eaf2;--muted:#8a90a6;--line:#2a2f3d;--accent:#ff5fa2}
body{margin:0;background:var(--bg);color:var(--ink);font:14px system-ui,sans-serif}main{max-width:1500px;margin:0 auto;padding:16px}
h1{margin:4px 0 12px}h2{margin:28px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}h3{margin:22px 0 6px}.dim{color:var(--muted);font-weight:400}
a{color:var(--accent)}.cards{display:flex;flex-wrap:wrap;gap:12px}.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px;min-width:210px}
.card span{color:var(--muted)}.big{font-size:28px;font-weight:800;margin:6px 0}.save{margin-top:6px;color:#7ee2a8;font-weight:700}
table{border-collapse:collapse;width:100%;margin:16px 0;background:var(--panel);border-radius:10px;overflow:hidden}th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
td i{color:#7ee2a8;font-style:normal}.pick{font-weight:700}.note{color:var(--muted);max-width:420px}.summary,.verdict{background:var(--panel);border-left:3px solid var(--accent);padding:10px 14px;border-radius:6px}
.style{font-size:12px;max-width:1100px}.row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}@media (max-width:1000px){.row{grid-template-columns:1fr}}figure{margin:0;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:8px}
figure img{width:100%;border-radius:6px;cursor:zoom-in;display:block}figcaption{font-size:12px;color:var(--muted);margin:6px 2px}.zooms{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.z{aspect-ratio:1;background-size:400%;background-repeat:no-repeat;border-radius:4px;border:1px solid var(--line);image-rendering:auto}
.wipe{margin:12px 0}.wipe select{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:4px}.wbox{position:relative;max-width:1100px;margin:8px 0}
.wbox img{width:100%;display:block;border-radius:6px}.wb{position:absolute;inset:0;clip-path:inset(0 0 0 50%)}.wl{position:absolute;top:0;bottom:0;left:50%;width:2px;background:var(--accent)}
.wipe input{width:100%;max-width:1100px}#lb{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;align-items:center;justify-content:center;z-index:9;cursor:zoom-out}#lb img{max-width:98vw;max-height:92vh}.lbcap{position:fixed;left:0;right:0;bottom:8px;text-align:center;color:#cfd3e2;font-size:13px;text-shadow:0 1px 2px #000}
@media (max-width:700px){main{padding:10px}.big{font-size:22px}}"""
JS = """document.querySelectorAll('.wipe').forEach(w=>{const r=w.querySelector('input'),b=w.querySelector('.wb'),l=w.querySelector('.wl'),s=w.querySelector('select');
const set=()=>{b.style.clipPath=`inset(0 0 0 ${r.value}%)`;l.style.left=r.value+'%'};r.oninput=set;s.onchange=()=>{b.src=s.value};set()});
const lb=document.getElementById('lb'),lbi=lb.querySelector('img'),lbc=lb.querySelector('.lbcap'),all=[...document.querySelectorAll('figure img')];let cur=-1;
// the enlarged view: mouse wheel (or arrow keys) steps through every picture on the page in order, so the variants of one style flip in place
const show=k=>{if(!all.length)return;cur=(k+all.length)%all.length;const im=all[cur];lbi.src=im.dataset.full;const f=im.closest('figure'),s=im.closest('section');
  lbc.textContent=(s&&s.querySelector('h3')?s.querySelector('h3').textContent+' · ':'')+(f&&f.querySelector('figcaption')?f.querySelector('figcaption').textContent:'')+`  (${cur+1}/${all.length} · wheel or ← → to flip, Esc to close)`;lb.style.display='flex'};
document.addEventListener('click',e=>{const i=e.target.closest('figure img');if(i)show(all.indexOf(i));else if(e.target.closest('#lb'))lb.style.display='none'});
lb.addEventListener('wheel',e=>{e.preventDefault();if(Math.abs(e.deltaY)<4)return;const now=Date.now();if(now-(lb._t||0)<140)return;lb._t=now;show(cur+(e.deltaY>0?1:-1))},{passive:false});
document.addEventListener('keydown',e=>{if(lb.style.display!=='flex')return;if(e.key==='ArrowRight'||e.key==='ArrowDown'){e.preventDefault();show(cur+1)}else if(e.key==='ArrowLeft'||e.key==='ArrowUp'){e.preventDefault();show(cur-1)}else if(e.key==='Escape')lb.style.display='none'});"""


def main(argv):
    runs = argv or [p.parent.name for p in sorted(ROOT.glob("bench/*/results.json"), key=lambda p: p.stat().st_mtime, reverse=True)]
    body = []
    for r in runs:
        f = ROOT / "bench" / r / "results.json"
        if f.is_file():
            body.append(section_run(json.loads(f.read_text(encoding="utf-8"))))
    body.append(section_refs())
    page = (f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Render bake-offs</title><style>{CSS}</style></head>"
            f"<body><main><h1>🧪 Render bake-offs <span class='dim'>speed vs quality, per style</span></h1><p class='dim'><a href='index.html'>← gallery</a> · times are GPU seconds from ComfyUI · "
            f"per-chapter estimates assume {CHAPTER} shots</p>{''.join(body)}</main><div id='lb'><img alt=''><div class='lbcap'></div></div><script>{JS}</script></body></html>")
    (ROOT / "gallery" / "bench.html").write_text(page, encoding="utf-8")
    print("wrote gallery/bench.html", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
