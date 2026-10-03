"""Atlases: living neural maps of a feeling-space . ONE engine for both maps of the 📖 Nev Novel deck:

  formality  explore/formality_atlas.json   ~60 concepts of formality (dress codes, ceremonies, registers...)   features rigidity hierarchy ritual ornament tradition publicness intimacy chaos
  emotion    explore/emotion_atlas.json     ~60 complex, media-real emotional concepts (bittersweet, saudade, found-family warmth...)
             features valence arousal intimacy temporal moral_weight agency absurdity (all 0-1)
             valence: unpleasant .. pleasant; arousal: still .. intense; intimacy: personal .. epic scope; temporal: past .. future orientation;
             moral_weight: neutral .. heavy right/wrong stakes; agency: helpless .. in control; absurdity: earnest .. absurd.

  file  {version, kind, features: [...], meta {title, axes {top, bottom, left, right}, placeholder, hues {family: [h, s]}}, layout {mean, basis, origin, sx, sy, gap, mode},
         nodes: [...], edges: [...]}
  node  {id, name, family, picture (how pictures look / are staged), voice (caption / dialogue register), beats? (emotion: how stories produce it),
         features {...0-1}, x, y (unit disc), added_by, ts, legacy?, aka?}
  edge  {a, b, w (0.1-1: how strongly two concepts are connected), uses (times it was reinforced), kind? (transition|cooccur|arc_pair|contrast|similar), why?, dir?}
  story {ts, sources [{key, cite, url, used_for}], notes, links [{a, b, w, kind, dir, why, src}]}   researched base wiring (import-story); reset rebuilds from it

LAYOUT (documented defaults, both PCA = classical MDS of the node's OWN feature vectors, deterministic):
  formality: PC1 (the formality axis) is y with formal up, PC2 is x; Everyday sits at the origin (the neutral value).
  emotion:   the plane is pinned to VALENCE (horizontal: unpleasant left .. pleasant right) and AROUSAL (vertical: still at the bottom, intense at the top) because that reads
             best; the other five features separate nodes via the synapses and the collision nudge (layout.explained = variance kept by this plane vs the best 2-D PCA plane).
             Centre = the mean = neutral (no emotional steer); distance from the centre = intensity.
  Each side of each axis is then stretched to reach the rim, the square maps onto the unit disc, and crowded nodes are nudged apart (gap 0.12).
  Synapses start as each node's 3 nearest feature neighbours; the user's ❤ / 👎 on episodes thicken / thin the pairs of the blend they were written with.

  python tools/atlas.py <formality|emotion> layout [--edges]
  python tools/atlas.py <kind> add "<name>" --family F --features k=v,k=v --picture "..." --voice "..." [--beats "..."] [--aka a,b] [--by claude] [--for "<request>"] [--force]
  python tools/atlas.py <kind> reinforce <idA> <idB> [+0.05|-0.1]
  python tools/atlas.py <kind> reset [--remove-added]      FACTORY RESET (a backup is written first): every synapse back to its initial weight + the original kNN wiring;
                                                          nodes added later (added_by != seed) are kept unless --remove-added
  python tools/atlas.py <kind> import-story research.json [--no-features]   researched STORY links (co-occur / transition / arc pair / contrast, with sources)
                                                          become the factory wiring (+ 2 nearest neighbours at half weight); feature fixes applied + re-layout; backup first
  python tools/atlas.py <kind> backups | restore [<file>]  list explore/<kind>_atlas.backup-YYYYMMDD-HHMMSS.json (newest 5 kept) / put one back (default newest; the current state is backed up first)
  python tools/atlas.py <kind> describe '<value json>' | near "<text>" | path <a> <b> | list | requests | resolve <id> [node]
  (--file <path> works with every command; tools/formality_atlas.py is a thin alias of `atlas.py formality`.)

A VALUE (what the deck stores in explore.json and episode.json) is {probe: {x, y}, blend: [{id, name, w} x3, w sums to 1], genre (top node name), secondary, mix (2nd's
share 0-0.5), intensity (probe distance from the centre 0-1)} plus, formality: level (-100 casual .. +100 formal, from y), formality_level; emotion: valence, arousal
(0-1, blend-weighted). The emotion centre is neutral (blend []). Standard library + numpy only (no GPU, no installs)."""
import json
import math
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAP = 0.12           # minimum spacing between nodes in the unit disc
EPS = 0.004          # blend softness: weight ~ 1 / (distance^2 + EPS)
W_MIN, W_MAX = 0.1, 1.0
MATCH = 0.55         # fuzzy score from which a typed feeling counts as an existing node
STOP = {"a", "an", "the", "of", "and", "in", "on", "with", "for", "to", "feeling", "formality", "vibe", "kind", "type", "style", "sort", "find", "like", "very", "so", "is", "it",
        "emotion", "emotional", "mood", "feel", "feels"}
