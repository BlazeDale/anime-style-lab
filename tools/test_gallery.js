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
(0, eval)(code + "\n;globalThis.__t = {get FB(){return FB}, set FB(v){FB=v}, overview, layerPage, videosPage, imagesPage, allImages, vidChip, byId, DATA, get VIDS(){return VIDS}, store, fbKey, atCandidates, imgRef, lineageText, qTerms, journeysPage, journeyPage, get JRN(){return JRN}, get jById(){return jById}, set JR(v){JR=v}, set BL(v){BL=v}, fbBar, isBlurred, jStartBox, set jOpen(v){jOpen=v}, layerNav, fdef, castMatches, get CASTOPTS(){return CASTOPTS}, castName, parseSubj, subjShort, toolbar, styleMark, subjMatch, treePage, treeAncestors, treeDescendants, treeSetBox, get TREE_EDGES(){return TREE_EDGES}};");
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
