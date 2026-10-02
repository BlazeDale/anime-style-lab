// Run the gallery's script against a stub DOM and check filter / layer logic.
const fs = require("fs");
const html = fs.readFileSync(process.argv[2], "utf8");
const code = html.match(/<script>([\s\S]*)<\/script>/)[1];

const el = () => {
  const e = { innerHTML: "", textContent: "", style: {}, dataset: {}, value: "", children: [],
    classList: { _s: new Set(), add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, f) { (f ?? !this._s.has(c)) ? this._s.add(c) : this._s.delete(c); }, contains(c) { return this._s.has(c); } },
    querySelector: () => el(), querySelectorAll: () => [], addEventListener() {}, contains: () => false, setAttribute() {}, removeAttribute() {}, getAttribute() { return null; },
    focus() {}, blur() {}, scrollIntoView() {}, setSelectionRange() {} };
  return e;
};
const els = {};
global.document = { querySelector: s => (els[s] = els[s] || el()), querySelectorAll: () => [], addEventListener() {},
  body: el(), documentElement: { setAttribute() {}, removeAttribute() {}, style: { setProperty() {} } }, activeElement: null, activeElement: null };
global.window = global; global.localStorage = { _d: {}, getItem(k) { return this._d[k] ?? null; }, setItem(k, v) { this._d[k] = v; }, removeItem(k) { delete this._d[k]; } };
global.sessionStorage = global.localStorage;
global.location = { hash: "", protocol: "http:" };
global.fetch = () => new Promise(() => {}); global.setInterval = () => 0; global.scrollTo = () => {}; global.scrollY = 0;
global.MutationObserver = class { observe() {} }; global.ResizeObserver = class { observe() {} }; global.CSS = { escape: s => s };
global.getComputedStyle = () => ({ backgroundColor: "" }); global.addEventListener = () => {};

// expose top-level const/let bindings for the checks below
(0, eval)(code + "\n;globalThis.__t = {get FB(){return FB},set FB(v){FB=v},overview,layerPage,videosPage,imagesPage,allImages,vidChip,byId,DATA,get VIDS(){return VIDS},store,fbKey,atCandidates,imgRef,lineageText,qTerms,journeysPage,journeyPage,get JRN(){return JRN},get jById(){return jById},set JR(v){JR=v},set BL(v){BL=v},fbBar,isBlurred,jStartBox,set jOpen(v){jOpen=v},jAnimOpen,layerNav,fdef,castMatches,get CASTOPTS(){return CASTOPTS},castName,parseSubj,treePage,treeAncestors,treeDescendants,treeSetBox,clipPanel,sceneClipChip,sceneClipBox,JCLIP,journeyReel,castNoteParse,castNoteBuild,CAST_TYPES,decideSwipe,shouldPreventMove,rectToFractions,applyDrag,cropThumb,refThumb,refCropRect,refEditOpen,mvGenBox,get TREE_EDGES(){return TREE_EDGES},fmtT,parseT,mvTimeToX,mvXToTime,mvRegion,lyricLines,mvListPage,mvPage,mvMerge,mvStatus,mvScenesOf,headlineHtml,headlinesOn,headlineBtn,mvMarkList,mvEditHtml,MVT,refOid,refOwner,get MVS(){return MVS},set MVS(v){MVS=v},get mvById(){return mvById},set mvById(v){mvById=v},set MVR(v){MVR=v},mvSortDrop,mvDropZone,mvEdgeHit,mvShift,mvSnapBeat,fixAreaBtn,rerollBtn,upscaleBtn,refitCtl,clipPrompt,coverBtn,mvLoupeSpan,mvStemColor,mvCutSection,mvCutRows,mvCutBusy,mvLaneGeom,mvStemsInfo,mvStemsBar,mvLanesOn,mvPaint,MV_STEM_COL,mvLyricBlocks,mvLyricHit,mvPickLyric,mvLyricsBar,mvHasLyrics,mvGeo,mvReel,mvPlayBtn,sceneClips,revsOf,revChip,revBtn,revViewHtml,revOpen,revPick,revRestore,RV,get REVS(){return REVS},get MTIMES(){return MTIMES},get EXPL(){return EXPL},set EXPL(v){EXPL=v; explById=Object.fromEntries(v.map(e=>[e.id,e]))},EXST,XC,xApply,exploreBar,exploreListPage,explorePage,xpTimeline,xpLayerHtml,xpAr,xpHold,xTint,xFade,xFmt,XF_RIM,XA,xaSet,xaValueAt,xaPath,xaFind,xaScore,xaPlaceLabels,xaNodeAlpha,xaEdgeGrow,xmDraw,xMapHtml,xmPlan,xfNeutral,xfNorm,xfWord,xfHint,xfCap,xfLevelWord,xTuneHtml,xeNeutral,XAF,XAE,XE_LEGACY,xvNorm,xeNorm,xeWord,xeHint,xeIntensityWord,xdNorm,xdSnap,xdAngle,xdFromPointer,xdWord,xdHint,xdStops,get XMAT(){return XMAT},xDialHtml,xcoresClean,xcoresAdd,xcoresEdit,xcoresRemove,xcoresResolve,xcoresMove,xcoresWeightAt,xcoresSig,xcoresActive,xCoresHtml,xcSyncSaga,XCORE_MAX,xcDirty,xcAdopt,xcSetV,xcSetMaturity,xcAddCore,xpFrameRect,xpFit,atlasForceStep,xfFall,xfRamp,XF_R,xaP,xaWarped,xaPhysics,xaSettle,xaWarpLoad,xaWarpSave,xaWarpClear,xaResetStep,xMapBtnsHtml,xkSnap,xkAngle,xkDrag,xkWord,xkHint,isExpl,cmLabel,cmLink,get SAGAS(){return SAGAS},set SAGAS(v){SAGAS=v; sagaById=Object.fromEntries(v.map(g=>[g.id,g]))},sagaPage,sgTimeline,sgMore,sgStatus,sgText,sgShots,vnBeats,vnAction,vnBackAction,vnTypeMs,vnReadMs,vnBeatMs,vnTyped,vnColor,vnHue,XP,xpNext,xpPrev,xpGo,xpExtend,xpBoot,sgOpen,bindSaga,vnShowBeat,vnArm,vnAuto,xpArm,xpClose,castTyped,castTip,animBtn,animBox,jplayBtn,clipVideoFor,subjShort,toolbar,styleMark,subjMatch,get JR(){return JR},set CM(v){CM=v},set VIDS(v){VIDS=v},set JRN(v){JRN=v},set jById(v){jById=v}};");
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
ok((gsel.match(/<option/g) || []).length === 5, "genre dropdown offers exactly All + the 4 base genres (modern/sci-fi/fantasy/horror)");
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
  ok(page.includes("data-jcrop") && page.includes("refCropFit(this)") && page.includes("data-jrf"), "journey page renders crop + note controls for the refs");
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
  ok(T.CAST_TYPES[0] === "Same kind as this image" && new Set(T.CAST_TYPES).size === T.CAST_TYPES.length && T.CAST_TYPES.length === 17, "cast types: default first, no duplicates, 17 chips");
  ok(T.castTyped({actions: ["cast"], note: n}, "cast") === " typed" && T.castTyped({actions: ["cast"], note: "x"}, "cast") === "" && T.castTyped({actions: ["love"], note: n}, "love") === "", "typed dot only on a 👥 mark with a 👥 line");
  ok(T.castTip({actions: ["cast"], note: n}, "tip").includes("Horror — a b") && T.castTip({}, "tip") === "tip", "cast tooltip shows the saved choice");
}


// ======================================================================================================
// Synthetic fixtures: evolved lineages cloned from the starter styles (paths rewritten so the image keys stay
// consistent), a journey, clips. Nothing here depends on what a user has rendered.
// ======================================================================================================
const IMG = (lin, ver = "v02", name = "f-modern_seed1001.png") => `evolutions/${lin}/${ver}/${name}`;
const cloneLin = (srcId, id, title, depth, parents, stamp) => {
  const l = JSON.parse(JSON.stringify(T.byId[srcId]).split(srcId).join(id));
  Object.assign(l, {id, title, depth, parent_images: parents, parent: parents.length ? parents[0].split("/").slice(1, 3).join("/") : "", created: stamp, rendered: stamp});
  return l;
};
const FIX = [];  // lineages added by the fixtures (removed again after the tree checks)
const addLin = l => { T.DATA.push(l); T.byId[l.id] = l; FIX.push(l); return l; };
const dropFix = () => { FIX.forEach(l => { T.DATA.splice(T.DATA.indexOf(l), 1); delete T.byId[l.id]; }); FIX.length = 0; };
const P1 = IMG("001-plain-anime"), P3 = IMG("003-ghibli-watercolor");
// a crossbreed (two parents) and a second-generation child of it
const fake = addLin(cloneLin("001-plain-anime", "900-test-cross", "Test cross", 1, [P1, IMG("002-90s-cel")], 150));
const fake2 = addLin(cloneLin("002-90s-cel", "901-test-evo", "Test evo", 2, [IMG("900-test-cross", "v02", "m-modern_seed1001.png")], 160));
// a family tree: set A (3 siblings) -> set (2) -> a deep chain, an unrelated chain, and a cross between the two chains
addLin(cloneLin("001-plain-anime", "951-evo-a", "Evo A", 1, [P1], 100));
addLin(cloneLin("001-plain-anime", "952-evo-b", "Evo B", 1, [P1], 200));
addLin(cloneLin("001-plain-anime", "953-evo-c", "Evo C", 1, [P1], 300));
addLin(cloneLin("003-ghibli-watercolor", "957-other-a", "Other A", 1, [P3], 50));
addLin(cloneLin("001-plain-anime", "954-evo-d", "Evo D", 2, [IMG("951-evo-a")], 110));
addLin(cloneLin("001-plain-anime", "955-evo-e", "Evo E", 2, [IMG("951-evo-a")], 120));
addLin(cloneLin("001-plain-anime", "956-cross", "Cross X", 2, [IMG("951-evo-a"), IMG("957-other-a")], 130));
addLin(cloneLin("001-plain-anime", "958-deep-a", "Deep A", 3, [IMG("954-evo-d")], 140));
addLin(cloneLin("001-plain-anime", "959-deep-b", "Deep B", 4, [IMG("958-deep-a")], 150));
addLin(cloneLin("001-plain-anime", "960-deep-c", "Deep C", 5, [IMG("959-deep-b")], 160));

// 1) layer pages: crossbreed set, highlight, links
{
  let out = T.layerPage(1, P1, null);
  ok(out.includes("Evolution 1") && out.includes("crossbreed"), "layer 1 renders crossbreed set");
  const setHl = html => /class="[^"]*\bevset\b[^"]*\bhl\b/.test(html);
  ok(setHl(out), "set highlighted via ?from=parent");
  ok(out.includes(`../${P1}`) && out.includes(`../${IMG("002-90s-cel")}`), "both parent thumbnails shown");
  ok(out.includes('class="strips'), "set uses the tile strips");
  out = T.layerPage(2, null, "set:901-test-evo");
  ok(setHl(out) && out.includes("#/e/1?hl="), "layer 2 highlights set and links up to layer 1");
  out = T.overview();
  ok(!out.includes("900-test-cross"), "evolution sets excluded from survey");
  ok(out.includes("🌱"), "evolved parent image gets an evolution chip");
  out = T.layerPage(99, null, null);
  ok(out.includes("doesn't exist yet"), "empty layer message");
}

// 2) sort by date: one flow, newest created first, dates shown; layer pages order whole evolution sets
{
  const L1 = T.byId["001-plain-anime"], L8 = T.byId["008-trigger-flat"], c1 = L1.created, c8 = L8.created;
  L1.created = 1000; L8.created = 2000;
  T.store.set("sort", "new");
  let out = T.overview();
  ok(!out.includes('class="rmark"') && out.includes('class="sdate"'), "date sort drops round markers and shows dates");
  const order = [...out.matchAll(/href="#\/l\/(\d{3}-[^"]+)"/g)].map(m => m[1]);
  ok(order.indexOf("008-trigger-flat") < order.indexOf("001-plain-anime"), "newest style comes before the oldest");
  T.store.set("sort", "old");
  const order2 = [...T.overview().matchAll(/href="#\/l\/(\d{3}-[^"]+)"/g)].map(m => m[1]);
  ok(order2.indexOf("001-plain-anime") < order2.indexOf("008-trigger-flat"), "oldest-first reverses it");
  const setOrder = () => [...T.layerPage(1, null, null).matchAll(/href="#\/l\/(\d{3}-[^"]+)"/g)].map(m => m[1]);
  const byRendered = T.DATA.filter(l => l.depth === 1 && l.rendered).sort((a, b) => b.rendered - a.rendered);
  const newestL = byRendered[0].id, oldestL = byRendered[byRendered.length - 1].id;
  T.store.set("sort", "recent");
  let so = setOrder();
  ok(so.indexOf(newestL) < so.indexOf(oldestL), `recently rendered puts the newest set (${newestL}) before the oldest (${oldestL}) on a layer page`);
  T.store.set("sort", "old");
  so = setOrder();
  ok(so.indexOf(oldestL) < so.indexOf(newestL), "oldest-first reverses set order on a layer page");
  T.store.set("sort", "rounds");
  L1.created = c1; L8.created = c8;
}

// 3) evolved filter: only styles with evolutions
{
  T.store.set("evolvedOnly", true);
  const out = T.overview();
  const evolvedParents = new Set(T.DATA.flatMap(l => (l.parent_images || []).map(p => p.split("/")[1])));
  const plain = T.DATA.find(l => !l.depth && !evolvedParents.has(l.id) && l.versions.some(v => v.images.length));
  ok(out.includes("001-plain-anime") && plain && !out.includes(plain.id + "/"), `evolved filter keeps only evolved styles (hides ${plain && plain.id})`);
  T.store.set("evolvedOnly", false);
}

// the journey fixture used by the journey / music-video blocks below
const FJ = {id: "902-fixture", title: "Fixture journey", name: "Iris", source: "evolutions/001-plain-anime/v01/seed1001.png", source_cap: "Plain anime", character: "a ranger", world: "a quiet coast",
  cast: [], refs: ["evolutions/001-plain-anime/v01/seed1001.png", "journeys/902-fixture/ch01/s1.png"], ref_crop: {}, ref_notes: {}, ref_for: {},
  chapters: [{id: "ch01", title: "One", summary: "", direction: "", choices: [], scenes: [
    {id: "s1", shot: "wide", caption: "The coast at dawn", src: "../journeys/902-fixture/ch01/s1.png", dialogue: []},
    {id: "s2", shot: "close", caption: "A lantern", src: "../journeys/902-fixture/ch01/s2.png", dialogue: []}]}]};
T.JRN = [FJ]; T.jById = {[FJ.id]: FJ};

// 4) videos page: lists clips, search narrows, source image gets a 🎬 badge, groups per style (synthetic clips)
{
  const mkv = (lin, n, eng, created) => ({src: `../evolutions/${lin}/v02/f-modern_seed1001__${eng}_seed${n}.mp4`, poster: `../${IMG(lin)}`, image: IMG(lin), lineage: lin, version: "v02", title: T.byId[lin].title,
    journey: false, mv: null, depth: 0, subject: "f-modern", subject_label: "x", engine: eng, tag: "", prompt: "p", note: "", created});
  const vids = [mkv("001-plain-anime", 1, "fasth3", 1), mkv("001-plain-anime", 2, "ltx25", 2), mkv("002-90s-cel", 3, "ltxia2v", 3),
    mkv("003-ghibli-watercolor", 4, "fasth3", 4), mkv("003-ghibli-watercolor", 5, "h3turbo", 5), mkv("003-ghibli-watercolor", 6, "fasth3", 6)];
  const hv = T.VIDS; T.VIDS = vids;
  T.store.set("q", ""); T.store.set("heartOnly", false); T.store.set("hideNope", false);
  let out = T.videosPage(null);
  ok((out.match(/data-vsrc=/g) || []).length === vids.length, "videos page lists every clip");
  T.store.set("q", "ltx");
  ok((T.videosPage(null).match(/data-vsrc=/g) || []).length === vids.filter(v => /^ltx/.test(v.engine)).length, "video search narrows by engine (ltx25 + ltxia2v)");
  T.store.set("q", "");
  ok(T.vidChip("../" + vids[0].image).includes("🎬"), "source image gets a video badge");
  // grouped: one collapsible group per style, counted, count-sortable
  const ids = html => [...html.matchAll(/data-collapse="([^"]+)"/g)].map(m => m[1]);
  location.hash = "#/videos"; T.store.set("sort", "most");
  const vp = T.videosPage(null), gk = ids(vp);
  ok(gk.length === 3 && gk.every(k => k.startsWith("v:")) && new Set(gk).size === gk.length, "videos grouped: one collapsible group per style");
  const vc = k => vids.filter(v => "v:" + v.lineage === k).length;
  ok(gk.every((k, i) => !i || vc(gk[i - 1]) >= vc(k)), "videos: Most images orders groups by clip count");
  T.store.set("collapsed", {[gk[0]]: 1});
  ok((T.videosPage(null).match(/data-vsrc=/g) || []).length === (vp.match(/data-vsrc=/g) || []).length - vc(gk[0]), "videos: a collapsed group hides its clips");
  T.store.set("collapsed", {}); T.store.set("sort", "rounds"); location.hash = "";
  T.VIDS = hv;
}

// 5) extra subject genres (creatures, undead, ...) appear in the genre filter only where such subjects exist
{
  ["fcast", "fg", "fgenre"].forEach(k => T.store.set(k, "all")); T.store.set("q", "");
  const gen = html => (html.match(/<select data-fsel="fgenre"[\s\S]*?<\/select>/) || [""])[0];
  ok(!gen(T.imagesPage()).includes('value="undead"'), "no undead subjects: the genre filter keeps the base genres");
  const ex = addLin(cloneLin("001-plain-anime", "940-extras", "Extras", 0, [], 5));
  ex.versions.forEach(v => v.slots.forEach(sl => { if (sl.subject === "f-modern") sl.subject = "z-undead@zed~1"; }));
  const ip = T.imagesPage();
  ok(gen(ip).includes('value="undead"') && ip.includes(">Genre: zombies<"), "genre filter offers zombies once an undead subject exists");
  ok(T.subjShort("z-undead@zed~1").includes("🧟") && T.subjShort("c-animals@zed~1").includes("🐾"), "kind icons on tile labels");
  const cm = q => T.castMatches(q).map(x => x.o.v);
  ok(cm("").length === T.CASTOPTS.length && cm("")[0] === "all", "cast search: empty query lists every cast, All first");
  ok(T.castMatches("zzqqxx").length === 0, "cast search: no match gives nothing");
  ok(cm("zed")[0] === "zed" && T.castName("zed") === "Zed cast", "cast search: a name match ranks first");
  T.store.set("fgenre", "undead");
  const nZ = T.allImages().filter(it => (it.sl.subject || "").startsWith("z-undead")).length;
  ok((T.imagesPage().match(/data-grid="all"/g) || []).length === nZ && nZ > 0, "undead genre filter narrows to those subjects");
  T.store.set("fgenre", "all"); T.store.set("fcast", "all");
  FIX.splice(FIX.indexOf(ex), 1); T.DATA.splice(T.DATA.indexOf(ex), 1); delete T.byId[ex.id];
}