FORMALITY_FEATS = ["rigidity", "hierarchy", "ritual", "ornament", "tradition", "publicness", "intimacy", "chaos"]
EMOTION_FEATS = ["valence", "arousal", "intimacy", "temporal", "moral_weight", "agency", "absurdity"]
KINDS = {
    "formality": {"file": "formality_atlas.json", "feats": FORMALITY_FEATS, "mode": "formal", "anchor": "everyday",
                  "meta": {"title": "Formality atlas", "placeholder": "Find a feeling of formality…", "noun": "formality",
                           "axes": {"top": "F O R M A L", "bottom": "C A S U A L", "left": "p l a i n", "right": "e x p r e s s i v e"},
                           "hues": {"dress codes": [38, 85], "ceremony and ritual": [292, 70], "social register": [160, 65], "spatial order": [205, 80], "eras and aesthetics": [345, 78],
                                    "speech register": [68, 72], "stick registers": [228, 38]}}},
    "emotion": {"file": "emotion_atlas.json", "feats": EMOTION_FEATS, "mode": "plane", "anchor": None, "axis": "valence", "second": "arousal",
                "meta": {"title": "Emotion atlas", "placeholder": "Find a feeling… (bittersweet, saudade, dread)", "noun": "emotion",
                         "axes": {"top": "I N T E N S E", "bottom": "S T I L L", "left": "u n p l e a s a n t", "right": "p l e a s a n t"},
                         "hues": {"love and longing": [335, 72], "loss and grief": [222, 55], "fear and dread": [275, 62], "anger and justice": [8, 78], "joy and delight": [48, 88],
                                  "wonder and awe": [190, 75], "calm and comfort": [150, 50], "tension and drive": [24, 82], "belonging and bonds": [95, 58],
                                  "self and shame": [310, 38], "absurd and playful": [168, 80], "resolve and hope": [60, 70]}}},
}
ATLAS = ROOT / "explore" / KINDS["formality"]["file"]   # kept for formality_atlas.py importers


def kind_of(atlas_or_name):
    if isinstance(atlas_or_name, str):
        return atlas_or_name if atlas_or_name in KINDS else "formality"
    k = (atlas_or_name or {}).get("kind")
    return k if k in KINDS else "formality"


def atlas_path(kind="formality", root=None):
    return Path(root or ROOT) / "explore" / KINDS[kind_of(kind)]["file"]


def now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def load(path=None, kind="formality"):
    p = Path(path or atlas_path(kind))
    try:
        a = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        k = kind_of(kind)
        return {"version": 1, "kind": k, "features": list(KINDS[k]["feats"]), "layout": {}, "nodes": [], "edges": []}
    if "kind" not in a:
        a["kind"] = kind_of(kind)
    return a


