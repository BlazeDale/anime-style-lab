# Operating manual for coding agents

This file is for whichever coding agent (Claude Code, Codex, Cursor, Copilot, Aider, Gemini CLI, ...) is driving
this repo. It assumes no memory of any earlier session — read it fresh each time. `README.md` is the human-facing
quickstart; this is the loop you run.

## What this project is

A local lab for exploring anime illustration styles with Qwen Image 2.1 in ComfyUI. The user reacts to renders in
a gallery page; you (the agent) act on their reactions — new style versions, new branch lineages, evolution sets
that crossbreed styles, journeys, video clips — and reply so they can see what you did.

## Layout

```
evolutions/NNN-slug/          one prompt lineage (a style/idea being refined)
  lineage.json                 {title, goal, parent, parent_images, round, tags}
  README.md                    GENERATED changelog table (via build_gallery.py) — don't hand-edit
  vNN/                          one prompt iteration
    prompt.txt                  exact positive prompt (a {subject} slot is filled per-character from subjects.json)
    params.json                  seeds, steps, cfg, aspect_ratio, megapixels, model, sampler, scheduler, subjects
    notes.json                   {change, why, verdict}
    workflow.json (or <name>.workflow.json per image)   exact API graph that was submitted
    seedNNNN.png / <subject>_seedNNNN.png                outputs
journeys/NNN-slug/            one character exploring their own world (🧭 in the gallery; NOT an evolution)
  journey.json                 {title, name, source, source_cap, style ("...{subject}..."), character, world, cast, refs, ref_resolution}
  chNN/chapter.json            {title, direction, summary, choices, verdict, revisions, params, scenes: [...]}
  chNN/sN.png                  scenes (+ sN.workflow.json)
gallery/index.html             GENERATED explorable gallery; gallery/data.json feeds live updates
subjects.json                  the character cast(s): {key: {label, text}}
config.json                    local machine config (comfy_url, comfy_python, gallery_port) — see tools/config.py
tools/
  build_gallery.py              evolutions/ + journeys/ -> gallery/index.html (+ lineage READMEs); rerun after any edit
  serve_gallery.py               local server: gallery + feedback API (marks, comments, pins, journeys, reroll, upscale, refit, queue)
  run_version.py                 render a version dir: python tools/run_version.py evolutions/NNN-x/vNN [...more]
  run_journey.py                 render a journey chapter: python tools/run_journey.py journeys/NNN-x/chNN
  run_video.py                   image-to-video: python tools/run_video.py <image.png> <engine> --motion "..." ...
  video_prompt.py                 builds the H3-format video prompt (used by run_video.py --motion)
  hires_card.py / refit.py / match_contrast.py   upscale / re-aspect / contrast-match helpers
  place_bubbles.py               position 💬 speech bubbles on journey scenes
  labkit.py                      shared helpers for the tools below (next lineage / cast id / version number, writing a cast)
  new_cast.py                    👥 more characters: new_cast.py <marked png> spec.json [--render] [--dry-run]
  new_set.py                     📌 evolve / cross: new_set.py spec.json [--render] [--dry-run]
  scene_fix.py                   journey reshoot: edit one scene, log it in `revisions`, re-render with a new seed
  animate_chapter.py             🎬 chapter reel: ONE run_video --batch for a journey chapter, audio rules built in
  fix_area.py                    ✎ inpaint one drawn box of an image (the gallery's Fix area button runs this)
  contact_sheet.py               numbered review grid of images / version dirs / chapter dirs (needs Pillow)
  feedback.py                    inbox / reply / creply / sreply / jreply — read and answer the user's marks
  watch_feedback.py              background watcher: one line per new gallery event (polls; resumes after a restart)
  doctor.py                      first-run check (--fix creates config.json, .venv, the gallery page)
  smoke_test.py                  render one image into feedback/smoke/ to prove the pipeline works
  pipeline.py                    render-queue registry + GPU ticket lock (used by run_version/run_journey/run_video)
  test_gallery.js                node tools/test_gallery.js gallery/index.html — logic checks against a stub DOM
  test_labkit.py / test_journey_tools.py   python tools/test_labkit.py, python tools/test_journey_tools.py — no ComfyUI, temp dirs only
```