// 6) journeys (🧭): pages, scene keys, start composer, blur marks (synthetic journey)
{
  const j = FJ;
  ok(T.fbKey("../journeys/" + j.id + "/ch01/s1.png") === `journeys/${j.id}/ch01/s1.png`, "fbKey keeps journey scene paths");
  let jp = T.journeysPage();
  ok(jp.includes(`#/j/${j.id}`) && jp.includes("jcard"), "journeys page lists the journey");
  jp = T.journeyPage(j.id);
  ok(jp.includes("What happens next?") && jp.includes(`data-jdirect="${j.id}"`), "journey page has the direction box");
  ok(jp.includes("figcaption") && jp.includes(j.chapters[0].scenes[0].caption.slice(0, 20)), "scenes show their captions");
  T.JR = [{id: "j9", kind: "direct", journey: j.id, text: "into the ice", ts: "t", status: "sent"}];
  ok(T.journeyPage(j.id).includes("Your agent is writing chapter"), "open direction shows as in progress");
  T.JR = [];
  const ch0 = j.chapters[0].id, ak = j.id + "/" + ch0;
  jp = T.journeyPage(j.id);
  ok(jp.includes(`data-janim="${ak}"`) && jp.includes("Animate chapter"), "each chapter has a 🎬 Animate chapter button");
  ok(!jp.includes("data-janimsend"), "animate note box starts closed");
  T.jAnimOpen.add(ak);
  ok(T.journeyPage(j.id).includes(`data-janimsend="${ak}"`), "clicking Animate chapter opens the note box");
  T.jAnimOpen.delete(ak);
  T.JR = [{id: "j8", kind: "animate", journey: j.id, chapter: ch0, text: "", ts: "t", status: "sent"}];
  jp = T.journeyPage(j.id);
  ok(jp.includes("Animation requested") && !jp.includes(`data-janim="${ak}"`), "open animate request disables the button");
  T.JR = [{id: "j8", kind: "animate", journey: j.id, chapter: ch0, text: "", ts: "t", status: "done", reply: "reel rendered"}];
  jp = T.journeyPage(j.id);
  ok(jp.includes("reel rendered") && jp.includes(`data-janim="${ak}"`), "answered animate request shows the reply and re-enables the button");
  T.JR = [];
  const scene = "../journeys/" + j.id + "/ch01/s1.png";
  ok(!T.fbBar(scene, "x").includes("data-pin") && !T.fbBar(scene, "x").includes('data-fb="cast"'), "scenes have no 📌 / 👥");
  ok(T.fbBar("../" + j.source, "x").includes("data-explore"), "lab images get the 🧭 button");
  T.jOpen = j.source;
  ok(T.jStartBox("../" + j.source, "cap").includes("data-jstart"), "start composer opens for the image");
}