def save(atlas, path=None):
    p = Path(path or atlas_path(atlas))
    p.parent.mkdir(parents=True, exist_ok=True)
    atlas.setdefault("kind", "formality")
    if "factory" not in atlas:
        atlas["factory"] = {"ts": now(), "seed_nodes": [n["id"] for n in atlas.get("nodes", []) if n.get("added_by") == "seed"]}
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(atlas, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(p)


def feats_of(atlas):
    return list(atlas.get("features") or KINDS[kind_of(atlas)]["feats"])


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def by_id(atlas):
    return {n["id"]: n for n in atlas.get("nodes", [])}


def fdist(a, b):
    ka = sorted(set(a["features"]) | set(b["features"]))
    return math.sqrt(sum((float(a["features"].get(k, 0.0)) - float(b["features"].get(k, 0.0))) ** 2 for k in ka))


def sim_w(d):
    return round(max(W_MIN, min(W_MAX, math.exp(-((d / 0.6) ** 2)))), 2)


def ekey(a, b):
    return tuple(sorted((a, b)))


def edge_of(atlas, a, b):
    k = ekey(a, b)
    for e in atlas.get("edges", []):
        if ekey(e["a"], e["b"]) == k:
            return e
    return None


# ---------------------------------------------------------------- layout (PCA == classical MDS of the feature vectors)
def _np():
    import numpy as np
    return np


def project(atlas, features):
    """feature dict -> (x, y) with the stored basis (so a node added later lands where a full re-layout would put it, before collision relaxing)"""
    lay = atlas["layout"]
    v = [float(features.get(k, 0.0)) - lay["mean"][i] for i, k in enumerate(feats_of(atlas))]
    x = sum(a * b for a, b in zip(v, lay["basis"][0]))
    y = sum(a * b for a, b in zip(v, lay["basis"][1]))
    return _squash(x - lay["origin"][0], y - lay["origin"][1], lay["sx"], lay["sy"])


def _squash(u, v, sx, sy):
    """each side of each axis is stretched to reach 1 (so the casual end and the sides are as visible as the formal top), then the square maps onto the disc"""
    u = u * (sx[0] if u >= 0 else sx[1])
    v = v * (sy[0] if v >= 0 else sy[1])
    return (u * math.sqrt(max(0.0, 1 - v * v / 2)), v * math.sqrt(max(0.0, 1 - u * u / 2)))


def _clamp_disc(x, y, r=1.0):
    d = math.hypot(x, y)
    return (x, y) if d <= r else (x * r / d, y * r / d)


def _relax(pos, fixed, gap=GAP, iters=800):
    """push crowded nodes apart (deterministic); `fixed` indexes never move"""
    n = len(pos)
    for _ in range(iters):
        moved = False
        for i in range(n):
            for j in range(i + 1, n):
                dx, dy = pos[j][0] - pos[i][0], pos[j][1] - pos[i][1]
                d = math.hypot(dx, dy)
                if d >= gap:
                    continue
                if d < 1e-9:
                    dx, dy, d = math.cos(i * 2.399), math.sin(i * 2.399), 1.0
                push = (gap - d) / 2 + 1e-4
                ux, uy = dx / d, dy / d
                fi, fj = i in fixed, j in fixed
                if fi and fj:
                    continue
                if fi:
                    pos[j] = _clamp_disc(pos[j][0] + ux * push * 2, pos[j][1] + uy * push * 2)
                elif fj:
                    pos[i] = _clamp_disc(pos[i][0] - ux * push * 2, pos[i][1] - uy * push * 2)
                else:
                    pos[i] = _clamp_disc(pos[i][0] - ux * push, pos[i][1] - uy * push)
                    pos[j] = _clamp_disc(pos[j][0] + ux * push, pos[j][1] + uy * push)
                moved = True
        if not moved:
            break
    return pos


def layout(atlas):
    """positions for every node from its own features (see the module doc for the per-kind axes); max radius 1"""
    np = _np()
    kind = kind_of(atlas)
    cfg = KINDS[kind]
    fs = feats_of(atlas)
    nodes = atlas["nodes"]
    X = np.array([[float(n["features"].get(k, 0.0)) for k in fs] for n in nodes], dtype=float)
    mean = X.mean(axis=0)
    Xc = X - mean
    _, _, Vt = np.linalg.svd(Xc, full_matrices=False)
    ids = [n["id"] for n in nodes]
    if cfg["mode"] == "plane":
        # readable default: the plane is pinned to the two named features (valence across, arousal up); the other features separate nodes through the synapses
        # (kNN in the full feature space) and the collision nudge. `explained` records how much variance the plane keeps vs the best 2-D PCA plane.
        bx = np.zeros(len(fs))
        bx[fs.index(cfg["axis"])] = 1.0
        by = np.zeros(len(fs))
        by[fs.index(cfg["second"])] = 1.0
        P = np.stack([Xc @ bx, Xc @ by], axis=1)
        origin = np.zeros(2)
        fixed = set()
        tot = float((Xc ** 2).sum()) or 1.0
        explained = [round(float((P ** 2).sum()) / tot, 3), round(float((Xc @ Vt[:2].T) ** 2).sum() / tot, 3) if False else round(float(((Xc @ Vt[:2].T) ** 2).sum()) / tot, 3)]
    else:
        by, bx = Vt[0].copy(), Vt[1].copy()
        j = int(np.argmax(np.abs(bx)))
        if bx[j] < 0:
            bx = -bx
        P = np.stack([Xc @ bx, Xc @ by], axis=1)
        hi = X[:, 0] >= 0.8
        if hi.any() and P[hi, 1].mean() < 0:
            by = -by
            P[:, 1] = -P[:, 1]
        anchor = cfg["anchor"]
        origin = P[ids.index(anchor)].copy() if anchor in ids else P.mean(axis=0)
        P = P - origin
        fixed = {ids.index(anchor)} if anchor in ids else set()
    sx = [1.0 / max(1e-9, float(P[:, 0].max())), 1.0 / max(1e-9, float(-P[:, 0].min()))]
    sy = [1.0 / max(1e-9, float(P[:, 1].max())), 1.0 / max(1e-9, float(-P[:, 1].min()))]
    pos = [_squash(float(a), float(b), sx, sy) for a, b in P]
    pos = _relax(pos, fixed)
    for n, (x, y) in zip(nodes, pos):
        n["x"], n["y"] = round(x, 4), round(y, 4)
    atlas["layout"] = {"mean": [round(float(v), 6) for v in mean], "basis": [[round(float(v), 6) for v in bx], [round(float(v), 6) for v in by]],
                       "origin": [round(float(origin[0]), 6), round(float(origin[1]), 6)], "sx": [round(v, 6) for v in sx], "sy": [round(v, 6) for v in sy], "gap": GAP}
    if cfg["mode"] == "plane":
        atlas["layout"]["mode"] = "valence x arousal plane"
        atlas["layout"]["explained"] = explained   # [this plane, the best PCA plane]
    atlas.setdefault("kind", kind)
    meta = atlas.setdefault("meta", {})
    for k, v in cfg["meta"].items():
        meta.setdefault(k, v)
    return atlas


def place(atlas, node):
    """position of one new node: project, then step away from any node closer than the gap"""
    x, y = _clamp_disc(*project(atlas, node["features"]))
    others = [(n["x"], n["y"]) for n in atlas["nodes"] if n["id"] != node["id"]]
    pos = others + [(x, y)]
    pos = _relax(pos, set(range(len(others))), iters=200)
    node["x"], node["y"] = round(pos[-1][0], 4), round(pos[-1][1], 4)
    return node


# ---------------------------------------------------------------- synapses
def knn_edges(atlas, ids=None, k=3):
    """3 nearest neighbours (feature space) of each node in `ids` (default all) -> new edges (existing ones are kept as they are)"""
    nodes = atlas["nodes"]
    have = {ekey(e["a"], e["b"]) for e in atlas.get("edges", [])}
    out = []
    for n in nodes:
        if ids is not None and n["id"] not in ids:
            continue
        near_ = sorted((fdist(n, m), m["id"]) for m in nodes if m["id"] != n["id"])[:k]
        for d, mid in near_:
            key = ekey(n["id"], mid)
            if key not in have:
                have.add(key)
                out.append({"a": key[0], "b": key[1], "w": sim_w(d), "uses": 0})
    return out


def components(atlas):
    adj = {n["id"]: set() for n in atlas["nodes"]}
    for e in atlas["edges"]:
        if e["a"] in adj and e["b"] in adj:
            adj[e["a"]].add(e["b"])
            adj[e["b"]].add(e["a"])
    seen, comps = set(), []
    for n in atlas["nodes"]:
        if n["id"] in seen:
            continue
        comp, stack = set(), [n["id"]]
        while stack:
            c = stack.pop()
            if c in comp:
                continue
            comp.add(c)
            stack.extend(adj[c] - comp)
        seen |= comp
        comps.append(comp)
    return comps


def connect(atlas):
    """join separate islands by the closest pair (feature space) so the network can always be navigated"""
    nodes = by_id(atlas)
    while True:
        comps = components(atlas)
        if len(comps) <= 1:
            return
        base = comps[0]
        best = min(((fdist(nodes[a], nodes[b]), a, b) for a in base for c in comps[1:] for b in c))
        key = ekey(best[1], best[2])
        atlas["edges"].append({"a": key[0], "b": key[1], "w": sim_w(best[0]), "uses": 0})


SIMILAR_K = 2       # with research story links, each node also keeps its 2 nearest feature neighbours ...
SIMILAR_SCALE = 0.5  # ... at half weight, so "next door" feelings stay reachable but story links lead


def story_edges(atlas):
    """the researched STORY links (atlas["story"]["links"]): emotions / registers
    that co-occur, transition or pay each other off in one story -> edges {a, b, w, uses 0, kind, why}; unknown ids skipped, duplicates keep the strongest"""
    ids = set(by_id(atlas))
    best = {}
    for l in (atlas.get("story") or {}).get("links") or []:
        a, b = l.get("a"), l.get("b")
        if a not in ids or b not in ids or a == b:
            continue
        k = ekey(a, b)
        w = round(max(W_MIN, min(W_MAX, float(l.get("w", 0.5)))), 2)
        if k not in best or w > best[k]["w"]:
            best[k] = {"a": k[0], "b": k[1], "w": w, "uses": 0, "kind": l.get("kind") or "story", "why": str(l.get("why") or "")[:200]}
            if l.get("dir") and l["dir"] != "both":
                best[k]["dir"] = l["dir"]
    return list(best.values())


def rebuild_edges(atlas):
    """factory wiring: the researched story links when the atlas has them (+ each node's SIMILAR_K nearest neighbours at SIMILAR_SCALE weight),
    else each node's 3 nearest feature neighbours; islands are then joined so the map can always be navigated"""
    story = story_edges(atlas)
    atlas["edges"] = story
    if story:
        for e in knn_edges(atlas, k=SIMILAR_K):
            e["w"] = round(max(W_MIN, e["w"] * SIMILAR_SCALE), 2)
            e["kind"] = "similar"
            atlas["edges"].append(e)
    else:
        atlas["edges"] = knn_edges(atlas)
    connect(atlas)
    atlas["edges"].sort(key=lambda e: (e["a"], e["b"]))


def import_story(atlas, data, apply_features=True):
    """take a research file {sources, links, feature_fixes, notes}: store it as atlas["story"], apply the feature fixes (re-layout when any changed),
    rebuild the factory wiring from it. Learned weights are replaced (back the file up first). -> report dict"""
    ids = by_id(atlas)
    bad = [l for l in data.get("links") or [] if l.get("a") not in ids or l.get("b") not in ids]
    links = [l for l in data.get("links") or [] if l not in bad]
    fixed = []
    if apply_features:
        fs = feats_of(atlas)
        for fx in data.get("feature_fixes") or []:
            n, k = ids.get(fx.get("id")), fx.get("feature")
            if n is None or k not in fs:
                continue
            old = n["features"].get(k)
            n["features"][k] = round(max(0.0, min(1.0, float(fx["to"]))), 2)
            n.setdefault("feature_notes", []).append({"feature": k, "from": old, "to": n["features"][k], "why": fx.get("why", ""), "src": fx.get("src", [])})
            fixed.append((n["id"], k, old, n["features"][k]))
    atlas["story"] = {"ts": now(), "sources": data.get("sources") or [], "notes": data.get("notes") or "", "links": links}
    if fixed:
        layout(atlas)
    rebuild_edges(atlas)
    deg = {}
    for e in atlas["edges"]:
        deg[e["a"]] = deg.get(e["a"], 0) + 1
        deg[e["b"]] = deg.get(e["b"], 0) + 1
    return {"links": len(links), "skipped": len(bad), "fixed": fixed, "edges": len(atlas["edges"]),
            "story_edges": sum(1 for e in atlas["edges"] if e.get("kind") not in ("similar", None)), "min_degree": min(deg.values()) if deg else 0}


def reinforce(atlas, a, b, delta):
    """strengthen (+) or weaken (-) the synapse a-b (created at 0.2 first if it did not exist); clamps 0.1-1.0; returns the edge"""
    nodes = by_id(atlas)
    if a not in nodes or b not in nodes or a == b:
        raise KeyError("unknown or identical node ids: %s %s" % (a, b))
    e = edge_of(atlas, a, b)
    if e is None:
        k = ekey(a, b)
        e = {"a": k[0], "b": k[1], "w": 0.2, "uses": 0}
        atlas["edges"].append(e)
    e["w"] = round(max(W_MIN, min(W_MAX, e["w"] + float(delta))), 3)
    e["uses"] = int(e.get("uses", 0)) + 1
    return e


def tree_pairs(v):
    """an ORBIT value (the deck's orbit view: centre -> 3 links -> 2 sub-links each) -> the (parent, child) pairs of its tree; [] for other values"""
    t = (v or {}).get("tree") if isinstance(v, dict) else None
    if not isinstance(t, dict) or not t.get("center"):
        return []
    out = [(t["center"], r) for r in t.get("ring1") or []]
    for r, ks in (t.get("kids") or {}).items():
        out += [(r, k) for k in ks or []]
    return out


def story_items(v):
    """[(id, w)] heaviest first: an orbit value folds each sub-link's weight into its parent (its emphasis applies only to the neuron it hangs on),
    so the centre and its three links lead; any other value = its blend"""
    bl = [(b.get("id"), float(b.get("w") or 0)) for b in ((v or {}).get("blend") or []) if b.get("id")]
    t = (v or {}).get("tree")
    if isinstance(t, dict) and t.get("center"):
        w = dict(bl)
        items = [(t["center"], w.get(t["center"], 0.0))] + [(r, w.get(r, 0.0) + sum(w.get(k, 0.0) for k in (t.get("kids") or {}).get(r) or [])) for r in t.get("ring1") or []]
        return sorted(items, key=lambda x: -x[1])
    return sorted(bl, key=lambda x: -x[1])


def reinforce_value(atlas, v, delta):
    """learning from a mark: an orbit value thickens its tree's own links (centre-link, link-sub-link); any other value its top-3 blend pairs"""
    nd = by_id(atlas)
    pairs = [(a, b) for a, b in tree_pairs(v) if a in nd and b in nd and a != b]
    if pairs:
        return [reinforce(atlas, a, b, delta) for a, b in pairs]
    return reinforce_blend(atlas, (v or {}).get("blend") or [], delta)


def reinforce_blend(atlas, blend, delta):
    """every pair among the blend's top 3 nodes (heaviest) -> list of touched edges"""
    blend = sorted([b for b in (blend or []) if isinstance(b, dict)], key=lambda b: -float(b.get("w") or 0))[:3]
    ids = [b["id"] for b in blend if b.get("id") in by_id(atlas)]
    out = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            out.append(reinforce(atlas, ids[i], ids[j], delta))
    return out


def path(atlas, a, b):
    """cheapest route a -> b along the synapses (cost 1 / w: strong connections are shorter) as a list of ids; [] if unreachable"""
    import heapq
    adj = {}
    for e in atlas["edges"]:
        c = 1.0 / max(W_MIN, e["w"])
        adj.setdefault(e["a"], []).append((e["b"], c))
        adj.setdefault(e["b"], []).append((e["a"], c))
    dist, prev, pq = {a: 0.0}, {}, [(0.0, a)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == b:
            break
        if d > dist.get(u, 1e18):
            continue
        for v, c in adj.get(u, []):
            nd = d + c
            if nd < dist.get(v, 1e18):
                dist[v], prev[v] = nd, u
                heapq.heappush(pq, (nd, v))
    if b not in dist:
        return []
    out, cur = [b], b
    while cur != a:
        cur = prev[cur]
        out.append(cur)
    return out[::-1]


# ---------------------------------------------------------------- values
def blend_features(atlas, blend):
    """weighted mean of the blend's node features -> {feature: 0-1}"""
    nd = by_id(atlas)
    out, tot = {}, 0.0
    for b in blend or []:
        n = nd.get(b.get("id"))
        if not n:
            continue
        w = float(b.get("w") or 0)
        tot += w
        for k, v in n["features"].items():
            out[k] = out.get(k, 0.0) + w * float(v)
    return {k: round(v / tot, 2) for k, v in out.items()} if tot else {}


def _extras(atlas, kind, x, y, blend):
    if kind == "formality":
        lvl = int(round(max(-1.0, min(1.0, y)) * 100))
        return {"level": lvl, "formality_level": 50 + lvl / 2}
    f = blend_features(atlas, blend)
    return {"valence": f.get("valence", 0.5), "arousal": f.get("arousal", 0.5)}


def value_at(atlas, x, y):
    """the value for a probe position (same maths as the page's xaValueAt); the formality centre is Everyday, the emotion centre is neutral"""
    kind = kind_of(atlas)
    x, y = _clamp_disc(float(x), float(y), 1.0)
    nodes = atlas["nodes"]
    if not nodes:
        return None
    if x == 0 and y == 0:
        return neutral(kind)
    ds = sorted(((math.hypot(n["x"] - x, n["y"] - y), n["id"]) for n in nodes))[:3]
    raw = [1.0 / (d * d + EPS) for d, _ in ds]
    tot = sum(raw)
    pct = [r / tot * 100 for r in raw]
    ip = [int(p) for p in pct]  # largest remainder -> whole percents that sum to 100
    for i in sorted(range(len(pct)), key=lambda i: -(pct[i] - ip[i]))[: 100 - sum(ip)]:
        ip[i] += 1
    nd = by_id(atlas)
    blend = [{"id": i, "name": nd[i]["name"], "w": round(p / 100, 2)} for (_, i), p in zip(ds, ip)]
    w1, w2 = blend[0]["w"], (blend[1]["w"] if len(blend) > 1 else 0)
    v = {"probe": {"x": round(x, 3), "y": round(y, 3)}, "blend": blend, "genre": blend[0]["name"], "secondary": blend[1]["name"] if len(blend) > 1 and w2 >= 0.05 else None,
         "mix": round(min(0.5, w2 / (w1 + w2)), 2) if len(blend) > 1 and w1 + w2 else 0.0, "intensity": round(min(1.0, math.hypot(x, y)), 2)}
    v.update(_extras(atlas, kind, x, y, blend))
    return v


def neutral(kind="formality"):
    if kind_of(kind) == "emotion":
        return {"probe": {"x": 0.0, "y": 0.0}, "blend": [], "genre": None, "secondary": None, "mix": 0.0, "intensity": 0.0, "valence": 0.5, "arousal": 0.5}
    return {"probe": {"x": 0.0, "y": 0.0}, "blend": [{"id": "everyday", "name": "Everyday", "w": 1.0}], "genre": "Everyday", "secondary": None, "mix": 0.0,
            "intensity": 0.0, "level": 0, "formality_level": 50}


def is_atlas_value(v):
    return isinstance(v, dict) and (isinstance(v.get("blend"), list) or isinstance(v.get("probe"), dict))


def blend_words(v, atlas=None, kind="formality"):
    """'Black tie 48% · Art Deco gala 32% · Diplomatic summit 20%' ('Everyday · neutral' / 'neutral (no emotional steer)' when empty)"""
    bl = (v or {}).get("blend") or []
    if not bl:
        return "neutral (no emotional steer)" if kind_of(atlas if atlas is not None else kind) == "emotion" else "Everyday · neutral"
    return " · ".join("%s %d%%" % (b.get("name") or b.get("id"), round(float(b.get("w", 0)) * 100)) for b in bl)


def top_node(v, atlas):
    bl = (v or {}).get("blend") or []
    return by_id(atlas).get(bl[0].get("id")) if bl else None


def top_lines(v, atlas=None, kind="formality"):
    """(picture, voice) of the blend's top node, or ('', '')"""
    atlas = atlas or load(kind=kind)
    n = top_node(v, atlas)
    return (n.get("picture", ""), n.get("voice", "")) if n else ("", "")


def tree_words(v, atlas):
    """'Grief → Bittersweet (Nostalgia, Tension) · → Catharsis (...) · → Heartbreak (...)' for an orbit value, '' otherwise"""
    t = (v or {}).get("tree")
    if not isinstance(t, dict) or not t.get("center"):
        return ""
    nd = by_id(atlas)
    nm = lambda i: nd[i]["name"] if i in nd else i  # noqa: E731
    parts = ["%s (%s)" % (nm(r), ", ".join(nm(k) for k in (t.get("kids") or {}).get(r) or [])) for r in t.get("ring1") or []]
    return "%s → %s" % (nm(t["center"]), " · ".join(parts)) if parts else nm(t["center"])


def describe_value(v, atlas=None, kind="formality"):
    atlas = atlas or load(kind=kind)
    k = kind_of(atlas)
    n = top_node(v, atlas)
    tw = tree_words(v, atlas)
    if tw:  # an orbit value: say the tree (centre → its three links with their two sub-links each); the flat blend follows
        return "orbit: %s; %s" % (tw, describe_value({kk: vv for kk, vv in v.items() if kk != "tree"}, atlas))
    if k == "emotion":
        s = blend_words(v, atlas)
        if not (v or {}).get("blend"):
            return s
        s += " (valence %.2f, arousal %.2f, intensity %.2f)" % (float(v.get("valence", 0.5)), float(v.get("arousal", 0.5)), float(v.get("intensity") or 0))
        if n:
            s += "; pictures: %s; captions: %s%s" % (n.get("picture", ""), n.get("voice", ""), "; story beats: " + n["beats"] if n.get("beats") else "")
        return s
    s = "%s (level %+d)" % (blend_words(v, atlas), int((v or {}).get("level") or 0))
    if n:
        s += "; pictures: %s; captions: %s" % (n.get("picture", ""), n.get("voice", ""))
    return s


# ---------------------------------------------------------------- fuzzy search (the page ports this exactly: xaScore)
def norm(s):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(s).lower()).split())