## First run

If `.venv/` or `config.json` doesn't exist yet, this is a fresh checkout:

1. `python tools/doctor.py` — one table of what's there and what's missing (Python, `.venv` + packages,
   `config.json`, Node, ComfyUI reachability, the Qwen Image 2.1 nodes, model files, optional video engines).
   Show the user the table before installing anything.
2. With their OK: `python tools/doctor.py --fix` — creates `config.json`, the `.venv` with `requirements.txt`, and
   the gallery page. It never touches ComfyUI or downloads models; missing models are for the user to fetch.
3. `python tools/smoke_test.py` — renders ONE image (001-plain-anime v02, `f-modern`) into `feedback/smoke/`
   through the real pipeline. It never overwrites the shipped renders in `evolutions/`.
4. Continue with "Session start" below.

## Session start

1. Start the gallery server in the background if it isn't running (`GET /api/queue` is a cheap liveness check):
   `.venv/Scripts/python tools/serve_gallery.py` (`.venv/bin/python` on macOS/Linux). Started with any other
   Python, it re-launches itself under the `.venv`, which has Pillow for the thumbnails.
2. Start the event watcher in the background and keep it running all session:
   `python tools/watch_feedback.py`. It prints one line per new gallery event, `[ACT]` for requests and `[info]`
   for things the server already handles. It polls the file, because `tail -F` misses appends on Windows. If your
   harness stops background commands after a while, restart it: it resumes from where the last watch stopped, so
   events sent during the gap still come through.
3. Run `python tools/feedback.py inbox`: it prints any unhandled marks, sets, journey requests, or comment threads
   waiting on you. Run it again whenever the watcher prints an `[ACT]` line, then act on everything it reports
   (see below) and reply to each item so it clears from the inbox.

Never leave marks/sets/journeys/comments unanswered across a session boundary if you can help it — the user is
waiting on a reply, not just a render.

### Which events need you

| event in `log.jsonl` | what it is | what you do |
|---|---|---|
| `submit` | the user pressed Send on their marks | `feedback.py inbox`, act on each 🎬 / note, `reply` |
| `set` | 📌 tray submitted (evolve = 1 image, cross = 2+) | build the set ("Evolution sets"), `sreply` |
| `journey` | 🧭 start, "what happens next?", or 🎬 "Animate chapter" (`kind: "animate"`) | write the chapter / the chapter's motions ("Journeys"), `jreply` |
| `journey-ref-note` | the user noted what a ⚓ reference shows / which character it is for | read the note (`run_journey` already applies it); nothing to render |
| `comment` | a new comment thread message | answer with `creply` (and act on it if it asks for something) |
| `reroll` / `upscale` / `refit` / `fix_area` / `journey-ref` / `journey-ref-crop` | 🎲 / ⤢ / ⬚ / ✎ buttons, ⚓ and ✂ on a reference | nothing: the server runs these itself. If one fails, see `feedback/pipeline/worker.log` |
| `style_mark` | ❤/👎 on a whole style | nothing now; weigh it when choosing what to evolve |

## The feedback loop

The gallery writes state to `feedback/*.json` and appends events to `feedback/log.jsonl`. `tools/feedback.py` is
your interface to it:

```
python tools/feedback.py inbox                        unhandled marks + open threads
python tools/feedback.py list [pending|sent|done]      marks by status (default: sent)
python tools/feedback.py reply <img-path> "<text>"     mark an image's request done, with a reply shown in the gallery
python tools/feedback.py comments                      open comment threads (last message is the user's)
python tools/feedback.py creply <target> "<text>"      reply in a thread (target: general, round:N, lineage:ID, version:ID/vNN, image:<path>)
python tools/feedback.py sets                          open 📌 sets (evolve = 1 image, cross = 2+ images)
python tools/feedback.py sreply <set-id> "<text>"      mark a set done; reply shows on every image in it
python tools/feedback.py journeys                      open 🧭 journey requests (start = new journey, direct = next chapter)
python tools/feedback.py jreply <req-id> "<text>" [journey-id]   mark a journey request done
```

