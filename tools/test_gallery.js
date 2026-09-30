// Run the gallery's script against a stub DOM and check filter / layer logic with real data.
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const code = html.match(/<script>([\s\S]*)<\/script>/)[1];

const el = () => {
  const e = { innerHTML: "", textContent: "", style: {}, dataset: {}, value: "", children: [],
    classList: { _s: new Set(), add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, f) { (f ?? !this._s.has(c)) ? this._s.add(c) : this._s.delete(c); }, contains(c) { return this._s.has(c); } },
    querySelector: () => el(), querySelectorAll: () => [], addEventListener() {}, contains: () => false,
    focus() {}, blur() {}, scrollIntoView() {}, setSelectionRange() {} };
  return e;
};
const els = {};
global.document = { querySelector: s => (els[s] = els[s] || el()), querySelectorAll: () => [], addEventListener() {},
  body: el(), documentElement: { setAttribute() {}, removeAttribute() {}, style: { setProperty() {} } }, activeElement: null };
global.window = global; global.localStorage = { _d: {}, getItem(k) { return this._d[k] ?? null; }, setItem(k, v) { this._d[k] = v; } };
global.sessionStorage = global.localStorage;
global.location = { hash: "", protocol: "http:" };
global.fetch = () => new Promise(() => {}); global.setInterval = () => 0; global.scrollTo = () => {}; global.scrollY = 0;
global.MutationObserver = class { observe() {} }; global.ResizeObserver = class { observe() {} }; global.CSS = { escape: s => s };
global.getComputedStyle = () => ({ backgroundColor: "" }); global.addEventListener = () => {};

// expose top-level const/let bindings for the checks below
(0, eval)(code + "\n;globalThis.__t = {get FB(){return FB}, set FB(v){FB=v}, overview, layerPage, videosPage, imagesPage, allImages, vidChip, byId, DATA, get VIDS(){return VIDS}, store, fbKey, atCandidates, imgRef, lineageText, qTerms, journeysPage, journeyPage, get JRN(){return JRN}, get jById(){return jById}, set JR(v){JR=v}, set BL(v){BL=v}, fbBar, isBlurred, jStartBox, set jOpen(v){jOpen=v}, layerNav, fdef, castMatches, get CASTOPTS(){return CASTOPTS}, castName, parseSubj, subjShort, toolbar, styleMark, subjMatch, treePage, treeAncestors, treeDescendants, treeSetBox, rectToFractions, applyDrag, cropThumb, refThumb, get TREE_EDGES(){return TREE_EDGES}};\n;Object.defineProperties(globalThis.__t, Object.getOwnPropertyDescriptors({decideSwipe, shouldPreventMove, castNoteParse, castNoteBuild, CAST_TYPES, castTyped, castTip, get VIDS(){return VIDS}, set VIDS(v){VIDS=v}, get JRN(){return JRN}, set JRN(v){JRN=v}, get jById(){return jById}, set jById(v){jById=v}, get JR(){return JR}, journeyReel, clipPanel, sceneClipBox, sceneClipChip, animBtn, animBox, jplayBtn, clipVideoFor, JCLIP, set CM(v){CM=v}, jAnimOpen}));");
const T = globalThis.__t;
const ok = (c, m) => { console.log((c ? "PASS " : "FAIL ") + m); if (!c) process.exitCode = 1; };
const clearFilters = () => { ["fcast", "fg", "fgenre"].forEach(k => T.store.set(k, "all"));
  ["heartOnly", "evolvedOnly", "hideNope", "renderedOnly", "upOnly", "fitOnly"].forEach(k => T.store.set(k, false)); T.store.set("q", ""); };

// 1) baseline: survey renders, contains every lineage
let out = T.overview();
ok(out.includes('class="strips'), "survey strips render");
["001-plain-anime", "002-90s-cel", "003-ghibli-watercolor", "004-shinkai-film", "005-gacha-keyart",
 "006-manga-screentone", "007-chibi", "008-trigger-flat"].forEach(id => ok(out.includes(id), `survey shows ${id}`));