def stem(t):
    return t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t


def tokens(s):
    return {stem(t) for t in norm(s).split() if t not in STOP}


def dice(a, b):
    def bg(s):
        s = " " + s + " "
        return [s[i:i + 2] for i in range(len(s) - 1)]
    x, y = bg(a), bg(b)
    if not x or not y:
        return 0.0
    ys = list(y)
    hit = 0
    for g in x:
        if g in ys:
            ys.remove(g)
            hit += 1
    return 2.0 * hit / (len(x) + len(y))


def score(text, node):
    q = norm(text)
    qt = tokens(text)
    if not q or not qt:
        return 0.0
    nn = norm(node["name"])
    if q == nn:
        return 1.0
    nt = tokens(node["name"] + " " + " ".join(node.get("aka") or []))
    dt = tokens(node.get("family", "") + " " + node.get("picture", "") + " " + node.get("voice", ""))
    s_name = len(qt & nt) / len(qt)
    s_desc = len(qt & dt) / len(qt)
    s_sub = 0.9 if (nn in q or q in nn) and len(q) >= 3 else 0.0
    return round(max(0.95 * dice(q, nn), 0.9 * s_name, 0.7 * s_desc, s_sub), 4)


def near(atlas, text, n=5):
    sc = sorted(((score(text, nd), nd["id"]) for nd in atlas["nodes"]), key=lambda t: (-t[0], t[1]))
    return [(i, s) for s, i in sc[:n] if s > 0]