### Marks (❤ / 👎 / 🎬 / 📌)

- **❤ love / 👎 nope** — persistent taste signal. Steer future choices toward/away from what's marked; note it in
  a version's `notes.json` `verdict` when relevant. These don't need a reply by themselves unless there's a note.
- **🎬 animate** — write a motion + sound prompt for that image (see "Video prompts" below) and render with
  `run_video.py`, default engine `fasth3`, then reply on the image.
- **👥 more characters** — same style, same layer, NOT an evolution: add a new version `vNN` to that image's lineage with
  the *identical* prompt and params and `params.subjects` = a NEW 6-character cast (3 women + 3 men by default) in the
  marked image's theme (modern / sci-fi / fantasy, or its kind: creatures, locations, ...). `notes.change` starts with
  `CHARACTERS:`. 👥 opens a popover with type chips (Women, Men, Mixed 3+3, Modern, Sci-fi, Fantasy, Horror, Creatures,
  Monsters, Villains, Undead, Robots/Machines, Everyday-job folk, Mythic, Locations; default "Same kind as this image") and a
  free-text box; the choice is saved in the mark's note as one line `👥 types: A, B — free text`, shown by
  `feedback.py inbox` / `list`. Read it and follow it: chosen types and text override "match the marked image's kind".
  Do it with `python tools/new_cast.py <marked png> spec.json [--render]`, where the spec is
  `{entries: [{kind, text}], change, why, prompt_edit?: [old, new]}`; the tool picks the next cast id and version, copies prompt and
  params from the *marked* image's version, writes keys `<kind>@<cast>~<n>`, and `--dry-run` writes nothing.
- **📌 pin (the evolve/cross tray)** — the user pins one or more images to a bottom tray with an optional
  directions box, then submits. This arrives as a `"set"` event: `{id, kind, images, caps, directions}` — `kind`
  is `"evolve"` for one image, `"cross"` for two or more. `python tools/feedback.py sets` lists open ones.
  Directions can contain `@<lineage#>/<vNN>/<image name>` references (typed with @-autocomplete in the tray);
  `feedback.py sets`/`inbox` expand each to its PNG path automatically.
  - Build the set as described under "Evolution sets" below (`python tools/new_set.py spec.json [--render]` does the
    mechanics: spec `{parents, why, tags, cast: {entries} | subjects, aspect_ratio?, variants: [{slug, title, change:
    "LABEL: goal", prompt (with {subject}), aspect_ratio?}]}`; it checks every variant prompt has the slot before writing).
  - Reply with `feedback.py sreply <id> "..."` — this marks the set done and shows the reply on every image in it.

### Comments

Free-text threads on `general`, `round:N`, `lineage:ID`, `version:ID/vNN`, or `image:<path>`. List open ones with
`feedback.py comments`, answer with `feedback.py creply <target> "..."`. A comment on the last scene of a journey
that describes what happens next counts as a direction: write the next chapter and reply there.

## Creating a version

A new version = one deliberate, describable change from its parent (prompt or params). To add `vNN` to an
existing lineage `evolutions/NNN-slug/`:

1. `vNN/prompt.txt` — the exact prompt, usually with a `{subject}` slot.
2. `vNN/params.json` — at minimum `seeds` (use `[1001]` for a single check render, more for a full cast pass),
   `steps`, `cfg`, `aspect_ratio`, `megapixels`, `model`, `sampler`, `scheduler`; add `subjects: [key, ...]` to
   pick which `subjects.json` keys fan out over `{subject}` (survey default: `f-modern`, `m-modern`, `f-scifi`,
   `m-scifi`, `f-fantasy`, `m-fantasy`, one seed each).
3. `vNN/notes.json` — `{"change": "...", "why": "...", "verdict": ""}`. Fill in `verdict` after you've looked at
   the render and/or gotten the user's reaction; quote their comments where relevant.
4. Render: `python tools/run_version.py evolutions/NNN-slug/vNN`. Existing images are skipped, so re-running
   only fills in what's missing. `--only f-modern,m-scifi` renders just those subjects; `--force` re-renders
   images that exist (the old ones move to `vNN/_rerolled/`, nothing is deleted).