// 2) ❤ filter shows a loved image and hides an unloved lineage
T.FB = { "evolutions/001-plain-anime/v01/seed1001.png": { actions: ["love"], status: "pending" } };
T.store.set("heartOnly", true);
out = T.overview();
ok(out.includes("001-plain-anime/v01/seed1001.png"), "loved image shown under ❤ filter");
ok(!out.includes("002-90s-cel/"), "unloved lineage hidden under ❤ filter");
T.store.set("heartOnly", false);
T.FB = {};

// 3) 👎 filter: a noped v02 image falls back to the same character's v01 render (same slot key)
T.FB = { "evolutions/001-plain-anime/v02/f-modern_seed1001.png": { actions: ["nope"], status: "pending" } };
T.store.set("hideNope", true);
out = T.overview();
ok(!out.includes("001-plain-anime/v02/f-modern_seed1001.png"), "noped image hidden");
ok(out.includes("001-plain-anime/v01/seed1001.png"), "cell falls back to the older un-noped render of the same character");
T.store.set("hideNope", false);
T.FB = {};

// 4) search: matches title/goal text; multi-word = AND; empty result shows a message
clearFilters();
T.store.set("q", "ghibli");
out = T.overview();
ok(out.includes("003-ghibli-watercolor") && !out.includes("001-plain-anime"), "search 'ghibli' shows only the Ghibli style");
T.store.set("q", "flat trigger");
out = T.overview();
ok(out.includes("008-trigger-flat") && !out.includes("003-ghibli-watercolor"), "multi-word search matches the goal text (AND)");
T.store.set("q", "zzzz-nothing");
ok(T.overview().includes("No styles match"), "empty search result message");
T.store.set("q", "");

// 5) evolved-only filter: nothing in this survey-only project has been evolved yet
T.store.set("evolvedOnly", true);
out = T.overview();
["001-plain-anime", "002-90s-cel", "003-ghibli-watercolor", "004-shinkai-film", "005-gacha-keyart",
 "006-manga-screentone", "007-chibi", "008-trigger-flat"].forEach(id => ok(!out.includes(id + "/"), `evolved-only hides ${id} (nothing evolved yet)`));
T.store.set("evolvedOnly", false);

// 6) clear-filters button appears only when something is filtered
T.store.set("heartOnly", true);
ok(T.overview().includes("data-clearf"), "clear-filters button shows when a filter is on");
T.store.set("heartOnly", false);
ok(!T.overview().includes("data-clearf"), "clear-filters button hidden when nothing is filtered");

// 7) images page: every rendered image (8 lineages x 8 images = 64), search narrows, evolved-only empties it
clearFilters();
const nAll = T.allImages().length;
ok(nAll === 64, `allImages sees every rendered image (${nAll}, expected 64)`);
ok((T.imagesPage().match(/data-grid="all"/g) || []).length === nAll, "images page shows every rendered image");
T.store.set("q", "chibi");
const nChibi = (T.imagesPage().match(/data-grid="all"/g) || []).length;
ok(nChibi > 0 && nChibi < nAll, "image search narrows (chibi)");
T.store.set("q", ""); T.store.set("evolvedOnly", true);
ok(!T.imagesPage().includes('data-grid="all"'), "evolved-only on the images page hides everything (survey only)");
T.store.set("evolvedOnly", false);

// 8) cast / gender / genre toolbar: this project only has the plain "Survey six" cast, 3 genres, no extras
clearFilters();
let ip = T.imagesPage();
ok(T.CASTOPTS.length === 2 && T.CASTOPTS.some(o => o.v === "survey" && o.lab === "Survey six"), "cast picker offers just All + Survey six (no per-set casts rendered)");
const tb = ip;
const gsel = (tb.match(/<select data-fsel="fgenre"[\s\S]*?<\/select>/) || [""])[0];
ok((gsel.match(/<option/g) || []).length === 4, "genre dropdown offers exactly All + the 3 base genres (modern/sci-fi/fantasy)");
ok((tb.match(/data-fset=/g) || []).length === 3, "toolbar shows the 3 gender buttons (All/♀/♂)");
T.store.set("fg", "f");
const nF = (T.imagesPage().match(/data-grid="all"/g) || []).length;
T.store.set("fg", "m");
const nM = (T.imagesPage().match(/data-grid="all"/g) || []).length;
ok(nF === 40 && nM === 24 && nF + nM === nAll, `gender filter splits ${nAll} images into ${nF} female-cast + ${nM} male-cast`);
T.store.set("fg", "all"); T.store.set("fgenre", "fantasy");
const nFantasy = (T.imagesPage().match(/data-grid="all"/g) || []).length;
ok(nFantasy === 16, `genre filter narrows to fantasy-subject images (${nFantasy}, expected 16)`);
T.store.set("fgenre", "all");
ok((T.imagesPage().match(/data-grid="all"/g) || []).length === nAll, "clearing filters restores every image");