# ---------------------------------------------------------------- requests from the page ("atlas_add": the user typed a feeling the map has no node for)
def req_file(root=None):
    return Path(root or ROOT) / "feedback" / "atlas_requests.json"


def _jload(p, d):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return d


def add_request(root, text, ts=None, atlas="formality"):
    """record a typed feeling (deduplicated while open, per atlas) -> the request dict ("new": True when it was just created)"""
    f = req_file(root)
    reqs = _jload(f, [])
    t = " ".join(str(text).split())[:200]
    atlas = kind_of(atlas)
    for r in reqs:
        if r.get("status") == "open" and r.get("atlas", "formality") == atlas and norm(r["text"]) == norm(t):
            return r
    r = {"id": "a%d" % (len(reqs) + 1), "text": t, "ts": ts or now(), "status": "open", "atlas": atlas}
    reqs.append(r)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(reqs, indent=1, ensure_ascii=False), encoding="utf-8")
    return {**r, "new": True}


def open_requests(root=None, atlas=None):
    return [r for r in _jload(req_file(root), []) if r.get("status") == "open" and (atlas is None or r.get("atlas", "formality") == kind_of(atlas))]


def resolve_request(root, key, node=None):
    f = req_file(root)
    reqs = _jload(f, [])
    n = 0
    for r in reqs:
        if r.get("status") == "open" and (r["id"] == key or norm(r["text"]) == norm(key)):
            r["status"], r["node"], r["done"] = "done", node, now()
            n += 1
    if n:
        f.write_text(json.dumps(reqs, indent=1, ensure_ascii=False), encoding="utf-8")
    return n


