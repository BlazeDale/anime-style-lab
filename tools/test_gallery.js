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
(0, eval)(code + "\n;globalThis.__t = {get FB(){return FB},set FB(v){FB=v},overview,layerPage,videosPage,imagesPage,allImages,vidChip,byId,DATA,get VIDS(){return VIDS},store,fbKey,atCandidates,imgRef,lineageText,qTerms,journeysPage,journeyPage,get JRN(){return JRN},get jById(){return jById},set JR(v){JR=v},set BL(v){BL=v},fbBar,isBlurred,jStartBox,set jOpen(v){jOpen=v},jAnimOpen,layerNav,fdef,castMatches,get CASTOPTS(){return CASTOPTS},castName,parseSubj,treePage,treeAncestors,treeDescendants,treeSetBox,clipPanel,sceneClipChip,sceneClipBox,JCLIP,journeyReel,castNoteParse,castNoteBuild,CAST_TYPES,decideSwipe,shouldPreventMove,rectToFractions,applyDrag,cropThumb,refThumb,refCropRect,refEditOpen,mvGenBox,get TREE_EDGES(){return TREE_EDGES},fmtT,parseT,mvTimeToX,mvXToTime,mvRegion,lyricLines,mvListPage,mvPage,mvMerge,mvStatus,mvScenesOf,mvDoneCount,hideDoneBtn,headlineHtml,headlinesOn,headlineBtn,mvMarkList,mvEditHtml,MVT,refOid,refOwner,get MVS(){return MVS},set MVS(v){MVS=v},get mvById(){return mvById},set mvById(v){mvById=v},set MVR(v){MVR=v},mvSortDrop,mvDropZone,mvEdgeHit,mvShift,mvSnapBeat,fixAreaBtn,rerollBtn,upscaleBtn,refitCtl,clipPrompt,coverBtn,mvLoupeSpan,mvStemColor,mvCutSection,mvCutRows,mvCutBusy,mvLaneGeom,mvStemsInfo,mvStemsBar,mvLanesOn,mvPaint,MV_STEM_COL,mvLyricBlocks,mvLyricHit,mvPickLyric,mvLyricsBar,mvHasLyrics,mvGeo,mvReel,mvPlayBtn,sceneClips,revsOf,revChip,revBtn,revViewHtml,revOpen,revPick,revRestore,RV,get REVS(){return REVS},get MTIMES(){return MTIMES},get EXPL(){return EXPL},set EXPL(v){EXPL=v; explById=Object.fromEntries(v.map(e=>[e.id,e]))},EXST,XC,xApply,exploreBar,exploreListPage,explorePage,xpTimeline,xpLayerHtml,xpAr,xpHold,xTint,xFade,xFmt,XF_RIM,XA,xaSet,xaValueAt,xaPath,xaFind,xaScore,xaPlaceLabels,xmDraw,xMapHtml,xfNeutral,xfNorm,xfWord,xfHint,xfCap,xfLevelWord,xTuneHtml,xeNeutral,XAF,XAE,XE_LEGACY,xvNorm,xeNorm,xeWord,xeHint,xeIntensityWord,xdNorm,xdSnap,xdAngle,xdFromPointer,xdWord,xdHint,xdStops,get XMAT(){return XMAT},xDialHtml,xcoresClean,xcoresAdd,xcoresEdit,xcoresRemove,xcoresResolve,xcoresMove,xcoresWeightAt,xcoresSig,xcoresActive,xCoresHtml,xcSyncSaga,XCORE_MAX,xcDirty,xcAdopt,xcSetV,xcSetMaturity,xcAddCore,xpFrameRect,xpFit,xaP,xaWarped,xaResetStep,xMapBtnsHtml,xSurprise,XSUR_WHERE,xpCopy,xpDragData,xpPrefetchFile,xpRetryUrl,xpRetryDelay,xpTimerState,xpQueueLine,xpQueueRows,xpEngRow,xpPosText,xpBacklog,xpChatToggle,XNW,xoCands,xoHubs,xoTree,xoBlend,xoValue,xoSt,xoTurn1,xoTurnP,xoTurnM,xoLock,xoLockedP,xoCandsDeep,xoCentre,xoClick,xoPos,xoTick,xoNext,xoLabelLook,xoLabelDim,xoState,xoDecks,xoOrbit,xoEdge,xoRoute,XO,xkSnap,xkAngle,xkWord,xkHint,isExpl,cmLabel,cmLink,get SAGAS(){return SAGAS},set SAGAS(v){SAGAS=v; sagaById=Object.fromEntries(v.map(g=>[g.id,g]))},sagaPage,sgTimeline,sgMore,sgStatus,sgText,sgShots,vnBeats,vnAction,vnBackAction,vnTypeMs,vnReadMs,vnBeatMs,vnTyped,vnColor,vnHue,XP,xpNext,xpPrev,xpGo,xpExtend,xpBoot,sgOpen,bindSaga,vnShowBeat,vnArm,vnAuto,xpArm,xpClose,subjMatch,showGroups,showPool,showPick,showUnseen,showLayout,showIsNew,showMinglePlan,showCorner,showDialPick,showQueueDelta,showStyleHref,showKind,showPage,XGENRES,XSUR_ROLES,XSUR_TRAITS,XSUR_DARK,XSUR_STAKES,xgNorm,xGenreHtml,xKnobHtml,xcKnobEvent,vnFitScale,vnFit,VN_MIN_SCALE,sgStartIndex,xpQueueProgress,pinReorder,pinSlot,qTarget,qLink,xkFromPointer,xkNear,xAnimOpen,xgsNorm,xcSetGenre,xcutSection,xmvBlock,xmvState,xmvFit,xmvParseLen,xmvRange,xmvReadout,xmvFmt,castTyped,castTip,animBtn,animBox,jplayBtn,clipVideoFor,subjShort,toolbar,styleMark,get JR(){return JR},set CM(v){CM=v},set VIDS(v){VIDS=v},set JRN(v){JRN=v},set jById(v){jById=v}};");
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
  ok4(h.includes("🎞 Final cut") && h.includes('data-mvasm="draft"') && h.includes('data-mvasm="youtube"') && h.includes('data-mvasm="suno"') && h.includes('data-mvasm="hooks"')
      && h.includes("Build draft") && h.includes("Build for YouTube") && h.includes("Build for Suno") && h.includes("Build for Hooks") && !h.includes("Build full quality"), "title + draft / YouTube / Suno / Hooks buttons");
  ok4(!h.includes("mvhooks"), "no hook list before a hooks build");
  T.mvById[id].final_cut.hooks = [{n: 1, t0: 0, t1: 18.5, mb: 9.1, headlines: ["ONE <PHONE> CALL"], src: "../musicvideos/900-fc/export/hooks/auto/01_0m00-0m18.mp4"},
    {n: 2, t0: 18.5, t1: 41, mb: 11, headlines: [], src: "../musicvideos/900-fc/export/hooks/auto/02_0m18-0m41.mp4"}];
  T.mvById[id].final_cut.hooks_from = "kiss.mp4";
  h = T.mvCutSection(T.mvById[id]);
  ok4(h.includes("🪝 2 hooks · cut from kiss.mp4") && h.includes('data-mvcutplay="../musicvideos/900-fc/export/hooks/auto/01_0m00-0m18.mp4"') && h.includes("18.5 s") && h.includes("22.5 s")
      && h.includes("ONE &lt;PHONE&gt; CALL") && h.includes("0:18"), "hook list: span, length, escaped headline, ▶ play each");
  T.mvById[id].final_cut.latest = {...latest, draft: false, target: "suno", all: [{src: "../musicvideos/900-fc/cut/kiss-suno.mp4", mtime: 1, mb: 140, target: "suno", w: 1920, h: 1080}, {src: "../musicvideos/900-fc/cut/kiss.mp4", mtime: 1, mb: 300, draft: false, w: 1920, h: 1080}, {src: "../musicvideos/900-fc/cut/kiss-draft.mp4", mtime: 1, mb: 40, draft: true}]};
  h = T.mvCutSection(T.mvById[id]);
  ok4(h.includes("✓ Suno") && h.includes("<b>Suno</b> 1920×1080 · 140 MB") && h.includes("<b>YouTube</b> 1920×1080 · 300 MB") && h.includes("<b>Draft</b>"), "builds labelled by target (old builds without one: draft flag -> Draft, else YouTube)");
  T.mvById[id].final_cut.status = {state: "running", stage: "hook 3/9", target: "hooks"};
  ok4(T.mvCutSection(T.mvById[id]).includes("hook 3/9 (Hooks)"), "running status names the target");
  T.mvById[id].final_cut = {latest, status: {state: "done"}, edit: []}; h = T.mvCutSection(T.mvById[id]);
  ok4(/<video class="mvcutv" src="..\/musicvideos\/900-fc\/cut\/song-draft.mp4\?v=1790000000"/.test(h) && h.includes('data-jclipv="../musicvideos/900-fc/cut/song-draft.mp4"'), "player of the latest cut (cache-busted by mtime, position kept over redraws)");
  ok4(h.includes('data-fb="love"') && h.includes('data-fb="nope"') && h.includes('data-src="../musicvideos/900-fc/cut/song-draft.mp4"') && h.includes('data-draft="image:musicvideos/900-fc/cut/song-draft.mp4"'), "❤ / 👎 + comment thread keyed by the cut mp4 path");
  ok4((h.match(/<tr><td>\d/g) || []).length === 3 && h.includes("fade to black") === false && h.includes("dissolve 1.00 s") && h.includes("white flash 0.13 s") && h.includes("ltxia2v 🎤") && h.includes(">still<"), "edit list: one row per cut with transition + duration, singing marked, stills named");
  ok4(h.includes("memory") && h.includes("now + dust") && h.includes("NOW -&gt; MEMORY &lt;b&gt;"), "look, fx and the escaped why");
  ok4(h.includes("12 cut, 11 dissolve, 1 white flash") && h.includes("Draft 1280×720") && h.includes("0:216".slice(0, 0) + "3:36.7"), "counts + built summary");
  ok4(!/data-mvasm="draft" disabled/.test(h), "buttons enabled when idle");
  T.mvById[id].final_cut.status = {state: "running", stage: "rendering piece 4/28 (s4)", draft: true};
  h = T.mvCutSection(T.mvById[id]);
  ok4(["draft", "youtube", "suno", "hooks"].every(t => new RegExp(`data-mvasm="${t}" disabled`).test(h)) && h.includes("rendering piece 4/28 (s4) (Draft)") && T.mvCutBusy(T.mvById[id]), "building: all four buttons disabled, stage + target shown");
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
{  // ⚙ queue rows link to where the item lives, any status
  const okq = (c, m) => ok(c, "queue links: " + m);
  const lins = Object.values(T.byId || {}), evo = lins.find(l => l.depth > 0), surv = lins.find(l => !l.depth);
  if (evo) { const t = T.qTarget(`evolutions/${evo.id}/v01/x_seed1001.png`, "image");
    okq(t.href === `#/e/${evo.depth}?hl=${encodeURIComponent(evo.id)}` && t.tree === `#/tree/${evo.id}`, "an evolve / cross variant -> its set on the layer page (highlighted) + 🌳 family tree"); }
  if (surv) okq(T.qTarget(`evolutions/${surv.id}/v02/a.png`, "image").href === `#/l/${surv.id}` && !T.qTarget(`evolutions/${surv.id}/v02/a.png`, "image").tree, "a survey style -> its lineage page");
  okq(T.qTarget("journeys/021-x/ch02/s3.png", "image").href === "#/j/021-x" && T.qTarget("musicvideos/002-y/sb01/s4.png", "image").href === "#/mv/002-y"
    && T.qTarget("explore/sagas/003-sample-saga/ch10/e3.png", "image").href === "#/nev/saga/003-sample-saga" && T.qTarget("explore/012-z/e2.png", "image").href === "#/nev/012-z", "journeys, music videos, sagas and episodes");
  okq(T.qTarget("mvasm:002-y|youtube", "image").href === "#/mv/002-y"
    && T.qTarget("fixarea:0.1,0.2,0.3,0.4|journeys/021-x/ch01/s2.png|remove the hat", "image").href === "#/j/021-x"
    , "worker keys (final-cut builds, fixes) resolve to their page");
  okq(T.qLink({out: "journeys/021-x/ch02/s3.png", kind: "image", status: "queued"}) === "#/j/021-x", "queued / running rows link too (not only done)");
}
{  // 📌 drag to reorder the pin tray
  const okp = (c, m) => ok(c, "pin order: " + m);
  okp(JSON.stringify(T.pinReorder(["a", "b", "c", "d"], 0, 2)) === '["b","c","a","d"]' && JSON.stringify(T.pinReorder(["a", "b", "c"], 2, 0)) === '["c","a","b"]'
    && JSON.stringify(T.pinReorder(["a", "b"], 0, 9)) === '["b","a"]' && JSON.stringify(T.pinReorder(["a", "b"], 5, 0)) === '["a","b"]', "move an item to a slot (clamped; bad index = no change)");
  okp(T.pinSlot(10, [50, 120, 190]) === 0 && T.pinSlot(100, [50, 120, 190]) === 1 && T.pinSlot(500, [50, 120, 190]) === 3, "the drop slot from the pointer x vs the other thumbnails' centres");
}
{  // the story text never leaves the picture: fit scale search, a stub box, the CSS bounds
  const okf = (c, m) => ok(c, "novel fit: " + m);
  okf(T.vnFitScale(() => true) === 1 && T.vnFitScale(k => k <= 0.7) === 0.7 && T.vnFitScale(() => false) === T.VN_MIN_SCALE, "fit scale: full size when it fits, the largest that fits, the floor otherwise");
  const mk = lines => { const box = {_k: 1, clientHeight: 100, clientWidth: 400, textContent: "", style: {setProperty(n, v) { if (n === "--vnk") box._k = +v; }},
    get scrollHeight() { return Math.round(lines(box.textContent) * 24 * box._k); }, get scrollWidth() { return 400; }}; return box; };
  const long = "word ".repeat(50), short = "Hello there.";  // 7 lines at full size in a 4-line box -> shrinks to 0.6
  { const b = mk(t => Math.ceil(t.length / 40)); const k = T.vnFit(b, b, long); okf(k < 1 && Math.ceil(long.length / 40) * 24 * k <= 101 && b.textContent === "", "a long line shrinks until the whole of it fits, and the box is left empty for typing (k " + k + ")"); }
  { const b = mk(t => Math.ceil(t.length / 40)); okf(T.vnFit(b, b, short) === 1, "a short line keeps full size"); }
  const css = html.match(/#xplayer \.vnnar \{[^}]*\}/)[0] + html.match(/#xplayer \.vnbox \{[^}]*\}/)[0];
  okf(/max-height: 42%/.test(css) && /max-height: 46%/.test(css) && (css.match(/var\(--vnk, 1\)/g) || []).length === 2 && (css.match(/var\(--fh, 100vh\)/g) || []).length === 2,
    "narration (42%) + dialogue (46%) boxes are capped inside the frame (no overlap), fonts follow frame width AND height and the fit scale");
  okf(/#xplayer \.xpos \{[^}]*right: calc\(var\(--frx, 0px\) \+ 14px\); top: calc\(var\(--fry, 0px\) \+ 12px\)/.test(html)
    && /#xplayer \.xqueue \{[^}]*right: calc\(var\(--frx, 0px\) \+ 14px\); top: calc\(var\(--fry, 0px\) \+ 44px\)[^}]*max-width: calc\(var\(--frw, 100vw\) \* \.36\)/.test(html)
    && /#xplayer \.xtimer \{[^}]*top: calc\(var\(--fry, 0px\) \+ 14px\)/.test(html) && /setProperty\(k, v \+ "px"\)/.test(html) && /"--frx", cur\.x/.test(html),
    "the chapter / position pill, the queue box and the timer hug the current picture (--frx/--fry/--frw from xpFit), not the screen");
  okf(/#xplayer \.vnbox \{[^}]*overflow: visible/.test(html) && /#xplayer \.vnname \{[^}]*top: -/.test(html), "the dialogue box never clips: the speaker's name tag sits above its top edge");
}
{  // a picture that failed to load mid-play (the server went away) is retried
  const ok8 = (c, m) => ok(c, "novel stream: " + m);
  const shot = (id, src) => ({id, src, narration: "n " + id, dialogue: [], aspect: "16:9", hold: 6});
  const mkG = n2 => ({id: "9xx", title: "T", cast: [], chapters: [{id: "ch01", num: 1, title: "A", shots: [shot("e1", "../x/ch01/e1.png"), shot("e2", "../x/ch01/e2.png")]},
    {id: "ch02", num: 2, title: "B", shots: Array.from({length: 6}, (_, i) => shot("e" + (i + 1), i < n2 ? `../x/ch02/e${i + 1}.png` : null))}]});
  const segs = T.sgTimeline(mkG(2), null, true); segs.push(...T.sgMore(mkG(6), segs));
  ok8(segs.filter(s => s.key.startsWith("ch02/")).map(s => s.id).join(",") === "e1,e2,e3,e4,e5,e6" && new Set(segs.map(s => s.key)).size === segs.length, "shots that render mid-play join the stream in order, none skipped or doubled");
  ok8(T.sgTimeline(mkG(6), 2, false).filter(s => s.type === "shot").length === 6, "▶ From here on chapter 2 plays all of its shots");
  ok8(T.xpRetryUrl("../x/e4.png?v=12", 1) === "../x/e4.png?v=12&r=1" && T.xpRetryUrl("../x/e4.png?v=12&r=1", 2) === "../x/e4.png?v=12&r=2" && T.xpRetryUrl("../x/e4.png", 3) === "../x/e4.png?r=3"
      && T.xpRetryUrl("../x/e4.png?r=3", 4) === "../x/e4.png?r=4", "retry URL: a fresh r= per try, the v= cache key kept");
  ok8([0, 1, 2, 3, 4, 7].map(T.xpRetryDelay).join(",") === "1000,2000,4000,8000,8000,8000", "retry delays back off to 8 s");
  { const S = T.xpTimerState;
    ok8(S({active: true}, 600).kind === "" && S({active: true}, 181).kind === "", "player timer: hidden while more than 3 minutes are left");
    const w = S({active: true}, 161);
    ok8(w.kind === "warn" && w.text.includes("left") && w.text.includes("2:4") && w.btn.includes("15"), "player timer: the last 3 minutes count down with a +15 min button: " + w.text);
    const p = S({active: false, reason: "timer"}, 0);
    ok8(p.kind === "paused" && p.btn.startsWith("Continue") && p.text.includes("Paused"), "player timer: after the window, Paused + Continue on screen");
    ok8(S({active: false, reason: "stopped"}, 0).kind === "" && S(null, 0).kind === "", "player timer: nothing when stopped by hand or never started");
    const Lq = T.xpQueueLine;
    ok8(Lq(null) === "" && Lq({jobs: [{items: [{status: "done", label: "x"}]}]}) === "⟳ queue idle", "player queue: says 'queue idle' when nothing renders (hidden only before the queue loads)");
    const qv = {now: 1000, avg: {image: 48}, avgm: {"QI2.1": 40}, jobs: [{items: [{status: "running", on_gpu: true, model: "QI2.1", kind: "image", label: "📖 003 ch05 e3", t0: 990}, {status: "queued", model: "QI2.1", kind: "image", label: "📖 003 ch05 e4"}, {status: "queued", model: "QI2.1", kind: "image", label: "📖 003 ch05 e5"}]}]};
    const ql = Lq(qv);
    ok8(ql.startsWith("⟳ 📖 003 ch05 e3") && ql.includes("2 more") && ql.includes("~"), "player queue: what is on the GPU, how many more, about how long: " + ql);
    const gB = {chapters: [{id: "ch05", num: 5, shots: [{src: "a"}, {src: "b"}]}, {id: "ch06", num: 6, shots: [{src: "a"}, {src: null}, {src: null}]}, {id: "ch07", num: 7, shots: Array.from({length: 14}, () => ({src: null}))}]};
    const qv6 = {now: 1000, avg: {image: 48}, avgm: {}, jobs: [{items: [{status: "running", kind: "image", label: "📖 003 ch06 · e2", out: "explore/sagas/003-x/ch06/e2.png", t0: 990}, {status: "queued", kind: "image", label: "📖 003 ch06 · e3", out: "explore/sagas/003-x/ch06/e3.png"}]}]};
    ok8(Lq(qv6, gB).endsWith(" · then ch07: 14 frames") && JSON.stringify(T.xpBacklog(gB, qv6.jobs[0].items)) === JSON.stringify([{id: "ch07", left: 14}]), "player queue backlog: a written chapter not yet queued shows as 'then ch07: 14 frames' (the rendering one is not counted twice): " + Lq(qv6, gB));
    ok8(Lq({jobs: []}, gB) === "⟳ waiting to render: ch06: 2 frames (+1 more chapter)", "player queue backlog: idle GPU with chapters waiting says so: " + Lq({jobs: []}, gB));
    { const qv7 = {now: 1000, avg: {image: 40}, avgm: {}, jobs: [{items: [{status: "running", kind: "image", label: "📖 007 ch03 · e5", out: "explore/sagas/007-x/ch03/e5.png", t0: 990}, {status: "queued", kind: "image", label: "📖 007 ch03 · e6", out: "explore/sagas/007-x/ch03/e6.png"}]},
        {items: [{status: "queued", kind: "image", label: "📖 007 ch02 · e6", out: "explore/sagas/007-x/ch02/e6.png"}, {status: "done", kind: "image", label: "old", out: "x"}]}]};
      const g7 = {id: "007-x", chapters: [{id: "ch03", num: 3, shots: [{src: 1}, {}]}, {id: "ch04", num: 4, shots: Array(14).fill({})}]};
      const r7 = T.xpQueueRows(qv7, g7);
      ok8(r7.length === 4 && r7[0] === "▶ 📖 007 ch03 · e5" && r7[1] === "· 📖 007 ch03 · e6" && r7[2] === "· 📖 007 ch02 · e6" && r7[3].startsWith("· then ch04: 14 frames"), "player queue rows: running first, then every queued item across jobs (a chapter + a redo), then waiting chapters: " + r7.join(" | "));
      const big = {jobs: [{items: Array(10).fill(0).map((_, i) => ({status: "queued", kind: "image", label: "f" + i, out: "x/" + i}))}]}, rb = T.xpQueueRows(big, null, 6);
      ok8(rb.length === 6 && rb[5] === "+5 more", "player queue rows: at most 6, then '+N more'");
      ok8(T.xpQueueRows(null, null).length === 0 && T.xpQueueRows({jobs: []}, null).length === 0, "player queue rows: none before the queue loads / when empty");
      // subtle render progress: only the job on the GPU, elapsed vs that model's average, 3..95 %, "finishing" past the average
      const pq = (el, extra = {}) => ({now: 1000, avg: {image: 60}, avgm: {"QI2.1": 40}, jobs: [{items: [{status: "running", on_gpu: true, kind: "image", model: "QI2.1", gpu_t0: 1000 - el, ...extra}, {status: "queued", kind: "image"}]}]});
      ok8(T.xpQueueProgress(pq(20)).pct === 50 && T.xpQueueProgress(pq(0)).pct === 3 && T.xpQueueProgress(pq(400)).pct === 95 && T.xpQueueProgress(pq(400)).finishing && !T.xpQueueProgress(pq(20)).finishing, "player queue progress: elapsed vs the model's average, clamped 3..95, finishing past it");
      ok8(T.xpQueueProgress(pq(20, {on_gpu: false})) === null && T.xpQueueProgress(null) === null && T.xpQueueProgress({jobs: []}) === null, "player queue progress: nothing on the GPU = no bar"); }    { const e0 = {src: "explore/sagas/007-x/ch03/e5.png", t0: 1000, read: 20000, beats: 3, seen: 3, paused: 0, pauseAt: 0};
      ok8(T.xpEngRow(e0, 23000, "next").act === "next" && T.xpEngRow(e0, 23000, "next").dwell === 22000, "engagement: a shot read through and then advanced = next");
      ok8(T.xpEngRow(e0, 6000, "next").act === "skip" && T.xpEngRow({...e0, seen: 1}, 40000, "next").act === "skip", "engagement: moving on before the text was read (time or lines) = skip");
      ok8(T.xpEngRow(e0, 23000, "auto").act === "auto" && T.xpEngRow(e0, 5000, "back").act === "back" && T.xpEngRow(e0, 5000, null).act === "jump", "engagement: auto / back / jump are kept as they are");
      ok8(T.xpEngRow({...e0, paused: 10000}, 23000, "next").dwell === 12000 && T.xpEngRow({...e0, pauseAt: 20000}, 23000, "next").dwell === 19000 && T.xpEngRow(null, 1, "next") === null, "engagement: pauses don't count as reading time"); }    ok8(T.xpPosText({type: "shot", chNum: 4, chTitle: "Collateral", n: 6, of: 15}) === "Ch 4 · Collateral · 6 / 15" && T.xpPosText({type: "chapter", num: 4}) === "" && T.xpPosText(null) === "", "player position: 'Ch 4 · Collateral · 6 / 15' on saga shots, nothing on cards");
    { const gP = {id: "x", title: "X", cast: [], chapters: [{id: "ch02", num: 2, title: "Two", shots: [{id: "e1", src: "a.png"}, {id: "e2"}, {id: "e3", src: "c.png"}]}]}, sp = T.sgTimeline(gP, null, false).filter(s => s.type === "shot");
      ok8(sp.length === 2 && sp[1].n === 3 && sp[1].of === 3 && sp[1].chNum === 2 && sp[1].chTitle === "Two", "player position: shot segments carry their chapter and place in it (unrendered shots still count)"); }    { const keepS = T.EXST.state, keepN = T.XNW.open;
      T.EXST.state = {active: true, left: 600, reason: ""}; T.XNW.open = false;
      let b = T.exploreBar(true);
      ok8(b.includes("⏳ Building novel…") && b.includes("disabled") && !b.includes("data-xnew") && !b.includes("Start the new novel"), "new novel: while a novel is running the button reads Building novel… (disabled, no new start)");
      T.XNW.open = true; b = T.exploreBar(true);
      ok8(!b.includes("Start the new novel") && b.includes("Building novel"), "new novel: ... even if the premise box was open (it stays Building until Stop or the timer)");
      T.EXST.state = {active: false, reason: "stopped"}; b = T.exploreBar(true); ok8(b.includes("▶ Start a NevNovella") && !b.includes("Building"), "new novel: after ■ Stop, Start is back");
      T.EXST.state = {active: false, reason: "timer"}; b = T.exploreBar(true);
      ok8(b.includes("Continue the novel") && b.includes("＋ New novel") && b.includes("Start the new novel"), "new novel: also offered next to Continue when paused");
      ok8(!T.exploreBar(false).includes("data-xnew"), "new novel: only on the NevNovella home page");
      T.EXST.state = keepS; T.XNW.open = keepN; }
    ok8(html.includes('<button data-xp="chat"') && html.includes('<div class="xchat"></div>') && html.includes('thread("general", "Message your agent')
        && html.includes('e.target.closest(".xchat")) { if (e.key === "Escape")') && html.includes("reelPanel(); xpChatPaint();") && typeof T.xpChatToggle === "function",
        "player chat: 💬 opens the General thread in a side panel, player keys stand down while typing, refreshed with the comments poll");
    ok8(html.includes('<div class="xqueue"') && /#xplayer \.xqueue \{[^}]*rgba\(255,255,255,\.72\)/.test(html) && html.includes('if (typeof xpQueue === "function") xpQueue();'), "player queue: a faint line, refreshed with the ⚙ Queue data");
    ok8(html.includes('<div class="xtimer"></div>') && html.includes('a === "continue"') && /function xTick\(\) \{\s*xpTimer\(\);/.test(html), "player timer: in the player markup, ticks every second, Continue posts from the player"); }
  ok8(html.includes("xpImgRetry(im)") && html.includes("picture didn't load: reconnecting"),"a picture that fails to load is retried with a note on the frame");
}
{  // 🎲 surprise premise follows the deck
  const ok6 = (c, m) => ok(c, "novel dice: " + m), seq = vals => { let i = 0; return () => vals[i++ % vals.length]; };
  const neutral = {presence: 50, maturity: {stop: 4}, emotion: {blend: [], intensity: 0}, formality: {blend: [], intensity: 0}, cores: []};
  let s = T.xSurprise(neutral, seq([0.99]));
  ok6(/^An? \S/.test(s) && s.endsWith(".") && !/Mood|Register|Through-line|Genre/.test(s), "neutral deck: one clean premise, no notes: " + s);
  // combinatorial: 200 rolls on one deck give well over 150 different premises
  const rolls = new Set(Array.from({length: 200}, () => T.xSurprise(neutral)));
  ok6(rolls.size > 150, "variety: 200 rolls on one deck -> " + rolls.size + " different premises");
  ok6(T.XSUR_ROLES.every(r => r.length >= 14) && T.XSUR_TRAITS.every(t => t.length >= 12) && T.XSUR_STAKES.every(x => x.length >= 10), "pools: 14+ roles, 12+ traits, 10+ stakes at every stop");
  const kids = Array.from({length: 300}, () => T.xSurprise({...neutral, maturity: {stop: 0}}));
  ok6(kids.every(p => T.XSUR_ROLES[0].some(w => p.includes(" " + w + " ")) && T.XSUR_STAKES[0].some(w => p.includes(w)) && !/death|betray|exile|occupied|blood|bkill/i.test(p) && !/Genre: |. With /.test(p)), "Preschool: toddler-cartoon leads and stakes only, no hooks");
  ok6(kids.every(p => !T.XGENRES.filter(g => T.XSUR_DARK.includes(g[0])).some(g => ["intimate", "filmic", "epic"].some(k => g[1][k].some(w => p.includes(w))))), "Preschool + Any: no places from the darker genres");
  ok6(Array.from({length: 50}, () => T.xSurprise({...neutral, maturity: {stop: 6}})).every(p => T.XSUR_ROLES[6].some(w => p.includes(" " + w + " "))), "Mature: adult-fiction leads");
  ok6(Array.from({length: 60}, () => T.xSurprise({...neutral, maturity: {stop: 3}})).every(p => !T.XGENRES.find(g => g[0] === "Romance")[2].some(h => p.includes(h))), "Tween + Any: no romance hooks");
  const inScale = (k, p) => [...T.XSUR_WHERE[k], ...T.XGENRES.flatMap(g => g[1][k])].some(w => p.includes(w));
  ok6(Array.from({length: 40}, () => T.xSurprise({...neutral, presence: 10})).every(p => inScale("intimate", p)) && Array.from({length: 40}, () => T.xSurprise({...neutral, presence: 95})).every(p => inScale("epic", p)), "presence: intimate knob -> a small place, epic -> a vast one (any genre's)");
  ok6(T.xSurprise({...neutral, maturity: {stop: 6}}, seq([0.3, 0.25])).startsWith("An "), "article: 'An' before a vowel");
  s = T.xSurprise({...neutral, emotion: {blend: [{name: "Bittersweet", w: 0.6}, {name: "Nostalgia", w: 0.3}, {name: "Hope", w: 0.1}], intensity: 0.7},
    formality: {blend: [{name: "Black tie", w: 0.5}], intensity: 0.6}, cores: [{name: "Found family", weight: 0.8, status: "active"}, {name: "Grief", weight: 0.3, status: "resolved"}, {name: "Revenge", weight: 0.5}]}, seq([0]));
  ok6(s.endsWith("Mood: bittersweet and nostalgia. Register: black tie. Through-line: found family and revenge."), "mood (top 2, w >= 0.2), register, active cores by weight (resolved skipped): " + s);
  ok6(!T.xSurprise({...neutral, emotion: {blend: [{name: "Awe", w: 1}], intensity: 0.1}}, seq([0])).includes("Mood"), "a barely-on emotion (intensity < 0.15) adds no mood");
  ok6(T.xSurprise({}, seq([0.99])).length > 20 && T.xSurprise({}, seq([0.99])).length <= 400, "an empty deck still works (Teen, filmic), <= 400 chars");
  // orbit values: the sun (40 %) + its heaviest planet (12 %) name the mood, the 4 % moons never do
  s = T.xSurprise({...neutral, emotion: {orbit: true, blend: [{name: "Grief", w: 0.4}, {name: "Tension", w: 0.12}, {name: "Hope", w: 0.12}, {name: "Awe", w: 0.04}], intensity: 0.7}}, seq([0]));
  ok6(s.endsWith("Mood: grief and tension."), "an orbit value names the sun + its heaviest planet: " + s);
  // 🎭 genre: the place comes from the genre at the presence scale; from Tween up a genre hook too; Any = the old pools
  const noir = T.XGENRES.find(g => g[0] === "Noir");
  s = T.xSurprise({...neutral, genre: "Noir", presence: 95}, seq([0]));
  ok6(s.includes(noir[1].epic[0]) && s.includes("Genre: noir, with " + noir[2][0]), "genre: Noir + epic presence -> a noir epic place and a noir hook: " + s);
  s = T.xSurprise({...neutral, genre: "noir", maturity: {stop: 1}, presence: 10}, seq([0]));
  ok6(s.includes(noir[1].intimate[0]) && /Genre: noir\.$/.test(s), "genre below Tween: the place only, no hook (kept kid-safe): " + s);
  ok6(!T.xSurprise({...neutral, genre: ""}, seq([0])).includes("Genre"), "genre Any: no genre note");
  ok6(T.XGENRES.length === 19 && T.XGENRES.every(g => ["intimate", "filmic", "epic"].every(k => g[1][k].length >= 2) && g[2].length >= 2) && T.xgNorm("science FICTION") === "Science fiction" && T.xgNorm("zzz") === "" && T.xgNorm(null) === "",
    "genre list: 19 genres, each with places at 3 scales + 2 hooks; xgNorm is case-blind, unknown = Any");
  { const keep = T.XC.genres; T.XC.genres = ["Western"]; const h = T.xGenreHtml(); ok6((h.match(/data-xgenre=/g) || []).length === 20 && /class="xgchip on"[^>]*data-xgenre="Western"/.test(h) && h.includes('data-xgenre=""'), "genre chips: Any + 19, the chosen one lit"); T.XC.genres = keep; }
  // up to 3 genres, the first leads
  ok6(JSON.stringify(T.xgsNorm(["horror", "Comedy", "zzz", "Horror", "Western", "Noir"])) === '["Horror","Comedy","Western"]' && JSON.stringify(T.xgsNorm("noir")) === '["Noir"]' && T.xgsNorm("").length === 0 && T.xgsNorm(null).length === 0, "genres: deduped, capped at 3, an old single genre string migrates to [g]");
  { const keep = T.XC.genres, doc = globalThis.document; T.XC.genres = [];
    T.xcSetGenre("Horror"); T.xcSetGenre("Comedy"); T.xcSetGenre("Western");
    ok6(JSON.stringify(T.XC.genres) === '["Horror","Comedy","Western"]', "genre chips toggle on, in the order picked");
    T.xcSetGenre("Noir"); ok6(JSON.stringify(T.XC.genres) === '["Comedy","Western","Noir"]', "a 4th pick replaces the oldest");
    T.xcSetGenre("Western"); ok6(JSON.stringify(T.XC.genres) === '["Comedy","Noir"]', "clicking a lit chip turns it off");
    const h2 = T.xGenreHtml(); ok6(h2.includes("lead</sup>") && h2.includes("Comedy + Noir (lead: Comedy)"), "the lead and the blend are shown");
    T.xcSetGenre(""); ok6(T.XC.genres.length === 0, "Any clears them");
    T.XC.genres = ["Noir", "Western"]; const s2 = T.xSurprise({...neutral, genres: ["Noir", "Western"], maturity: {stop: 4}}, seq([0]));
    ok6(s2.includes("Genre: noir + western"), "🎲 surprise names the chosen genres: " + s2);
    T.XC.genres = keep; }
  ok6(T.xTuneHtml().includes("<h4>Genre</h4>"), "the deck has a Genre control");
}
{  // 🪐 orbit view = a solar system: the sun stays; three planets (the sun's links, dealt into 3 decks: inner = strongest) on their own ellipses, two moons each;
   // HOLD the sun = the planets race and each deals its next link per lap (different speeds = different intervals); hold a planet = its moons; click = next; double-click = new sun
  const ok7 = (c, m) => ok(c, "atlas orbit: " + m), E = T.XAE, O = T.XO;
  const st0 = T.xoCentre("grief"), tr = T.xoTree(E, st0), c1 = T.xoCands(E, "grief");
  ok7(JSON.stringify(T.xoDecks([1, 2, 3, 4, 5, 6, 7], 3)) === "[[1,4,7],[2,5],[3,6]]" && JSON.stringify(T.xoDecks([1, 2], 3)) === "[[1],[2]]", "decks: the links are dealt round-robin (strongest to the inner planet first)");
  ok7(tr.center === "grief" && JSON.stringify(tr.ring1) === JSON.stringify(c1.slice(0, 3)) && tr.decks1.every((d, i) => d[0] === c1[i]) && c1.length > 3, "the three strongest links are the first planets, inner = strongest; " + c1.length + " links in the decks");
  ok7(c1.every((id, i) => i === 0 || E.adj.grief.find(e => e.id === c1[i - 1]).w >= E.adj.grief.find(e => e.id === id).w), "deck order = link strength");
  ok7(tr.ring1.every(p => tr.kids[p].length === 2 && tr.kids[p].every(k => k !== "grief" && !tr.ring1.includes(k))), "each planet has two moons (never the sun or another planet)");
  const bl = T.xoBlend(E, tr), w = id => (bl.find(b => b.id === id) || {}).w;
  ok7(bl[0].id === "grief" && Math.abs(bl.reduce((s, b) => s + b.w, 0) - 1) < 0.03 && w("grief") > w(tr.ring1[0]) && w(tr.ring1[0]) > w(tr.kids[tr.ring1[0]][0]), "the value: each orbit from the sun weighs less (sun > planet > moon): " + bl.map(b => b.id + " " + b.w).join(", "));
  const tp = T.xoTree(E, T.xoTurnP(st0, 0, 1));
  ok7(tp.ring1[0] === tr.decks1[0][1] && tp.ring1[1] === tr.ring1[1] && tp.ring1[2] === tr.ring1[2] && tp.center === "grief", "one planet deals its next link; the others and the sun stay");
  const ta = T.xoTree(E, T.xoTurn1(st0, 1)); ok7(ta.ring1.every((p, i) => p === tr.decks1[i][1 % tr.decks1[i].length]), "◀ ▶ moves every planet on one");
  ok7(T.xoTree(E, T.xoTurnP(st0, 1, -1)).ring1[1] === tr.decks1[1][tr.decks1[1].length - 1], "turning back wraps round a planet's deck");
  const p = tr.ring1[0], tm = T.xoTree(E, T.xoTurnM(st0, p, 1, 1));
  ok7(tr.decks2[p][1].length < 2 || (tm.kids[p][1] === tr.decks2[p][1][1] && tm.kids[p][0] === tr.kids[p][0]), "one moon deals its next sub-link; its twin stays");
  let r = T.xoClick(st0, tr, p, false); ok7(r.act === "planet" && r.st.center === "grief" && r.st.k1[0] === 1, "one click on a planet = its next link (never moves the sun)");
  r = T.xoClick(st0, tr, tr.kids[p][0], false); ok7(r.st.center === "grief" && (tr.decks2[p][0].length < 2 || r.st.k2[p][0] === 1), "one click on a moon = its next sub-link");
  r = T.xoClick(st0, tr, p, true); ok7(r.act === "center" && r.st.center === p && JSON.stringify(r.st.k1) === "[0,0,0]", "a double-click makes that body the sun");
  ok7(T.xoClick(st0, tr, "grief", false).act === "none" && T.xoClick(st0, tr, "grief", true).act === "none", "clicking the sun does nothing (hold it instead; it stays until cleared)");
  const ht = T.xoTree(E, {center: null}); ok7(ht.hubs && ht.cands1.length === E.fams.length && T.xoClick({center: null}, ht, ht.cands1[2], false).act === "center", "no sun (neutral): one body per colour family; one click starts there");
  // the race: holding the sun, each planet deals per lap at its own speed (inner first); holding a planet races only its moons
  const s0 = {ph: [0, 0, 0], mph: [[0, 0], [0, 0], [0, 0]], acc: [0, 0, 0], macc: [[0, 0], [0, 0], [0, 0]]};
  let s = s0, laps = [0, 0, 0], first = [];
  for (let k = 0; k < 1900; k++) { s = T.xoTick(s, {kind: "sun"}, 0.016, false); s.swaps.forEach(x => { if (x.kind === "planet") { laps[x.i]++; if (!first.includes(x.i)) first.push(x.i); } }); }
  ok7(laps[0] > laps[1] && laps[1] > laps[2] && laps[2] >= 1 && first[0] === 0, "holding the sun for 30 s: every planet brings in new links (each half lap), inner ones more often (deals " + laps.join("/") + ")");
  { const sp = O.ORB.map((e, i) => e.w * O.HOLD * Math.hypot(e.a, e.b) / Math.SQRT2 * 160);   // ~px/s at a 360 px canvas (R ~ 160)
    ok7(sp.every(v2 => v2 > 35 && v2 < 95) && O.MOON.every(mo => Math.abs(mo.w) * O.MHOLD * mo.r * 160 < 70), "racing speeds stay trackable by eye: planets ~" + sp.map(Math.round).join("/") + " px/s, moons under 70 px/s");
    const nx = T.xoNext(s0, {kind: "sun"}); ok7(nx && nx.kind === "planet" && nx.i === 0 && nx.frac === 0, "next to deal (the highlighted orbit): from a standing start the inner, fastest planet");
    const s1 = {...s0, acc: [0.1, 3.0, 0]}; ok7(T.xoNext(s1, {kind: "sun"}).i === 1 && Math.abs(T.xoNext(s1, {kind: "sun"}).frac - 3.0 / Math.PI) < 1e-9, "next = whichever has the least time left to its gate, with how far it is");
    ok7(T.xoNext(s1, {kind: "sun"}, (k, i) => i !== 1).i === 0 && T.xoNext(s0, null) === null, "a locked / single-deck planet is never 'next'; nothing is next without a hold");
    ok7(T.xoNext(s0, {kind: "planet", i: 2}).kind === "moon" && T.xoNext(s0, {kind: "planet", i: 2}).i === 2, "holding a planet: the next moon to deal is highlighted"); }  { // smooth labels: opacity / size from readiness (subtle), a softer label under a solid one fades out of the way
    const lk0 = T.xoLabelLook(0, true), lk1 = T.xoLabelLook(1, true), lkn = T.xoLabelLook(null, true);
    ok7(lk0.alpha < lk1.alpha && lk1.alpha === 1 && lk0.alpha >= 0.6 && lk0.size < lk1.size && lk1.size - lk0.size <= 3 && lkn.alpha > lk0.alpha && T.xoLabelLook(0.2, false, true).alpha === 1, "label look: just changed = a little softer / smaller, about to change = solid / a touch larger (subtle); hover = solid");
    ok7(T.xoLabelLook(0.5, true).size > T.xoLabelLook(0.4, true).size && T.xoLabelLook(0.41, true).alpha - T.xoLabelLook(0.4, true).alpha < 0.01, "label look changes continuously with readiness (no jumps)");
    const mk = (x, t, hov) => ({x, y: 0, w: 60, h: 14, target: t, hov}), apart = T.xoLabelDim([mk(0, 0.7), mk(100, 0.9)]), cross = T.xoLabelDim([mk(0, 0.7), mk(10, 0.9)]);
    ok7(apart[0].target === 0.7 && apart[1].target === 0.9, "labels apart keep their opacity");
    ok7(cross[0].target < 0.25 && cross[1].target === 0.9, "a softer label passing under a more solid one fades away (it doesn't obstruct): " + cross[0].target.toFixed(2));
    const brush = T.xoLabelDim([mk(0, 0.7), mk(55, 0.9)]); ok7(brush[0].target > cross[0].target && brush[0].target < 0.7, "a slight overlap dims a little, a full one a lot (smooth with the overlap)");
    ok7(T.xoLabelDim([mk(0, 0.7, true), mk(10, 0.9)])[0].target === 0.7, "the hovered label is never dimmed"); }  s = s0; let ms = 0, ps = 0; for (let k = 0; k < 400; k++) { s = T.xoTick(s, {kind: "planet", i: 1}, 0.016, false); s.swaps.forEach(x => { if (x.kind === "moon" && x.i === 1) ms++; if (x.kind === "planet") ps++; }); }
  ok7(ms >= 2 && ps === 0, "holding a planet races only its own moons (" + ms + " moon swaps, no planet swaps)");
  s = s0; for (let k = 0; k < 600; k++) s = T.xoTick(s, null, 0.016, false); ok7(!s.swaps.length && s.ph[0] > 0 && s.ph[0] < 1.5 && s.mph[0][1] < 0, "no hold: everything only drifts slowly (no swaps), moons round in opposite directions");
  ok7(T.xoTick(s0, null, 1, true).ph[0] === 0, "reduced motion: no drift");
  { // 🔒 shift-click locks a planet / moon
    let rl = T.xoClick(st0, tr, p, false, true); const sl = rl.st;
    ok7(rl.act === "lock" && T.xoLockedP(sl, 0) && sl.center === "grief", "shift-click a planet locks it");
    ok7(T.xoClick(sl, tr, p, false).act === "locked" && JSON.stringify(T.xoTurn1(sl, 1).k1) === "[0,1,1]", "a locked planet ignores clicks and ◀ ▶ (the others move on)");
    const lk = {p: [true, false, false], m: [[false, false], [true, false], [false, false]]}; let ls = s0, sw = [];
    for (let k = 0; k < 900; k++) { ls = T.xoTick(ls, {kind: "sun"}, 0.016, false, lk); sw = sw.concat(ls.swaps); }
    ok7(ls.ph[0] === 0 && !sw.some(x => x.kind === "planet" && x.i === 0) && sw.some(x => x.kind === "planet" && x.i === 1), "holding the sun: the locked planet stands still and keeps its link; the rest race on");
    ls = s0; for (let k = 0; k < 300; k++) ls = T.xoTick(ls, {kind: "planet", i: 1}, 0.016, false, lk); ok7(ls.mph[1][0] === 0 && ls.mph[1][1] !== 0, "a locked moon stands still while its twin races");
    rl = T.xoClick(sl, tr, p, false, true); ok7(rl.act === "unlock" && !T.xoLockedP(rl.st, 0), "shift-click again unlocks");
    const lv = T.xoValue(E, T.xoClick(st0, tr, tr.kids[p][1], false, true).st, 0.6); ok7(lv.tree.lm[p][1] === true && JSON.stringify(T.xvNorm(lv, E).tree.lm) === JSON.stringify(lv.tree.lm), "locks live in the value (saved / reloaded)"); }  { // ♾ long holds deepen the decks: 2 then 3 links out
    const d1 = T.xoCandsDeep(E, "grief", 1), d2 = T.xoCandsDeep(E, "grief", 2), d3 = T.xoCandsDeep(E, "grief", 8);
    ok7(JSON.stringify(d1) === JSON.stringify(c1) && d2.length === d1.length + T.XO.GROW && d3.length > d2.length && d3.length <= d1.length + 7 * T.XO.GROW && JSON.stringify(d2.slice(0, d1.length)) === JSON.stringify(d1) && new Set(d3).size === d3.length && !d3.includes("grief"), "deeper decks keep the direct links first, then add the next 6 best relatives per step, 2 then 3 links out (" + d1.length + " → " + d2.length + " → " + d3.length + ")");
    const td = T.xoTree(E, {...T.xoTurnP(st0, 1, 1), d1: 2}), tn = T.xoTree(E, T.xoTurnP(st0, 1, 1));
    ok7(JSON.stringify(td.ring1) === JSON.stringify(tn.ring1) && td.cands1.length > tn.cands1.length, "deepening keeps the planets where they are (only the decks grow)");
    const vd = T.xoValue(E, {...st0, d1: 2, d2: {[tr.ring1[0]]: 3}}, 0.6); ok7(vd.tree.d1 === 2 && vd.tree.d2[tr.ring1[0]] === 3 && T.xoSt(E, vd).d1 === 2 && T.xoCentre("joy").d1 === undefined, "the depth lives in the value; a new sun starts at depth 1"); }  const v = T.xoValue(E, T.xoTurnP(st0, 2, 1), 0.7);
  ok7(v.orbit && v.tree.center === "grief" && JSON.stringify(v.tree.k1) === "[0,0,1]" && v.intensity === 0.7 && v.genre === E.by.grief.name && typeof v.valence === "number", "the value keeps the deck offsets, strength and the usual fields");
  ok7(JSON.stringify(T.xvNorm(v, E)) === JSON.stringify(v), "an orbit value survives xvNorm unchanged (saved / sent / reloaded)");
  ok7(T.xoSt(E, {blend: [{id: "saudade", w: 0.6}, {id: "joy", w: 0.4}]}).center === "saudade" && T.xoSt(T.XAF, T.xfNeutral()).center === "everyday" && JSON.stringify(T.xoSt(E, {orbit: true, tree: {center: "grief", k1: 2}}).k1) === "[0,0,0]", "older values: centre on the top neuron; formality starts on Everyday; an old single k1 resets the decks");
  const pos = T.xoPos(tr, [0, 1, 2], [[0, 1], [2, 3], [4, 5]]), dd = (a, b) => Math.hypot(a.x - b.x, a.y - b.y), rad = tr.ring1.map(id => dd(pos.get(id), {x: 0, y: 0}));
  ok7(pos.get("grief").x === 0 && rad[0] < rad[1] && rad[1] < rad[2] && dd(pos.get(tr.ring1[0]), T.xoOrbit(0, 0)) < 1e-9, "the planets sit on their own ellipses, the strongest closest to the sun");
  ok7(tr.ring1.every((p2, i) => tr.kids[p2].every((k, m) => Math.abs(dd(pos.get(k + "@" + p2), pos.get(p2)) - O.MOON[m].r) < 1e-9)), "moons circle their own planet");
  ok7(O.ORB.every((e, i) => i === 0 || (e.a > O.ORB[i - 1].a && e.w < O.ORB[i - 1].w && e.tilt !== O.ORB[i - 1].tilt)), "orbits: farther = slower, each tilted differently (not quite right, like a real system)");
  { const calls = {}, gr = {addColorStop() {}}, ctx = new Proxy({}, {get: (t, k) => k === "createRadialGradient" || k === "createLinearGradient" ? () => gr : k === "measureText" ? () => ({width: 44}) : (...a) => { calls[k] = (calls[k] || 0) + 1; }, set: () => true});
    const e0 = T.XC.emotion, f0 = T.XC.formality; let err = "";
    for (const [ev, fv] of [[T.xaValueAt(E.by.awe.x, E.by.awe.y, E), T.xaValueAt(T.XAF.by.streetwear.x, T.XAF.by.streetwear.y, T.XAF)], [v, T.xfNeutral()], [T.xeNeutral(), T.xoValue(T.XAF, T.xoCentre("rave"), 0.5)]]) {
      T.XC.emotion = ev; T.XC.formality = fv; try { T.xmDraw(ctx, 320, 320, 5000, E, 0.016); T.xmDraw(ctx, 320, 320, 5100, T.XAF, 0.016); } catch (x) { err += x.message + " "; } }
    T.XC.emotion = v; const ob = T.xoState(E); for (const hd of [{kind: "sun", key: "grief"}, {kind: "planet", i: 0, key: tr.ring1[0]}]) { ob.hold = hd; ob.acc = [1, 2, 0.5]; ob.macc = [[1, 4], [0, 0], [0, 0]]; try { T.xmDraw(ctx, 320, 320, 6000, E, 0.016); if (!ob.next) err += "no next during " + hd.kind + " "; } catch (x) { err += "hold " + hd.kind + ": " + x.message + " "; } } ob.hold = null;
    T.XC.emotion = e0; T.XC.formality = f0; ok7(!err && calls.ellipse >= 3, "a frame draws (orbits as ellipses) for an old probe value, an orbit value and neutral, on both atlases " + err); }
  { const k0 = T.XC.cores, add = T.xcoresAdd([], v, "Grief arc"), c = add.added, again = T.xcoresClean(add.cores)[0];
    ok7(c && c.blend.length === 3 && c.blend[0].id === "grief" && c.warped && again.blend[0].id === "grief" && JSON.stringify(again.blend) === JSON.stringify(c.blend), "＋ Add as core from an orbit value: the sun + its heaviest planets (moons folded in), kept as given through clean-ups: " + c.blend.map(b => b.id + " " + b.w).join(", "));
    T.XC.cores = k0; }
  const mh = T.xMapHtml(E);
  ok7(mh.includes('data-xoturn="emotion"') && mh.includes("xastr-emotion") && mh.includes("hold the sun") && T.xMapBtnsHtml(E).includes("data-xaclear") && !mh.includes("hold to pull") && !T.xMapBtnsHtml(E).includes("keep shape"), "markup: ◀ ▶, the hold hint, the strength slider, ○ clear; push / pull and keep-shape are gone");
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
    let cs = r.cores; r = T.xcoresAdd(cs, at("saudade")); ok5(!r.added && /already the core/.test(r.reason) && r.cores.length === 1, "cores: the same feeling is not set twice");
    const s0 = cs[0].id; r = T.xcoresAdd(cs, at("grief")); cs = r.cores;
    ok5(r.added && T.xcoresActive(cs).length === 1 && T.xcoresActive(cs)[0].blend[0].id === "grief" && cs.find(c => c.id === s0).status === "resolved" && r.replaced.join() === "Saudade", "cores: ONE active core: setting a new one retires the old to resolved, kept");
    for (const id of ["defiance", "tenderness"]) { r = T.xcoresAdd(cs, at(id)); cs = r.cores; }
    ok5(cs.length === 4 && T.xcoresActive(cs).length === 1 && new Set(cs.map(c => c.id)).size === 4 && cs[0].blend[0].id === "tenderness", "cores: the newest is the active one, earlier ones kept as resolved, unique ids");
    const g = cs[0].id; cs = T.xcoresEdit(cs, g, {weight: 0.9, name: "Dear Heart"}); ok5(cs[0].weight === 0.9 && cs[0].name === "Dear Heart" && cs[1].weight === 0.6, "cores: weight + rename edit one core");
    ok5(W(0.62) === 0.6 && W(0.68) === 0.7 && W(-1) === 0 && W(5) === 1 && W(0.5) === 0.5, "cores: the drag-bar snaps to 5% steps within 0-1");
    r = T.xcoresResolve(cs, g, true); cs = r.cores; ok5(r.ok && T.xcoresActive(cs).length === 0 && cs.find(c => c.id === g).status === "resolved", "cores: resolve retires the core (none active)");
    r = T.xcoresResolve(cs, s0, false); cs = r.cores; ok5(r.ok && T.xcoresActive(cs).length === 1 && T.xcoresActive(cs)[0].id === s0, "cores: reopen an earlier core");
    r = T.xcoresResolve(cs, g, false); ok5(r.ok && T.xcoresActive(r.cores).length === 1 && T.xcoresActive(r.cores)[0].id === g && r.cores.find(c => c.id === s0).status === "resolved", "cores: reopening while one is active swaps them");
    const full = r.cores; cs = T.xcoresRemove(full, s0); ok5(cs.length === full.length - 1 && !cs.some(c => c.id === s0), "cores: remove");
    ok5(T.xcoresClean(JSON.parse(JSON.stringify(full))).length === full.length && T.xcoresClean([{name: "x"}, null, 3, {blend: []}]).length === 0 && T.xcoresSig(full) === T.xcoresSig(JSON.parse(JSON.stringify(full))), "cores: clean keeps good ones and drops junk; signature is stable");
    const six = Array.from({length: 7}, (_, i) => ({id: "k" + i, name: "n" + i, ...at(["joy", "grief", "awe", "dread", "serenity", "pride", "shame"][i]), status: "active", weight: 0.5}));
    { const cl = T.xcoresClean(six); ok5(cl.length === 7 && T.xcoresActive(cl).length === 1 && T.xcoresActive(cl)[0].id === "k0", "cores: an old save with 7 active keeps the first active, the rest as resolved (nothing lost)"); }
    // the DOM markup
    const keepC = T.XC.cores, keepE = T.XC.emotion; T.XC.cores = full; T.XC.emotion = at("saudade"); const h = T.xCoresHtml();
    ok5(h.includes("data-xcadd") && h.includes("↻ Replace core") && !h.includes("Add as core") && (h.match(/data-xcw/g) || []).length === 1 && !h.includes("data-xcgrip") && h.includes("data-xcname") && h.includes("data-xcdel") && h.includes("data-xcres") && h.includes("data-xcgo") && h.includes("3 earlier / resolved") && h.includes("Emotional core<"),
      "cores markup: one core with weight bar + rename + resolve + remove (no reorder grip), Replace button, earlier ones folded");
    T.XC.cores = []; const he = T.xCoresHtml(); ok5(he.includes("No core yet") && he.includes("◎ Set as core"), "cores markup: empty state offers Set as core"); T.XC.cores = keepC; T.XC.emotion = keepE;
    // per saga: opening the home loads the current saga's cores; a different saga id re-syncs; a saga without cores keeps the deck's
    const keepS = T.SAGAS, k0 = [T.XC.cores, T.XC.maturity, T.XC.coresSaga]; T.XC.coresSaga = "";
    T.SAGAS = [{id: "900-test", title: "T", chapters: [], cast: [], cores: [{id: "c1", name: "Saved grief", probe: at("grief").probe, blend: at("grief").blend, weight: 0.8, status: "active", history: [{chapter: "ch01", beat: "x"}]}], maturity: {stop: 2, label: "Family"}}];
    ok5(T.xcSyncSaga() === true && T.XC.cores.length === 1 && T.XC.cores[0].name === "Saved grief" && T.XC.cores[0].weight === 0.8 && T.XC.maturity.label === "Family" && T.XC.coresSaga === "900-test", "per saga: the home page loads the current saga's cores + maturity from its bible");
    ok5(T.xcSyncSaga() === false, "per saga: ... once (your edits on the deck stay)");
    T.XC.cores = [{id: "mine", name: "Mine", ...at("joy"), status: "active", weight: 0.4}]; T.SAGAS = [{id: "901-new", title: "N", chapters: [], cast: [], cores: []}];
    ok5(T.xcSyncSaga() === true && T.XC.cores[0].id === "mine" && T.XC.coresSaga === "901-new", "per saga: a new saga without cores starts with the deck's");
    T.SAGAS = keepS; [T.XC.cores, T.XC.maturity, T.XC.coresSaga] = k0; }
  { const mh = T.xMapHtml(T.XAE), mf = T.xMapHtml(T.XAF); ok5([mh, mf].every(h => h.includes("data-xareset") && h.includes("⟲ Factory reset") && h.includes("data-xaclear") && !h.includes("data-xaremove") && !h.includes("data-xakeep")), "map markup (both atlases): ○ clear, ⟲ Factory reset (no keep-shape / warp buttons)");
    const m = {confirm: null}, t0 = 1000000;
    ok5(T.xaResetStep(m, t0) === "armed" && m.confirm.until === t0 + 4000 && m.confirm.remove === false, "factory reset: the first click only arms it (4 s), 'also remove neurons added later' is OFF");
    ok5(T.xaResetStep(m, t0 + 3999) === "do", "factory reset: a second click inside 4 s does it");
    const m2 = {confirm: {until: t0 + 4000, remove: true}}; ok5(T.xaResetStep(m2, t0 + 4001) === "armed" && m2.confirm.remove === false, "factory reset: the confirmation times out after 4 s (back to armed-from-scratch)");
    T.XAE.m.confirm = {until: Date.now() + 4000, remove: false}; const ch = T.xMapBtnsHtml(T.XAE); T.XAE.m.confirm = null;
    ok5(ch.includes("Reset to defaults? click again") && ch.includes("data-xaremove=\"emotion\"") && ch.includes("also remove neurons added later") && !/data-xaremove="emotion" checked/.test(ch), "factory reset: the armed state asks again and offers the unticked 'also remove neurons added later' box"); }
  // 🎚 maturity dial: 7 discrete stops, a vintage channel selector
  ok5(T.xdStops().length === 7 && T.xdStops().map(s => s.label).join("|") === "Preschool|Kids|Family|Tween|Teen|Young adult|Mature", "maturity: the 7 stops, Preschool .. Mature");
  ok5(T.xdStops().every(s => s.feels_like && s.story && s.pictures && s.ceiling) && /Saturday-morning/.test(T.xdStops()[1].feels_like) && /PG-13/.test(T.xdStops()[4].feels_like) && /adult fiction/.test(T.xdStops()[6].feels_like), "maturity: each stop has feels_like / story / pictures / ceiling (from tools/maturity.py via the payload)");
  ok5(/no sexual content/i.test(T.XMAT.ceiling) && /no graphic gore/i.test(T.XMAT.ceiling) && /adults only/i.test(T.XMAT.ceiling) && /under 18/i.test(T.XMAT.ceiling) && /fully clothed/i.test(T.XMAT.ceiling) && /no on-screen injury or blood/i.test(T.XMAT.ceiling), "maturity: the hard ceiling text travels with the payload");
  ok5(T.xdSnap(2.4) === 2 && T.xdSnap(2.6) === 3 && T.xdSnap(-4) === 0 && T.xdSnap(99) === 6 && T.xdSnap("x") === 0, "maturity: discrete detents only (rounds to a whole stop, clamped 0-6)");
  ok5(T.xdAngle(0) === -130 && T.xdAngle(3) === 0 && T.xdAngle(6) === 130 && near(T.xdAngle(1) - T.xdAngle(0), 260 / 6), "maturity: the pointer sweeps -130 .. +130 degrees in equal steps");
  ok5(T.xdFromPointer(0, -50) === 3 && T.xdFromPointer(-50, 0) === 1 && T.xdFromPointer(50, 0) === 5 && T.xdFromPointer(-30, 30) === 0 && T.xdFromPointer(30, 30) === 6, "maturity: an absolute rotary (up = Tween, left = Kids, right = Young adult, the bottom corners = the ends)");
  ok5(T.xdFromPointer(-1, 50) === 0 && T.xdFromPointer(1, 50) === 6 && T.xdFromPointer(-40, -40) === 2 && T.xdFromPointer(40, -40) === 4, "maturity: dead zone at the bottom snaps to the nearer end; diagonals pick Family / Teen");
  ok5(JSON.stringify(T.xdNorm(2)) === '{"stop":2,"label":"Family"}' && T.xdNorm("Young adult").stop === 5 && T.xdNorm({stop: 9}).label === "Mature" && T.xdNorm(null).stop === 4 && T.xdNorm("zzz").label === "Teen" && T.xdWord({stop: 0}) === "Preschool" && /toddler/.test(T.xdHint(0)), "maturity: normalising numbers / labels / objects / junk (default Teen)");
  { const h = T.xDialHtml(); ok5(h.includes('class="xdial"') && h.includes('role="slider"') && h.includes('aria-valuemax="6"') && T.xdStops().every(s => h.includes(`>${s.label}</text>`)) && (h.match(/data-xdv=/g) || []).length === 14 && /at the discretion of the user and the model/i.test(h),
      "maturity markup: the dial with 7 printed stops, tick + label each, and the discretion note"); }
  // presence knob: detents, sweep, drag
  ok5(T.xkSnap(48) === 50 && T.xkSnap(52) === 50 && T.xkSnap(56) === 55 && T.xkSnap(22) === 20 && T.xkSnap(-9) === 0 && T.xkSnap(130) === 100, "knob clicks into 21 stops (every 5), clamped");
  ok5(T.xkAngle(0) === -130 && T.xkAngle(50) === 0 && T.xkAngle(100) === 130, "knob sweeps -130 .. +130 degrees, like the maturity dial");
  ok5(T.xkFromPointer(0, -50) === 50 && T.xkFromPointer(50, 0) === 85 && T.xkFromPointer(-50, 0) === 15 && T.xkFromPointer(10, 50) === 100 && T.xkFromPointer(-10, 50) === 0, "knob is an absolute rotary: where the pointer points (up = Filmic), clamped past the ends");
  { const h = T.xKnobHtml(); ok5((h.match(/class="xdt xkt/g) || []).length === 21 && (h.match(/data-xkv=/g) || []).length === 5 && h.includes('class="xdsvg"') && h.includes(">Intimate</text>") && h.includes(">Epic</text>") && T.xkNear(60) === 50 && T.xkNear(65) === 75,
    "knob markup = the maturity dial's look: 21 ticks, 5 printed labels (nearest one lit)"); }
  { const h = T.xKnobHtml(); ok5(!h.includes("xddial") && h.includes('class="xkdial"'), "knob needle has its own class (sharing .xddial made the maturity dial turn the knob)"); }
  { const knob = {querySelector: () => ({getBoundingClientRect: () => ({left: 10, top: 20, width: 300})})}, at = v => { const a = T.xkAngle(v) * Math.PI / 180; return {clientX: 10 + 150 + 70 * Math.sin(a), clientY: 20 + 104 - 70 * Math.cos(a)}; };
    const was = T.XC.presence, got = [0, 25, 50, 85, 100].map(v => { T.xcKnobEvent(at(v), knob); return T.XC.presence; }); T.XC.presence = was;
    ok5(JSON.stringify(got) === "[0,25,50,85,100]", "knob pointer: pointing at a mark lands on that mark (centre 150,104 of the 300-wide viewBox): " + got); }
  ok5(T.xkWord(0) === "Intimate" && T.xkWord(50) === "Filmic" && T.xkWord(100) === "Epic" && T.xkWord(25) === "Close" && T.xkWord(75) === "Wide" && T.xkWord(65) === "Wide", "knob words");
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
  { const L = T.xaPlaceLabels([{id: "a", w: 60, h: 13, x: 100, y: 100, pri: 3}, {id: "b", w: 60, h: 13, x: 104, y: 102, pri: 2}, {id: "c", w: 60, h: 13, x: 108, y: 98, pri: 1}, {id: "d", w: 60, h: 13, x: 4, y: 4, pri: 0.5}], 320, 320);
    const hit = (p, q) => p.x < q.x + 60 && q.x < p.x + 60 && p.y < q.y + 13 && q.y < p.y + 13;
    ok5(L.length >= 3 && L[0].id === "a" && L.every((p, i) => L.every((q, j) => i === j || !hit(p, q))) && L.every(p => p.x >= 2 && p.y >= 2 && p.x + 60 <= 318 && p.y + 13 <= 318), "labels: no overlaps, inside the canvas, highest priority first (no label soup)"); }
  { const calls = {}, gr = {addColorStop() {}}, ctx = new Proxy({}, {get: (t, k) => k === "createRadialGradient" || k === "createLinearGradient" ? () => gr : k === "measureText" ? () => ({width: 44}) : (...a) => { calls[k] = (calls[k] || 0) + 1; }, set: () => true});
    T.xmDraw(ctx, 320, 320, 1234); ok5(calls.arc >= 10 && calls.stroke >= 9 && calls.fillText >= 8 && calls.save === calls.restore, "canvas draw: a full orbit frame (centre, links, sub-links, labels) runs without error"); }
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
  ok5(nav.includes('href="#/nev"') && /📖 NevNovella \d+/.test(nav) && /class="on"[^>]*>📖 NevNovella/.test(nav) && !/class="on">Survey/.test(nav), "header tab 📖 NevNovella (count, highlighted on its pages, not Survey)");
  location.hash = "#/nev/900-test-ep"; T.layerNav();
  ok5(/class="on"[^>]*>📖 NevNovella/.test(els["#layers"].innerHTML), "the #/nev address highlights the tab too (#/explore is the old alias)");
  location.hash = "";
  ok5(T.cmLabel("image:explore/900-test-ep/e3.png") === "Explore shot 900-test-ep/e3" && T.cmLink("image:explore/900-test-ep/e3.png") === "#/nev/900-test-ep" && T.cmLink("explore:900-test-ep") === "#/nev/900-test-ep", "comment labels + links for shots and episodes");
  ok5(T.fbKey("../explore/900-test-ep/e3.png?v=5") === "explore/900-test-ep/e3.png" && T.isExpl("../explore/900-test-ep/e3.png") && !T.isExpl("../journeys/x/ch01/s1.png"), "marks use keys explore/...png");
  // bar states
  T.EXST.state = null;
  ok5(T.exploreBar().includes("Loading"), "bar: loading before the first poll");
  T.xApply({active: false, reason: "idle", left: 0, until: 0, presence: null, emotion: null});
  let h = T.exploreBar(true);
  ok5(h.includes('data-xop="start"') && h.includes("▶ Start a NevNovella") && h.includes('id="xseed"') && !h.includes('data-xop="stop"') && !h.includes('data-xop="continue"'), "idle: big Start button + optional seed box");
  ok5(h.includes('class="xknob"') && h.includes('class="xdial"') && h.includes('id="xmap-emotion"') && h.includes('id="xmap"') && h.includes("Cinematic presence") && h.includes("Emotion atlas") && h.includes("Maturity") && h.includes('role="slider"'), "idle: every tactile control is there");
  ok5(["Intimate", "Close", "Filmic", "Wide", "Epic"].every(w => h.includes(`>${w}</text>`)) && ["Preschool", "Kids", "Family", "Tween", "Teen", "Young adult", "Mature"].every(w => h.includes(`>${w}</text>`)), "knob labels + the seven maturity stops are printed round the dial");
  ok5(!/camera|zoom|\bpan\b|Ken Burns/i.test(h), "UI words are about the pictures, not camera moves");
  T.xApply({active: true, reason: "", left: 761, until: 0, presence: 50, emotion: null});
  h = T.exploreBar();
  ok5(h.includes("NevNovella running") && h.includes('id="xleft">12:41<') && h.includes('data-xop="stop"') && h.includes('data-xop="tune"') && h.includes("Apply") && !h.includes('data-xop="start"'), "active: countdown 12:41, Stop, Apply");
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
  ok5(h.includes("📖 NevNovella") && h.includes('data-go="#/nev/900-test-ep"') && h.includes("The Lighthouse &lt;Keeper&gt;") && h.includes("✓ ready · 3 shots") && h.includes("🎨 rendering 0/1") && h.includes("Lights at the edge"), "list: cover cards with title (escaped), status, topic");
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
{  // 📖 NevNovella sagas: bible page, list order, the visual-novel line machine (typing, click sequencing, auto-advance timing), chapter cards, the endless stream
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
  ok6(T.vnTypeMs("x".repeat(100)) === 3400 && T.vnTypeMs("") === 250 && T.vnTypeMs("ab") === 250, "typing takes 34 ms per character (min 250 ms)");
  ok6(T.vnReadMs("one two three") === 2200 && T.vnReadMs(Array(50).fill("w").join(" ")) === 900 + 50 * 330 && T.vnReadMs("") === 2200, "reading time: 900 ms + 330 ms per word, at least 2.2 s");
  ok6(T.vnBeatMs("hello there") === T.vnTypeMs("hello there") + T.vnReadMs("hello there"), "auto-advance delay = typing + reading");
  ok6(T.vnTyped("hello", 0) === "" && T.vnTyped("hello", 68) === "he" && T.vnTyped("hello", 170) === "hello" && T.vnTyped("hello", 1e6) === "hello" && T.vnTyped("a😀b", 34) === "a" && T.vnTyped("a😀b", 68) === "a😀", "text types on a character at a time (emoji-safe), never past the end");
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
  // 🎬 Animate chapter on saga chapters
  { const keepA = T.EXST.anim, ak = "900-test-saga/ch01";
    T.EXST.anim = [];
    ok6(h.includes(`data-xanim="${ak}"`) && h.includes(`data-xanim="900-test-saga/ch02"`) && h.includes("Animate chapter") && !h.includes("data-xanimsend"), "saga chapters have a 🎬 Animate chapter button, note box closed");
    T.xAnimOpen.add(ak); ok6(T.sagaPage("900-test-saga").includes(`data-xanimsend="${ak}"`) && T.sagaPage("900-test-saga").includes(`data-xanimcancel="${ak}"`), "clicking it opens the note box (Send / Cancel)"); T.xAnimOpen.delete(ak);
    T.EXST.anim = [{id: "a1", kind: "animate", saga: "900-test-saga", chapter: "ch01", text: "slow", ts: "t", status: "open"}];
    let hx = T.sagaPage("900-test-saga");
    ok6(hx.includes("Animation requested") && !hx.includes(`data-xanim="${ak}"`) && hx.includes(`data-xanim="900-test-saga/ch02"`), "an open request shows 'Animation requested' on that chapter only");
    T.EXST.anim = [{id: "a1", kind: "animate", saga: "900-test-saga", chapter: "ch01", text: "", ts: "t", status: "done", reply: "reel rendered"}];
    hx = T.sagaPage("900-test-saga");
    ok6(hx.includes("reel rendered") && hx.includes(`data-xanim="${ak}"`), "an answered request shows the reply and the button again");
    T.EXST.anim = keepA; }
  // 🎞 Final cut on saga chapters: hidden until a shot has a clip; 4 build buttons; busy state; latest build + hooks
  { const c1 = sg.chapters[0], k = "900-test-saga/ch01";
    ok6(!T.sagaPage("900-test-saga").includes("data-xasm=") && T.xcutSection(sg, c1) === "", "final cut: hidden while no shot has a clip");
    c1.shots[0].clips = 1;
    let hh = T.sagaPage("900-test-saga");
    ok6(["draft", "youtube", "suno", "hooks"].every(t => hh.includes(`data-xasm="${k}/${t}"`)) && hh.includes("🎞 Final cut") && !hh.includes('data-xasm="900-test-saga/ch02/'), "final cut: the 4 build buttons appear on the chapter that has a clip only");
    ok6(!hh.includes("<video") || !hh.includes("data-xcutv="), "final cut: no player before a build");
    c1.final_cut = {latest: null, builds: [], status: {state: "running", target: "draft", stage: "piece 3/5 (e3)", ts: 1}, hooks: []};
    hh = T.xcutSection(sg, c1);
    ok6(hh.includes("piece 3/5") && hh.includes("(Draft)") && (hh.match(/data-xasm=[^>]* disabled/g) || []).length === 4, "final cut: busy state shows the stage and disables all 4 buttons");
    const b1 = {src: "../explore/sagas/900-test-saga/ch01/cut/test-ch01.mp4", target: "youtube", mtime: 100, mb: 12.5, w: 1920, h: 1080, duration: 65};
    c1.final_cut = {latest: b1, builds: [b1, {...b1, src: b1.src.replace(".mp4", "-draft.mp4"), target: "draft", w: 960, h: 540, mb: 3}], status: {state: "done", target: "youtube", ts: 1}, hooks: [{n: 1, file: "01-e1-e2.mp4", t0: 3, t1: 20, mb: 2, shots: ["e1", "e2"], src: "../explore/sagas/900-test-saga/ch01/cut/hooks/01-e1-e2.mp4"}], hooks_from: "test-ch01.mp4"};
    hh = T.xcutSection(sg, c1);
    ok6(hh.includes(`data-xcutv="${k}"`) && hh.includes("test-ch01.mp4?v=100") && hh.includes("1920×1080") && hh.includes("🪝 1 hooks") && hh.includes("data-xcutplay=") && hh.includes('data-draft="image:explore/sagas/900-test-saga/ch01/cut/test-ch01.mp4"') && !(hh.match(/data-xasm=[^>]* disabled/g) || []).length,
      "final cut: the latest build plays with its comment thread, other builds + hooks listed, buttons enabled again");
    c1.final_cut = {latest: null, builds: [], status: {state: "error", target: "hooks", msg: "boom"}, hooks: []};
    ok6(T.xcutSection(sg, c1).includes("Build failed: boom"), "final cut: a failed build shows its message");
    hh = T.xcutSection(sg, c1);
    ok6(hh.includes('data-xmusicfile="900-test-saga/ch01"') && hh.includes("Choose a song") && !hh.includes("<audio") && !hh.includes("data-xmusicclear"), "music: no song yet -> a picker / drop zone, no player");
    c1.music = {src: "../explore/sagas/900-test-saga/ch01/cut/music.mp3", mtime: 5, name: "my <song>.mp3", clip_sound: "low", offset: 12};
    hh = T.xcutSection(sg, c1);
    ok6(hh.includes("my &lt;song&gt;.mp3") && hh.includes("<audio") && hh.includes("music.mp3?v=5") && hh.includes('data-xmusicclear="900-test-saga/ch01"') && /<option value="low" selected>/.test(hh) && hh.includes('value="12"') && hh.includes("Replace"), "music: the track name (escaped), a player, ✖ remove, clip-sound + start offset options");
    c1.music = null;
    c1.final_cut = null; c1.shots[0].clips = 0; }
  // 🎞 Music video (saga level): range pickers, song / length, live readout, 4 builds, player
  { const keepMv = sg.mv;
    ok6(T.xmvParseLen("4:05") === 245 && T.xmvParseLen("245") === 245 && T.xmvParseLen("") === 0 && T.xmvParseLen("x") === 0 && T.xmvParseLen("1:02:03") === 3723 && T.xmvFmt(245) === "4:05", "music video: song length parsing + formatting");
    ok6(JSON.stringify(T.xmvRange("ch01-ch03", ["ch01", "ch02", "ch03", "ch04"])) === '["ch01","ch02","ch03"]' && JSON.stringify(T.xmvRange("ch02", ["ch01", "ch02"])) === '["ch02"]' && T.xmvRange("", ["ch01"]).length === 0, "music video: range parsing");
    const f1 = T.xmvFit(Array(45).fill(5), 245, false);  // 225 s natural, 44 s of dissolves
    ok6(f1.ok && Math.abs(f1.raw - 225 / (245 + 44)) < 1e-6 && f1.cells === 45, "music video: uniform speed = natural / (target + dissolves)");
    const f2 = T.xmvFit(Array(20).fill(5), 245, true);
    ok6(!f2.ok && f2.add > 0 && T.xmvFit(Array(60).fill(5), 100, false).add < 0 && T.xmvFit(Array(45).fill(5), 245, true).raw > T.xmvFit(Array(45).fill(5), 245, false).raw, "music video: outside 0.7-1.4x says how many cells to add / drop; the music tail is reserved");
    for (const c of sg.chapters) for (const s of c.shots) { s.nat = s.src ? 5 : 0; s.clips = 0; }
    sg.chapters[0].shots[0].clips = 1; sg.mv = null;
    let hm = T.sagaPage("900-test-saga");
    ok6(hm.includes("🎞 Music video") && hm.includes('data-xmvrange="from"') && hm.includes('data-xmvrange="to"') && hm.includes('placeholder="mm:ss"') && ["draft", "youtube", "suno", "hooks"].every(t => hm.includes(`data-xmvasm="900-test-saga/${t}"`)) && !hm.includes("<audio"), "music video: range pickers, a song-length field, the 4 build buttons (no song yet)");
    sg.mv = {cfg: {chapters: "ch01-ch02", length: "0:30"}, music: null, final_cut: {}};
    hm = T.xmvBlock(sg);
    ok6(hm.includes("4 cells") && hm.includes("natural 0:17") && hm.includes("at ") && /at 0\.\d\dx/.test(hm), "music video: the live readout for the chosen range + typed length: " + (hm.match(/xmvread[^<]*</) || [""])[0]);
    sg.mv = {cfg: {chapters: "ch01-ch02", offset: 2, clip_sound: "low"}, music: {src: "../explore/sagas/900-test-saga/cut/music.mp3", mtime: 3, name: "big <song>.mp3", dur: 32}, final_cut: {}};
    hm = T.xmvBlock(sg);
    ok6(hm.includes("big &lt;song&gt;.mp3") && hm.includes("<audio") && hm.includes('data-xmvmusicclear="900-test-saga"') && /<option value="low" selected>/.test(hm) && hm.includes("→ 0:30"), "music video: the song replaces the length field; the target = its duration minus the start offset");
    const bm = {src: "../explore/sagas/900-test-saga/cut/test-saga-ch01-ch02.mp4", target: "youtube", mtime: 9, mb: 40, w: 1920, h: 1080, duration: 30, range: "ch01-ch02", speed: 0.78};
    sg.mv.final_cut = {latest: bm, builds: [bm], status: {state: "done", target: "youtube"}, hooks: [{n: 1, file: "01-e1-e2.mp4", t0: 0, t1: 15, src: "../explore/sagas/900-test-saga/cut/hooks-ch01-ch02/01-e1-e2.mp4", range: "ch01-ch02"}]};
    hm = T.xmvBlock(sg);
    ok6(hm.includes('data-xcutv="mv:900-test-saga"') && hm.includes("0.78x") && hm.includes("🪝 1 hooks") && hm.includes('data-draft="image:explore/sagas/900-test-saga/cut/test-saga-ch01-ch02.mp4"'), "music video: the latest build plays with comments; speed, hooks listed");
    sg.mv.final_cut = {status: {state: "running", target: "draft", stage: "piece 2/4"}};
    ok6((T.xmvBlock(sg).match(/data-xmvasm=[^>]* disabled/g) || []).length === 4 && T.xmvBlock(sg).includes("piece 2/4"), "music video: busy state disables the buttons");
    for (const c of sg.chapters) for (const s of c.shots) { delete s.nat; delete s.clips; }
    sg.mv = {cfg: {}, music: null, final_cut: {}};
    ok6(T.xmvBlock(sg) === "", "music video: hidden when nothing is playable");
    sg.mv = keepMv; }
  // ▶ on every rendered tile
  ok6(h.includes('class="sgtileplay" data-sgplay="900-test-saga" data-from="1" data-at="ch01/e1"') && !h.includes('data-at="ch02/e2"'), "every rendered tile has ▶ Play from this picture (not the unrendered ones)");
  { const segs = [{key: "title"}, {key: "ch01"}, {key: "ch01/e1"}, {key: "ch01/e3"}];
    ok6(T.sgStartIndex(segs, "ch01/e3") === 3 && T.sgStartIndex(segs, null) === 0 && T.sgStartIndex(segs, "ch09/e9") === 0, "a tile's ▶ starts on that picture; unknown / none = the beginning"); }
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
  clock += 34 * 10; tick(); ok6(nar().textContent === "The harbou" && T.XP.typed === false, "typing progresses with the clock: 10 characters in 340 ms");
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
  ok6(htmlS.includes('data-xp="copy"') && htmlS.includes('a === "copy") xpCopy()') && htmlS.includes("C copy picture") && /key === "c" \|\| e\.key === "C"/.test(htmlS)
      && htmlS.includes("navigator.clipboard.write") && htmlS.includes('execCommand("copy")') && typeof T.xpCopy === "function", "player: ⧉ copy the picture on screen (button, C / Ctrl+C; clipboard API with an execCommand fallback for plain-http LAN)");
  { const d = T.xpDragData("../explore/sagas/001-my-saga/ch01/e2.png?v=123", "http://127.0.0.1:8765/gallery/index.html#/nev");
    ok6(d["text/uri-list"] === "http://127.0.0.1:8765/explore/sagas/001-my-saga/ch01/e2.png" && d["text/plain"] === d["text/uri-list"]
        && d.DownloadURL === "image/png:001-my-saga_ch01_e2.png:http://127.0.0.1:8765/explore/sagas/001-my-saga/ch01/e2.png", "player drag: absolute URL as link + text (cache-buster dropped), DownloadURL with a readable file name");
    const lh = T.xpLayerHtml({type: "shot", src: "../explore/x/e1.png", ar: 1.78, beats: [{t: "n"}]});
    ok6(htmlS.includes("e.dataTransfer.items.add(f)") && htmlS.includes("if (seg.src) xpPrefetchFile(seg.src)") && typeof T.xpPrefetchFile === "function", "player drag: carries the PNG file itself (prefetched), not only a 127.0.0.1 link other sites can't reach");
    ok6(/draggable="true" data-xpimg="..\/explore\/x\/e1.png"/.test(lh) && /#xplayer \.vnnar, #xplayer \.vnbox, #xplayer \.xcap \{ pointer-events: none; \}/.test(htmlS) && htmlS.includes('addEventListener("dragstart"'), "player drag: the picture is draggable, text boxes let the drag through, playback pauses while dragging"); }
  ok6(!/@keyframes xk/.test(htmlS), "still no camera-motion keyframes");
  T.EXPL = hbE; T.SAGAS = hbS; T.EXST.state = hs6; location.hash = "";
}

// music-video comment threads: box on top, newest first; other images keep the old order
{
  const mv = T.clipPanel("../musicvideos/001-x/sb01/s1__ltxia2v-a_seed1.mp4", "c"), jr = T.clipPanel("../journeys/001-x/ch01/s1__fasth3_seed1.mp4", "c");
  ok(!mv || /class="thread newest"/.test(mv), "mv thread: compose box on top, newest first");
  ok(!jr || !/class="thread newest"/.test(jr), "journey clip thread keeps oldest-first with the box at the bottom");
}

// ✓ Hide approved on the storyboard
{
  const b = T.hideDoneBtn(3);
  ok(/data-hidedone/.test(b) && /Hide approved/.test(b) && /\(3\)/.test(b), "storyboard: Hide approved toggle shows the approved count");
  ok(T.mvDoneCount({storyboards: []}) === 0, "mvDoneCount: empty storyboard = 0");
}
{  // slideshow
  const lins = [{id: "001-a", title: "A", depth: 0, created: "2026-10-01 10:00:00", versions: [{id: "v01", images: [{src: "evolutions/001-a/v01/f-modern@x_seed1.png"}, {src: "evolutions/001-a/v01/c-animals@x~1_seed1.png"}]}, {id: "v02", images: []}]},
                {id: "050-b", title: "B", depth: 1, created: "2026-09-01 10:00:00", versions: [{id: "v01", images: [{src: "evolutions/050-b/v01/l-location@y_seed1.png"}]}]}];
  const g = T.showGroups(lins);
  ok(g.length === 2 && g[0].key === "001-a/v01" && g[0].imgs.length === 2, "show: one group per rendered version (empty versions skipped)");
  const m = {loved: s => /c-animals/.test(s), noped: () => false, styleMark: () => ""};
  const now = Date.parse("2026-10-03T10:00:00");
  ok(T.showPool(g, {layer: "survey"}, m, now).map(x => x.key).join() === "001-a/v01", "show: survey filter keeps depth 0");
  ok(T.showPool(g, {layer: "evo"}, m, now).map(x => x.key).join() === "050-b/v01", "show: evolutions filter keeps depth > 0");
  ok(T.showPool(g, {fresh: "7d"}, m, now).length === 1, "show: last 7 days drops older styles");
  const k = T.showPool(g, {kind: "creatures"}, m, now);
  ok(k.length === 1 && k[0].imgs.length === 1 && /c-animals/.test(k[0].imgs[0].src), "show: kind filter narrows images and drops empty groups");
  ok(T.showPool(g, {loved: "loved"}, m, now).length === 1, "show: loved filter keeps loved images only");
  ok(T.showPool(g, {}, {...m, styleMark: l => l === "050-b" ? "nope" : ""}, now).length === 1, "show: a 👎 style is hidden");
  ok(T.showPool(g, {}, {...m, noped: s => /f-modern/.test(s)}, now)[0].imgs.length === 1, "show: 👎 images hidden");
  const pool = [1, 2, 3, 4, 5, 6].map(i => ({key: "k" + i}));
  const seen = {k1: 9, k2: 8, k3: 7, k4: 6};
  const picks = new Set([0, 0.3, 0.6, 0.99].map(r => T.showPick(pool, seen, () => r).key));
  ok([...picks].every(k => k === "k5" || k === "k6"), "show: picks only among the least-recently-shown third");
  ok(T.showPick(pool, {}, () => 0, "k1").key !== "k1", "show: never repeats the current group when there's a choice");
  ok(T.showPick([], {}) === null && T.showPick([{key: "a"}], {}, () => 0, "a").key === "a", "show: empty pool = null, lone group still shows");
  ok(T.showKind("x/p-props@a.png") === "props" && T.showKind("x/m-scifi@a.png") === "people", "show: kind from the subject prefix");
}
{  // slideshow card table
  let s = 1; const rnd = () => (s = (s * 9301 + 49297) % 233280) / 233280;
  for (const [n, a, W, H] of [[1, .75, 1600, 900], [6, .75, 1600, 900], [8, 1.78, 3440, 1440], [9, .66, 390, 800], [3, 1.78, 390, 800]]) {
    const L = T.showLayout(n, a, W, H, rnd);
    const inside = L.every(p => p.x - p.w / 2 >= -2 && p.x + p.w / 2 <= W + 2 && p.y - p.h / 2 >= -2 && p.y + p.h / 2 <= H + 2);
    const apart = L.every((p, i) => L.every((q, j) => i >= j || Math.abs(p.x - q.x) > (p.w + q.w) / 2 * .85 || Math.abs(p.y - q.y) > (p.h + q.h) / 2 * .85));  // tuck at most ~15%
    ok(L.length === n && inside && apart && L.every(p => Math.abs(p.rot) <= 4.5), `show: ${n} cards of aspect ${a} land on a ${W}x${H} table, inside, overlapping at most ~15%`);
  }
  ok(T.showLayout(0, 1, 100, 100).length === 0, "show: no cards, empty layout");
  ok(T.showLayout(6, .75, 1600, 900, rnd)[0].h > T.showLayout(6, .75, 1600, 900, rnd)[0].w, "show: portrait cards stay portrait");
}
{  // slideshow: just-finished evolve / cross sets jump the queue, woven in
  const now = Date.parse("2026-10-03T18:00:00"), sec = s => Math.floor(Date.parse(s) / 1000);
  const v = (n, have) => ({id: "v01", params: {seeds: [1001], subjects: Array.from({length: n}, (_, i) => "s" + i)}, images: Array.from({length: have}, (_, i) => ({src: `evolutions/x/v01/f-modern@s${i}_seed1001.png`}))});
  const lins = [
    {id: "001-old", depth: 0, created: sec("2026-09-01T10:00:00"), versions: [v(2, 2)]},
    {id: "002-old", depth: 0, created: sec("2026-09-02T10:00:00"), versions: [v(2, 2)]},
    {id: "400-cross", depth: 2, parent_images: ["a.png", "b.png"], created: sec("2026-10-03T17:00:00"), rendered: sec("2026-10-03T17:40:00"), versions: [v(3, 3)]},
    {id: "401-evo", depth: 1, parent_images: ["a.png"], created: sec("2026-10-03T16:00:00"), rendered: sec("2026-10-03T17:20:00"), versions: [v(3, 3)]},
    {id: "402-half", depth: 1, parent_images: ["c.png"], created: sec("2026-10-03T17:50:00"), versions: [v(3, 1)]},
    {id: "403-stale", depth: 1, parent_images: ["d.png"], created: sec("2026-09-20T10:00:00"), versions: [v(3, 3)]}];
  const g = T.showGroups(lins), by = k => g.find(x => x.lid === k);
  ok(by("400-cross").set === "cross" && by("401-evo").set === "evolve" && by("001-old").set === "", "show: groups know cross / evolve / survey");
  ok(by("402-half").complete === false && by("400-cross").complete === true, "show: a set still rendering isn't complete");
  ok(T.showIsNew(by("400-cross"), now) && !T.showIsNew(by("402-half"), now) && !T.showIsNew(by("403-stale"), now) && !T.showIsNew(by("001-old"), now), "show: new = a finished evolve/cross set from the last 48 h");
  const p1 = T.showPick(g, {}, () => 0, null, {now});
  ok(p1.lid === "401-evo", "show: the first-finished new set is dealt first");
  const p2 = T.showPick(g, {[p1.key]: now}, () => 0, p1.key, {now, lastFresh: true});
  ok(!T.showIsNew(p2, now), "show: never two new sets back to back while other styles exist (woven in)");
  const p3 = T.showPick(g, {[p1.key]: now, [p2.key]: now}, () => 0, p2.key, {now, lastFresh: false});
  ok(p3.lid === "400-cross", "show: the next new set comes right after one other style");
  ok(T.showPick(g, {"401-evo/v01": now, "400-cross/v01": now}, () => .99, null, {now}) && !["401-evo", "400-cross"].includes(T.showPick(g, {"401-evo/v01": now, "400-cross/v01": now}, () => 0, null, {now}).lid), "show: once shown, new sets rejoin the normal rotation");
  ok(T.showPick([by("400-cross")], {}, () => 0, null, {now, lastFresh: true}).lid === "400-cross", "show: only new sets left = still dealt");
  ok(T.showPool(g, {fresh: "7d"}, {loved: () => false, noped: () => false, styleMark: () => ""}, now).every(x => !x.lid.endsWith("old")), "show: last 7 days works on epoch-second created");
}
{  // slideshow: pinned cards mingle with the hand
  const cards = T.showLayout(6, .75, 1600, 900, () => .5), W = 1600, H = 900;
  const P = T.showMinglePlan(cards, 2, W, H);
  ok(P.paths.length === 2 && P.ms > 6000, "mingle: 2 pins, a slow walk");
  const rests = path => path.slice(1, -1).filter((q, i, a) => i % 2 === 0);
  ok(P.paths.every(p => rests(p).length === 6), "mingle: each pin rests beside every card of the hand");
  ok(P.paths.every(p => p.every((q, i) => !i || q.t >= p[i - 1].t) && p[p.length - 1].t === P.ms), "mingle: keyframe times run forward and end together");
  const near = (q, c) => Math.abs(q.x - c.x) <= c.w && Math.abs(q.y - c.y) <= c.h;
  const a = rests(P.paths[0]), b = rests(P.paths[1]);
  ok(a.every((q, s) => !cards.filter(c => near(q, c)).some(c => near(b[s], c) && Math.abs(b[s].x - q.x) < 1)), "mingle: two pins never rest on the same card at once");
  ok(P.paths.every(p => p[0].y > H && p[p.length - 1].y > H), "mingle: pins rise from below and sink back");
  ok(T.showMinglePlan(cards, 0, W, H).ms === 0 && T.showMinglePlan([], 3, W, H).ms === 0, "mingle: no pins or no hand = no mingle");
  ok(T.showMinglePlan(cards, 9, W, H).paths.length === 4, "mingle: at most 4 pins at once");
}
{  // slideshow: the carried character of an evolve / cross set
  const g = T.showGroups([{id: "500-x", depth: 1, parent_images: ["evolutions/090-a/v02/f-modern@sigilfire2~3_seed1001.png", "evolutions/056-b/v01/f-fantasy@amano_seed1001.png"],
    versions: [{id: "v01", images: [{src: "../evolutions/500-x/v01/f-modern@sigilfire2~3_seed1001.png"}, {src: "../evolutions/500-x/v01/f-fantasy@amano_seed1001.png"}, {src: "../evolutions/500-x/v01/m-modern@orig9~1_seed1001.png"}]}]},
    {id: "001-s", depth: 0, versions: [{id: "v01", images: [{src: "../evolutions/001-s/v01/f-modern@sigilfire2~3_seed1001.png"}]}]}]);
  ok(g[0].imgs.map(i => !!i.carried).join() === "true,false,false", "show: only the FIRST parent's character is the carried one");
  ok(!g[1].imgs[0].carried, "show: survey styles have no carried character");
}
{  // slideshow: no game sets
  const v = {id: "v01", images: [{src: "../evolutions/x/v01/f-modern@a_seed1001.png"}]};
  const g = T.showGroups([{id: "600-art", tags: ["evolution"], versions: [v]}, {id: "601-game", tags: ["game assets", "props"], versions: [v]}]);
  ok(g.map(x => x.lid).join() === "600-art", "show: game-asset lineages stay out of the slideshow");
}
{  // slideshow: the whole-set ❤ sits on the top row's right-most card
  const L = T.showLayout(7, .75, 1600, 900, () => .5), c = T.showCorner(L), top = Math.min(...L.map(p => p.y));
  ok(c && c.y < top + c.h / 2 && L.filter(p => p.y < top + c.h / 2).every(p => p.x <= c.x), "show: the set pill goes on the top row's right-most card");
  ok(T.showCorner([]) === null, "show: no cards, no set pill");
}
{  // slideshow: 👥 radial dial
  ok(T.showDialPick(0, 0, 10) === -1 && T.showDialPick(10, 10, 10) === -1, "dial: the middle = same kind");
  ok(T.showDialPick(0, -100, 10) === 0 && T.showDialPick(100, 0, 10) === 3 && T.showDialPick(0, 100, 10) === 5 && T.showDialPick(-100, 0, 10) === 8, "dial: up / right / down / left pick options 0 / 3 / 5 / 8 of 10");
  ok(T.showDialPick(0, -400, 10) === null, "dial: far outside = cancel");
}
{  // slideshow: queue counter
  ok(T.showQueueDelta(undefined, 12) === 0 && T.showQueueDelta(12, 15) === 3 && T.showQueueDelta(15, 14) === 0 && T.showQueueDelta(14, 14) === 0, "queue counter: animates only when images are added");
}
{  // slideshow: a set waits until every style in it is fully rendered
  const v = (n, have) => ({id: "v01", params: {seeds: [1001], subjects: Array.from({length: n}, (_, i) => "s" + i)}, images: Array.from({length: have}, (_, i) => ({src: `evolutions/x/v01/f-modern@s${i}_seed1001.png`}))});
  const g = T.showGroups([{id: "700-a", depth: 1, parent_images: ["p.png", "q.png"], versions: [v(3, 3)]}, {id: "701-b", depth: 1, parent_images: ["p.png", "q.png"], versions: [v(3, 1)]},
    {id: "702-c", depth: 1, parent_images: ["z.png"], versions: [v(2, 2)]}]);
  const m = {loved: () => false, noped: () => false, styleMark: () => ""};
  ok(g.find(x => x.lid === "700-a").setDone === false && g.find(x => x.lid === "702-c").setDone === true, "show: a set is done only when every sibling style is fully rendered");
  ok(T.showPool(g, {}, m).map(x => x.lid).join() === "702-c", "show: half-rendered sets (and their finished siblings) stay out of the show");
}
{  // slideshow: the new layout uses the table better
  const L = T.showLayout(7, .75, 1600, 900, () => .5);
  ok(L[0].h > 900 * .42, "show: 7 portrait cards on 1600x900 are now big (taller than 42% of the screen)");
  ok(T.showLayout(12, .75, 1600, 900, () => .5).length === 12, "show: a 12-card hand fits");
}
{  // slideshow: a set seen half-rendered regains its priority once it finishes
  const v = n => ({id: "v01", params: {seeds: [1001], subjects: Array.from({length: n}, (_, i) => "s" + i)}, images: Array.from({length: n}, (_, i) => ({src: `evolutions/x/v01/f-modern@s${i}_seed1001.png`}))});
  const now = Date.parse("2026-10-03T20:00:00"), sec = s => Math.floor(Date.parse(s) / 1000);
  const g = T.showGroups([{id: "800-new", depth: 1, parent_images: ["a.png"], created: sec("2026-10-03T19:00:00"), rendered: sec("2026-10-03T19:50:00"), versions: [v(2)]},
    {id: "001-old", depth: 0, created: sec("2026-09-01T10:00:00"), rendered: sec("2026-09-01T10:00:00"), versions: [v(2)]}]);
  const seenEarly = {"800-new/v01": Date.parse("2026-10-03T19:30:00")}, seenAfter = {"800-new/v01": Date.parse("2026-10-03T19:55:00")};
  ok(T.showPick(g, seenEarly, () => 0, null, {now}).lid === "800-new", "show: a set dealt while still rendering is fresh again once it finishes");
  ok(T.showPick(g, seenAfter, () => 0, null, {now}).lid === "001-old", "show: once seen after it finished, it rejoins the normal rotation");
  // a later 👥 version rendering into a SIBLING must not make the set fresh again
  const vs = (id, t) => ({id, params: {seeds: [1001], subjects: ["s0"]}, images: [{src: `evolutions/x/${id}/s0_seed1001.png`}], slots: [{ts: sec(t)}]});
  const g2 = T.showGroups([{id: "810-a", depth: 1, parent_images: ["a.png", "b.png"], created: sec("2026-10-03T19:00:00"), rendered: sec("2026-10-03T19:40:00"), versions: [vs("v01", "2026-10-03T19:40:00")]},
    {id: "811-b", depth: 1, parent_images: ["a.png", "b.png"], created: sec("2026-10-03T19:00:00"), rendered: sec("2026-10-03T19:58:00"), versions: [vs("v01", "2026-10-03T19:41:00"), vs("v02", "2026-10-03T19:58:00")]}]);
  const a = g2.find(x => x.key === "810-a/v01");
  ok(!T.showUnseen(a, {"810-a/v01": Date.parse("2026-10-03T19:45:00")}), "show: a sibling's later 👥 version doesn't make a seen set fresh again");
  ok(T.showUnseen(g2.find(x => x.key === "811-b/v02"), {"811-b/v02": Date.parse("2026-10-03T19:45:00")}), "show: the 👥 version itself is fresh once it lands");
}
{  // cast box: "every character matching …" across the whole library
  const m = T.castMatches("uniform");
  const top = m.find(x => x.o.v.startsWith("char:"));
  ok(top && top.o.v === "char:uniform" && top.o.n >= 1, "cast box: 'uniform' offers 🎹 every character matching it (all casts) ahead of single-character matches");
  T.store.set("fcast", "char:uniform");
  const k = Object.keys(T.DATA.reduce((a, l) => (l.versions.forEach(v => v.slots.forEach(sl => a[sl.subject] = 1)), a), {})).find(s => T.subjMatch(s));
  ok(!!k, "cast box: the char: filter matches at least one rendered subject");
  T.store.set("fcast", "all");
}
{  // slideshow: paused double-click opens the style's page
  ok(T.showStyleHref({lid: "412-clay-jojo-toon", depth: 2}) === "#/e/2?hl=412-clay-jojo-toon" && T.showStyleHref({lid: "042-moebius", depth: 0}) === "#/l/042-moebius", "show: double-click target = the style's evolution layer (highlighted) or survey lineage page");
}