// 9) @ references in the tray: search finds images by style/character words and returns short refs
clearFilters();
{
  const hits = T.atCandidates("plain baseline");
  ok(hits.length > 0 && hits.every(h => h.ref.startsWith("@001/")), "@ search 'plain baseline' finds only the plain-anime lineage's images");
  ok(T.atCandidates("").length === 40, "@ with no query lists the first 40 candidates (of 64)");
}

// 10) search covers the full prompts: character descriptions (not just titles), and "quoted phrases" stay one term
{
  const sailors = T.allImages().filter(it => it.text.includes("sailor uniform"));
  // every v01 used this character directly (2 seeds) before v02 generalized to the 6-subject template (adds 1 f-modern each): 8 styles x 3
  ok(sailors.length === 24, "image search finds a character by words from its full description ('sailor uniform', 24 renders across v01 + v02 f-modern)");
  ok(T.lineageText(T.byId["005-gacha-keyart"]).includes("mobile-game splash art"), "style search text includes the lineage's goal");
  ok(JSON.stringify(T.qTerms('red "flowing cape" knight')) === JSON.stringify(["red", "flowing cape", "knight"]), "quoted phrase stays one search term");
}

// 11) 👍/❤ marks a whole style (not a request; applied immediately, no Send needed)
{
  T.FB = {};
  ok(T.styleMark("003-ghibli-watercolor") === "", "a style starts unmarked");
  T.FB = { "style:003-ghibli-watercolor": { actions: ["love"], status: "done" } };
  ok(T.styleMark("003-ghibli-watercolor") === "love", "a loved style reports 'love'");
  T.FB = {};
}

// 12) blur marks (server-side, independent of any render data)
T.BL = { "evolutions/001-plain-anime/v02/f-modern_seed1001.png": true };
ok(T.isBlurred("../evolutions/001-plain-anime/v02/f-modern_seed1001.png"), "blur mark matches the gallery-relative src");
ok(T.fbBar("../evolutions/001-plain-anime/v02/f-modern_seed1001.png", "x").includes('class="blurb on"'), "blurred image shows 🌫 as on");
T.BL = {};

// 13) journeys / videos pages: no journeys or clips exist in this project yet, but the pages must still render cleanly
ok(T.JRN.length === 0, "no journeys in this project yet");
out = T.journeysPage();
ok(out.includes("Journeys") && !out.includes("undefined"), "journeys page renders its empty state without crashing");
out = T.videosPage(null);
ok(T.VIDS.length === 0 && out.includes("0 clips"), "videos page renders with zero clips");

// 14) evolution layer page: none exist yet, so it shows the "doesn't exist yet" message
out = T.layerPage(1, null, null);
ok(out.includes("doesn't exist yet"), "evolution layer 1 doesn't exist yet (survey-only project)");

// 15) family tree page: a survey lineage has no ancestors and no descendant evolution sets
{
  const out2 = T.treePage("003-ghibli-watercolor");
  ok(out2.includes("Ghibli-esque watercolor"), "tree page titles the focus lineage");
  ok(out2.includes('class="tnode tfocus"'), "focus renders as the larger centered card");
  const ancCount = (T.treeAncestors(T.byId["003-ghibli-watercolor"]).nodes || []).length;
  ok(ancCount === 0, "a survey lineage has no ancestors to walk up to (nothing evolved from anything yet)");
  ok(T.treePage("999-does-not-exist").includes("Unknown lineage"), "unknown lineage id shows an empty-state message");
}