# ---------------------------------------------------------------- learning from the user's marks
def episode_json_for(root, key):
    """'explore/001-x/e3.png' or 'explore/sagas/001-x/ch02/e3.png' -> the episode.json path, or None"""
    m = re.match(r"(explore/(?:sagas/[^/]+/ch[^/]+|[^/]+))/[^/]+\.png$", key or "")
    return Path(root) / m.group(1) / "episode.json" if m and not m.group(1).endswith("/sagas") else None


def learn_from_mark(root, key, delta, atlas_path=None, kind="formality"):
    """❤ / 👎 on an explore shot: reinforce the blend of that episode's value of this atlas (formality, emotion; the active cores' blends count for emotion too).
    Returns the number of edges touched"""
    f = episode_json_for(root, key)
    if not f:
        return 0
    ep = _jload(f, {})
    kind = kind_of(kind)
    vals = []
    v = ep.get(kind)
    if is_atlas_value(v) and v.get("blend"):
        vals.append(v)
    if kind == "emotion":
        for c in ep.get("cores") or []:
            if isinstance(c, dict) and c.get("status", "active") == "active" and c.get("blend"):
                vals.append(c)
    if not vals:
        return 0
    p = atlas_path or atlas_path_default(root, kind)
    atlas = load(p, kind)
    touched = []
    for x in vals:
        touched += reinforce_value(atlas, x, delta)
    if touched:
        save(atlas, p)
    return len(touched)