5. Rebuild: `python tools/build_gallery.py` (also regenerates the lineage's `README.md` changelog table — never
   hand-edit that file).

Branching an idea into a genuinely different direction = a **new** `NNN-slug` lineage whose `lineage.json.parent`
points at the version it branched from.

## Style prompts describe the look only

A style prompt (a version's `prompt.txt` with its `{subject}` slot, and a journey's `style`) carries **medium, linework,
finish, palette, texture and mood** and nothing else. No places, settings, time of day, weather or scene lighting ("lived-in
interior", "night windows", "firelit hall"): those come from each subject or scene, and putting them in the style limits
the variety of worlds it can show. **The test: "will this limit the variety of the world? If yes, it's setting, not style:
remove it."** Vary settings and times of day across the cast instead. Apply the same test when you make 👥 versions of an
older lineage whose prompt still carries setting (`new_cast.py` spec `prompt_edit` removes it).

## Casting rules

Every character used in this project — survey subjects, evolution-set casts, journey casts, video NPCs — follows
the same rules:

- **Original and style-independent.** Characters are never pulled from a style's own franchise, world, or genre:
  no named characters, no races/species specific to that IP (e.g. no night elves for a WoW-flavored style, no
  planar oddballs for a Planescape-flavored style, no signature props). The style supplies the *look*
  (linework, shading, palette, mood); the cast is yours to invent. The one exception is a character the user
  explicitly asks you to use.
- **Specific, not generic.** Every character needs a described face, costume, and props, a specific action, a
  camera angle, and a clear emotion. Never "a tiny figure in a vast space" — that produces faceless stick figures,
  especially layered on top of a style that already favors negative space.
- **Medium or full-body framing with a readable face.** Not extreme long shots.
- **Gender and expression first, in plain words.** Open each subject with them ("a stern, unsmiling woman
  blacksmith in her fifties, ..."): a job title alone gets rendered with its stereotype (a "blacksmith" came out as
  a man), and a stylized look drifts toward smiling unless the text says otherwise (a "grim" diver came out laughing).
- **Mix everyday and unusual characters** in a set of 6 — spread scale, mood, setting, pose, and what makes each
  one interesting. Never six variations on one idea.
- **Tone:** serious and cinematic by default, even for outwardly cute/cartoon styles — save jovial or comedic for
  scenes that are actually comedic. Adult characters are fully clothed and non-suggestive; no gore. Monsters and
  villains read as eerie/weighty, never cute, never played for laughs.

## Evolution sets (📌 evolve / cross)

Evolving or crossbreeding an image from the gallery creates a small set of **sibling lineages** — new,
independent styles, each one a variant:

- **Evolve** (1 pinned image) → typically ~3 variant-style lineages, each `lineage.json.parent_images = [that
  image's path]`.
- **Cross** (2+ pinned images) → the variant styles merge/blend the parent styles; `parent_images` lists all of
  them. The variant's `README.md` diff is shown against the first parent.
- Each variant's `v01` = the parent style's prompt with **one** deliberate change (amplify what's working / fix
  what's weak / a related twist), keeping the `{subject}` slot, quoting the user's comments/marks in `notes.json`
  `why`.
- Give the set its **own new 6-character cast** in `subjects.json` under fresh keys (never reuse the plain survey
  keys for an evolution set) — `<slot>@<cast-name>~1..3` pattern works well, e.g. `f-modern@duskfall~1`. Follow
  the casting rules above. Render all variants at seed `1001` across the full 6-subject spread so the set reads
  as a rethought style shown across modern/sci-fi/fantasy × both genders, same as the original survey.
- `build_gallery.py` computes each lineage's evolution *layer* automatically (survey = layer 0; a set sits one
  layer below its deepest parent image) — you don't set this by hand.
- If a render job is already running when you create a new set, restart it so it picks up the new
  `build_gallery.py` state (jobs reload the builder before each rebuild, so this only matters for the very first
  build after adding the lineage).

## Gallery tools worth knowing

- **✎ Fix area** (lightbox, evolutions and journey scenes): the user draws a box and says what should be there;
  `POST /api/fix_area {src, box, text}` queues `tools/fix_area.py` on the same one-at-a-time worker as rerolls. It inpaints
  only the box (VAEEncode + SetLatentNoiseMask + KSampler, the image's own prompt led by "In the marked area: <text>.
  Everything else stays as it is.") and pastes the result over the ORIGINAL pixels through a feathered mask, so nothing
  outside the box changes. **Strength: removal texts (remove / no X / without / get rid...) repaint at denoise 1.0 and
  strip face clauses from the prompt; everything else at 0.65 so the old shape and colour guide the fix.** The queued job
  carries the image's mtime (`--if-mtime`): if a 🎲 replaced the picture meanwhile, the job is skipped and a comment on the
  image says so, because the box no longer fits. The old file moves to `_rerolled/`; `params.json` / `chapter.json` gets
  `fixes_area`. The `fix_area` event is informational.
- **Mobile lightbox**: on touch, swipe up raises and swipe down lowers the caption + buttons panel (a grab bar is the
  affordance; the ⌃ Details button is hidden), and pull-to-refresh is blocked while the lightbox is open.
- **`tools/contact_sheet.py out.jpg <version dirs | chNN dirs | pngs>`** makes a numbered grid for reviewing a whole
  set or chapter in one look (needs Pillow, which `requirements.txt` includes).

## Video prompts (image-to-video)

`python tools/run_video.py <image.png> <engine> --motion "..." [--camera "..." --sound "..." --line "..." --voice "..." --seconds 5]`

- Engines: `fasth3` (FastVideo FastH3, 8-step MiniMax H3 distill — default, best motion-prompt adherence) and
  `h3turbo` (full H3 + a 4-step lightx2v LoRA). Default to `fasth3` unless you have a specific reason not to.
- Prompts are built by `tools/video_prompt.py` in H3's native structured format: a header (medium + subject "from
  <Picture 1> in its original scene" + style traits + a style-lock sentence) / `SHOT n:` lines / an `Audio:` line.
  Structured beats prose here — prose has been seen to break a style's medium (e.g. a watercolor look drifting
  into 3D) where the style-lock sentence holds it.
- **No music by default** — every generated music bed tested so far has sounded off-key/unsynced; the builder
  appends "no music" unless you pass `--music`. **No ambience/drone by default either** — it appends "no
  background hum or drone" unless you pass `--sound`. Sound should tie to a *visible* action (a creak, a release,
  a whoosh); voices, laughs, and sighs work well. Monster/boss clips: eerie and weighty, never cute, and don't
  darken the frame for "ominous" — let the motion and sound carry the mood, keep the scene's own lighting.