// journey reel + clips + Animate chapter (synthetic journey: no project content needed)
{
  const img = n => `journeys/900-fixture/ch01/${n}.png`;
  const mk = (id, image, created, extra = {}) => ({src: `../journeys/900-fixture/ch01/${id}.mp4`, poster: "../" + image, image, journey: true, created, engine: "fasth3", tag: "reel", ...extra});
  const J = {id: "900-fixture", title: "Fixture", name: "Iris", source: "evolutions/001-plain-anime/v01/seed1001.png", refs: [],
    chapters: [{id: "ch01", title: "One", scenes: [{id: "s1", src: "../" + img("s1"), caption: "a"}, {id: "s2", src: "../" + img("s2"), caption: "b"}]}]};
  T.JRN = [J]; T.jById = {[J.id]: J};
  const old1 = mk("s1_old", img("s1"), 1), new1 = mk("s1_new", img("s1"), 3), loved1 = mk("s1_loved", img("s1"), 2), only2 = mk("s2_a", img("s2"), 5);
  T.VIDS = [old1, new1, loved1, only2];
  T.FB = {};
  let reel = T.journeyReel(J);
  ok(reel.length === 2 && reel[0].src === new1.src && reel[0].sc === "s1", "reel: no marks = the newest clip of each scene, in scene order");
  T.FB = {[T.fbKey(loved1.src)]: {actions: ["love"], status: "done"}};
  reel = T.journeyReel(J);
  ok(reel[0].src === loved1.src, "reel: a loved clip wins over a newer unmarked one");
  T.FB = {[T.fbKey(new1.src)]: {actions: ["nope"], status: "done"}, [T.fbKey(loved1.src)]: {actions: ["nope"], status: "done"}};
  reel = T.journeyReel(J);
  ok(reel[0].src === old1.src, "reel: noped clips are skipped, falling back to the newest non-noped one");
  T.FB = {[T.fbKey(only2.src)]: {actions: ["nope"], status: "done"}};
  ok(T.journeyReel(J).length === 1, "reel: a scene whose only clip is noped drops out of the reel");
  T.FB = {};
  ok(reel.every(r => r.cap0 && r.cap0.includes("Ch 1")), "reel entries carry a caption for their mark/comment panel");
  ok(T.jplayBtn(J).includes('data-jplay="900-fixture"') && T.jplayBtn({...J, chapters: [{id: "ch01", scenes: []}]}) === "", "play button only when the journey has clips");
  const pg0 = T.journeyPage(J.id);
  ok(pg0.includes('data-jclips="' + img("s1") + '"') && !pg0.includes("data-jclipv="), "scene with clips: chip opens the inline player (closed by default)");
  T.JCLIP[img("s1")] = new1.src;
  const pg1 = T.journeyPage(J.id), tg = "image:" + T.fbKey(new1.src);
  ok(pg1.includes("data-jclipv=") && pg1.includes(`data-draft="${tg}"`), "open scene clip shows the player and the clip's comment box");
  ok(/data-fb="love"[^>]*data-src="[^"]*\.mp4"/.test(pg1) && pg1.includes('data-fb="nope"'), "inline clip panel has love / nope on the clip");
  ok(pg1.includes('data-jclipsel='), "several clips on a scene show a clip picker");
  ok(T.clipPanel(new1.src, "x").includes(`data-cpost="${tg}"`), "clipPanel = marks + thread");
  delete T.JCLIP[img("s1")];
  // Animate chapter button: idle -> requested (open request) -> box for the note
  ok(pg0.includes('data-janim="900-fixture/ch01"'), "chapter header has an Animate chapter button");
  ok(T.animBtn(J, J.chapters[0]).includes("Animate chapter"), "animBtn idle label");
  T.JR.push({id: "j1", kind: "animate", journey: J.id, chapter: "ch01", status: "sent", ts: "t", text: ""});
  ok(T.animBtn(J, J.chapters[0]).includes("Animation requested") && T.animBtn(J, J.chapters[0]).includes("disabled"), "open animate request disables the button");
  T.JR.length = 0;
  T.jAnimOpen.add("900-fixture/ch01");
  ok(T.animBox(J, J.chapters[0]).includes('data-janimsend="900-fixture/ch01"'), "animBox shows the note form once opened");
  T.jAnimOpen.clear();
  // a comment box knows nothing about a video unless it sits inside the reel or an inline clip box
  ok(T.clipVideoFor(null) === null && T.clipVideoFor({}) === null, "clipVideoFor: nothing without a container");
  T.VIDS = []; T.JRN = []; T.jById = {}; T.FB = {};
}