def atlas_path_default(root, kind):
    return Path(root) / "explore" / KINDS[kind_of(kind)]["file"]


# ---------------------------------------------------------------- factory reset + backups
KEEP_BACKUPS = 5


def reset_atlas(atlas, remove_added=False):
    """factory state: every synapse rebuilt from the features (initial weights, uses 0, learned weights gone). Seed nodes always stay; nodes added later stay unless remove_added"""
    added = [n["id"] for n in atlas["nodes"] if n.get("added_by") != "seed"]
    removed = []
    if remove_added and added:
        atlas["nodes"] = [n for n in atlas["nodes"] if n.get("added_by") == "seed"]
        removed, added = added, []
    n_old = len(atlas.get("edges", []))
    rebuild_edges(atlas)
    atlas.setdefault("factory", {"ts": now(), "seed_nodes": [n["id"] for n in atlas["nodes"] if n.get("added_by") == "seed"]})
    return {"edges_reset": max(n_old, len(atlas["edges"])), "removed_nodes": removed, "kept_added": added}


def _backup_glob(kind, root=None):
    p = atlas_path(kind, root)
    return p.parent, p.stem + ".backup-"


def _bkey(q):
    """oldest -> newest: by timestamp, then by the same-second counter (-2, -3 ...)"""
    m = re.search(r"backup-(\d{8}-\d{6})(?:-(\d+))?$", q.stem)
    return (m.group(1), int(m.group(2) or 1)) if m else (q.stem, 0)


def list_backups(kind, root=None):
    d, pre = _backup_glob(kind, root)
    return sorted(d.glob(pre + "*.json"), key=_bkey) if d.exists() else []


def backup_atlas(kind, root=None, src=None):
    """copy the live atlas file to explore/<kind>_atlas.backup-YYYYMMDD-HHMMSS.json (unique within a second), keep the newest KEEP_BACKUPS; returns the path"""
    import shutil
    live = Path(src) if src else atlas_path(kind, root)
    d, pre = _backup_glob(kind, root) if not src else (live.parent, live.stem + ".backup-")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    same = [_bkey(q)[1] for q in d.glob(f"{pre}{stamp}*.json")]
    n = max(same) + 1 if same else 1
    dest = d / (f"{pre}{stamp}.json" if n == 1 else f"{pre}{stamp}-{n}.json")
    shutil.copy2(live, dest)
    olds = sorted(d.glob(pre + "*.json"), key=_bkey)
    for q in olds[:-KEEP_BACKUPS]:
        q.unlink(missing_ok=True)
    return dest


def restore_atlas(kind, backup=None, root=None, src=None):
    """put a backup (file name / path; default the newest) back over the live file, after backing the current state up first; returns the restored backup path"""
    import shutil
    live = Path(src) if src else atlas_path(kind, root)
    d, pre = (live.parent, live.stem + ".backup-") if src else _backup_glob(kind, root)
    have = sorted(d.glob(pre + "*.json"), key=_bkey)
    if backup:
        b = Path(backup)
        b = b if b.is_file() else d / b.name
    else:
        b = have[-1] if have else None
    if not b or not b.is_file():
        raise FileNotFoundError("no such backup: %s" % (backup or "(none exist)"))
    pre_restore = backup_atlas(kind, root, src) if live.exists() else None
    shutil.copy2(b, live)
    return b


# ---------------------------------------------------------------- CLI
def _opt(args, name, default=None):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            v = args[i + 1]
            del args[i:i + 2]
            return v
    return default


def _flag(args, name):
    if name in args:
        args.remove(name)
        return True
    return False


def _parse_features(s, fs):
    out = {}
    for part in (s or "").split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            k = k.strip().lower()
            if k not in fs:
                raise SystemExit("unknown feature %r (use %s)" % (k, ", ".join(fs)))
            out[k] = max(0.0, min(1.0, float(v)))
    return out