- **Re-animating a character**: always write a new NPC line and a new action — `run_video.py` refuses an exact
  repeat unless you pass `--allow-repeat`.
- **Motion text describes only what is really in the shot.** No similes ("clouds drift like a flock of sheep" renders actual
  sheep) and never name a thing that must not appear ("no speech" makes speech; the builder's own "no music" is the exception
  it has tested). Say what happens, positively.
- **Speech.** H3 babbles gibberish in a clip with no `line`. "no speech, no voices" makes it worse, and "stoic and wordless"
  alone still babbles. What works: put **"silently" on the main action verb** in `--motion` ("the guard silently watches the
  road") **only when no face is visible in the frame**, plus the builder's automatic stoic clause and an `Audio:` line that
  leads with `Only the sounds of <--soundscape> can be heard: <sfx>`. **With a face on screen, have a narrator read the
  caption instead** (`--line <caption> --speaker "an unseen narrator off-screen, a voice-over; nobody in the picture moves
  their lips"`). In multi-character frames pass `--speaker "<who, where in frame>"` (batch key `speaker`) so only that person
  talks; without it the line can go to the wrong person. Journey scenes describe the scene's own cast (`noref` scenes
  describe the scene itself and don't carry the lead's sheet, which would turn other characters into the lead).
- 5 seconds fits about one action beat; split a longer arc into two `--shot` values or increase `--seconds`.
- Queue multiple clips as one process (`run_video.py --batch clips.json`, a list of per-clip dicts) rather than
  chaining separate invocations, so they all show in the queue panel up front.