// reference crop: pure math + rendering
{
  const f = T.rectToFractions, near = (a, b) => Array.isArray(a) && a.every((v, i) => Math.abs(v - b[i]) < 1e-6);
  ok(near(f(100, 50, 300, 250, 400, 500), [0.25, 0.1, 0.75, 0.5]), "rectToFractions: pixel box -> fractions");
  ok(near(f(300, 250, 100, 50, 400, 500), [0.25, 0.1, 0.75, 0.5]), "rectToFractions: drag from the bottom-right corner is normalised");
  ok(near(f(-50, -20, 500, 900, 400, 500), [0, 0, 1, 1]), "rectToFractions: clamped to the picture");
  ok(f(10, 10, 12, 200, 400, 500) === null && f(10, 10, 200, 12, 400, 500) === null, "rectToFractions: under 2% either way is refused");
  ok(f(NaN, 0, 10, 10, 400, 500) === null && f(0, 0, 10, 10, 0, 500) === null, "rectToFractions: NaN / zero-size picture refused");
  const d = T.applyDrag, W = 400, H = 300;
  const r0 = {x0: 100, y0: 100, x1: 200, y1: 180};
  ok(JSON.stringify(d("new", null, {x: 50, y: 60}, {x: 20, y: 500}, W, H)) === JSON.stringify({x0: 20, y0: 60, x1: 50, y1: 300}), "applyDrag new: normalised + clamped");
  const mv = d("move", r0, {x: 150, y: 140}, {x: 1000, y: 140}, W, H);
  ok(mv.x1 === W && mv.x1 - mv.x0 === 100 && mv.y0 === 100, "applyDrag move: keeps its size, stops at the edge");
  const se = d("se", r0, {x: 200, y: 180}, {x: 260, y: 210}, W, H);
  ok(se.x0 === 100 && se.y0 === 100 && se.x1 === 260 && se.y1 === 210, "applyDrag se handle grows the box");
  const fl = d("w", r0, {x: 100, y: 140}, {x: 300, y: 140}, W, H);
  ok(fl.x0 === 200 && fl.x1 === 300 && fl.y0 === 100, "applyDrag w handle dragged past the far edge flips instead of inverting");
  const g = T.cropThumb([0.25, 0.1, 0.5 + 0.25, 0.5], 1.6, 64);
  ok(Math.abs(g.w - 64 * 0.5 * 1.6 / 0.4) < 1e-6 && Math.abs(g.imgH - 160) < 1e-6 && Math.abs(g.left + 0.25 * g.imgW) < 1e-6, "cropThumb geometry");
  const src = "journeys/901-crop/ch01/s1.png";
  const jn = {id: "901-crop", title: "Crop fixture", name: "Iris", source: "evolutions/001-plain-anime/v01/seed1001.png", refs: [src],
    cast: [{name: "Bram", look: "a tall guard"}], ref_crop: {[src]: [0.2, 0.1, 0.6, 0.5]}, ref_notes: {[src]: "the lantern"}, ref_for: {[src]: "Bram"},
    chapters: [{id: "ch01", title: "One", scenes: [{id: "s1", src: "../" + src, caption: "a"}]}]};
  T.JRN = [jn]; T.jById = {[jn.id]: jn};
  const t = T.refThumb(jn, src);
  ok(t.includes('data-crop="0.2,0.1,0.6,0.5"') && t.includes("data-jcrop"), "ref thumbnail shows the crop and a crop button");
  ok(t.includes('value="the lantern"') && t.includes('<option value="Bram" selected>') && t.includes("data-jrsave"), "ref thumbnail carries its note and 'use for' target");
  const page = T.journeyPage(jn.id);
  ok(page.includes("data-jcrop") && page.includes("cropFit(this)") && page.includes("data-jrf"), "journey page renders crop + note controls for the refs");
  T.decideSwipe && T.decideSwipe(0, -90, false, 0, false);
  T.JRN = []; T.jById = {};
}