def add_node(atlas, name, family, features, picture, voice, by="claude", aka=None, force=False, beats=None):
    """grow the map; refuses a duplicate (same name / id, a >= 0.9 fuzzy name match, or features within 0.1 of an existing node) unless force"""
    nid = slug(name)
    if not nid:
        raise ValueError("empty name")
    if nid in by_id(atlas):
        raise ValueError("node %s already exists" % nid)
    hit = near(atlas, name, 1)
    if not force and hit and hit[0][1] >= 0.9:
        raise ValueError("%r looks like the existing node %s (%.2f); reuse it or pass --force" % (name, hit[0][0], hit[0][1]))
    feats = {k: round(float(features.get(k, 0.0)), 2) for k in feats_of(atlas)}
    node = {"id": nid, "name": name, "family": family, "picture": picture, "voice": voice, "features": feats, "x": 0.0, "y": 0.0, "added_by": by, "ts": now()}
    if beats:
        node["beats"] = beats
    if aka:
        node["aka"] = aka
    if not force:
        for n in atlas["nodes"]:
            if fdist(node, n) < 0.10:
                raise ValueError("features are nearly identical to %s; extend that node's picture instead, or pass --force" % n["id"])
    place(atlas, node)
    atlas["nodes"].append(node)
    atlas["edges"].extend(knn_edges(atlas, {nid}))
    connect(atlas)
    return node


def main(argv, kind=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = list(argv)
    if kind is None:
        if args and args[0] in KINDS:
            kind = args.pop(0)
        else:
            raise SystemExit("usage: atlas.py <formality|emotion> layout|add|reinforce|describe|near|path|list|requests|resolve ...")
    f = _opt(args, "--file")
    cmd = args.pop(0) if args else "list"
    atlas = load(f, kind)
    atlas["kind"] = kind
    fs = feats_of(atlas)
    if cmd == "layout":
        rebuild = _flag(args, "--edges") or not atlas.get("edges")
        layout(atlas)
        if rebuild:
            rebuild_edges(atlas)
        save(atlas, f)
        print("laid out %d nodes%s, %d edges" % (len(atlas["nodes"]), " (edges rebuilt)" if rebuild else "", len(atlas["edges"])))
    elif cmd == "add":
        name = args.pop(0)
        family, picture, voice = _opt(args, "--family", "added"), _opt(args, "--picture", ""), _opt(args, "--voice", "")
        beats = _opt(args, "--beats")
        feats, by = _parse_features(_opt(args, "--features", ""), fs), _opt(args, "--by", "claude")
        aka, forreq, force = _opt(args, "--aka"), _opt(args, "--for"), _flag(args, "--force")
        if not feats or not picture or not voice:
            raise SystemExit("add needs --features, --picture and --voice")
        node = add_node(atlas, name, family, feats, picture, voice, by, [a.strip() for a in aka.split(",")] if aka else None, force, beats)
        save(atlas, f)
        n = resolve_request(ROOT, forreq or name, node["id"])
        near_ids = [e["a"] if e["b"] == node["id"] else e["b"] for e in atlas["edges"] if node["id"] in (e["a"], e["b"])]
        print("added %s at (%.3f, %.3f), wired to %s%s" % (node["id"], node["x"], node["y"], ", ".join(near_ids), "; closed %d request(s)" % n if n else ""))
    elif cmd == "reinforce":
        a, b = args[0], args[1]
        d = float(args[2]) if len(args) > 2 else 0.05
        e = reinforce(atlas, a, b, d)
        save(atlas, f)
        print("%s - %s  w=%.3f  uses=%d" % (e["a"], e["b"], e["w"], e["uses"]))
    elif cmd == "reset":
        rm = _flag(args, "--remove-added")
        bk = backup_atlas(kind, None, f) if f else backup_atlas(kind)
        r = reset_atlas(atlas, rm)
        save(atlas, f)
        print("reset %s atlas to factory wiring: %d synapses, removed %s, kept added %s; backup %s" % (kind, len(atlas["edges"]), r["removed_nodes"] or "none", r["kept_added"] or "none", bk.name))
    elif cmd == "import-story":
        src = Path(args.pop(0))
        nofeat = _flag(args, "--no-features")
        bk = backup_atlas(kind, None, f) if f else backup_atlas(kind)
        r = import_story(atlas, json.loads(src.read_text(encoding="utf-8")), not nofeat)
        save(atlas, f)
        print("%s atlas: %d story links (%d skipped: unknown ids), %d feature fixes%s; %d synapses (%d story), every node has >= %d; backup %s"
              % (kind, r["links"], r["skipped"], len(r["fixed"]), " (re-laid out)" if r["fixed"] else "", r["edges"], r["story_edges"], r["min_degree"], bk.name))
        for nid, k, a, b in r["fixed"]:
            print("  %s.%s %s -> %s" % (nid, k, a, b))
    elif cmd == "backups":
        for b in (list_backups(kind) if not f else sorted(Path(f).parent.glob(Path(f).stem + ".backup-*.json"))):
            print(b.name)
    elif cmd == "restore":
        b = restore_atlas(kind, args[0] if args else None, None, f)
        print("restored %s (the previous state was backed up first)" % b.name)
    elif cmd == "describe":
        print(describe_value(json.loads(args[0]), atlas))
    elif cmd == "near":
        for i, s in near(atlas, " ".join(args), 5):
            print("%.2f  %s  (%s)" % (s, i, by_id(atlas)[i]["name"]))
    elif cmd == "path":
        print(" -> ".join(path(atlas, args[0], args[1])))
    elif cmd == "requests":
        for r in open_requests(atlas=kind):
            print("%s  %s  %r" % (r["id"], r["ts"], r["text"]))
    elif cmd == "resolve":
        print("closed %d" % resolve_request(ROOT, args[0], args[1] if len(args) > 1 else None))
    else:
        fam = {}
        for n in atlas["nodes"]:
            fam.setdefault(n["family"], []).append(n["id"])
        for k, v in fam.items():
            print("%s (%d): %s" % (k, len(v), ", ".join(v)))
        print("%d nodes, %d edges" % (len(atlas["nodes"]), len(atlas["edges"])))


if __name__ == "__main__":
    main(sys.argv[1:])