## Journeys (🧭)

A journey follows **one character** from a lab image through their own world, chapter by chapter, directed by the
user. The character should not be posing for the camera — they exist in their world, and the world gets real
detail.

- **Start**: triggered by a 🧭 mark on a lab image (+ optional text). Create `journeys/NNN-slug/` (next free
  number): `journey.json` with the source version's style prompt (keep its `{subject}` slot), a character sheet
  (face, hair, outfit, props — read it off the image), a world bible grown from the image's setting, and
  `refs: [source image path]`. Then `ch01/chapter.json` with 6 scenes: vary the shots (wide establishing / medium
  / close detail / action), each a candid moment in a different place; write a one-line storybook `caption` per
  scene; end with 3-4 `choices` (hooks for what chapter comes next). **Before the first render, look at the source
  image and set `ref_crop` to the character's head and shoulders** (see below): a full-body reference leaks its
  pose into scenes, which on a first test cost a redo of 3 of 6 scenes. Render with
  `python tools/run_journey.py journeys/NNN-slug/ch01`, and `jreply` to the request as soon as the journey folder
  exists (the gallery links the request to the new journey).
- **Direct**: a "what happens next?" request (or a comment on the last scene of the latest chapter) → new `chNN`
  whose `direction` quotes the user verbatim; add any new places/NPCs to `world` as they appear.
- **Consistency**: `run_journey.py` feeds the journey's `refs` into `TextEncodeQwenImage21` as reference images
  (plus VAE, `ref_resolution` default 768) alongside a repeated character-sheet description and a CANDID clause
  (unaware of the viewer, three-quarter/profile/behind). The reference image's own background and pose can leak
  into scenes — watch for it and redo affected scenes (move the bad render to `chNN/_rerolled/`, edit the scene,
  re-run, and log it in the chapter's `revisions`). Never use a 16:9 scene as the *only* reference — the model
  tends to near-duplicate it.
- **Cast, not world soup**: journey `cast: {name: look}` + each scene's `with: [names]` + `place` — describe only
  who's actually in that scene ("X is the only person in the scene" if so), or side characters and clutter can
  bleed in from other scenes.
- **Cameos**: a cast entry can be `{look, ref: <lab png>, from}` to reuse an existing character portrait as an
  extra reference image (named "Reference image N shows X" in the prompt). Only do this with a same-style
  portrait (same lineage/version, or a sibling style from the same evolution set) — cross-style characters stay
  text-only.
- **`ref_crop`**: `{png: [x0, y0, x1, y1]}` (fractions) crops a reference to head-and-shoulders via ComfyUI's
  `ImageCrop` — useful when a full-body reference is leaking its pose into every scene. The gallery has a ✂ editor for it
  (after ⚓ on a scene, or under a thumbnail in the journey page's "Character references" row): draw, move or resize a box,
  Save / Clear / Cancel → `POST /api/journeys {op: "ref_crop", journey, src, crop: [x0,y0,x1,y1] | null}`. Thumbnails show the
  crop as the model gets it, so look at them before rendering; un-anchoring a reference drops its crop.
- **Reference notes + targets**: journey `ref_notes {png: text}` and `ref_for {png: lead name | cast key}` (default: the
  lead). The UI has a note field and a "Use for" select under each reference thumbnail (`op: "ref_note"`; the
  `journey-ref-note` event just means "read the note"). A `ref_for` cast-member reference goes ONLY to scenes whose `with` names
  that member (noref scenes too) and is named "Reference image N shows <note>."; a noted lead reference is named "shows
  <lead>: <note>." This stops, say, a cropped prop from leaking into every scene with the lead.
- **Director's `camera` field**: every scene may carry `camera` (shot size, angle, lens, frame position, facing, crop, depth
  layers). `run_journey.py` puts it first ("Camera: ...") and drops CANDID's fixed "three-quarter view, profile or from
  behind", which fights other framings. `python tools/scene_fix.py journeys/NNN/chNN sN --why "..."` (+ `--camera`,
  `--camera-append`, `--prompt`, `--prompt-append`, `--replace OLD NEW`, `--sheet-replace OLD NEW`, `--with a,b`, `--noref` /
  `--ref`, `--no-render`, `--dry-run`) reshoots one scene: edits it, logs `revisions`, and re-renders with a new seed
  (the old files go to `chNN/_rerolled/`). It warns when a camera looks from-behind but the scene isn't `noref`.