// 7) the family tree (#/tree/<id>): ancestors -> focus -> descendant sets (synthetic chain)
{
  const out = T.treePage("951-evo-a");
  ok(out.includes("Evo A"), "tree page titles the focus lineage");
  ok(out.includes('class="tnode tfocus"'), "focus renders as the larger centered card");
  ok(out.includes(T.byId["001-plain-anime"].title) && out.includes("001-plain-anime"), "ancestor row shows the survey image it evolved from, labelled with its lineage title");
  ok(/trow-label">Survey/.test(out), "ancestor generation labelled Survey");
  const set = out.split('data-tid="set:0:0"')[1] || "";
  ok(["954-evo-d", "955-evo-e"].every(id => set.includes(id)), "sibling evolutions of the focus are grouped into one bracketed set");
  ok(out.includes('href="#/tree/951-evo-a"'), "nodes link to #/tree/<id> to re-center");
  ok(out.includes('href="#/l/951-evo-a"') || out.includes('href="#/l/001-plain-anime"'), "a secondary link opens the plain lineage page");
  // crossbreed: both parents shown, from two different chains
  const cross = T.treePage("956-cross");
  ok(cross.includes("951-evo-a") && cross.includes("957-other-a"), "crossbreed ancestors show both parent chains");
  ok(T.TREE_EDGES.filter(e => e.to === "lin:956-cross").every(e => e.cross), "both edges into a crossbreed focus are marked as crossbreed edges");
  // a set with an out-of-chain crossbreed parent gets an "other parent" chip
  T.treePage("951-evo-a");
  const crossSet = T.treeDescendants(T.byId["951-evo-a"], 8).gens[0].find(s => s.members.some(m => m.id === "956-cross"));
  ok(crossSet && T.treeSetBox(crossSet).includes("tparentchip other"), "a crossbreed child set flags the parent from outside this chain");
  // a survey lineage (no parent_images) has no ancestor rows
  const surveyTree = T.treePage("001-plain-anime");
  ok(!/trow-label">Survey<\/div><div class="trow-nodes"><\/div>/.test(surveyTree), "no empty ancestor row rendered");
  ok((T.treeAncestors(T.byId["001-plain-anime"]).nodes || []).length === 0, "the survey lineage itself has no ancestors to walk up to");
  // deep chain folds beyond a few generations
  ok(surveyTree.includes('class="tree-more"'), "generations beyond the shown depth fold into a collapsible <details>");
  ok(T.treePage("999-does-not-exist").includes("Unknown lineage"), "unknown lineage id shows an empty-state message");
  dropFix();
}

// image counts, "Most images" sort, collapsible strips
{
  const ids = html => [...html.matchAll(/data-collapse="([^"]+)"/g)].map(m => m[1]);
  const cnt = id => T.byId[id].versions.reduce((n, v) => n + (v.images || []).length, 0);
  T.store.set("sort", "most");
  let out = T.overview(), order = ids(out).filter(id => T.byId[id]);
  ok(order.length > 2 && order.every((id, i) => !i || cnt(order[i - 1]) >= cnt(id)), "Most images: survey strips ordered by image count");
  ok(out.includes('class="scount"'), "strips show an image count");
  T.store.set("sort", "fewest");
  order = ids(T.overview()).filter(id => T.byId[id]);
  ok(order.every((id, i) => !i || cnt(order[i - 1]) <= cnt(id)), "Fewest images: reversed order");
  T.store.set("sort", "rounds");
  const first = ids(T.overview())[0];
  T.store.set("collapsed", {[first]: 1});
  out = T.overview();
  const strip = out.slice(out.lastIndexOf('<div class="strip', out.indexOf(`data-collapse="${first}"`)), out.indexOf(`data-collapse="${first}"`) + 400);
  ok(/class="strip[^"]*collapsed/.test(strip) && !out.slice(out.indexOf(`data-collapse="${first}"`)).split('class="strip')[0].includes("<img"), "collapsed strip hides its tiles");
  ok(out.includes("data-collapseall"), "toolbar has collapse / expand all");
  T.store.set("collapsed", {});
  // 🗑 remove a journey reference
  const jn = T.JRN.find(j => (j.refs || []).length > 1) || T.JRN[0];
  if (jn) {
    const refs = jn.refs && jn.refs.length ? jn.refs : [jn.source];
    const extra = refs.find(r => r !== jn.source);
    if (extra) ok(T.refThumb(jn, extra).includes("data-jrefdel"), "extra reference has a 🗑 remove button");
    const saved = jn.refs; jn.refs = [jn.source];
    ok(!T.refThumb(jn, jn.source).includes("data-jrefdel"), "the lone source reference can't be removed");
    jn.refs = saved;
  } else ok(true, "no journeys (skipped)");
}
// Images page: one collapsible group per style
{
  location.hash = "#/images"; T.store.set("sort", "most");
  const ip = T.imagesPage(), gids = [...ip.matchAll(/data-collapse="([^"]+)"/g)].map(m => m[1]);
  ok(gids.length > 2 && new Set(gids).size === gids.length && gids.every(id => T.byId[id]), "Images page: one group per style");
  T.store.set("collapsed", {[gids[0]]: 1});
  const ip2 = T.imagesPage(), n0 = (ip.match(/data-grid="all"/g) || []).length, n1 = (ip2.match(/data-grid="all"/g) || []).length;
  ok(n1 < n0 && /class="strip[^"]*collapsed/.test(ip2), "Images page: a collapsed group hides its images");
  T.store.set("collapsed", {}); T.store.set("sort", "rounds"); location.hash = "";
}
// 🎵 music videos
{
  const ok2 = (c, m) => ok(c, "mv: " + m);
  ok2(T.fmtT(0) === "0:00.0" && T.fmtT(75.04) === "1:15.0" && T.fmtT(59.96) === "1:00.0" && T.fmtT(9.3) === "0:09.3", "fmtT m:ss.s incl. rounding carry: " + [T.fmtT(0), T.fmtT(75.04), T.fmtT(59.96), T.fmtT(9.3)]);
  ok2(T.fmtT(-3) === "0:00.0" && T.fmtT(NaN) === "0:00.0" && T.fmtT(600) === "10:00.0", "fmtT clamps negatives / NaN, minutes > 9");
  ok2(T.parseT("1:15.5") === 75.5 && T.parseT("9.5") === 9.5 && T.parseT("0:00.0") === 0 && Number.isNaN(T.parseT("x")) && Number.isNaN(T.parseT("1:2:3")), "parseT");
  ok2(T.mvTimeToX(30, 120, 1200) === 300 && T.mvTimeToX(5, 0, 100) === 0, "mvTimeToX");
  ok2(T.mvXToTime(300, 120, 1200) === 30 && T.mvXToTime(-50, 120, 1200) === 0 && T.mvXToTime(5000, 120, 1200) === 120 && T.mvXToTime(10, 120, 0) === 0, "mvXToTime clamps");
  let r = T.mvRegion(600, 300, 120, 1200);
  ok2(r && r.t0 === 30 && r.t1 === 60, "mvRegion orders a right-to-left drag: " + JSON.stringify(r));
  r = T.mvRegion(-100, 5000, 120, 1200);
  ok2(r && r.t0 === 0 && r.t1 === 120, "mvRegion clamps to the track");
  ok2(T.mvRegion(100, 101, 120, 1200) === null && T.mvRegion(100, 100, 120, 1200) === null, "mvRegion: under 0.2 s is null");
  ok2(T.mvRegion(100, 103, 120, 1200) !== null, "mvRegion: 0.3 s is kept");
  ok2(T.mvRegion(0, 10, 0, 100) === null && T.mvRegion(NaN, 10, 120, 1200) === null, "mvRegion: bad input is null");
  const ll = T.lyricLines("  Hello there \r\n\r\n   \nsecond line\n");
  ok2(ll.length === 2 && ll[0] === "Hello there" && ll[1] === "second line" && T.lyricLines(null).length === 0, "lyricLines: trimmed non-empty lines");
  // list + page from a synthetic music video pushed into the data
  const ref = "evolutions/001-plain-anime/v01/seed1001.png";
  const mv = {id: "900-test-song", title: "Test <Song>", idea: "a lighthouse keeper sings", lyrics: "line one\nline two", status: "submitted", created: "2026/09/30", audio: "musicvideos/900-test-song/audio/song.mp3", vocals: null,
    refs: [ref], ref_crop: {}, ref_notes: {}, ref_for: {}, cast: [{name: "Keeper", look: "an old man"}], name: "", style: "", character: "", world: "",
    markers: [{id: "m1", t0: 10, t1: 20.5, lyric: "line one", note: "wide on the sea", emph: 2}, {id: "m2", t0: 30, t1: 40, lyric: "", note: "", emph: 3}],
    ref_requests: [{id: "r1", text: "a photo of a lighthouse", done: false}, {id: "r2", text: "the keeper's hands", done: true}],
    analysis: {duration: 120, peaks: [[-0.5, 0.5], [-0.2, 0.3]], beats: [1, 2], tempo: 100, sections: [40, 80]},
    storyboards: [{id: "sb01", title: "First pass", direction: "", summary: "sea and stone", choices: [], scenes: [
      {id: "s1", shot: "wide", caption: "the lamp turns", lyric: "line one", t0: 10, t1: 20.5, src: "../musicvideos/900-test-song/sb01/s1.png", dialogue: []},
      {id: "s2", shot: "close", caption: "his hands", t0: 30, t1: 40, src: null, dialogue: []}]}]};
  const hadMVS = T.MVS, hadBy = T.mvById;
  T.MVS = []; T.mvById = {};
  ok2(T.mvListPage().includes("No music videos yet"), "empty list says so");
  T.mvMerge(mv);
  ok2(T.mvById[mv.id] && T.MVS.length === 1, "mvMerge adds a new music video");
  T.mvMerge({id: mv.id, title: "Renamed"}); ok2(T.mvById[mv.id].title === "Renamed" && T.mvById[mv.id].markers.length === 2, "mvMerge updates fields, keeps the rest");
  T.mvById[mv.id].title = mv.title;
  T.MVR = [{id: "v1", kind: "submit", mv: mv.id, text: "go", ts: "t", status: "sent"}];
  let lp = T.mvListPage();
  ok2(lp.includes('data-go="#/mv/900-test-song"') && lp.includes("Test &lt;Song&gt;") && lp.includes("2 markers") && lp.includes("Submitted") && lp.includes("line one") && lp.includes("data-mvnew"), "list page card: title escaped, markers, status, first lyric, new button");
  T.layerNav(); ok2(true, "layerNav runs with music videos");
  let pg = T.mvPage(mv.id);
  ok2(pg.includes('data-jrefdel="mv:900-test-song"') && pg.includes('data-jcrop="mv:900-test-song"') && pg.includes('data-jrf="mv:900-test-song"'), "references use the mv: owner id for ✂ / 🗑 / note");
  ok2(pg.includes('<canvas class="mvtl">') && pg.includes("data-mvzoom") && pg.includes('id="mvaslot"'), "timeline canvas, zoom slider and audio slot render");
  ok2(pg.includes('data-mvmk="m1"') && pg.includes("0:10.0–0:20.5") && pg.includes("wide on the sea") && pg.includes("♪ line one") && pg.includes('data-mvmk="m2"'), "marker list: ranges, lyric, note");
  ok2(pg.includes("a photo of a lighthouse") && /data-mvreq="r2"[^>]*checked/.test(pg) && !/data-mvreq="r1"[^>]*checked/.test(pg), "reference requests are a tickable checklist");
  ok2(pg.includes('data-draft="mvidea:900-test-song"') && pg.includes('data-draft="mvlyrics:900-test-song"') && pg.includes("line one\nline two"), "idea + lyrics textareas keep drafts");
  ok2(pg.includes("Submitted: waiting for your agent"), "open submit shows as waiting");
  ok2(pg.includes('data-mvscene="../musicvideos/900-test-song/sb01/s1.png"') && pg.includes("♪ line one") && pg.includes("rendering…"), "storyboard frames: image, lyric, pending frame");
  ok2(T.mvScenesOf(T.mvById[mv.id]).length === 1 && T.mvScenesOf(T.mvById[mv.id])[0].cap.includes("sb01"), "lightbox list = rendered frames with captions");
  // 📰 headlines: decorative lower thirds from scene.headline
  ok2(!pg.includes("hlayer") && !pg.includes("data-hltoggle"), "no headline on the scenes: no overlay, no toggle");
  { const sc = T.mvById[mv.id].storyboards[0].scenes[0]; sc.headline = 'Robot <dog> & "co"'; T.mvById[mv.id].headline_tag = "TV NEWS";
    let hp = T.mvPage(mv.id);
    ok2(hp.includes('<div class="hlayer"><div class="hl"><span class="hltag">TV NEWS</span><span class="hltx">Robot &lt;dog&gt; &amp; &quot;co&quot;</span>') && !hp.includes("<dog>"), "headline renders over the frame with the mv tag, text escaped");
    ok2(hp.includes("data-hltoggle") && hp.includes("📰 Headlines on"), "a 📰 Headlines toggle shows when a scene has a headline");
    sc.headline_tag = "LIVE"; ok2(T.mvPage(mv.id).includes('<span class="hltag">LIVE</span>'), "scene headline_tag overrides the mv tag");
    delete sc.headline_tag; delete T.mvById[mv.id].headline_tag; ok2(T.mvPage(mv.id).includes('<span class="hltag">BREAKING</span>'), "default tag is BREAKING");
    const l0 = T.mvScenesOf(T.mvById[mv.id])[0]; ok2(l0.headline === sc.headline, "the lightbox list carries the headline");
    T.store.set("headlines", false); ok2(!T.headlinesOn() && T.headlineBtn().includes("📰 Headlines off") && !T.headlineBtn().includes(' on"'), "toggle off is stored per viewer and relabels the button");
    T.store.set("headlines", true); ok2(T.headlinesOn() && T.headlineHtml("") === "", "toggle on again; an empty headline renders nothing");
    delete sc.headline; }
  ok2(T.fbKey("../musicvideos/900-test-song/sb01/s1.png") === "musicvideos/900-test-song/sb01/s1.png" && T.refOid("musicvideos/900-test-song/sb01/s1.png") === "mv:900-test-song" && T.refOwner("mv:900-test-song") === T.mvById[mv.id], "fbKey / refOid / refOwner accept musicvideos/ paths");
  // editor: nothing selected -> hint; a selection -> fields
  ok2(T.mvEditHtml(T.mvById[mv.id]).includes("drag across it"), "editor hint when nothing is selected");
  T.MVT.sel = {id: null, t0: 12, t1: 15.5, lyric: "", note: "", emph: 1};
  let ed = T.mvEditHtml(T.mvById[mv.id]);
  ok2(ed.includes("New marker") && ed.includes('value="0:12.0"') && ed.includes('value="0:15.5"') && ed.includes("data-mvsave") && !ed.includes("data-mvdel") && ed.includes('<option value="line one">'), "editor for a new region: times, save, lyric-line picker, no delete");
  T.MVT.sel = {...mv.markers[0]};
  ed = T.mvEditHtml(T.mvById[mv.id]);
  ok2(ed.includes("Edit marker") && ed.includes('data-mvdel="m1"') && ed.includes('data-mvemph="2"') && /class="on" style="--ec:#f0a030"/.test(ed), "editor for an existing marker: delete + emphasis");
  T.MVT.sel = null;
  // no audio / no analysis placeholders
  const m2 = T.mvById[mv.id], an = m2.analysis, au = m2.audio;
  m2.analysis = null; ok2(T.mvPage(mv.id).includes("Analysing the song"), "audio without analysis says Analysing…");
  m2.audio = null; ok2(T.mvPage(mv.id).includes("Upload the song to see its waveform") && !T.mvPage(mv.id).includes('id="mvaslot"'), "no audio: upload hint, no player");
  m2.audio = au; m2.analysis = an;
  m2.refs = []; ok2(T.mvPage(mv.id).includes("None yet"), "no references is allowed");
  m2.refs = [ref];
  ok2(T.mvPage("999-nope").includes("Unknown music video"), "unknown id");
  T.MVR = [{id: "v1", kind: "submit", mv: mv.id, text: "go", ts: "t", status: "done", reply: "storyboard ready"}];
  ok2(T.mvPage(mv.id).includes("Agent: storyboard ready"), "agent reply shown");
  T.MVS = hadMVS; T.mvById = hadBy; T.MVR = [];
}
// 🎚 stems
{
  const ok3 = (c, m) => ok(c, "stems: " + m), F = (name, type = "") => ({name, type}), S = T.mvSortDrop;
  ok3(S([F("Sample Song Stems.zip")], "audio").stems && !S([F("Sample Song Stems.zip")], "audio").audio, "a .zip dropped on the song zone goes to stems");
  ok3(S([F("x", "application/zip")], "vocals").stems && S([F("x", "application/x-zip-compressed")], "stems").stems, "zip by MIME type, and on the stems zone");
  const zs = S([F("stems.zip"), F("Sample Song.mp3")], "audio");
  ok3(zs.stems && zs.audio && zs.audio.name === "Sample Song.mp3", "zip + a hand-picked song: both go up");
  ok3(S([F("Sample Song.mp3")], "stems").audio && !S([F("Sample Song.mp3")], "stems").stems, "an mp3 dropped on the stems zone is taken as the song");
  ok3(Object.keys(S([F("cover.png", "image/png")], "stems")).length === 0, "images still ignored");
  ok3(T.mvStemColor("drums") !== T.mvStemColor("bass") && T.mvStemColor("nonsense") === T.MV_STEM_COL.other && T.mvStemColor("vocals") === T.MV_STEM_COL.vocals, "role colours, unknown role = other");
  let g = T.mvLaneGeom(5, false), gc = T.mvLaneGeom(5, true);
  ok3(g.H === 130 + 5 * 14 && g.top(2) === 130 + 28 && gc.H === 130 + 55 && T.mvLaneGeom(0, false).H === 130, "lane geometry: waveform 130 px + 14 px per lane (11 compact)");
  ok3(T.mvStemsInfo({}) === "" && T.mvStemsInfo({stems: [1], stems_info: {song: "mixdown of 9 stems", vocals: "Lead Vocals.wav"}}) === "✓ song = mixdown of 9 stems · vocals = Lead Vocals.wav", "picked-files line");
  ok3(T.mvStemsInfo({stems: [1], stems_info: {song: "x.wav (the full mix in the zip)", vocals: null}}).includes("none found"), "no lead vocal is said");
  const lane = n => Array.from({length: 200}, (_, i) => (i % 20 < n ? 80 : 0));
  const sd = {tempo: 120, beat_source: "drums", beats: [1, 2, 3], downbeats: [1], warnings: ["Bass is 0.050 s behind the song: shifted into place"], sections: [40],
    stems: [{name: "Drums", role: "drums", lane: lane(10), entrances: [0], segments: [[0, 100]]}, {name: "Lead Vocals", role: "vocals", lead: true, lane: lane(6), entrances: [20], segments: [[20, 90]]},
      {name: "Guitar", role: "guitar", lane: lane(14), entrances: [], segments: [[0, 100]]}],
    moments: [{t: 60, t1: 70, kind: "solo", stems: ["Guitar"], note: "x"}, {t: 80, t1: 90, kind: "breakdown", stems: ["Drums"], note: "y"}, {t: 40, kind: "fill", stems: ["Drums"], note: "z"}]};
  const mv = {id: "900-st", title: "St", refs: [], markers: [], storyboards: [], audio: "musicvideos/900-st/audio/song.wav", audio_from: "stems-mixdown", analysis: {duration: 100, peaks: [[-0.5, 0.5]], beats: [1], tempo: 100, sections: [40]},
    stems: [{name: "Drums"}, {name: "Lead Vocals"}, {name: "Guitar"}], stems_info: {song: "mixdown of 3 stems", vocals: "Lead Vocals.wav"}};
  const hM = T.MVS, hB = T.mvById;
  T.MVS = [mv]; T.mvById = {"900-st": mv};
  let pg = T.mvPage("900-st");
  ok3(pg.includes('data-mvdrop="stems"') && pg.includes("a zip alone is enough") && pg.includes("the lead vocal and the full mix are picked out automatically"), "stems drop zone explains that the zip alone is enough");
  ok3(pg.includes("✓ song = mixdown of 3 stems · vocals = Lead Vocals.wav") && pg.includes("Analysing stems"), "after the upload: what became the song / vocals; stems analysing");
  mv.stems_error = "no readable stems"; pg = T.mvPage("900-st");
  ok3(pg.includes("Couldn't analyse the 3 stems (no readable stems)") && pg.includes("data-mvstclear"), "failed analysis shows the error");
  mv.stems_error = ""; mv.stems_data = sd; pg = T.mvPage("900-st");
  ok3(pg.includes("3 stems") && pg.includes("data-mvlanes") && pg.includes("Hide lanes") && pg.includes("Bass is 0.050 s behind") && pg.includes("beats from the drum stem") && pg.includes("3 key moments"), "stems bar: count, toggle, offset warning, beat source, moments");
  T.store.set("mvlanes", false);
  ok3(!T.mvLanesOn(mv) && T.mvPage("900-st").includes("Show lanes"), "lanes can be hidden (per viewer)");
  T.store.set("mvlanes", true);
  // paint into a recording stub canvas: taller with lanes, names drawn, lead marked
  const calls = {fillText: [], fillRect: 0, lineWidth: []}, ctx = new Proxy({}, {get: (t, k) => k === "measureText" ? s => ({width: 5 * String(s).length}) : k === "fillText" ? (s => calls.fillText.push(s)) : k === "fillRect" ? (() => { calls.fillRect++; }) : k === "getPropertyValue" ? (() => "") : (t[k] ?? (() => {})), set: (t, k, v) => { t[k] = v; return true; }});
  const wrap = {clientWidth: 800, scrollLeft: 0}, cv = {isConnected: true, parentNode: wrap, dataset: {}, style: {}, width: 0, height: 0, getContext: () => ctx};
  const hCS = global.getComputedStyle; global.getComputedStyle = () => ({getPropertyValue: () => ""});
  const hC = T.MVT.canvas, hId = T.MVT.id; T.MVT.canvas = cv; T.MVT.id = "900-st"; T.MVT.zoom = 1;
  T.mvPaint();
  ok3(cv.style.height === (130 + 3 * 14) + "px" && calls.fillText.includes("★ Lead Vocals") && calls.fillText.includes("Drums") && calls.fillText.includes("Guitar"), "canvas grows 14 px per stem; lane names drawn, lead vocal starred");
  T.store.set("mvlanes", false); cv.dataset = {}; calls.fillText.length = 0; T.mvPaint();
  ok3(cv.style.height === "130px" && !calls.fillText.includes("Drums"), "hidden lanes: the canvas is the plain waveform again");
  T.store.set("mvlanes", true); wrap.clientWidth = 400; cv.dataset = {}; T.mvPaint();
  ok3(cv.style.height === (130 + 3 * 11) + "px", "narrow width: compact lanes");
  global.getComputedStyle = hCS; T.MVT.canvas = hC; T.MVT.id = hId;
  // the mixdown status, before the song exists
  mv.audio = null; mv.analysis = null; mv.stems_data = null; pg = T.mvPage("900-st");
  ok3(pg.includes("Mixing the 3 stems down into a song"), "while the mixdown renders");
  mv.analysis_error = "ffmpeg failed"; ok3(T.mvPage("900-st").includes("ffmpeg failed"), "mixdown failure is shown");
  // clearing on the server (no `stems` key any more) empties the page state
  mv.stems_data = sd; mv.analysis_error = ""; T.mvMerge({id: "900-st", title: "St", audio: null});
  ok3(!T.mvById["900-st"].stems && !T.mvById["900-st"].stems_data && !T.mvById["900-st"].stems_info, "mvMerge: removed stems leave the page");
  T.MVS = hM; T.mvById = hB; T.MVT.id = hId;
}
// 🎤 lyric lane
{
  const ok4 = (c, m) => ok(c, "lyric lane: " + m);
  const lines = [{i: 0, text: "Well", t0: 10, t1: 20, conf: 1}, {i: 1, text: "You were sitting", t0: 20, t1: 30, conf: 0.4}, {i: 2, text: "Spread line", t0: 30, t1: 40, conf: 0.9, spread: true},
    {i: 3, text: "Well", t0: 60, t1: 70, conf: 1}, {i: 4, text: "empty", t0: 80, t1: 80, conf: 1}];
  const bl = T.mvLyricBlocks(lines, 100, 1000);
  ok4(bl.length === 4 && bl[0].x0 === 100 && bl[0].x1 === 200 && bl[3].x0 === 600, "one block per timed line (zero-length dropped), time -> pixels");
  ok4(bl.map(b => b.est).join() === "false,true,true,false", "conf < 0.5 or a spread line = estimated (dashed)");
  ok4(T.mvLyricBlocks([{i: 0, text: "x", t0: 1, t1: 1.001, conf: 1}], 100, 100)[0].x1 - T.mvLyricBlocks([{i: 0, text: "x", t0: 1, t1: 1.001, conf: 1}], 100, 100)[0].x0 >= 2, "a tiny line still gets a 2 px block");
  ok4(T.mvLyricBlocks(null, 100, 1000).length === 0, "no timing, no blocks");
  const g0 = T.mvLaneGeom(3, false, 130, true), g1 = T.mvLaneGeom(3, true, 130, true), g2 = T.mvLaneGeom(3, false);
  ok4(g0.lyr === 16 && g0.top(0) === 146 && g0.H === 130 + 16 + 42 && g1.lyr === 13 && g1.H === 130 + 13 + 33 && g2.lyr === 0 && g2.H === 130 + 42 && g2.top(0) === 130, "the lyric lane sits between the waveform and the stem lanes (16 px, 13 compact)");
  ok4(T.mvLyricHit(150, 135, g0, bl).i === 0 && T.mvLyricHit(650, 130, g0, bl).i === 3, "hit test: a block in the lyric lane");
  ok4(T.mvLyricHit(150, 120, g0, bl) === null && T.mvLyricHit(150, 146, g0, bl) === null && T.mvLyricHit(450, 135, g0, bl) === null && T.mvLyricHit(150, 135, g2, bl) === null, "...not on the waveform, the stem lanes, a gap, or with no lyric lane");
  const ov = T.mvLyricBlocks([{i: 0, text: "long", t0: 0, t1: 50, conf: 1}, {i: 1, text: "short", t0: 10, t1: 20, conf: 1}], 100, 1000);
  ok4(T.mvLyricHit(150, 135, g0, ov).i === 1, "overlapping blocks: the narrowest wins");
  const pm = {lyrics_timing: {lines}};
  let tp = T.mvPickLyric(pm, "You were sitting", null);
  ok4(tp && tp.t0 === 20 && tp.t1 === 30, "picking a timed line gives its From / To");
  ok4(T.mvPickLyric(pm, "Well", 65).t0 === 60 && T.mvPickLyric(pm, "Well", 5).t0 === 10 && T.mvPickLyric(pm, "Well", null).t0 === 10, "a repeated line: the occurrence nearest the current marker");
  ok4(T.mvPickLyric(pm, "not in the song", null) === null && T.mvPickLyric({}, "Well", null) === null && T.mvPickLyric(pm, "empty", null) === null, "unknown / untimed lines give null");
  const bar = o => T.mvLyricsBar({audio: "a.wav", lyrics: "Well", ...o});
  ok4(bar({}).includes("data-mvlyrplace") && bar({}).includes("Place lyrics") && !/data-mvlyrplace\s+disabled/.test(bar({})), "button offered once there are lyrics and a song");
  const timed = {lyrics_timing: {lines, source: "musicvideos/x/audio/vocals.wav"}};
  ok4(bar(timed).includes("Re-place lyrics") && bar(timed).includes("5 lines placed from the vocals") && bar(timed).includes("dashed = estimated"), "after placing: count, source, dashed = estimated");
  ok4(bar({lyrics_pending: true}).includes("Placing lyrics…") && !bar({lyrics_pending: true}).includes("data-mvlyrplace"), "queued: 'Placing lyrics…', no second click");
  ok4(bar({lyrics_error: "no speech found"}).includes("Couldn't place the lyrics (no speech found)") && bar({lyrics_error: "x"}).includes("data-mvlyrplace"), "failure shows the error and keeps the button");
  ok4(/data-mvlyrplace\s+disabled/.test(bar({lyrics: ""})) && bar({lyrics: ""}).includes("Save the lyrics"), "no lyrics saved: disabled with a hint");
  ok4(T.mvLyricsBar({lyrics: "Well"}) === "", "no song or vocals: no button");
  // the editor's picker carries the times, and the page paints the lane
  const mv = {id: "900-ly", title: "Ly", refs: [], markers: [], storyboards: [], audio: "musicvideos/900-ly/audio/song.wav", lyrics: "Well\nYou were sitting\nMissing line", lyrics_timing: {lines, source: "x/vocals.wav"},
    analysis: {duration: 100, peaks: [[-0.5, 0.5]], beats: [], tempo: 100, sections: []}};
  const hM = T.MVS, hB = T.mvById; T.MVS = [mv]; T.mvById = {"900-ly": mv};
  T.MVT.sel = {id: null, t0: 5, t1: 6, lyric: "", note: "", emph: 1};
  const ed = T.mvEditHtml(mv);
  ok4(ed.includes("0:10.0 · Well") && ed.includes("0:20.0 · You were sitting") && /<option value="Missing line">Missing line<\/option>/.test(ed), "'Pick a lyric line…' shows the start time of each timed line");
  T.MVT.sel = null;
  const calls = {text: [], strokes: 0, dashes: []}, ctx = new Proxy({}, {get: (t, k) => k === "measureText" ? s => ({width: 5 * String(s).length}) : k === "fillText" ? (s => calls.text.push(s)) : k === "setLineDash" ? (d => calls.dashes.push(d.length)) : (t[k] ?? (() => {})), set: (t, k, v) => { t[k] = v; return true; }});
  const wrap = {clientWidth: 1000, scrollLeft: 0}, cv = {isConnected: true, parentNode: wrap, dataset: {}, style: {}, width: 0, height: 0, getContext: () => ctx};
  const hCS = global.getComputedStyle; global.getComputedStyle = () => ({getPropertyValue: () => ""});
  const hC = T.MVT.canvas, hId = T.MVT.id; T.MVT.canvas = cv; T.MVT.id = "900-ly"; T.MVT.zoom = 1;
  T.mvPaint();
  ok4(cv.style.height === "146px" && calls.text.includes("Well") && calls.text.includes("You were sitting") && calls.dashes.includes(2), "canvas is 16 px taller, line text drawn inside its block, estimated blocks dashed");
  global.getComputedStyle = hCS; T.MVT.canvas = hC; T.MVT.id = hId;
  T.MVS = hM; T.mvById = hB;
}
// 🎬 music-video clips
{
  const ok5 = (c, m) => ok(c, "mv clips: " + m);
  const id = "900-clip", k1 = `musicvideos/${id}/sb01/s1.png`, k2 = `musicvideos/${id}/sb01/s2.png`;
  const mkv = (img, eng, created) => ({src: `../${img.replace(/\.png$/, "")}__${eng}_seed1.mp4`, poster: "../" + img, image: img, lineage: id, version: "sb01", title: "Clip Song", journey: false, mv: id,
    depth: 0, subject: "f-modern", subject_label: "x", engine: eng, tag: "", prompt: "p", note: "", created});
  const v1 = mkv(k1, "fasth3", 10), v1b = mkv(k1, "h3turbo", 20), v2 = mkv(k2, "fasth3", 5);
  const mv = {id, title: "Clip Song", refs: [], markers: [], cast: [], storyboards: [{id: "sb01", title: "First", scenes: [
    {id: "s1", shot: "wide", caption: "c1", lyric: "line one", t0: 10, t1: 20, src: `../${k1}`, dialogue: []}, {id: "s2", shot: "close", caption: "c2", t0: 30, t1: 40, src: `../${k2}`, dialogue: []},
    {id: "s3", shot: "x", caption: "c3", src: null, dialogue: []}]}]};
  const hM = T.MVS, hB = T.mvById, hF = T.FB; T.MVS = [mv]; T.mvById = {[id]: mv};
  T.VIDS.push(v1, v1b, v2);
  try {
    ok5(T.sceneClips({src: `../${k1}`}).length === 2 && T.sceneClips({src: `../${k1}`})[0] === v1b, "frame clips found by the frame's png, newest first");
    let pg = T.mvPage(id);
    ok5(pg.includes(`data-jclips="${k1}"`) && pg.includes(`data-jclips="${k2}"`) && /data-jclips="musicvideos\/900-clip\/sb01\/s1.png"[^>]*>🎬 2</.test(pg), "frames with clips get the 🎬 N chip (s1: 2, s2: 1); no chip on the pending frame");
    ok5(!pg.includes("data-jclipv"), "the inline player is closed until the chip is clicked");
    ok5(pg.includes("data-mvplay") && pg.includes("Play storyboard · 2 clips"), "▶ Play storyboard button counts frames with clips");
    const hJ = T.JCLIP[k1]; T.JCLIP[k1] = v1.src; pg = T.mvPage(id);
    ok5(pg.includes("data-jclipv") && pg.includes("data-jclipsel") && pg.includes(`data-src="${v1b.src}"`), "open chip: inline player, clip picker, clip panel");
    delete T.JCLIP[k1];
    const rl = T.mvReel(mv);
    ok5(rl.length === 2 && rl[0].src === v1b.src && rl[1].src === v2.src && /sb01 · s1 · 0:10\.0/.test(rl[0].label), "reel = one clip per frame in storyboard order, newest first");
    T.FB = {[v1.src.replace(/^\.\.\//, "")]: {action: "love", status: "pending", actions: ["love"]}};
    const rl2 = T.mvReel(mv);
    ok5(rl2[0].src === v1.src || rl2[0].src === v1b.src, "a loved clip is kept for its frame when marks exist");
    T.FB = {[v1b.src.replace(/^\.\.\//, "")]: {action: "nope", status: "pending", actions: ["nope"]}};
    ok5(T.mvReel(mv)[0].src === v1.src, "a 👎 clip is skipped");
    T.FB = hF;
    const vp = T.videosPage();
    ok5(vp.includes("🎵 Clip Song") && vp.includes(`href="#/mv/${id}"`) && vp.includes('data-collapse="v:900-clip"'), "Videos page: clips grouped under '🎵 <title>' with key v:<mv id>, linking to the music video");
    ok5(T.mvPlayBtn({id: "zzz", storyboards: []}) === "", "no clips, no play button");
    if (hJ) T.JCLIP[k1] = hJ;
  } finally {
    [v1, v1b, v2].forEach(v => T.VIDS.splice(T.VIDS.indexOf(v), 1));
    T.MVS = hM; T.mvById = hB; T.FB = hF;
  }
}
// drag-and-drop song/vocals
{
  const F = (name, type = "") => ({name, type}), S = T.mvSortDrop;
  let r = S([F("Sample Song (final).wav")], "vocals");
  ok(r.vocals && r.vocals.name === "Sample Song (final).wav" && !r.audio, "one file goes to the zone it was dropped on");
  r = S([F("kiss_me_vocals.wav"), F("kiss_me_mix.wav")], "audio");
  ok(r.audio.name === "kiss_me_mix.wav" && r.vocals.name === "kiss_me_vocals.wav", "two files: *vocal* to vocals, the other to the song");
  r = S([F("Sample Song Acapella.flac"), F("Sample Song.mp3")], "vocals");
  ok(r.audio.name === "Sample Song.mp3" && r.vocals.name === "Sample Song Acapella.flac", "acapella counts as vocals");
  ok(!Object.keys(S([F("cover.png", "image/png")], "audio")).length, "non-audio files are ignored");
  ok(S([F("take", "audio/wav")], "audio").audio, "audio MIME without an extension still counts");
  const page = T.mvPage ? (T.MVS = [{id: "900-t", title: "T", refs: [], markers: [], storyboards: []}], T.mvById = {"900-t": T.MVS[0]}, T.mvPage("900-t")) : "";
  ok(page.includes('data-mvdrop="audio"') && page.includes('data-mvdrop="vocals"'), "mv page has both drop zones");
  T.MVS = []; T.mvById = {};
}
{  // Firefox: a drag over text gives a Text node as event target
  location.hash = "#/mv/900-t";
  const zone = {dataset: {mvdrop: "vocals"}}, parent = {closest: sel => sel === "[data-mvdrop]" ? zone : null};
  ok(T.mvDropZone({target: {nodeType: 3, parentElement: parent}}) === zone, "drop zone found from a Text-node target (Firefox)");
  ok(T.mvDropZone({target: {nodeType: 1, closest: () => null}}) === null, "no zone outside the drop areas");
  location.hash = "";
}
{  // adjust a set marker without re-marking
  const sel = {t0: 10, t1: 20}, dur = 100, w = 1000;  // 10 px per second: edges at 100 px and 200 px
  ok(T.mvEdgeHit(104, sel, dur, w) === "t0" && T.mvEdgeHit(195, sel, dur, w) === "t1" && T.mvEdgeHit(150, sel, dur, w) === "move"
     && T.mvEdgeHit(300, sel, dur, w) === null && T.mvEdgeHit(150, null, dur, w) === null, "mvEdgeHit: start / end / middle / outside");
  ok(T.mvEdgeHit(113, sel, dur, w, 16) === "t0" && T.mvEdgeHit(113, sel, dur, w) === "move", "touch gets a wider grab zone");
  let r = T.mvShift(sel, "t0", 12.345, dur);
  ok(r.t0 === 12.35 && r.t1 === 20, "drag the start: end stays");
  ok(T.mvShift(sel, "t0", 25, dur).t0 === 19.8 && T.mvShift(sel, "t1", 5, dur).t1 === 10.2, "edges never cross (0.2 s minimum)");
  ok(T.mvShift(sel, "t1", 150, dur).t1 === 100 && T.mvShift(sel, "t0", -3, dur).t0 === 0, "edges clamp to the song");
  r = T.mvShift(sel, "move", 50, dur, 5);
  ok(r.t0 === 45 && r.t1 === 55, "slide keeps the length (grab offset kept)");
  ok(T.mvShift(sel, "move", 99, dur, 5).t1 === 100, "slide stops at the end");
  ok(T.mvSnapBeat(10.3, [9.8, 10.45, 11.1]) === 10.45 && T.mvSnapBeat(3, []) === 3, "snap to the nearest beat");
  ok(T.mvEditHtml({id: "x", lyrics: ""}) !== undefined, "editor renders");
}
{  // 🖼 "Request a reference" on the music-video page
  const mv = {id: "900-g", title: "G", name: "Dana", refs: [], markers: [], storyboards: [], cast: [{name: "Alice", look: "x"}],
    gen_requests: [{id: "g1", text: "Alice <b>full</b> body", for: "Alice", status: "open", ts: "t"}, {id: "g2", text: "the mic", for: "", status: "done", result: "musicvideos/900-g/refs/gen_1.png", ts: "t"}, {id: "g3", text: "old", for: "", status: "cancelled", ts: "t"}]};
  T.MVS = [mv]; T.mvById = {"900-g": mv}; T.MVR = [];
  let pg = T.mvPage("900-g");
  ok(pg.includes('data-mvgen="toggle"') && pg.includes("➕ Request a reference") && pg.indexOf("➕ Request a reference") < pg.indexOf("refgrid"), "references header has the Request a reference button");
  ok(!pg.includes('data-draft="mvgen:900-g"'), "form closed by default");
  ok(pg.includes("⏳") && pg.includes("Alice &lt;b&gt;full&lt;/b&gt; body") && pg.includes("for Alice") && pg.includes('data-mvgencancel="g1"'), "open request listed (escaped) with a withdraw button");
  ok(pg.includes("✓ 1 request added") && !pg.includes("musicvideos/900-g/refs/gen_1.png") && !pg.includes('data-mvgencancel="g2"') && !pg.includes(">old<"), "done request collapses into the added toggle (no duplicate thumbnail), no withdraw; cancelled hidden");
  T.MVT.gen = true; pg = T.mvPage("900-g");
  ok(pg.includes('data-draft="mvgen:900-g"') && pg.includes('data-draft="mvgenfor:900-g"') && pg.includes('data-mvgen="send"') && pg.includes('data-mvgen="cancel"'), "open form: draft textarea + Use for select + Send/Cancel");
  ok(/<option value="">Dana \(the lead\)<\/option>/.test(pg) && pg.includes('<option value="Alice">Alice</option>'), "Use for: the lead (empty value) and each cast member");
  {  // the real mv.json cast is a {name: look} map + the click handler must route the buttons
    const m2 = {...mv, id: "900-h", cast: {"Alice": "x", "the photo": "y"}}; T.mvById["900-h"] = m2; T.MVS.push(m2);
    T.mvPage("900-h"); T.MVT.gen = true; const p2 = T.mvPage("900-h");  // switching pages closes the form; reopen it
    ok(p2.includes('<option value="Alice">Alice</option>') && p2.includes('<option value="the photo">the photo</option>'), "Use for works with a {name: look} cast");
    ok(/closest\("[^"]*\[data-mvgen\][^"]*\[data-mvgencancel\]/.test(html), "page click handler routes data-mvgen / data-mvgencancel");
  }
  T.MVT.gen = false; T.mvMerge({id: "900-g", title: "G"}); ok(T.mvById["900-g"].gen_requests.length === 0, "mvMerge clears gen_requests when mv.json has none");
}
{  // "What do you need from this reference?" box + Ask on music video references
  const mv = {id: "900-f", refs: ["evolutions/a/v01/x.png"], ref_crop: {}, markers: [], storyboards: []};
  let t = T.refThumb(mv, mv.refs[0], "mv:900-f");
  ok(t.includes('data-mvrefask="900-f"') && t.includes('data-draft="mvrefask:900-f:evolutions/a/v01/x.png"') && t.includes("What do you need from this reference?"), "mv ref: text box + Ask button (draft-safe)");
  ok(!t.includes("data-mvface"), "mv ref: the 🙂 face buttons are gone from the UI");
  const jn = T.JRN[0];
  ok(!jn || !T.refThumb(jn, (jn.refs || [jn.source])[0]).includes("data-mvrefask"), "journeys don't get the Ask box");
}
{  // music-video references get the storyboard toolbar
  const gen = "musicvideos/900-r/refs/gen_2.png", evo = "evolutions/a/v01/x.png";
  const mv = {id: "900-r", title: "R", refs: [gen, evo], ref_crop: {}, markers: [], storyboards: []};
  const tg = T.refThumb(mv, gen, "mv:900-r"), te = T.refThumb(mv, evo, "mv:900-r");
  ok(tg.includes('class="fbbar') && tg.includes('data-mvref="' + gen + '"'), "mv ref (generated): fbBar toolbar inside a .cell + lightbox hook");
  ok(tg.includes('data-reroll="' + gen + '"') && tg.includes("data-fb=\"love\""), "mv ref (generated): 🎲 reroll + ❤ buttons");
  ok(te.includes('class="fbbar') && te.includes('data-fb="love"') && te.includes('data-fb="nope"'), "mv ref (lab image): ❤ / 👎 via fbBar");
  ok(T.rerollBtn(gen).includes("data-reroll") && T.fixAreaBtn(gen) !== "" && T.upscaleBtn(gen) !== "" && T.refitCtl(gen) !== "", "refs paths get reroll / fix area / upscale / refit");
  ok(T.rerollBtn("musicvideos/900-r/refs/_rerolled/gen_2__20261001-101010.png") === "", "revision archive files get no reroll");
  ok(T.refThumb({id: "j", title: "J", refs: [evo], source: evo}, evo).indexOf("fbbar") < 0, "journey references stay plain");
}
{  // compact reference cards: fixed-ratio image area, crop as overlay, ✎ panel, request chips, done toggle
  const evo = "evolutions/a/v01/x.png", mv = {id: "900-k", title: "K", name: "Bob", refs: [evo, "evolutions/a/v01/y.png"], ref_crop: {[evo]: [0.25, 0.1, 0.75, 0.6]},
    ref_notes: {[evo]: "the shop sign"}, ref_for: {[evo]: "the sign"}, cast: [{name: "the sign"}], markers: [], storyboards: []};
  T.refEditOpen.clear();
  const t = T.refThumb(mv, evo, "mv:900-k"), t2 = T.refThumb(mv, mv.refs[1], "mv:900-k");
  ok(t.includes('class="jref rcard mvref"') && t.includes('class="cell rcell mvrefcell"') && t.includes('class="rimg"') && t.includes('onload="refCropFit(this)"'), "ref card: one fixed-ratio image area (.rcell) with the toolbar cell");
  ok(t.includes('class="rcrop" data-crop="0.25,0.1,0.75,0.6"') && t.includes('class="rcbadge"') && !t.includes('class="jrc"'), "ref card: crop is an overlay on the image + a ✂ badge, no second preview");
  ok(!t2.includes("rcrop") && !t2.includes("rcbadge"), "ref card: no crop, no overlay");
  ok(t.includes('class="rline"') && t.includes('title="the shop sign → the sign"') && t.includes('class="rwho">→ the sign') && t.includes(">the shop sign<"), "ref card: one caption line = note + → target pill (full text on hover)");
  ok(t2.includes("no note") && !t2.includes("rwho"), "ref card: empty note placeholder, no target pill for the lead");
  ok(/class="rtop"><button data-refedit="edit"[^>]*>✎<\/button><button data-refedit="ask"[^>]*>＋<\/button><button class="jrefdel"/.test(t), "ref card: ✎ / ＋ Ask / 🗑 in the image corner");
  const ed = t.slice(t.indexOf('class="redit"'));
  ok(ed.includes("data-jrsave") && ed.includes('class="jrw"') && ed.includes("data-jcrop=\"mv:900-k\"") && ed.includes('data-mvrefask="900-k"') && ed.includes('data-draft="mvrefask:900-k:' + evo + '"'), "ref card: note, Use-for, Save, ✂ crop and Ask live in the ✎ panel (drafts kept)");
  ok(!t.includes("jrcap\" title") || t.indexOf('class="redit"') > t.indexOf('class="rline"'), "ref card: panel comes after the caption line");
  T.refEditOpen.add("mv:900-k|" + evo);
  ok(T.refThumb(mv, evo, "mv:900-k").includes('rcard mvref open"') && T.refThumb(mv, evo, "mv:900-k").includes('aria-expanded="true"') && !t2.includes(" open\""), "ref card: the open ✎ panel survives a re-render");
  T.refEditOpen.clear();
  const g = T.refCropRect([0.25, 0.1, 0.75, 0.6], 100, 100, 200, 250);  // square picture in a 4:5 area: contain leaves 25px bands top and bottom
  ok(Math.abs(g.left - 25) < 1e-9 && Math.abs(g.width - 50) < 1e-9 && Math.abs(g.top - (25 + 0.1 * 200) / 250 * 100) < 1e-9 && Math.abs(g.height - 100 / 250 * 100) < 1e-9, "refCropRect: crop mapped onto the contained picture");
  ok(T.refCropRect([0, 0, 1, 1], 0, 0, 10, 10) === null, "refCropRect: unknown size -> null");
  ok(T.refThumb(mv, evo, "mv:900-k").includes("rtop"), "ref card tools shown");
  T.MVT.id = "900-k"; T.MVT.doneOpen = false;
  mv.gen_requests = [{id: "g1", text: "Alice full body", status: "open", for: "Alice"}, {id: "g2", text: "the sign", status: "done", result: "musicvideos/900-k/refs/gen_1.png", reply: "added"}, {id: "g3", text: "a mic", status: "done", src: evo}, {id: "g4", text: "gone", status: "cancelled"}];
  let gb = T.mvGenBox(mv);
  ok(gb.includes('class="rq"') && gb.includes("⏳") && gb.includes("Alice full body") && gb.includes("for Alice") && gb.includes('data-mvgencancel="g1"'), "request chips: open request = ⏳ chip with ✖");
  ok(gb.includes('data-mvgen="done"') && gb.includes("✓ 2 requests added ▸") && !gb.includes("a mic") && !gb.includes("<img"), "done requests collapse into one toggle, no thumbnails");
  ok(!gb.includes("gone"), "cancelled requests stay hidden");
  T.MVT.doneOpen = true; gb = T.mvGenBox(mv);
  ok(gb.includes("▾") && gb.includes("a mic") && gb.includes("from x.png") && gb.includes('class="rq done"') && !gb.includes("<img"), "expanded: done requests as plain chips (their image is already a card)");
  T.MVT.doneOpen = false;
  const j0 = T.JRN[0];
  if (j0) { const jt = T.refThumb(j0, (j0.refs || [j0.source])[0]); ok(jt.includes('class="rcell"') && jt.includes("class=\"redit\"") && !jt.includes("fbbar") && !jt.includes("data-refedit=\"ask\""), "journey ref: same card, no toolbar, no Ask"); }
}
{  // a cleared crop / note must leave the page too (mv.json drops the empty dicts)
  const id = "900-c"; T.MVS = [{id, refs: ["a.png"], ref_crop: {"a.png": [0.1, 0.1, 0.5, 0.5]}, ref_notes: {"a.png": "x"}, markers: [], storyboards: []}];
  T.mvById = {[id]: T.MVS[0]};
  T.mvMerge({id, refs: ["a.png"], markers: []});
  ok(!T.mvById[id].ref_crop["a.png"] && !T.mvById[id].ref_notes["a.png"], "mvMerge: server-cleared crop and note leave the page");
  T.MVS = []; T.mvById = {};
}
{  // storyboard frames get the same image tools as journey scenes
  const f = "../musicvideos/001-x/sb01/s3.png";
  ok(T.fixAreaBtn(f).includes("data-fixarea") && T.rerollBtn(f) && T.upscaleBtn(f) && T.refitCtl(f).includes("data-refit"), "sbNN frames: Fix area, reroll, upscale, refit");
  ok(!T.fixAreaBtn("../musicvideos/001-x/audio/cover.png"), "no Fix area on non-frame images");
}
{  // 🕘 past revisions: chip on tiles/scenes, lightbox button, compare view, filmstrip order, restore wiring
  const cur = "../evolutions/999-rv/v01/f-x_seed1001.png", sc = "../journeys/998-rv/ch01/s3.png", mv = "../musicvideos/997-rv/sb01/s1.png";
  const mk = (dir, stem, ts) => ({src: `../${dir}/_rerolled/${stem}__${ts.replace(/[-\/ :]/g, "").replace(/^(\d{8})/, "$1-")}.png`, ts});
  T.REVS["evolutions/999-rv/v01/f-x_seed1001.png"] = [mk("evolutions/999-rv/v01", "f-x_seed1001", "2026/02/02 02:02:02"), mk("evolutions/999-rv/v01", "f-x_seed1001", "2026/01/01 01:01:01")];
  T.REVS["journeys/998-rv/ch01/s3.png"] = [mk("journeys/998-rv/ch01", "s3", "2026/03/03 03:03:03")];
  T.REVS["musicvideos/997-rv/sb01/s1.png"] = [mk("musicvideos/997-rv/sb01", "s1", "2026/04/04 04:04:04")];
  ok(T.revsOf(cur).length === 2 && T.revsOf(cur + "?v=3").length === 2 && T.revsOf("../evolutions/999-rv/v01/none.png").length === 0, "revsOf: keyed like fbKey (?v= ignored), empty when none");
  ok(T.revChip(cur).includes('data-revs="../evolutions/999-rv/v01/f-x_seed1001.png"') && T.revChip(cur).includes("🕘 2") && T.revChip("../evolutions/999-rv/v01/none.png") === "", "chip: 🕘 N on images with revisions only");
  ok(T.fbBar(cur, "c").includes("revchip") && T.fbBar(sc, "c").includes("🕘 1") && T.fbBar(mv, "c").includes("🕘 1") && !T.fbBar("../evolutions/999-rv/v01/none.png", "c").includes("revchip"), "tiles, journey scenes and music-video frames carry the chip via fbBar");
  ok(T.revBtn(cur).includes("2 earlier versions") && T.revBtn(sc).includes("1 earlier version<") || T.revBtn(sc).includes("1 earlier version\""), "lightbox button: pluralised count");
  ok(T.revBtn("../evolutions/999-rv/v01/none.png") === "", "no button without revisions");
  // compare view
  Object.assign(T.RV, {src: cur, i: 0, mode: "side", old: false, wipe: 50, busy: false, msg: ""});
  let h = T.revViewHtml(cur, 0, "side", T.RV);
  ok(h.includes("Current") && h.includes("Earlier · 2026/02/02 02:02:02") && h.includes("1 of 2 earlier versions") && h.includes("_rerolled/f-x_seed1001__20260202-020202.png"), "side by side: current + the chosen earlier version with its timestamp");
  const strip = [...h.matchAll(/data-rvpick="(\d+)"[^>]*title="([^"]+)"/g)].map(m => m[1] + "@" + m[2]);
  ok(strip.join(",") === "0@2026/02/02 02:02:02,1@2026/01/01 01:01:01", "filmstrip: newest first, one thumb per revision with timestamps: " + strip);
  ok(/rvthumb on" data-rvpick="0"/.test(h) && /data-rvstep="-1" disabled/.test(h) && !/data-rvstep="1" disabled/.test(h), "first version selected: Newer disabled, Older enabled");
  ok(h.includes("data-rvrestore") && h.includes("data-rvclose") && h.includes('data-rvmode="flip"') && h.includes('data-rvmode="wipe"'), "restore, close and flip/wipe modes are offered");
  ok(/src="\/thumb\/evolutions\/999-rv\/v01\/_rerolled\/f-x_seed1001__20260202-020202.png/.test(h), "filmstrip uses /thumb/ WebP thumbnails; the compare uses the full PNG");
  const hf = T.revViewHtml(cur, 1, "flip", {...T.RV, old: true}), hw = T.revViewHtml(cur, 1, "wipe", {...T.RV, wipe: 30});
  ok(hf.includes("data-rvflip") && hf.includes("Earlier · 2026/01/01 01:01:01") && /data-rvstep="1" disabled/.test(hf), "flip mode: click target, caption follows the state, last version disables Older");
  ok(hw.includes("data-rvwipe") && hw.includes("inset(0 70% 0 0)"), "wipe mode: slider + clip at 30%");
  ok(T.revViewHtml(cur, 5, "side", T.RV).includes("No earlier versions"), "out-of-range index renders a safe message");
  // open / step
  T.revOpen(cur, 0);
  ok(globalThis.document.querySelector("#revs").classList.contains("show") && globalThis.document.querySelector("#revs .rvbox").innerHTML.includes("1 of 2"), "revOpen shows the overlay with version 1");
  T.revPick(1); ok(T.RV.i === 1 && globalThis.document.querySelector("#revs .rvbox").innerHTML.includes("2 of 2"), "stepping to the next version repaints");
  T.revPick(2); T.revPick(-1); ok(T.RV.i === 1, "stepping past either end is ignored");
  // restore wiring: POSTs key + the archive path, then mirrors the swap locally
  let sent = null;
  global.fetch = async (u, o) => { sent = {u, body: JSON.parse(o.body)}; return {ok: true, json: async () => ({ok: true, archived: "f-x_seed1001__20260930-120000.png", ts: "2026/09/30 12:00:00", mtime: 1790000000})}; };
  T.revPick(0);
  T.revRestore().then(() => {
    ok(sent && sent.u === "/api/revision/restore" && sent.body.src === "evolutions/999-rv/v01/f-x_seed1001.png" && sent.body.rev === "evolutions/999-rv/v01/_rerolled/f-x_seed1001__20260202-020202.png", "restore POSTs {src, rev} as project-relative keys");
    const rl = T.revsOf(cur);
    ok(rl.length === 2 && rl[0].ts === "2026/09/30 12:00:00" && rl[0].src.endsWith("_rerolled/f-x_seed1001__20260930-120000.png") && rl[1].ts === "2026/01/01 01:01:01", "after restore: the replaced picture leads the list, the restored one is gone (undoable)");
    ok(T.MTIMES["evolutions/999-rv/v01/f-x_seed1001.png"] === 1790000000 && T.RV.i === 0 && !T.RV.busy && /Restored/.test(T.RV.msg), "after restore: mtime bumped (fresh ?v=), selection reset, message shown");
    global.fetch = async () => ({ok: false, status: 400, json: async () => ({error: "bad revision"})});
    return T.revRestore();
  }).then(() => {
    ok(/refused: bad revision/.test(T.RV.msg) && !T.RV.busy && T.revsOf(cur).length === 2, "a refused restore shows the error and changes nothing");
    delete T.REVS["evolutions/999-rv/v01/f-x_seed1001.png"]; delete T.REVS["journeys/998-rv/ch01/s3.png"]; delete T.REVS["musicvideos/997-rv/sb01/s1.png"];
    global.fetch = () => new Promise(() => {});
  });
}
{  // 📝 the prompt behind a clip
  const v = {src: "../musicvideos/900-p/sb01/s1__fasth3_seed1.mp4", poster: "../musicvideos/900-p/sb01/s1.png", image: "musicvideos/900-p/sb01/s1.png", lineage: "900-p", version: "sb01", title: "P", journey: false, mv: "900-p",
    depth: 0, subject: "f-modern", subject_label: "x", engine: "fasth3", tag: "", prompt: "a slow push-in <b>", note: "", created: 1};
  T.VIDS.push(v);
  { const h = T.clipPrompt(v.src); ok(h.includes("cprompt") && h.includes("<pre>"), "clip panel shows the clip's full prompt"); }
  T.VIDS.splice(T.VIDS.indexOf(v), 1);
  ok(T.clipPrompt("../nope.mp4") === "", "no prompt block for an unknown clip");
}
{  // 🖼 storyboard frame as the music video's cover
  const id = "900-cv"; T.MVS = [{id, title: "C", refs: [], markers: [], storyboards: [], cover: "musicvideos/900-cv/sb01/s2.png"}]; T.mvById = {[id]: T.MVS[0]};
  ok(T.coverBtn("../musicvideos/900-cv/sb01/s2.png").includes("Cover ✓") && T.coverBtn("../musicvideos/900-cv/sb01/s3.png").includes("Set as cover"), "cover button: current vs set");
  ok(!T.coverBtn("../evolutions/001-x/v01/a.png"), "no cover button outside music videos");
  ok(T.mvListPage().includes("900-cv/sb01/s2.png"), "the list card uses the chosen cover");
  T.MVS = []; T.mvById = {};
}
{  // 🎞 Final cut section
  const ok4 = (c, m) => ok(c, "final cut: " + m), id = "900-fc";
  const mk = fc => ({id, title: "Fc <Song>", refs: [], markers: [], audio: "musicvideos/900-fc/audio/song.wav", storyboards: [{id: "sb01", title: "sb", scenes: [{id: "s1", src: "../musicvideos/900-fc/sb01/s1.png", t0: 0, t1: 5}]}], final_cut: fc});
  const cuts = [{n: 1, frame: "s1", kind: "clip", engine: "fasth3", fit: "trim", t0: 0, t1: 9, song_t0: 0, song_t1: 6, in: "cut", in_dur: 0, look: "now", fx: ["dust"], why: "drums in"},
    {n: 2, frame: "s3", kind: "sing", engine: "ltxia2v", fit: "sing-placed", t0: 9, t1: 14, song_t0: 6, song_t1: 11, in: "dissolve", in_dur: 1, look: "memory", fx: [], why: "NOW -> MEMORY <b>"},
    {n: 3, frame: "s4", kind: "still", engine: null, fit: "still-kenburns", t0: 14, t1: 20, song_t0: 11, song_t1: 17, in: "flash", in_dur: 0.125, look: "now", fx: [], why: "the drop"}];
  const latest = {src: "../musicvideos/900-fc/cut/song-draft.mp4", mtime: 1790000000, draft: true, duration: 216.7, w: 1280, h: 720, counts: {cut: 12, dissolve: 11, flash: 1}, build_seconds: 70, strip: "../musicvideos/900-fc/cut/kiss-draft_strip.jpg", cuts};
  const hB = T.mvById, hM = T.MVS;
  T.mvById = {[id]: mk({latest, status: {state: "done"}, edit: []})}; T.MVS = [T.mvById[id]];
  let h = T.mvCutSection(T.mvById[id]);
  ok4(h.includes("🎞 Final cut") && h.includes('data-mvasm="draft"') && h.includes('data-mvasm="full"') && h.includes("Build draft") && h.includes("Build full quality"), "title + both build buttons");
  ok4(/<video class="mvcutv" src="..\/musicvideos\/900-fc\/cut\/song-draft.mp4\?v=1790000000"/.test(h) && h.includes('data-jclipv="../musicvideos/900-fc/cut/song-draft.mp4"'), "player of the latest cut (cache-busted by mtime, position kept over redraws)");
  ok4(h.includes('data-fb="love"') && h.includes('data-fb="nope"') && h.includes('data-src="../musicvideos/900-fc/cut/song-draft.mp4"') && h.includes('data-draft="image:musicvideos/900-fc/cut/song-draft.mp4"'), "❤ / 👎 + comment thread keyed by the cut mp4 path");
  ok4((h.match(/<tr><td>\d/g) || []).length === 3 && h.includes("fade to black") === false && h.includes("dissolve 1.00 s") && h.includes("white flash 0.13 s") && h.includes("ltxia2v 🎤") && h.includes(">still<"), "edit list: one row per cut with transition + duration, singing marked, stills named");
  ok4(h.includes("memory") && h.includes("now + dust") && h.includes("NOW -&gt; MEMORY &lt;b&gt;"), "look, fx and the escaped why");
  ok4(h.includes("12 cut, 11 dissolve, 1 white flash") && h.includes("Draft 1280×720") && h.includes("0:216".slice(0, 0) + "3:36.7"), "counts + built summary");
  ok4(!/data-mvasm="draft" disabled/.test(h), "buttons enabled when idle");
  T.mvById[id].final_cut.status = {state: "running", stage: "rendering piece 4/28 (s4)", draft: true};
  h = T.mvCutSection(T.mvById[id]);
  ok4(/data-mvasm="draft" disabled/.test(h) && /data-mvasm="full" disabled/.test(h) && h.includes("rendering piece 4/28 (s4)") && T.mvCutBusy(T.mvById[id]), "building: buttons disabled, stage shown");
  T.mvById[id].final_cut.status = {state: "queued"}; ok4(T.mvCutSection(T.mvById[id]).includes("Queued…"), "queued status");
  T.mvById[id].final_cut.status = {state: "error", error: "ffmpeg failed <x>"}; h = T.mvCutSection(T.mvById[id]);
  ok4(h.includes("Build failed: ffmpeg failed &lt;x&gt;") && !/data-mvasm="draft" disabled/.test(h), "error shown escaped, buttons usable again");
  T.mvById[id].final_cut = {latest: null, status: null, edit: [{frame: "s1", t0: 0, t1: 6, in: {type: "cut", dur: 0}, look: "now", fx: ["dust"], why: "plan"}, {frame: "s2", t0: 6, t1: 9, in: {type: "fadeblack", dur: 0.8}, look: "memory", fx: [], why: "p2"}]};
  h = T.mvCutSection(T.mvById[id]);
  ok4(!h.includes("<video") && h.includes("Not built yet") && h.includes("2 cuts") && h.includes("fade to black 0.80 s") && h.includes("<details class=\"mvedl\" open>"), "no cut yet: the plan from edit.json, open");
  T.mvById[id].final_cut = null; ok4(T.mvCutSection(T.mvById[id]).includes("Build a draft") && !T.mvCutSection(T.mvById[id]).includes("<table"), "no edit list, no cut: just the build buttons");
  T.mvById[id].storyboards = []; ok4(T.mvCutSection(T.mvById[id]) === "", "hidden without a storyboard");
  T.mvById[id] = mk({latest, status: {state: "done"}}); ok4(T.mvPage(id).includes("🎞 Final cut") && T.mvPage(id).indexOf("Final cut") < T.mvPage(id).indexOf("Storyboards"), "on the music-video page, before the storyboards");
  T.mvById = hB; T.MVS = hM;
}
{  // 🔍 loupe window while dragging a marker edge
  const [a, b] = T.mvLoupeSpan(100, 200, 1000);  // 5 px/s timeline, 8x zoom, 240 px loupe = 6 s
  ok(Math.abs((b - a) - 6) < 1e-9 && Math.abs((a + b) / 2 - 100) < 1e-9, "loupe shows 1/8 of the timeline's scale, centred on the edge");
  const [c] = T.mvLoupeSpan(1, 200, 1000), [, d2] = T.mvLoupeSpan(199.5, 200, 1000);
  ok(c === 0 && Math.abs(d2 - 200) < 1e-9, "loupe window clamps inside the song");
}
{  // 🌌 Explore: tab, start / continue / countdown states, episode page, the player's markup, the knob + wheel value mapping
  const ok5 = (c, m) => ok(c, "explore: " + m);
  const near = (a, b, e = 1e-9) => Math.abs(a - b) < e;
  // 🧠 Emotion Atlas (replaces the 8-emotion wheel): complex, media-real emotional concepts on a valence x arousal map
  const E = T.XAE, EFE = ["valence", "arousal", "intimacy", "temporal", "moral_weight", "agency", "absurdity"];
  ok5(E.nodes.length >= 58 && new Set(E.nodes.map(n => n.family)).size >= 10 && E.edges.length >= E.nodes.length, "emotion atlas: loaded from the payload, 58+ nodes in 10+ families, synapses between them: " + E.nodes.length);
  ok5(["bittersweet", "nostalgia", "saudade", "mono-no-aware", "hiraeth", "catharsis", "found-family-warmth", "slow-burn-tension", "unrequited-love", "forbidden-love", "heartbreak", "survivor-s-guilt", "righteous-fury", "revenge", "redemption", "betrayal",
    "dread", "existential-dread", "cosmic-horror", "sublime-terror", "awe", "wonder", "whimsy", "absurdity", "cozy-comfort", "ennui", "defiance", "liberation", "hope-against-the-odds", "triumph", "jealousy", "shame", "pride", "camaraderie", "loneliness",
    "tenderness", "wanderlust", "homesickness", "grief", "serenity", "euphoria", "melancholy", "longing", "tension", "joy"].every(id => E.by[id]), "emotion atlas: every concept from the brief is a node");
  ok5(T.XE_LEGACY.length === 8 && T.XE_LEGACY.every(id => E.by[id] && E.by[id].legacy), "emotion atlas: the 8 old wheel emotions are legacy nodes (same ids) for migration");
  ok5(E.nodes.every(n => EFE.every(k => n.features[k] >= 0 && n.features[k] <= 1) && n.picture && n.voice && n.beats && Math.hypot(n.x, n.y) <= 1.0001) && E.edges.every(e => e.w >= 0.1 && e.w <= 1 && E.by[e.a] && E.by[e.b]), "emotion atlas: every node has 7 features 0-1, picture + voice + beats lines, sits inside the unit disc; synapses 0.1-1");
  { const cor = (xs, ys) => { const n = xs.length, mx = xs.reduce((a, b) => a + b) / n, my = ys.reduce((a, b) => a + b) / n; let sxy = 0, sxx = 0, syy = 0; xs.forEach((x, i) => { sxy += (x - mx) * (ys[i] - my); sxx += (x - mx) ** 2; syy += (ys[i] - my) ** 2; }); return sxy / Math.sqrt(sxx * syy); };
    ok5(cor(E.nodes.map(n => n.x), E.nodes.map(n => n.features.valence)) > 0.85 && cor(E.nodes.map(n => n.y), E.nodes.map(n => n.features.arousal)) > 0.6, "emotion layout: valence runs left to right, arousal bottom to top");
    ok5(E.by["joy"].x > 0.5 && E.by["grief"].x < -0.4 && E.by["righteous-fury"].y > 0.6 && E.by["serenity"].y < 0 && E.by["ennui"].y < -0.7, "emotion layout: joy right, grief left, righteous fury high, serenity and ennui low"); }
  { const n = E.by["saudade"], v = T.xaValueAt(n.x + 0.01, n.y, E), brute = E.nodes.map(m => [Math.hypot(m.x - n.x - 0.01, m.y - n.y), m.id]).sort((a, b) => a[0] - b[0]).slice(0, 3).map(a => a[1]);
    ok5(v.blend.length === 3 && Math.abs(v.blend.reduce((s, b) => s + b.w, 0) - 1) < 1e-9 && JSON.stringify(v.blend.map(b => b.id)) === JSON.stringify(brute) && v.blend[0].id === "saudade" && v.valence >= 0 && v.valence <= 1 && v.arousal >= 0 && v.arousal <= 1 && !("level" in v), "emotion value: the 3 nearest nodes, whole percents, valence + arousal of the blend: " + JSON.stringify(v.blend)); }
  { const z = T.xaValueAt(0, 0, E);
    ok5(JSON.stringify(z) === JSON.stringify(T.xeNeutral()) && z.blend.length === 0 && z.genre === null && T.xeWord(z).startsWith("neutral") && T.xeIntensityWord(z) === "no steer", "emotion: the centre is neutral (no blend, no steer)");
    const st = E.by["bittersweet"], bv = T.xaValueAt(st.x, st.y, E);
    ok5(/^Bittersweet \d+% · .+ \d+% · .+ \d+%$/.test(T.xeWord(bv)) && T.xeHint(bv).includes(st.picture) && /captions: /.test(T.xeHint(bv)) && /^(subtle|moderate|strong) \d+%$/.test(T.xeIntensityWord(bv)), "emotion readout: 'Bittersweet 4x% · … · …', the picture line, the caption voice, intensity: " + T.xeWord(bv)); }
  { const m = T.xeNorm({primary: "awe", secondary: "wonder", mix: 0.3, intensity: 0.8}), l = T.xeNorm({primary: "longing", secondary: "melancholy", mix: 0.3, intensity: 0.8});
    ok5(m.blend.length === 2 && m.blend[0].id === "awe" && m.blend[1].id === "wonder" && m.blend[0].w === 0.7 && m.intensity === 0.8 && m.legacy === true && T.xeWord(m) === "Awe 70% · Wonder 30%" && JSON.stringify(T.xeNorm(m)) === JSON.stringify(m), "migration: an old wheel value (awe -> wonder) lands on those legacy nodes and is stable: " + T.xeWord(m));
    ok5(l.blend[0].id === "longing" && l.blend[1].id === "melancholy" && l.valence > 0.2 && l.valence < 0.5 && l.intensity === 0.8, "migration: longing / melancholy 70/30 -> " + T.xeWord(l));
    ok5(JSON.stringify(T.xeNorm({primary: null, secondary: null, mix: 0, intensity: 0})) === JSON.stringify(T.xeNeutral()) && JSON.stringify(T.xeNorm({primary: "joy", intensity: 0})) === JSON.stringify(T.xeNeutral()) && JSON.stringify(T.xeNorm(null)) === JSON.stringify(T.xeNeutral()) && JSON.stringify(T.xeNorm("junk")) === JSON.stringify(T.xeNeutral()), "migration: neutral / zero-intensity / junk = neutral");
    const keep = JSON.stringify(T.XC.emotion); T.XC.emotion = T.xeNeutral(); T.xcAdopt({primary: "dread", secondary: null, mix: 0, intensity: 0.7}, T.XAE);
    ok5(T.XC.emotion.blend.length === 1 && T.XC.emotion.blend[0].id === "dread" && T.XC.emotion.intensity === 0.7, "migration: a saved wheel value is adopted onto the atlas"); T.XC.emotion = JSON.parse(keep); }
  ok5(T.xTint({probe: {x: 0, y: 0}, blend: [], intensity: 0}) === "rgb(244,239,230)" && T.xTint(T.xaValueAt(E.by["joy"].x, E.by["joy"].y, E)) !== "rgb(244,239,230)" && T.xTint(T.xaValueAt(E.by["grief"].x, E.by["grief"].y, E)) !== T.xTint(T.xaValueAt(E.by["joy"].x, E.by["joy"].y, E)), "caption tint from an atlas value: neutral = warm white, joy and grief differ");
  ok5(T.xFade(T.xeNeutral()) === 1 && T.xFade(T.xaValueAt(E.by["ennui"].x, E.by["ennui"].y, E)) > 1 && T.xFade(T.xaValueAt(E.by["euphoria"].x, E.by["euphoria"].y, E)) < 1, "dissolve from an atlas value: calm = slower, intense = quicker");
  // 🧩 emotional cores: saved probe points that stack (up to 5), weighted, reorderable, resolvable
  { const at = id => T.xaValueAt(E.by[id].x, E.by[id].y, E), W = T.xcoresWeightAt;
    let r = T.xcoresAdd([], T.xeNeutral()); ok5(!r.added && r.cores.length === 0 && /neutral/.test(r.reason), "cores: the neutral centre cannot be added");
    r = T.xcoresAdd([], at("saudade")); ok5(r.added && r.added.weight === 0.6 && r.added.status === "active" && r.added.name === "Saudade" && r.added.blend[0].id === "saudade" && r.cores.length === 1, "cores: add saves the probe + blend, name = the top node, default weight 0.6");
    let cs = r.cores; r = T.xcoresAdd(cs, at("saudade")); ok5(!r.added && /already a core/.test(r.reason) && r.cores.length === 1, "cores: the same feeling is not added twice");
    for (const id of ["grief", "defiance", "tenderness", "wanderlust"]) { r = T.xcoresAdd(cs, at(id)); cs = r.cores; }
    ok5(cs.length === 5 && T.xcoresActive(cs).length === 5 && new Set(cs.map(c => c.id)).size === 5, "cores: five active, unique ids");
    r = T.xcoresAdd(cs, at("triumph")); ok5(!r.added && r.cores.length === 5 && /limit/.test(r.reason), "cores: a sixth active core is refused (max 5)");
    const g = cs[1].id; cs = T.xcoresEdit(cs, g, {weight: 0.9, name: "Dear Grief"}); ok5(cs[1].weight === 0.9 && cs[1].name === "Dear Grief" && cs[0].weight === 0.6, "cores: weight + rename edit one core");
    ok5(W(0.62) === 0.6 && W(0.68) === 0.7 && W(-1) === 0 && W(5) === 1 && W(0.5) === 0.5, "cores: the drag-bar snaps to 5% steps within 0-1");
    cs = T.xcoresMove(cs, g, 0); ok5(cs[0].id === g && cs.length === 5, "cores: reorder (drag) moves a core to a new place");
    cs = T.xcoresMove(cs, g, 99); ok5(cs[4].id === g, "cores: reorder clamps to the end");
    r = T.xcoresResolve(cs, g, true); cs = r.cores; ok5(r.ok && T.xcoresActive(cs).length === 4 && cs[cs.length - 1].id === g || cs.find(c => c.id === g).status === "resolved", "cores: resolve retires a core out of the active list");
    r = T.xcoresAdd(cs, at("triumph")); ok5(r.added && T.xcoresActive(r.cores).length === 5, "cores: a slot freed by resolving can be reused");
    const full = r.cores; ok5(!T.xcoresResolve(full, g, false).ok, "cores: reopening a resolved core needs a free slot");
    cs = T.xcoresRemove(full, g); ok5(cs.length === full.length - 1 && !cs.some(c => c.id === g), "cores: remove");
    ok5(T.xcoresClean(JSON.parse(JSON.stringify(full))).length === full.length && T.xcoresClean([{name: "x"}, null, 3, {blend: []}]).length === 0 && T.xcoresSig(full) === T.xcoresSig(JSON.parse(JSON.stringify(full))), "cores: clean keeps good ones and drops junk; signature is stable");
    const six = Array.from({length: 7}, (_, i) => ({id: "k" + i, name: "n" + i, ...at(["joy", "grief", "awe", "dread", "serenity", "pride", "shame"][i]), status: "active", weight: 0.5}));
    ok5(T.xcoresActive(T.xcoresClean(six)).length === 5, "cores: loading 7 active ones keeps 5");
    // the DOM markup
    const keepC = T.XC.cores, keepE = T.XC.emotion; T.XC.cores = full; T.XC.emotion = at("saudade"); const h = T.xCoresHtml();
    ok5(h.includes("data-xcadd") && h.includes("＋ Add as core") && (h.match(/data-xcw/g) || []).length === 5 && h.includes("data-xcgrip") && h.includes("data-xcname") && h.includes("data-xcdel") && h.includes("data-xcres") && h.includes("data-xcgo") && h.includes("1 resolved"), "cores markup: add button, a weight drag-bar + grip + rename + resolve + remove on every row, resolved ones folded");
    T.XC.cores = []; ok5(T.xCoresHtml().includes("No cores yet"), "cores markup: empty state"); T.XC.cores = keepC; T.XC.emotion = keepE;
    // per saga: opening the home loads the current saga's cores; a different saga id re-syncs; a saga without cores keeps the deck's
    const keepS = T.SAGAS, k0 = [T.XC.cores, T.XC.maturity, T.XC.coresSaga]; T.XC.coresSaga = "";
    T.SAGAS = [{id: "900-test", title: "T", chapters: [], cast: [], cores: [{id: "c1", name: "Saved grief", probe: at("grief").probe, blend: at("grief").blend, weight: 0.8, status: "active", history: [{chapter: "ch01", beat: "x"}]}], maturity: {stop: 2, label: "Family"}}];
    ok5(T.xcSyncSaga() === true && T.XC.cores.length === 1 && T.XC.cores[0].name === "Saved grief" && T.XC.cores[0].weight === 0.8 && T.XC.maturity.label === "Family" && T.XC.coresSaga === "900-test", "per saga: the home page loads the current saga's cores + maturity from its bible");
    ok5(T.xcSyncSaga() === false, "per saga: ... once (your edits on the deck stay)");
    T.XC.cores = [{id: "mine", name: "Mine", ...at("joy"), status: "active", weight: 0.4}]; T.SAGAS = [{id: "901-new", title: "N", chapters: [], cast: [], cores: []}];
    ok5(T.xcSyncSaga() === true && T.XC.cores[0].id === "mine" && T.XC.coresSaga === "901-new", "per saga: a new saga without cores starts with the deck's");
    T.SAGAS = keepS; [T.XC.cores, T.XC.maturity, T.XC.coresSaga] = k0; }
  // 🌀 gravity + repulsor: a view-only warp of the map (long hold = pull, right-click hold = push), springing back on release
  { const mk = (x, y) => ({hx: x, hy: y, x, y, vx: 0, vy: 0}), d = (n, w) => Math.hypot(n.x - w.x, n.y - w.y), run = (ns, well, secs, opt) => { for (let t = 0; t < secs; t += 0.016) T.atlasForceStep(ns, well, 0.016, opt); };
    let ns = [mk(0.3, 0), mk(0.35, 0.2), mk(-0.4, 0.2), mk(1.4, 1.4)], well = {x: 0, y: 0, mode: 1, k: 1}, d0 = ns.map(n => d(n, well));
    run(ns, well, 1, {}); ok5(ns.slice(0, 3).every((n, i) => d(n, well) < d0[i] * 0.5), "gravity: nearby nodes slide toward the well (halved their distance in 1 s): " + ns.slice(0, 3).map((n, i) => d0[i].toFixed(2) + "->" + d(n, well).toFixed(2)).join(" "));
    ok5(Math.hypot(ns[3].x - ns[3].hx, ns[3].y - ns[3].hy) < 0.01, "gravity: a far node (beyond the disc) is not affected");
    ns = [mk(0.3, 0), mk(0.5, 0.3), mk(-0.4, 0.2)]; well = {x: 0, y: 0, mode: -1, k: 1}; d0 = ns.map(n => d(n, well)); run(ns, well, 1, {});
    ok5(ns.every((n, i) => d(n, well) > d0[i] + 0.05), "repulsor: nodes are pushed away from the pointer");
    ns = [mk(0.3, 0)]; well = {x: 0, y: 0, mode: 1, k: 0}; run(ns, well, 1, {}); ok5(Math.abs(ns[0].x - 0.3) < 1e-9, "no force until the hold has ramped up (k = 0)");
    ok5(T.xfFall(0) === 1 && T.xfFall(T.XF_R) > 0.3 && T.xfFall(T.XF_R) < 0.6 && T.xfFall(0.9) < 0.1 && T.xfFall(1) === 0 && T.xfFall(0.2) > T.xfFall(0.5), "falloff: strongest at the pointer, about half at R, gone at the rim");
    ok5(T.xfRamp(0) === 0 && T.xfRamp(5) === 1 && T.xfRamp(0.3) < 0.2 && T.xfRamp(0.6) < T.xfRamp(0.9) && T.xfRamp(0.9) < 1, "force ramps up with the hold time (ease-in, capped at 1)");
    const ws = pull => { const a = [mk(0.2, 0.1), mk(-0.5, -0.3), mk(0.6, 0.5)]; run(a, {x: 0, y: 0, mode: pull ? 1 : -1, k: 1}, 1, {}); return a; };
    ns = ws(true); const warped = ns.map(n => ({...n})); run(ns, null, 1.2, {});
    ok5(ns.every((n, i) => Math.hypot(n.x - n.hx, n.y - n.hy) < Math.hypot(warped[i].x - warped[i].hx, warped[i].y - warped[i].hy) * 0.2 + 0.03), "spring-back: after about 1.2 s the nodes are (nearly) home");
    run(ns, null, 2.5, {}); ok5(ns.every(n => Math.hypot(n.x - n.hx, n.y - n.hy) < 0.004 && Math.hypot(n.vx, n.vy) < 0.004), "spring-back converges to rest at the home positions");
    ns = ws(true); ns.forEach(n => { n.vx = 0; n.vy = 0; }); const kept = ns.map(n => [n.x, n.y]); run(ns, null, 3, {keep: true}); ok5(ns.every((n, i) => Math.abs(n.x - kept[i][0]) < 0.02 && Math.abs(n.y - kept[i][1]) < 0.02), "keep shape: with the spring off the warped arrangement stays");
    ns = [mk(0.3, 0), mk(0.31, 0.01)]; run(ns, {x: 0.3, y: 0, mode: 1, k: 1}, 1.5, {}); ok5(Math.hypot(ns[0].x - ns[1].x, ns[0].y - ns[1].y) > 0.03, "pulled-in nodes keep a little room (no single dot)");
    // the blend is read from the DISPLACED positions, and a value taken from a warped map keeps its blend
    const F = T.XAF, far = F.by["rave"];
    const before = T.xaValueAt(far.x, far.y, F); F.off = {}; F.off["black-tie"] = [far.x - F.by["black-tie"].x, far.y - F.by["black-tie"].y]; F.off["sleepover"] = [far.x - F.by["sleepover"].x + 0.02, far.y - F.by["sleepover"].y];
    const wv = T.xaValueAt(far.x, far.y, F), ids2 = wv.blend.map(b => b.id);
    ok5(ids2.includes("black-tie") && ids2.includes("sleepover") && ids2.includes("rave") && !before.blend.map(b => b.id).includes("black-tie") && wv.warped === true && T.xaWarped(F), "pulling Black tie and Sleepover onto Rave makes the three share the blend (read from the displaced positions): " + T.xfWord(wv));
    ok5(JSON.stringify(T.xvNorm(wv, F)) === JSON.stringify(wv), "a value taken from a warped map keeps its blend when it is normalised");
    F.off = {}; ok5(JSON.stringify(T.xvNorm(wv, F)) === JSON.stringify(wv) && !T.xaWarped(F) && T.xaValueAt(far.x, far.y, F).warped === undefined, "... also after the nodes spring home (the kept value is the one that is sent); the plain map reports no warp");
    // the real loop: a physics tick under a held well moves the node and the probe takes the warped blend; after release everything springs home and stops
    { const A = T.XAE, id = "joy", n = A.by[id]; A.off = {}; A.vel = {}; A.well = {x: n.x - 0.2, y: n.y, mode: 1, k: 0, t0: performance.now() - 1500, pid: 1};
      let moving = true; for (let i = 0; i < 40 && moving; i++) moving = T.xaPhysics(A, 0.016);
      const o = A.off[id]; ok5(o && o[0] < -0.02 && T.xaWarped(A) && T.XC.emotion.warped === true, "xaPhysics: a held well on the map moves the node and the probe takes the warped blend");
      A.well = null; for (let i = 0; i < 600 && moving; i++) moving = T.xaPhysics(A, 0.016);
      ok5(!moving && !T.xaWarped(A) && Object.keys(A.off).length === 0, "xaPhysics: after release everything springs home and the loop stops (nothing keeps moving)");
      A.keep = true; A.off[id] = [0.3, 0.1]; T.xaWarpSave(A); T.xaWarpClear(A); ok5(!A.keep && !T.xaWarped(A), "reset clears the warp and keep"); T.XC.emotion = T.xeNeutral(); }
    // persistence per viewer per atlas, tolerant of a broken store
    { const A = T.XAF; A.keep = true; A.off = {"rave": [0.25, -0.1], "ghost": [1, 1]}; T.xaWarpSave(A); const raw = JSON.parse(localStorage.getItem("xwarp:formality"));
      ok5(raw.keep === true && raw.off.rave[0] === 0.25, "keep shape: the offsets are saved per viewer in localStorage (xwarp:formality)");
      A.off = {}; A.keep = false; A.warpLoaded = false; T.xaWarpLoad(A); ok5(A.keep === true && A.off.rave && A.off.rave[1] === -0.1 && !A.off.ghost, "... and restored on the next visit (unknown nodes ignored)");
      localStorage.setItem("xwarp:formality", "{{broken"); A.off = {}; A.keep = false; A.warpLoaded = false; T.xaWarpLoad(A); ok5(A.keep === false && !T.xaWarped(A), "a broken store is ignored");
      T.xaWarpClear(A); ok5(localStorage.getItem("xwarp:formality") === null, "clearing the warp removes the saved offsets"); A.warpLoaded = true; }
    // markup: hint, keep toggle, reset, factory reset with the two-click confirm
    const mh = T.xMapHtml(T.XAE), mf = T.xMapHtml(T.XAF);
    ok5([mh, mf].every(h => h.includes("hold to pull · right-click to push") && h.includes("data-xakeep") && h.includes("data-xawarp") && h.includes("data-xareset") && h.includes("📌 keep shape") && h.includes("↺ reset") && h.includes("⟲ Factory reset") && !h.includes("data-xaremove")), "map markup (both atlases): the hold / right-click hint, 📌 keep shape, ↺ reset, ⟲ Factory reset");
    const m = {confirm: null}, t0 = 1000000;
    ok5(T.xaResetStep(m, t0) === "armed" && m.confirm.until === t0 + 4000 && m.confirm.remove === false, "factory reset: the first click only arms it (4 s), 'also remove neurons added later' is OFF");
    ok5(T.xaResetStep(m, t0 + 3999) === "do", "factory reset: a second click inside 4 s does it");
    const m2 = {confirm: {until: t0 + 4000, remove: true}}; ok5(T.xaResetStep(m2, t0 + 4001) === "armed" && m2.confirm.remove === false, "factory reset: the confirmation times out after 4 s (back to armed-from-scratch)");
    T.XAE.m.confirm = {until: Date.now() + 4000, remove: false}; const ch = T.xMapBtnsHtml(T.XAE); T.XAE.m.confirm = null;
    ok5(ch.includes("Reset to defaults? click again") && ch.includes("data-xaremove=\"emotion\"") && ch.includes("also remove neurons added later") && !/data-xaremove="emotion" checked/.test(ch), "factory reset: the armed state asks again and offers the unticked 'also remove neurons added later' box"); }
  // 🎚 maturity dial: 7 discrete stops, a vintage channel selector
  ok5(T.xdStops().length === 7 && T.xdStops().map(s => s.label).join("|") === "Preschool|Kids|Family|Tween|Teen|Young adult|Mature", "maturity: the 7 stops, Preschool .. Mature");
  ok5(T.xdStops().every(s => s.feels_like && s.story && s.pictures && s.ceiling) && /Saturday-morning/.test(T.xdStops()[1].feels_like) && /PG-13/.test(T.xdStops()[4].feels_like) && /literary adult/.test(T.xdStops()[6].feels_like), "maturity: each stop has feels_like / story / pictures / ceiling (from tools/maturity.py via the payload)");
  ok5(/no sexual content/i.test(T.XMAT.ceiling) && /no graphic gore/i.test(T.XMAT.ceiling) && /only between adults/i.test(T.XMAT.ceiling) && /fully clothed/i.test(T.XMAT.ceiling) && /no on-screen injury or blood/i.test(T.XMAT.ceiling), "maturity: the hard ceiling text travels with the payload");
  ok5(T.xdSnap(2.4) === 2 && T.xdSnap(2.6) === 3 && T.xdSnap(-4) === 0 && T.xdSnap(99) === 6 && T.xdSnap("x") === 0, "maturity: discrete detents only (rounds to a whole stop, clamped 0-6)");
  ok5(T.xdAngle(0) === -130 && T.xdAngle(3) === 0 && T.xdAngle(6) === 130 && near(T.xdAngle(1) - T.xdAngle(0), 260 / 6), "maturity: the pointer sweeps -130 .. +130 degrees in equal steps");
  ok5(T.xdFromPointer(0, -50) === 3 && T.xdFromPointer(-50, 0) === 1 && T.xdFromPointer(50, 0) === 5 && T.xdFromPointer(-30, 30) === 0 && T.xdFromPointer(30, 30) === 6, "maturity: an absolute rotary (up = Tween, left = Kids, right = Young adult, the bottom corners = the ends)");
  ok5(T.xdFromPointer(-1, 50) === 0 && T.xdFromPointer(1, 50) === 6 && T.xdFromPointer(-40, -40) === 2 && T.xdFromPointer(40, -40) === 4, "maturity: dead zone at the bottom snaps to the nearer end; diagonals pick Family / Teen");
  ok5(JSON.stringify(T.xdNorm(2)) === '{"stop":2,"label":"Family"}' && T.xdNorm("Young adult").stop === 5 && T.xdNorm({stop: 9}).label === "Mature" && T.xdNorm(null).stop === 4 && T.xdNorm("zzz").label === "Teen" && T.xdWord({stop: 0}) === "Preschool" && /toddler/.test(T.xdHint(0)), "maturity: normalising numbers / labels / objects / junk (default Teen)");
  { const h = T.xDialHtml(); ok5(h.includes('class="xdial"') && h.includes('role="slider"') && h.includes('aria-valuemax="6"') && T.xdStops().every(s => h.includes(`>${s.label}</text>`)) && (h.match(/data-xdv=/g) || []).length === 14 && /mature themes only/i.test(h) && /no sexual content/i.test(h) && /no graphic gore/i.test(h) && /fully clothed/i.test(h),
      "maturity markup: the dial with 7 printed stops, tick + label each, and the hard ceiling in plain sight"); }
  // presence knob: detents, sweep, drag
  ok5(T.xkSnap(48) === 50 && T.xkSnap(52) === 50 && T.xkSnap(56) === 56 && T.xkSnap(22) === 25 && T.xkSnap(-9) === 0 && T.xkSnap(130) === 100, "knob clicks into the detents (0 25 50 75 100) within 5, free between");
  ok5(T.xkAngle(0) === -135 && T.xkAngle(50) === 0 && T.xkAngle(100) === 135, "dial sweeps -135 .. +135 degrees");
  ok5(T.xkDrag(50, 0, -20) === 60 && T.xkDrag(50, 0, -200) === 100 && T.xkDrag(50, 0, 200) === 0 && T.xkDrag(50, 20, 0) === 60, "drag up or right = more epic, down or left = more intimate, clamped");
  ok5(T.xkWord(0) === "Intimate" && T.xkWord(50) === "Filmic" && T.xkWord(100) === "Epic" && T.xkWord(25) === "Leaning intimate" && T.xkWord(75) === "Leaning epic", "knob words");
  ok5(/close, quiet, personal pictures/.test(T.xkHint(0)) && /composed, classic framing/.test(T.xkHint(50)) && /vast, dramatic, grand pictures/.test(T.xkHint(100)), "knob hints describe the pictures, not camera moves");
  // 🧠 Formality Atlas (replaces the joypad stick): neurons + synapses, probe -> blend, migration, search, glide, reveal, labels, markup
  const A = T.XA, sl = s => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, ""), FE = ["rigidity", "hierarchy", "ritual", "ornament", "tradition", "publicness", "intimacy", "chaos"];
  ok5(A.nodes.length >= 48 && A.edges.length >= A.nodes.length && new Set(A.nodes.map(n => n.family)).size >= 6, "atlas: loaded from the payload, 48+ neurons in 6+ families, synapses between them");
  ok5(["white-tie", "coronation", "family-sunday-dinner", "rave", "perfect-symmetry", "punk", "liturgical", "tea-ceremony", "brutalist-civic"].every(id => A.by[id]) && T.XF_RIM.every(n => A.by[sl(n)]) && A.by["everyday"], "atlas: the example concepts and all 13 retired stick registers are neurons");
  ok5(A.nodes.every(n => FE.every(k => n.features[k] >= 0 && n.features[k] <= 1) && n.picture && n.voice && Math.hypot(n.x, n.y) <= 1.0001) && A.edges.every(e => e.w >= 0.1 && e.w <= 1 && A.by[e.a] && A.by[e.b]), "atlas: every neuron has 8 features 0-1, a picture + voice line and sits inside the unit disc; synapses 0.1-1");
  ok5(A.by["everyday"].x === 0 && A.by["everyday"].y === 0 && A.nodes.filter(n => n.features.rigidity >= 0.8).reduce((s, n) => s + n.y, 0) > 0 && A.by["coronation"].y > 0.7 && A.by["sleepover"].y < -0.2, "atlas layout: Everyday at the centre, the formal region up, casual below");
  { const n = A.by["black-tie"], v = T.xaValueAt(n.x + 0.01, n.y), brute = A.nodes.map(m => [Math.hypot(m.x - n.x - 0.01, m.y - n.y), m.id]).sort((a, b) => a[0] - b[0]).slice(0, 3).map(a => a[1]);
    ok5(v.blend.length === 3 && Math.abs(v.blend.reduce((s, b) => s + b.w, 0) - 1) < 1e-9 && JSON.stringify(v.blend.map(b => b.id)) === JSON.stringify(brute) && v.blend[0].id === "black-tie" && v.blend[0].w >= v.blend[1].w && v.blend[1].w >= v.blend[2].w, "probe -> blend: the 3 nearest neurons, weights sum to 1, strongest first: " + T.xfWord(v));
    ok5(v.genre === "Black tie" && v.secondary === v.blend[1].name && v.mix > 0 && v.mix <= 0.5 && ["probe", "blend", "genre", "secondary", "mix", "intensity", "level", "formality_level"].every(k => k in v), "value keeps the old keys: genre = top name, secondary, mix <= 0.5"); }
  { const v = T.xaValueAt(0.3, 0.5), lo = T.xaValueAt(0, -5), far = T.xaValueAt(3, 0);
    ok5(v.level === 50 && v.formality_level === 75 && v.intensity === 0.58 && lo.level === -100 && lo.formality_level === 0 && lo.probe.y === -1 && far.probe.x === 1 && far.intensity === 1, "level comes from y (-100 casual .. +100 formal), intensity = distance from the centre, the probe clamps to the disc"); }
  { const z = T.xaValueAt(0, 0);
    ok5(JSON.stringify(z) === JSON.stringify(T.xfNeutral()) && z.genre === "Everyday" && z.intensity === 0 && z.level === 0 && z.formality_level === 50 && T.xfWord(z) === "Everyday · neutral", "the centre = Everyday, neutral"); }
  { const n = T.xfNorm, N0 = JSON.stringify(T.xfNeutral());
    ok5(JSON.stringify(n(50)) === N0 && n(100).blend[0].id === "courtly" && n(100).level > 60 && n(0).blend[0].id === "feral" && n(0).level < -30 && n(83).blend[0].id === "martial" && n(17).blend[0].id === "street", "migration: old numbers 0-100 -> the neuron of the nearest old register");
    const st = n({genre: "Martial", secondary: "Diplomatic", mix: 0.3, intensity: 0.9, level: 40, formality_level: 70});
    ok5(st.blend.some(b => b.id === "martial") && ["martial", "diplomatic"].includes(st.blend[0].id) && st.level > 40 && st.probe && st.blend.length === 3, "migration: an old stick object (Martial -> Diplomatic) lands between those two neurons");
    ok5(JSON.stringify(n(null)) === N0 && JSON.stringify(n("x")) === N0 && JSON.stringify(n({genre: "Bogus", intensity: 1})) === N0 && JSON.stringify(n({genre: "Martial", intensity: 0})) !== "", "migration: junk -> neutral");
    const p = n({probe: {x: 0.2, y: 0.4}}); ok5(JSON.stringify(p) === JSON.stringify(T.xaValueAt(0.2, 0.4)) && JSON.stringify(n(p)) === JSON.stringify(p) && JSON.stringify(n(n(st))) === JSON.stringify(n(st)), "norm: a saved probe is re-derived from the atlas and the result is stable");
    const b = n({blend: [{id: "rave", w: 0.5}, {id: "punk", w: 0.5}]}); ok5(b.blend.some(x => x.id === "rave" || x.id === "punk") && b.probe, "norm: a blend without a probe is placed at its weighted centre"); }
  ok5(T.xaFind("funeral").id === "state-funeral" && T.xaFind("Coronation").id === "coronation" && T.xaFind("tea ceremony").score === 1 && T.xaFind("feeling of a wedding").id === "wedding" && T.xaFind("bioluminescent jellyfish") === null && T.xaFind("") === null && T.xaFind("   ") === null, "search: fuzzy-matches a neuron by name / words; nothing close = null (the agent is asked to map it)");
  ok5(T.xaScore("slang", A.by["slang"]) === 1 && T.xaScore("state funerals", A.by["state-funeral"]) > 0.8 && T.xaScore("xyzzy", A.by["slang"]) < 0.55, "search score: exact 1, plural still close, nonsense low");
  { const p = T.xaPath("white-tie", "rave"), ek = new Set(A.edges.map(e => e.a < e.b ? e.a + "|" + e.b : e.b + "|" + e.a));
    ok5(p[0] === "white-tie" && p[p.length - 1] === "rave" && p.length >= 3 && p.slice(1).every((id, i) => ek.has(p[i] < id ? p[i] + "|" + id : id + "|" + p[i])), "glide path: runs along existing synapses and ends on the target (" + p.join(" > ") + ")");
    ok5(JSON.stringify(T.xaPath("rave", "rave")) === '["rave"]' && T.xaPath("rave", "nope").length === 0, "glide path: same node, unknown node");
    const keep = {nodes: A.nodes, edges: A.edges}, mk = id => ({id, name: id, family: "t", picture: "p", voice: "v", features: {}, x: 0.1, y: 0.1});
    T.xaSet({nodes: [mk("a"), mk("b"), mk("c")], edges: [{a: "a", b: "b", w: 1}, {a: "b", b: "c", w: 1}, {a: "a", b: "c", w: 0.1}]});
    ok5(JSON.stringify(T.xaPath("a", "c")) === '["a","b","c"]', "glide path: strong synapses are short (a-b-c at w 1 beats the direct a-c at w 0.1)");
    T.xaSet({nodes: [mk("a"), mk("b")], edges: []}); ok5(T.xaPath("a", "b").length === 0, "glide path: disconnected = no route"); T.xaSet(keep); }
  { const f0 = T.XC.formality; T.XC.formality = T.xfNeutral(); const pl = T.xmPlan("rave"), ek = new Set(A.edges.map(e => e.a < e.b ? e.a + "|" + e.b : e.b + "|" + e.a));
    ok5(pl && pl.ids[pl.ids.length - 1] === "rave" && pl.pts.length === pl.ids.length + 1 && pl.pts[0].x === 0 && pl.pts[0].y === 0 && pl.edges.every(k => ek.has(k)) && T.xmPlan("nope") === null, "glide plan: probe -> nearest neuron -> along the edges -> target, lighting each edge");
    T.XC.formality = f0; }
  { const c = A.nodes.find(n => Math.hypot(n.x, n.y) < 0.01), r = A.nodes.reduce((b, n) => Math.hypot(n.x, n.y) > Math.hypot(b.x, b.y) ? n : b), eg = A.edges.reduce((b, e) => e.w > b.w ? e : b);
    ok5(T.xaNodeAlpha(c, 0) === 0 && T.xaNodeAlpha(c, 0.4) === 1 && T.xaNodeAlpha(r, 0.3) === 0 && T.xaNodeAlpha(r, 0.9) === 1 && T.xaNodeAlpha(r, 99) === 1, "reveal: neurons fade in from the centre outward (the rim last), all there by 0.9 s");
    ok5(A.edges.every(e => T.xaEdgeGrow(e, 0) === 0 && T.xaEdgeGrow(e, 1.6) === 1) && A.edges.every(e => T.xaEdgeGrow(e, 0.9) <= T.xaEdgeGrow(e, 1.1)) && A.edges.some(e => T.xaEdgeGrow(e, 0.6) > 0) && A.edges.some(e => T.xaEdgeGrow(e, 0.6) === 0), "reveal: synapses grow outward after the neurons, every one complete by ~1.6 s");
    ok5(T.xaNodeAlpha(r, 99, 0) === 0 && T.xaNodeAlpha(r, 99, 0.35) === 0.5 && T.xaNodeAlpha(r, 99, 5) === 1 && T.xaEdgeGrow(eg, 99, 0.2) === 0 && T.xaEdgeGrow(eg, 99, 5) === 1, "reveal: a neuron added later draws itself in from its birth, its synapses after it"); }
  { const L = T.xaPlaceLabels([{id: "a", w: 60, h: 13, x: 100, y: 100, pri: 3}, {id: "b", w: 60, h: 13, x: 104, y: 102, pri: 2}, {id: "c", w: 60, h: 13, x: 108, y: 98, pri: 1}, {id: "d", w: 60, h: 13, x: 4, y: 4, pri: 0.5}], 320, 320);
    const hit = (p, q) => p.x < q.x + 60 && q.x < p.x + 60 && p.y < q.y + 13 && q.y < p.y + 13;
    ok5(L.length >= 3 && L[0].id === "a" && L.every((p, i) => L.every((q, j) => i === j || !hit(p, q))) && L.every(p => p.x >= 2 && p.y >= 2 && p.x + 60 <= 318 && p.y + 13 <= 318), "labels: no overlaps, inside the canvas, highest priority first (no label soup)"); }
  { const calls = {}, gr = {addColorStop() {}}, ctx = new Proxy({}, {get: (t, k) => k === "createRadialGradient" || k === "createLinearGradient" ? () => gr : k === "measureText" ? () => ({width: 44}) : (...a) => { calls[k] = (calls[k] || 0) + 1; }, set: () => true});
    A.m.t0 = performance.now() - 5000;  /* the reveal animation is long over */ T.xmDraw(ctx, 320, 320, 1234); ok5(calls.arc >= A.nodes.length && calls.stroke >= A.edges.length && calls.fillText >= 8 && calls.save === calls.restore, "canvas draw: a full frame (neurons, synapses, labels, probe) runs without error"); }
  { const f0 = T.XC.formality; T.XC.formality = T.xaValueAt(A.by["black-tie"].x + 0.02, A.by["black-tie"].y); const d = T.xMapHtml();
    ok5(d.includes('<canvas id="xmap"') && d.includes('role="application"') && d.includes('id="xasearch"') && d.includes("Find a feeling of formality…") && d.includes('id="xago"') && d.includes("Black tie") && /level \+\d+/.test(d) && d.includes('id="xatlas-hint"') && !d.includes("xstick") && !/camera|zoom|Ken Burns/i.test(d), "map markup: canvas, search box, readout of the blend with the level, hint line");
    ok5(/^Black tie \d+% · .+ \d+% · .+ \d+%$/.test(T.xfWord(T.XC.formality)) && T.xfHint(T.XC.formality).includes(A.by["black-tie"].picture) && / captions$/.test(T.xfHint(T.XC.formality)), "readout: 'Black tie 48% · … · …' and the top neuron's picture + caption voice");
    T.XC.formality = T.xfNeutral(); ok5(T.xMapHtml().includes("Everyday · neutral") && T.xfHint(T.xfNeutral()).includes("relaxed but composed"), "map markup: centre = Everyday, neutral"); T.XC.formality = f0; }
  { const at = id => T.xaValueAt(A.by[id].x, A.by[id].y), tier = id => T.xfCap(at(id)).tier;
    ok5(tier("coronation") === "ceremonial" && tier("high-mass") === "ceremonial" && tier("white-tie") === "formal" && tier("boardroom") === "formal" && tier("rave") === "casual" && tier("sleepover") === "casual" && tier("feral") === "casual" && tier("smart-casual") === "natural" && T.xfCap(T.xfNeutral()).tier === "natural", "caption typography from the top neuron's features: rigid + ritual = ceremonial, rigid = formal, loose / chaotic / intimate = casual");
    ok5(/small-caps/.test(T.xfCap(at("coronation")).css) && /Palatino/.test(T.xfCap(at("coronation")).css) && /font-weight:300/.test(T.xfCap(at("rave")).css) && T.xfCap(0).tier === "casual" && /font-weight:300/.test(T.xfCap(0).css) && T.xfCap(50).tier === "natural" && T.xfCap(50).css === "" && T.xfCap(100).tier === "formal" && /small-caps/.test(T.xfCap(100).css) && T.xfCap(undefined).tier === "natural", "typography: atlas values and old numbers (old episodes)");
    ok5(T.xfCap({genre: "Courtly", intensity: 1, level: 100}).tier === "ceremonial" && T.xfCap({genre: "Feral", intensity: 0.8}).tier === "casual", "typography: an old stick value in an old episode.json still gets its type");
    ok5(!/animation|transform|translate|scale|zoom/i.test(T.xfCap(0).css + T.xfCap(100).css + T.xfCap(at("coronation")).css), "typography only, no motion"); }
  { const d = T.xTuneHtml(); ok5(d.indexOf("xknob") < d.indexOf('class="xdial"') && d.indexOf('class="xdial"') < d.indexOf('id="xmap-emotion"') && d.indexOf('id="xmap-emotion"') < d.indexOf("data-xcadd") && d.indexOf("data-xcadd") < d.indexOf('id="xmap"') && d.includes("Emotion atlas") && d.includes("Formality atlas") && d.includes("Maturity") && !d.includes("xwheel") && !d.includes("xstick") && !/camera|zoom|\bpan\b|Ken Burns/i.test(d), "control deck: presence knob, maturity dial, Emotion atlas + cores row, Formality atlas");
    ok5(d.includes('class="xmaps"') && d.indexOf('class="xmaps"') < d.indexOf('id="xmap-emotion"') && d.indexOf('id="xmap-emotion"') < d.indexOf('id="xmap"') && d.includes('id="xasearch-emotion"') && d.includes('id="xasearch"') && d.includes('id="xago-emotion"') && d.includes("Find a feeling… (bittersweet"), "control deck: two atlases side by side in one responsive grid, each with its own probe canvas + find box"); }
  // player knobs: hold time, caption tint, dissolve speed (nothing moves)
  ok5(T.xpHold(6, 0) === 8 && T.xpHold(6, 50) === 6 && T.xpHold(6, 100) === 4 && T.xpHold(6, undefined) === 6 && T.xpHold(1, 100) === 2, "intimate = longer holds, epic = shorter (min 2 s)");
  ok5(T.xTint(null) === "rgb(244,239,230)" && T.xTint({primary: "dread", secondary: null, mix: 0, intensity: 0}) === "rgb(244,239,230)" && T.xTint({primary: "dread", secondary: null, mix: 0, intensity: 1}) === "rgb(243,179,179)", "caption tint: warm white, pulled to the emotion by its intensity");
  ok5(T.xFade(null) === 1 && T.xFade({primary: "serenity", intensity: 1}) === 1.7 && T.xFade({primary: "tension", intensity: 1}) === 0.65 && T.xFade({primary: "tension", intensity: 0}) === 1, "calm emotions dissolve slowly, tense ones quicker");
  // fixtures
  const hb = T.EXPL, hs = T.EXST.state;
  const sh = (id, src, extra) => ({id, prompt: "p " + id, caption: "cap " + id, aspect: "16:9", hold: 6, src, mtime: 0, ...extra});
  const ep = {id: "900-test-ep", title: "The Lighthouse <Keeper>", topic: "Lights at the edge", premise: "a night on the rock", status: "done", created: "2026/10/01 12:00:00", presence: 20, emotion: {primary: "serenity", secondary: null, mix: 0, intensity: 0.6},
    cover: "../explore/900-test-ep/e1.png", shots: [sh("e1", "../explore/900-test-ep/e1.png"), sh("e2", "../explore/900-test-ep/e2.png", {aspect: "9:16"}), sh("e3", null)]};
  T.EXPL = [ep, {...ep, id: "899-b", title: "B", status: "rendering", cover: null, shots: [sh("e1", null)]}];
  // tab + routing helpers
  location.hash = "#/explore/900-test-ep";
  T.layerNav();
  const nav = els["#layers"].innerHTML;
  ok5(nav.includes('href="#/nev"') && /📖 Nev Novel \d+/.test(nav) && /class="on"[^>]*>📖 Nev Novel/.test(nav) && !/class="on">Survey/.test(nav), "header tab 📖 Nev Novel (count, highlighted on its pages, not Survey)");
  location.hash = "#/nev/900-test-ep"; T.layerNav();
  ok5(/class="on"[^>]*>📖 Nev Novel/.test(els["#layers"].innerHTML), "the #/nev address highlights the tab too (#/explore is the old alias)");
  location.hash = "";
  ok5(T.cmLabel("image:explore/900-test-ep/e3.png") === "Explore shot 900-test-ep/e3" && T.cmLink("image:explore/900-test-ep/e3.png") === "#/nev/900-test-ep" && T.cmLink("explore:900-test-ep") === "#/nev/900-test-ep", "comment labels + links for shots and episodes");
  ok5(T.fbKey("../explore/900-test-ep/e3.png?v=5") === "explore/900-test-ep/e3.png" && T.isExpl("../explore/900-test-ep/e3.png") && !T.isExpl("../journeys/x/ch01/s1.png"), "marks use keys explore/...png");
  // bar states
  T.EXST.state = null;
  ok5(T.exploreBar().includes("Loading"), "bar: loading before the first poll");
  T.xApply({active: false, reason: "idle", left: 0, until: 0, presence: null, emotion: null});
  let h = T.exploreBar(true);
  ok5(h.includes('data-xop="start"') && h.includes("▶ Start a Nev Novel") && h.includes('id="xseed"') && !h.includes('data-xop="stop"') && !h.includes('data-xop="continue"'), "idle: big Start button + optional seed box");
  ok5(h.includes('class="xknob"') && h.includes('class="xdial"') && h.includes('id="xmap-emotion"') && h.includes('id="xmap"') && h.includes("Cinematic presence") && h.includes("Emotion atlas") && h.includes("Maturity") && h.includes('role="slider"'), "idle: every tactile control is there");
  ok5(["intimate", "Intimate", "Filmic", "Epic"].every(w => h.includes(w)) && ["Preschool", "Kids", "Family", "Tween", "Teen", "Young adult", "Mature"].every(w => h.includes(`>${w}</text>`)), "knob labels + the seven maturity stops are printed round the dial");
  ok5(!/camera|zoom|\bpan\b|Ken Burns/i.test(h), "UI words are about the pictures, not camera moves");
  T.xApply({active: true, reason: "", left: 761, until: 0, presence: 50, emotion: null});
  h = T.exploreBar();
  ok5(h.includes("Nev Novel running") && h.includes('id="xleft">12:41<') && h.includes('data-xop="stop"') && h.includes('data-xop="tune"') && h.includes("Apply") && !h.includes('data-xop="start"'), "active: countdown 12:41, Stop, Apply");
  T.EXST.deadline = Date.now() + 5000;
  ok5(T.exploreBar().includes('id="xleft">0:05<') && T.xFmt(65) === "1:05" && T.xFmt(0) === "0:00" && T.xFmt(-3) === "0:00" && T.xFmt(600) === "10:00", "countdown formatting");
  T.xApply({active: false, reason: "timer", left: 0, until: 1, presence: 50, emotion: null});
  h = T.exploreBar();
  ok5(h.includes("Paused after 15 min") && h.includes("Continue the novel") && h.includes('data-xop="continue"') && !h.includes('data-xop="stop"'), "timer ran out: prominent Continue (must be pressed) + an optional Start a new novel");
  T.xApply({active: false, reason: "stopped", left: 0, until: 1, presence: null, emotion: null});
  ok5(T.exploreBar(true).includes('data-xop="start"') && !T.exploreBar().includes('data-xop="start"'), "after Stop: Start again (home page only)");
  // Apply lights up when the controls differ from what the agent was given
  // match every deck value (cores / maturity / formality come from the live payload otherwise)
  T.xApply({active: true, reason: "", left: 100, until: 0, presence: 50, emotion: T.xeNeutral(), cores: T.XC.cores, maturity: T.XC.maturity, formality: T.XC.formality});
  T.XC.presence = 50; T.XC.emotion = T.xeNeutral();
  ok5(!/xapply dirty/.test(T.exploreBar()), "Apply is quiet while the controls match the server");
  T.XC.formality = T.xaValueAt(0.6, 0.3);
  ok5(/xapply dirty/.test(T.exploreBar()), "Apply is highlighted when the probe moved");
  T.XC.formality = T.xfNeutral();
  T.XC.presence = 80;
  ok5(/xapply dirty/.test(T.exploreBar()), "Apply is highlighted when the knob moved");
  T.XC.presence = 50; T.XC.emotion = {primary: "joy", secondary: null, mix: 0, intensity: 0.5};
  ok5(/xapply dirty/.test(T.exploreBar()), "... or the emotion probe");
  T.XC.emotion = T.xeNeutral(); T.XC.maturity = {stop: 1, label: "Kids"};
  ok5(/xapply dirty/.test(T.exploreBar()), "... or the maturity dial"); T.XC.maturity = T.xdNorm(null);
  { const k0 = T.XC.cores; T.XC.cores = T.xcoresAdd([], T.xaValueAt(T.XAE.by["saudade"].x, T.XAE.by["saudade"].y, T.XAE)).cores;
    ok5(/xapply dirty/.test(T.exploreBar()), "... or a core was added"); T.XC.cores = k0; }
  T.XC.emotion = T.xeNeutral();
  // list + episode pages
  h = T.exploreListPage();
  ok5(h.includes("📖 Nev Novel") && h.includes('data-go="#/nev/900-test-ep"') && h.includes("The Lighthouse &lt;Keeper&gt;") && h.includes("✓ ready · 3 shots") && h.includes("🎨 rendering 0/1") && h.includes("Lights at the edge"), "list: cover cards with title (escaped), status, topic");
  h = T.explorePage("900-test-ep");
  ok5(h.includes("The Lighthouse &lt;Keeper&gt;") && h.includes('data-xplay="900-test-ep"') && !/data-xplay="900-test-ep" disabled/.test(h) && h.includes("▶ Play"), "episode: title + Play button");
  ok5(h.includes('data-xshot="../explore/900-test-ep/e1.png"') && h.includes("⏳ e3 not rendered yet") && h.includes("cap e1") && h.includes("cap e2"), "episode: shots in order with captions, unrendered ones marked");
  ok5(h.includes('data-fb="love"') && h.includes('data-fb="nope"') && h.includes('data-src="../explore/900-test-ep/e1.png"') && h.includes("data-reroll=") && !h.includes('data-fb="cast"') && !h.includes("data-pin=") && !h.includes("data-explore="), "episode: ❤ 👎 💬 + 🎲 on shots, no 👥 / 📌 / 🧭");
  ok5(h.includes('data-draft="explore:900-test-ep"'), "episode: comment thread");
  ok5(T.explorePage("899-b").includes("disabled") && T.explorePage("nope").includes("Unknown episode"), "no pictures yet: Play disabled; unknown id handled");
  // the cinematic player: stills only
  const tl = T.xpTimeline(ep);
  ok5(tl.length === 3 && tl[0].type === "title" && tl.every(x => x.type !== "end") && tl[1].src === "../explore/900-test-ep/e1.png" && tl[2].type === "shot", "timeline: title card, rendered shots only, NO end card (the stream never ends)");
  ok5(tl[0].dur === 3 && tl[1].dur === T.xpHold(6, 20) && T.xpHold(6, 20) > 6, "title 3 s, shot holds follow the presence knob (intimate 20 = longer than 6 s)");
  ok5(near(tl[1].ar, 16 / 9) && near(tl[2].ar, 9 / 16) && tl[1].fade === T.xFade(ep.emotion) && tl[1].fade > 1, "letterbox ratio per shot, crossfade from the emotion (serenity = slower than 1 s)");
  const lay = T.xpLayerHtml(tl[1]);
  ok5(lay.includes('class="xframe"') && lay.includes("<img src=") && lay.includes("cap e1") && lay.includes("color:" + T.xTint(ep.emotion)) && lay.includes("--ar:"), "shot layer: framed still + tinted caption");
  ok5(!/animation|transform|xk\d|zoom|pan/i.test(lay), "shot layer has no motion at all");
  // the narration / dialogue / caption hug the PICTURE, not the screen
  { const R = T.xpFrameRect, uw = R(16 / 9, 3440, 1440), ph = R(16 / 9, 390, 844), po = R(9 / 16, 1600, 900), ex = R(16 / 9, 1920, 1080);
    ok5(near(uw.w, 2560, 0.01) && near(uw.h, 1440, 0.01) && near(uw.x, 440, 0.01) && near(uw.y, 0, 0.01), "picture rect: 16:9 in a 3440x1440 ultrawide is pillarboxed 2560x1440 at x=440: " + JSON.stringify(uw));
    ok5(near(ph.w, 390, 0.01) && near(ph.h, 219.38, 0.01) && near(ph.x, 0, 0.01) && near(ph.y, 312.31, 0.01), "picture rect: 16:9 on a 390x844 phone is letterboxed 390x219.38 at y=312.31: " + JSON.stringify(ph));
    ok5(near(po.w, 506.25, 0.01) && near(po.h, 900, 0.01) && near(po.x, 546.88, 0.01) && near(ex.w, 1920, 0.01) && near(ex.x, 0, 0.01) && near(ex.y, 0, 0.01) && R(0, 100, 100).w === 100 && R(NaN, 1600, 900).h === 900, "picture rect: a 9:16 shot pillarboxes in 1600x900, an exact fit has no bars, junk aspect = 16:9"); }
  { const sh = T.xpLayerHtml({type: "shot", ar: 16 / 9, src: "a.png", fade: 1, tint: "rgb(1,1,1)", face: "", beats: [{kind: "narr", text: "x"}]}), cap = T.xpLayerHtml({type: "shot", ar: 16 / 9, src: "a.png", fade: 1, tint: "rgb(1,1,1)", face: "", caption: "hello"});
    ok5(/^<div class="xframe" data-ar="1\.77\d*" style="--ar:[^"]*"><img [^>]*><div class="vnnar"><\/div><div class="vnbox">.*<\/div><\/div>$/s.test(sh), "narration + dialogue boxes live INSIDE the picture frame (anchored to its edge, not the screen)");
    ok5(/^<div class="xframe"[^>]*><img [^>]*><div class="xcap"[^>]*>hello<\/div><\/div>$/s.test(cap), "the caption sits inside the picture frame too"); }
  { const fe = {...ep, formality: 100}, fl = T.xpLayerHtml(T.xpTimeline(fe)[1]), cl = T.xpLayerHtml(T.xpTimeline({...ep, formality: 0})[1]);
    ok5(fl.includes("small-caps") && cl.includes("font-weight:300") && !lay.includes("small-caps") && !lay.includes("font-weight:300"), "formality sets the caption typeface in the player"); }
  ok5(T.xpLayerHtml(tl[0]).includes("The Lighthouse &lt;Keeper&gt;") && T.xpLayerHtml(tl[0]).includes("Lights at the edge") && !/fin/.test(T.xpLayerHtml(tl[2])), "title card, no fin");
  ok5(T.xpAr("4:3") === 4 / 3 && T.xpAr(undefined) === 16 / 9 && T.xpAr("junk") === 16 / 9, "aspect parsing");
  const html = require("fs").readFileSync(process.argv[2], "utf8");
  ok5(!/@keyframes xk|\.xk0|XP_KEN/.test(html), "no Ken Burns code left in the page");
  ok5(/#xplayer \{[^}]*background: #000/.test(html) && html.includes("requestFullscreen") && html.includes("data-xp=\"prev\"") && html.includes("key === \"Escape\"") && html.includes("ArrowRight") && html.includes("touchend"), "player: black full-screen overlay, fullscreen request, prev/next buttons, keys + swipe");
  T.EXPL = hb; T.EXST.state = hs;
  function XE_NAMES_ALL() { return ["joy", "wonder", "awe", "tension", "dread", "melancholy", "longing", "serenity"]; }
}
{  // 📖 Nev Novel sagas: bible page, list order, the visual-novel line machine (typing, click sequencing, auto-advance timing), chapter cards, the endless stream
  const ok6 = (c, m) => ok(c, "novel: " + m);
  const hbE = T.EXPL, hbS = T.SAGAS, hs6 = T.EXST.state;
  const P = "../explore/sagas/900-test-saga";
  const shot = (id, ch, extra) => ({id, prompt: "p " + id, caption: "cap " + id, aspect: "16:9", hold: 6, with: [], place: "", narration: "", dialogue: [], src: `${P}/${ch}/${id}.png`, mtime: 0, ...extra});
  const mkSaga = () => ({id: "900-test-saga", title: "The Glass <Harbour>", logline: "A pilot owes the tide", created: "2026/10/01 10:00:00", style: "ink {subject}",
    world: {setting: "A drowned port city", rules: "Tides carry memory", tech_or_magic: "", tone: "wistful"},
    cast: [{name: "Mira", role: "pilot", look: "red scarf, grey eyes", voice: "dry, quick", status: "alive", first_chapter: "ch01", ref: `${P}/ch01/e2.png`, color: null, mtime: 0},
           {name: "Tobias", role: "engineer", look: "tall, soot-stained apron", voice: "", status: "injured", first_chapter: "ch01", ref: null, color: "#ffcc00", mtime: 0}],
    places: [{name: "Glass Harbour", look: "mirrored quays", first_chapter: "ch01"}], factions: [{name: "Harbour Guild", aim: "keep the sea quiet", look: "blue coats"}], lore: [{topic: "The Lull", text: "Every tenth tide is silent."}],
    threads: [{id: "t1", text: "Who cut the cable?", opened: "ch01", status: "open", closed_in: null}, {id: "t2", text: "The missing map", opened: "ch01", status: "closed", closed_in: "ch02"}],
    timeline: [{chapter: "ch01", event: "Mira reaches the harbour"}, {chapter: "ch02", event: "The map is found"}], cover: `${P}/ch01/e1.png`,
    chapters: [
      {id: "ch01", num: 1, title: "Arrival", summary: "Mira arrives.", status: "done", presence: 20, emotion: {primary: "serenity", secondary: null, mix: 0, intensity: 0.6}, formality: null, shots: [
        shot("e1", "ch01", {narration: "The harbour was glass at dawn.", dialogue: [{who: "Mira", text: "Quiet, isn't it?"}, {who: "Harbour master", text: "Too quiet.", off: true}], with: ["Mira"], place: "Glass Harbour"}),
        shot("e2", "ch01", {dialogue: [{who: "Tobias", text: "You are late."}], with: ["Tobias"]}),
        shot("e3", "ch01", {caption: "A gull over the quay"})]},
      {id: "ch02", num: 2, title: "The Map", summary: "A map.", status: "rendering", presence: 50, emotion: null, formality: null, shots: [shot("e1", "ch02", {narration: "Paper in the dark."}), shot("e2", "ch02", {src: null, narration: "Later."})]},
      {id: "ch03", num: 3, title: "Low Tide", summary: "", status: "draft", presence: 50, emotion: null, formality: null, shots: [shot("e1", "ch03", {src: null, narration: "x"})]}]});
  const sg = mkSaga(); T.SAGAS = [sg]; T.EXST.state = {active: false, reason: "idle", left: 0, until: 0, presence: null, emotion: null};
  // ---- pure reading-time + typing helpers
  ok6(T.vnTypeMs("x".repeat(100)) === 2800 && T.vnTypeMs("") === 250 && T.vnTypeMs("ab") === 250, "typing takes 28 ms per character (min 250 ms)");
  ok6(T.vnReadMs("one two three") === 1800 && T.vnReadMs(Array(50).fill("w").join(" ")) === 700 + 50 * 280 && T.vnReadMs("") === 1800, "reading time: 700 ms + 280 ms per word, at least 1.8 s");
  ok6(T.vnBeatMs("hello there") === T.vnTypeMs("hello there") + T.vnReadMs("hello there"), "auto-advance delay = typing + reading");
  ok6(T.vnTyped("hello", 0) === "" && T.vnTyped("hello", 56) === "he" && T.vnTyped("hello", 140) === "hello" && T.vnTyped("hello", 1e6) === "hello" && T.vnTyped("a😀b", 28) === "a" && T.vnTyped("a😀b", 56) === "a😀", "text types on a character at a time (emoji-safe), never past the end");
  ok6(T.vnColor("Mira", sg.cast) === T.vnColor("Mira", sg.cast) && T.vnColor("Mira", sg.cast) !== T.vnColor("Tobias", [{name: "Tobias"}]) && T.vnColor("Tobias", sg.cast) === "#ffcc00" && /^hsl\(/.test(T.vnColor("Mira", sg.cast)), "speaker colours: stable per name, a cast colour wins");
  const b1 = T.vnBeats(sg.chapters[0].shots[0], sg.cast);
  ok6(b1.length === 3 && b1[0].kind === "narr" && b1[1].kind === "say" && b1[1].who === "Mira" && !b1[1].off && b1[2].off === true, "beats: narration first, then each dialogue line (off-screen flagged)");
  ok6(T.vnBeats({narration: "  ", dialogue: [{who: "A", text: ""}]}, []).length === 0 && T.vnBeats(null, []).length === 0, "empty lines are not beats");
  ok6(JSON.stringify(T.vnAction(3, 0, false)) === '{"act":"finish"}' && JSON.stringify(T.vnAction(3, 0, true)) === '{"act":"beat","beat":1}' && JSON.stringify(T.vnAction(3, 2, true)) === '{"act":"shot"}' && JSON.stringify(T.vnBackAction(2)) === '{"act":"beat","beat":1}' && JSON.stringify(T.vnBackAction(0)) === '{"act":"prevshot"}', "click sequencing: finish the typing, next line, then next picture; back = previous line, then previous picture");
  // ---- timeline: title card, chapter cards, rendered shots only, no end card
  const tl = T.sgTimeline(sg, null, true);
  ok6(tl.map(x => x.type).join() === "title,chapter,shot,shot,shot,chapter,shot", "timeline: saga title, chapter card + its pictures, next chapter card; unrendered shots and picture-less chapters wait: " + tl.map(x => x.type).join());
  ok6(tl[1].num === 1 && tl[1].title === "Arrival" && tl[5].num === 2 && tl.every(x => x.type !== "end"), "chapter cards carry the number + title; never an end card");
  ok6(tl[2].beats.length === 3 && tl[2].caption === "" && tl[4].beats.length === 0 && tl[4].caption === "A gull over the quay", "shots with lines get the VN boxes; a silent shot keeps the old caption");
  ok6(T.sgTimeline(sg, 2, false).map(x => x.type).join() === "chapter,shot" && T.sgTimeline(sg, 2, false)[0].num === 2, "Play from a chapter: starts at that chapter card, no title card");
  ok6(tl[2].dur === T.xpHold(6, 20) && tl[2].fade === T.xFade(sg.chapters[0].emotion), "hold + crossfade still follow the chapter's steer");
  // ---- the endless stream: new pictures and whole new chapters join as they render
  ok6(T.sgMore(sg, tl).length === 0, "nothing new yet: nothing appended");
  sg.chapters[1].shots[1].src = `${P}/ch02/e2.png`;
  let more = T.sgMore(sg, tl);
  ok6(more.length === 1 && more[0].key === "ch02/e2" && more[0].beats[0].text === "Later.", "a freshly rendered picture of the running chapter is appended");
  sg.chapters[2].shots[0].src = `${P}/ch03/e1.png`;
  more = T.sgMore(sg, tl);
  ok6(more.map(x => x.type).join() === "shot,chapter,shot" && more[1].num === 3 && more[1].title === "Low Tide", "a new chapter joins with its chapter card");
  ok6(T.sgMore(sg, [...tl, ...more]).length === 0, "no duplicates once appended");
  sg.chapters[1].shots[1].src = null; sg.chapters[2].shots[0].src = null;
  // ---- pages
  let h = T.sagaPage("900-test-saga");
  ok6(h.includes("The Glass &lt;Harbour&gt;") && h.includes("A pilot owes the tide") && h.includes("▶ Play from the start") && h.includes('data-sgplay="900-test-saga"') && h.includes("3 chapters"), "saga page: title (escaped), logline, Play from the start");
  ok6(h.includes("Chapter 1 — Arrival") && h.includes("Chapter 2 — The Map") && h.includes('data-from="1"') && h.includes('data-from="2"') && /data-from="3" disabled/.test(h), "chapters with ▶ From here (disabled until a picture exists)");
  ok6(h.includes("red scarf, grey eyes") && h.includes("explore/sagas/900-test-saga/ch01/e2.png") && h.includes('sgbadge">injured') && h.includes("No reference yet") && h.includes("tall, soot-stained apron"), "bible: cast cards with the reference portrait (or a ? placeholder), status badges and looks");
  ok6(h.includes("Glass Harbour") && h.includes("mirrored quays") && h.includes("Harbour Guild") && h.includes("The Lull") && h.includes("A drowned port city") && h.includes("Tides carry memory"), "bible: world, places, factions, lore");
  ok6(h.includes("Open (1)") && h.includes("Who cut the cable?") && h.includes("Closed (1)") && h.includes("The missing map") && h.includes("Mira reaches the harbour"), "threads open / closed and the timeline");
  ok6(h.includes("The harbour was glass at dawn.") && (h.includes("Quiet, isn&#39;t it?") || h.includes("Quiet, isn't it?")), "shots list their narration + dialogue");
  ok6(h.includes("Harbour master (off-screen)") && h.includes("⏳ e2 not rendered yet"), "off-screen speakers marked; unrendered shots shown as waiting");
  ok6(h.includes('data-fb="love"') && h.includes('data-fb="nope"') && h.includes("data-reroll=") && h.includes(`data-src="${P}/ch01/e1.png"`) && !h.includes('data-fb="cast"') && !h.includes("data-pin="), "shots: ❤ 👎 + 🎲 via the usual bar, no 👥 / 📌");
  ok6(h.includes('data-draft="saga:900-test-saga"') && T.sagaPage("nope").includes("Unknown novel"), "comment thread on the novel; unknown id handled");
  ok6(T.cmLabel("image:explore/sagas/900-test-saga/ch01/e3.png") === "Saga shot 900-test-saga/ch01/e3" && T.cmLink("image:explore/sagas/900-test-saga/ch01/e3.png") === "#/nev/saga/900-test-saga" && T.cmLink("saga:900-test-saga") === "#/nev/saga/900-test-saga", "comment labels + links for saga shots");
  ok6(T.isExpl(`${P}/ch01/e1.png`), "saga shots count as explore shots for marks / reroll");
  T.EXPL = [{id: "899-one", title: "One-off", topic: "t", status: "done", created: "2026/10/01 11:00:00", cover: null, shots: []}];
  h = T.exploreListPage();
  ok6(h.indexOf("📖 Novels") >= 0 && h.indexOf("📖 Novels") < h.indexOf("One-off episodes") && h.indexOf('data-go="#/nev/saga/900-test-saga"') < h.indexOf('data-go="#/nev/899-one"'), "list: novels first, then one-off episodes");
  ok6(h.includes("3 chapters · 4/6 pictures") && h.includes("A pilot owes the tide") && h.includes("ch01/e1.png"), "list: novel card with chapter count, logline, cover");
  ok6(T.sgText(sg).includes("glass at dawn") && T.sgText(sg).includes("mira") && T.sgStatus(sg).startsWith("3 chapters"), "search text covers captions, narration, cast");
  // ---- the player machine on a tiny fake DOM, virtual clock and captured timers
  const mk = () => { const kids = {}, e = el(); e.querySelector = s => (kids[s] = kids[s] || mk()); e.querySelectorAll = () => []; e.appendChild = () => {}; e.className = ""; return e; };
  const realST = global.setTimeout, realCT = global.clearTimeout, realSI = global.setInterval, realCI = global.clearInterval, realNow = Date.now, realRAF = global.requestAnimationFrame;
  let clock = 1e6; const timers = [], ticks = [];
  global.setTimeout = (f, ms) => { timers.push({f, ms, live: true}); return timers.length; }; global.clearTimeout = id => { if (timers[id - 1]) timers[id - 1].live = false; };
  global.setInterval = f => { ticks.push(f); return ticks.length; }; global.clearInterval = id => { if (ticks[id - 1]) ticks[id - 1] = () => {}; };
  Date.now = () => clock; global.requestAnimationFrame = f => f(); global.Image = class {};
  const realCE = document.createElement; document.createElement = () => mk();
  const live = () => timers.filter(t => t.live), lastTimer = () => live().slice(-1)[0], tick = () => ticks[ticks.length - 1]();
  T.store.set("vnauto", true);
  Object.assign(T.XP, {open: true, segs: T.sgTimeline(sg, null, true), i: -1, paused: false, el: mk(), sg: "900-test-saga", beat: -1, typed: true, lay: null});
  const txt = () => T.XP.lay.querySelector(".vnbox").querySelector(".vntext"), nar = () => T.XP.lay.querySelector(".vnnar"), nameTag = () => T.XP.lay.querySelector(".vnbox").querySelector(".vnname").textContent;
  T.xpGo(0);
  ok6(T.XP.i === 0 && T.XP.segs[0].type === "title" && lastTimer().ms === 4000, "title card first; with Auto on it moves on after its 4 s");
  T.xpNext(); ok6(T.XP.i === 1 && T.XP.segs[1].type === "chapter" && lastTimer().ms === 4000, "click on a card = next; the chapter card shows 4 s: Chapter 1");
  T.xpNext();
  ok6(T.XP.i === 2 && T.XP.beat === 0 && T.XP.typed === false && nar().textContent === "", "picture e1: narration starts typing");
  clock += 28 * 10; tick(); ok6(nar().textContent === "The harbou" && T.XP.typed === false, "typing progresses with the clock: 10 characters in 280 ms");
  T.xpNext(); ok6(nar().textContent === "The harbour was glass at dawn." && T.XP.typed === true && T.XP.beat === 0, "click while typing = finish the line at once");
  ok6(lastTimer().ms === T.vnReadMs("The harbour was glass at dawn."), "then Auto waits the reading time (" + lastTimer().ms + " ms) before the next line");
  T.xpNext(); ok6(T.XP.beat === 1 && T.XP.i === 2 && nameTag() === "Mira" && txt().textContent === "", "next click = dialogue line 1 in the dialogue box, speaker tag Mira");
  clock += T.vnTypeMs("Quiet, isn't it?") + 5; tick(); ok6(T.XP.typed === true && txt().textContent === "Quiet, isn't it?" && T.XP.lay.querySelector(".vnbox").classList.contains("done"), "typed to the end: the ▼ prompt (done) shows");
  ok6(lastTimer().ms === T.vnReadMs("Quiet, isn't it?"), "auto-advance timer = reading time of that line");
  lastTimer().f(); ok6(T.XP.beat === 2 && nameTag() === "Harbour master (off-screen)", "the auto timer reads on: line 2 (off-screen voice labelled)");
  T.xpNext(); T.xpNext(); ok6(T.XP.i === 3 && T.XP.beat === 0, "after the last line the next click shows the next picture (e2)");
  T.xpPrev(); ok6(T.XP.i === 2, "back with no earlier line = previous picture");
  T.xpGo(4); ok6(T.XP.i === 4 && T.XP.beat === -1 && T.XP.lay.innerHTML.includes("xcap") && lastTimer().ms === T.xpHold(6, 20) * 1000, "silent shot: old caption style + hold-time auto-advance");
  // Auto off: nothing advances by itself
  T.store.set("vnauto", false);
  T.xpGo(1); const cardTimer = live().filter(t => t.ms === 4000).length;
  ok6(T.vnAuto() === false && T.XP.i === 1, "Auto off: stays on a card");
  T.xpGo(2); clock += 60000; tick();
  const afterType = lastTimer();
  ok6(T.XP.typed === true && !(afterType && afterType.live && afterType.ms === T.vnReadMs("The harbour was glass at dawn.")), "Auto off: a finished line sets no advance timer (the reader clicks)");
  T.store.set("vnauto", true);
  // the stream: at the end, wait; then new pictures + a new chapter appear
  const nSeg = T.XP.segs.length;
  T.xpGo(nSeg); ok6(T.XP.i !== nSeg && lastTimer().ms === 3000, "end of what exists: stays on the last picture and looks again in 3 s (no end card)");
  sg.chapters[1].shots[1].src = `${P}/ch02/e2.png`; sg.chapters[2].shots[0].src = `${P}/ch03/e1.png`;
  T.xpGo(nSeg);
  ok6(T.XP.segs.length === nSeg + 3 && T.XP.i === nSeg && T.XP.segs[nSeg].key === "ch02/e2" && T.XP.segs[nSeg + 1].type === "chapter", "new pictures and the next chapter's card are appended and shown as they render");
  T.xpGo(nSeg + 1); ok6(T.XP.segs[T.XP.i].num === 3 && T.XP.lay.innerHTML.includes("Chapter 3") && T.XP.lay.innerHTML.includes("Low Tide"), "chapter title card: Chapter 3 + its title");
  sg.chapters[1].shots[1].src = null; sg.chapters[2].shots[0].src = null;
  Object.assign(T.XP, {open: false, sg: null});
  global.setTimeout = realST; global.clearTimeout = realCT; global.setInterval = realSI; global.clearInterval = realCI; Date.now = realNow; global.requestAnimationFrame = realRAF; document.createElement = realCE;
  // ---- markup + no motion
  const htmlS = require("fs").readFileSync(process.argv[2], "utf8");
  const lay6 = T.xpLayerHtml(T.sgTimeline(sg, null, false)[1]);
  ok6(lay6.includes('class="vnnar"') && lay6.includes('class="vnbox"') && lay6.includes('class="vnname"') && lay6.includes('class="vnmore"') && lay6.includes("<img src=") && !/animation|transform|zoom|kenburns/i.test(lay6), "shot layer: full picture + narration box + dialogue box, no motion");
  ok6(/\.vnnar \{[^}]*left: 3%[^}]*top: 4%/.test(htmlS) && /\.vnbox \{[^}]*bottom: 4%/.test(htmlS) && /\.vnname \{[^}]*border: 2px solid currentColor/.test(htmlS) && /\.vnnar \{[^}]*Georgia/.test(htmlS) && /\.vnnar \{[^}]*rgba\(10,10,14,\.62\)/.test(htmlS), "CSS: narration top-left, serif, translucent; dialogue box at the bottom with a coloured name tag");
  ok6(htmlS.includes('data-xp="auto"') && htmlS.includes("vnauto") && htmlS.includes("Auto ✓") && htmlS.includes("Click / Space / → read on"), "player: Auto toggle (default on, remembered), VN key hints");
  ok6(!/@keyframes xk/.test(htmlS), "still no camera-motion keyframes");
  T.EXPL = hbE; T.SAGAS = hbS; T.EXST.state = hs6; location.hash = "";
}