// swipe up / down raises / lowers the lightbox details on touch
{
  const d = T.decideSwipe;
  ok(d(5, -90, false, 0, false) === "open", "swipe up with the panel closed opens it");
  ok(d(5, 90, true, 0, false) === "close", "swipe down with the panel open (scrolled to top) closes it");
  ok(d(5, 90, true, 40, false) === null, "swipe down inside a scrolled panel just scrolls");
  ok(d(5, 90, false, 0, false) === null && d(5, -90, true, 0, false) === null, "no-op when already in that state");
  ok(d(0, -30, false, 0, false) === null, "under 50px is not a swipe");
  ok(d(80, -90, false, 0, false) === null, "diagonal swipe (|dy| <= 1.5|dx|) ignored");
  ok(d(0, -90, false, 0, true) === null, "ignored while zoomed");
  const pm = T.shouldPreventMove;
  ok(pm(2, 30, false, 0, false, 1, false) && pm(2, -30, false, 0, false, 1, false), "closed panel: vertical drags are cancelled (no pull-to-refresh)");
  ok(pm(2, 30, true, 0, false, 1, false) && !pm(2, 30, true, 50, false, 1, false) && !pm(2, -30, true, 0, false, 1, false), "open panel: only a down-drag at the top is cancelled, the rest scrolls");
  ok(!pm(2, 30, false, 0, true, 1, false) && !pm(2, 30, false, 0, false, 2, false) && !pm(2, 30, false, 0, false, 1, true) && !pm(40, 30, false, 0, false, 1, false), "not cancelled when zoomed, multi-touch, typing or horizontal");
}
// 👥 popover: the chip choice rides in the mark's note as one line
{
  const P = T.castNoteParse, B = T.castNoteBuild;
  ok(B("", ["Women", "Sci-fi"], "with cats") === "👥 types: Women, Sci-fi — with cats", "cast note: chips + text");
  ok(B("", ["Men"], "") === "👥 types: Men", "cast note: chips only");
  ok(B("", [], "only text") === "👥 types: — only text", "cast note: text only");
  ok(B("", [], "  ") === "", "cast note: empty builds nothing");
  const n = B("make it moody", ["Horror"], "a\nb");
  ok(n === "👥 types: Horror — a b\nmake it moody", "cast note merges with existing text, newlines flattened: " + JSON.stringify(n));
  const q = P(n);
  ok(q.types.length === 1 && q.types[0] === "Horror" && q.text === "a b" && q.rest === "make it moody", "cast note round-trips");
  const n2 = B(n, ["Men", "Undead"], "new");
  ok(n2 === "👥 types: Men, Undead — new\nmake it moody", "re-saving replaces the 👥 line, keeps other text");
  ok(B(n2, [], "") === "make it moody", "removing keeps the other note text");
  ok(P("just a note").types.length === 0 && P(undefined).rest === "", "parse: no 👥 line");
  ok(T.CAST_TYPES[0] === "Same kind as this image" && new Set(T.CAST_TYPES).size === T.CAST_TYPES.length, "cast types: default first, no duplicates");
  ok(T.castTyped({actions: ["cast"], note: n}, "cast") === " typed" && T.castTyped({actions: ["cast"], note: "x"}, "cast") === "" && T.castTyped({actions: ["love"], note: n}, "love") === "", "typed dot only on a 👥 mark with a 👥 line");
  ok(T.castTip({actions: ["cast"], note: n}, "tip").includes("Horror — a b") && T.castTip({}, "tip") === "tip", "cast tooltip shows the saved choice");
}