- **No-person shots** (inserts, empty landscapes): give the scene `nofigure: true`, or make it `noref` with a camera that says
  "NO person / face / ...". `run_journey.py` (`is_nofigure`) then skips the CANDID clause and the "<lead> is the only person"
  line and states "There are no people in this image". Without this, an insert of hands or an object tends to grow a
  stranger's face, because the rest of the prompt still talks about the character.
- **🎬 Animate chapter**: the button in each chapter header (with an optional note box) posts `{op: "animate", journey, chapter,
  text}` → a `journey` event with `kind: "animate"` (`feedback.py journeys` shows the chapter). Write per-scene `motion`
  (continuing scene to scene; plus optional `sfx`, `soundscape`, `camera_move`, `speaker_desc`, `voice`, `seconds`) into
  `chapter.json`, then run `python tools/animate_chapter.py journeys/NNN/chNN [--scenes s1,s3] [--engine fasth3] [--seed N] [--tag
  reel] [--mode auto|narrate|silent|storybook] [--dry-run]`. It decides the audio per scene and enforces the speech rules
  above: dialogue → that line + the named speaker; radio-only → an off-screen radio voice; `noref` with no dialogue → silent
  (warns if `motion` lacks "silently"); a visible face with no dialogue → a narrator reads the caption (`journey.json`
  `narrator_voice` overrides the voice); `--mode storybook` narrates every scene's caption. It writes `chNN/_reel_batch.json`,
  prints the table (use `--dry-run` to check it first), and runs ONE `run_video.py --batch`. Finish with `jreply`.
- **▶ Play journey / clips in place**: once any scene has a clip, the journey card and page show a button that plays one clip per
  scene back to back (chapter → scene order). Per scene the reel uses the newest ❤ clip, else the newest clip that isn't 👎.
  A scene with clips also shows a 🎬 N chip that opens an inline player with ❤ / 👎 and the clip's comment thread; the reel
  player has the same panel. Comments on a clip are prefixed with the playback time (`[@3.2s] ...`), so "the tone here" can be
  located. They are ordinary `image:<clip path>` threads: answer with `creply`.
- **💬 Speech bubbles**: scene `dialogue: [{who, text, pos: [x%, y%], tail: bl|br|b|tl|tr, radio: bool, w}]`. These
  render as HTML overlays in the gallery, not painted into the image. Write the dialogue with the chapter, leave
  open space in the upper frame for scenes that need it, then **look at the actual render** and place `pos`/`tail`
  with `tools/place_bubbles.py journeys/NNN/chNN sN "0:x,y,tail,w" ...` so no bubble covers a face and each tail
  points at its speaker.

## The GPU: one job at a time

`tools/pipeline.py` hands out a GPU ticket (`pipeline.gpu_acquire(kind)` / `gpu_release(kind)`) that
`run_version.py`, `run_journey.py`, and `run_video.py` all take before submitting to ComfyUI and release when
their job finishes. **Never submit directly to ComfyUI's `/prompt` bypassing this** — interleaving different model
kinds (image vs. video) forces ComfyUI to reload weights on almost every job, which is far slower than letting a
few same-kind jobs run back to back. If this ComfyUI install is shared with something else (another tool, another
session), `pipeline.yield_to_other_clients(server)` will wait for jobs it doesn't recognize as "ours" before
submitting — this is optional and a no-op if nothing else is using the install.

## Never expose the server

`serve_gallery.py` only accepts connections from loopback and private-LAN addresses by design — do not change
that, do not put it behind a public tunnel/port-forward, and do not weaken the check. It has no auth beyond that
network restriction.

## After rendering

Fill in each new version's `notes.json` `verdict` (and the journey chapter's `verdict`/`revisions` if relevant),
then `python tools/build_gallery.py`, then reply to whatever mark/set/journey/comment prompted the work.
