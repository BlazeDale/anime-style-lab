# anime-style-lab

A local lab for exploring anime illustration styles with [Qwen Image 2.1](https://github.com/QwenLM) in
[ComfyUI](https://github.com/comfyanonymous/ComfyUI).

The loop:

1. **Survey** — render the same handful of characters (modern / sci-fi / fantasy, one woman and one man each) in a
   spread of different anime styles (cel-shaded, watercolor, screentone, gacha key art, chibi, ...).
2. **React** — browse the results in a local gallery page and mark what you like: ❤ love, 👎 nope, 📌 pin for
   evolving or crossbreeding, 🎬 pin for turning into a short video clip.
3. **Evolve** — an AI coding agent (Claude Code, Codex, Cursor, whatever you point at this repo) reads your marks
   and comments, and iterates: new versions of a style ("what changed and why"), new branch lineages, or whole new
   *evolution sets* that crossbreed two styles together.
4. **Explore further** — turn a favorite character into a **journey** (a chapter-by-chapter story where they exist
   in their own world, not posing for the camera), or animate a still image into a short **video** clip.

Everything lives on disk as plain JSON + PNG files under `evolutions/` and `journeys/`; `tools/build_gallery.py`
turns that into a single static `gallery/index.html`, and `tools/serve_gallery.py` serves it locally with a small
feedback API (marks, comments, pins) so the gallery and your coding agent can talk to each other.

See **AGENTS.md** for the full operating manual if you're pointing a coding agent at this repo — it covers the
feedback loop, how to create a new style version or lineage, casting rules, video prompts, and journeys.

## Requirements

Tested on **Windows** with an NVIDIA GPU. The tools are written to also run on macOS/Linux (they find `.venv/bin/`
there), but that hasn't been tested yet: issues and fixes welcome.

- A recent **ComfyUI** install with the Qwen Image 2.1 custom nodes (`TextEncodeQwenImage21`,
  `ResolutionSelector`) available. These ship with a sufficiently recent ComfyUI frontend/core; if they're
  missing, update ComfyUI.
- Model files, in ComfyUI's usual model folders:
  - **Diffusion model**: `qwen_image_2.1_int8_convrot.safetensors` (or another Qwen Image 2.1 checkpoint — edit
    `params.json` per version to use a different one)
  - **Text encoder**: `qwen3vl_8b_int8_convrot.safetensors`
  - **VAE**: `qwen_image_2.1_vae_bf16.safetensors`
  - Optional, for sharper upscales (`tools/hires_card.py`, `tools/refit.py --model`): an ESRGAN-style upscale
    model such as `4x-AnimeSharp.pth`
  - Optional, for `tools/run_video.py`: image-to-video models matching one of the templates in
    `workflows/base/` (FastVideo FastH3, or MiniMax H3 + a 4-step lightx2v LoRA). The extra engines are each optional too
    and need their own model files and the stock ComfyUI nodes of the matching built-in template:
    LTX-2.5 22B (`ltx25`), Wan 2.2 14B image-to-video + lightx2v LoRAs (`wan22`), Wan 2.2 S2V 14B (`s2v`, `s2vfull`),
    LTX-2.3 22B image+audio (`ltxia2v`, lip sync). `python tools/doctor.py` lists which model files are missing.
  - Optional, `tools/lipsync.py` (experimental): the VideoHelperSuite and LatentSync custom nodes (never installed for you).
- **Python 3.10+** and **Node.js** (only for running `tools/test_gallery.js`; no npm packages needed).
- For the 🎵 music-video area (all optional): **ffmpeg** + **ffprobe** on your PATH (or set `ffmpeg` / `ffprobe` in
  `config.json`), and the pip packages `librosa`, `soundfile` and `faster-whisper` (listed in `requirements.txt`; lyric
  placement runs faster-whisper on the CPU and downloads its speech model on first use). Without them the rest of the lab works.
- [`comfy-cli`](https://github.com/Comfy-Org/comfy-cli), used by `run_version.py` / `run_video.py` to convert the
  workflow templates into API graphs.

## Quick start

Start ComfyUI first, then:

```
python tools/doctor.py            # what's there, what's missing (changes nothing)
python tools/doctor.py --fix      # create config.json + .venv (comfy-cli, Pillow, numpy) + the gallery page
python tools/smoke_test.py        # render one image into feedback/smoke/ to prove the pipeline end to end
```

`doctor.py` checks Python, the `.venv`, `config.json`, Node, whether ComfyUI answers at `comfy_url`, the Qwen
Image 2.1 nodes, and every model file the workflow templates load. It never installs anything into ComfyUI or
downloads models; it tells you which files to fetch. Edit `config.json` if your ComfyUI isn't on
`127.0.0.1:8188`.

### With a coding agent

Open the repo in your agent (Claude Code, Codex, Cursor, ...) and paste:

> Read AGENTS.md; it's your operating manual for this repo. Run tools/doctor.py and show me the result before
> installing anything. Once I say go, fix what's missing, run tools/smoke_test.py, start the gallery server and
> the feedback watcher in the background, and give me the gallery URL. Then act on my gallery reactions as
> AGENTS.md describes.

Claude Code users can type `/check` any time to have the agent read the inbox and act on it.

## Start the gallery server

```
.venv/Scripts/python tools/serve_gallery.py       # macOS/Linux: .venv/bin/python
```

Started with a different Python, it re-launches itself under the `.venv` (which has Pillow for the thumbnails).

Opens on **http://127.0.0.1:8765/gallery/** (port from `config.json`'s `gallery_port`). It also serves on your
LAN (other devices on your network can reach it at your machine's LAN IP) — it refuses connections from anywhere
else, so **never put this server on the public internet** or forward its port through your router.

## Render a version

```
.venv/Scripts/python tools/run_version.py evolutions/001-plain-anime/v01
```

Reads `prompt.txt` + `params.json` from that version folder, submits to ComfyUI, and writes the resulting PNG(s)
next to them. Images that already exist are skipped; `--only f-modern` renders one subject, and `--force`
re-renders (the old image moves to `vNN/_rerolled/`).

## Rebuild the gallery

```
.venv/Scripts/python tools/build_gallery.py
```

Scans `evolutions/`, `journeys/`, `musicvideos/` and `explore/`, writes `gallery/index.html` + `gallery/data.json`, and regenerates each
lineage's `README.md`. `serve_gallery.py` and `run_version.py` call this automatically after a render, so you
rarely need to run it by hand — but it's harmless (and fast) to run any time.

## Tests

```
node tools/test_gallery.js gallery/index.html
```

Runs a battery of logic checks against the built gallery page using a stub DOM. All should PASS; check the PASS
count, not just "no FAIL lines" — a JS syntax error crashes the run with zero output, which can look green if you
only grep for FAIL.

Run the Python tool tests (no ComfyUI needed, they use temp dirs):

```
python tools/test_labkit.py
python tools/test_journey_tools.py
python tools/test_revisions.py
python tools/test_mv_assemble.py   # needs ffmpeg
python tools/test_mv_refgen.py
python tools/test_mv_stems.py      # needs ffmpeg, librosa, soundfile
python tools/test_atlas.py
python tools/test_formality_atlas.py
python tools/test_deck.py
python tools/test_explore.py
python tools/test_saga.py
```

## More features

- **👥 more characters**: pick types (or write your own) and get a new cast in the same style (`tools/new_cast.py`).
- **✎ Fix area**: draw a box on an image, say what should be there, and only that area is repainted.
- **Journeys**: a ✂ crop editor and per-reference notes, no-person shots, scene reshoots (`tools/scene_fix.py`), a ▶ reel that
  prefers your ❤ clips, clip comments in place, and 🎬 Animate chapter (`tools/animate_chapter.py`).
- **Mobile lightbox**: swipe up / down for the details panel.
- **Gallery**: image counts, sorting and collapsible strips on every style, Videos grouped per style/journey, a **🕘 past
  revisions** viewer (compare, flip, wipe, restore any earlier version of a rerolled/fixed image), per-model chips and
  per-model average render times in the **⚙ Queue**, compact reference cards with an in-place crop overlay, and a daily
  **housekeeping** pass that prunes old discards after saving each one's lesson (`tools/housekeeping.py`). Queue rows link to
  their set, journey or saga; the 📌 tray reorders by drag; the cast box finds "every character matching …" across all casts;
  code updates wait until you stop watching.
- **🎞 Slideshow** (`#/show`): styles thrown onto a black table as spinning cards in slow motion, new evolve / cross sets first,
  your pins mingling with each hand, ❤ / 👎 / 📋 / 👥 on every card, drag to pin or out of the page, and an optional second
  monitor that extends the same show.
- **Render queue** (`tools/render_queue.py`): sets render one job at a time on the gallery server's worker (resumes after a
  restart) and a `render_done` event cues your agent to review them; `feedback.py taste` / `verdict` keep the loop light.
- **🎵 Music videos** (`musicvideos/`, `tools/mv_*.py`): a project per song with lyrics, an idea, reference images, and a
  waveform timeline where you mark what is sung when. Drop a **zip of stems** and the tool finds the mix, the lead vocal and
  every band member's entrances, solos, breakdowns and fills; **🎤 place lyrics** aligns your lyric lines to the vocal with
  faster-whisper; your agent storyboards with images (`run_journey.py` on `musicvideos/NNN/sbNN`), you request references
  or ask a reference for a variation, add scene **headlines** (lower-third overlays), and `mv_assemble.py` builds the **final
  cut** with the original song untouched (edit list, transitions, looks, dust, beat flashes, lyric captions), with build
  targets for a draft, a full-quality YouTube master, a size-capped Suno upload and **hooks**. `mv_hooks.py` exports each scene
  as a standalone clip with its headline and song slice, or (`--auto`) the whole song as 10-30 s hooks cut at scene changes and
  vocal pauses. A ✓ Hide approved toggle on the storyboard shows only the frames still to do. Experimental: the two-plate lip-sync composite
  (`mv_plates.py` + `mv_composite.py`) and the LatentSync pass (`lipsync.py`).
- **📖 NevNovella** (`explore/`, `tools/saga.py`, `tools/explore_*.py`): a never-ending visual novel your agent writes as you
  watch. A saga bible (lore, cast, places, threads) keeps continuity; cast reference images keep faces consistent; a full-screen
  visual-novel player shows stills with narration and dialogue. A deck steers it: composition **presence**, an **Emotion Atlas**
  and a **Formality Atlas** (living maps of ~140 concepts wired by researched story links, browsed as a little solar system of
  related feelings, whose connections strengthen with your likes), one emotional **core** per saga, up to three **genres**, and a
  **maturity** dial (Preschool to Mature) whose content ceiling rides in every image prompt; anything romantic involves adults
  only at every stop, and Mature content is left to the discretion of you and the model writing the story. Each session runs in a 15-minute window and waits for you to press Continue. Chapters are
  checked for story craft (scenes with goals and stakes, a costly choice, a hook, faces that show the moment) and paced so the
  reading keeps up with the renders; the player shows your place, the render queue and the timer, copies or drags out the
  current picture, and has a chat panel for your agent. 🎬 Animate a chapter, then build its **final cut** (draft, YouTube
  master, Suno, hooks; `tools/saga_assemble.py`) with world-building overview captions, your own uploaded song, beat-snapped
  cuts and a shared grade, or cut a range of chapters into one music video fitted to the song's length.
- **🧪 Render bake-offs** (`tools/saga_bench.py`, `tools/style_bench.py`, `tools/bench_page.py`): try render settings (steps,
  reference resolution, megapixels + upscaler) on real lineages and saga shots and compare speed and quality per style on
  `gallery/bench.html`. `tools/shot.py` screenshots the running gallery in headless Edge.
- **Engines**: optional LTX, Wan 2.2 and audio-driven lip-sync video engines (see Requirements).

## Layout

```
evolutions/NNN-slug/          one prompt lineage; vNN/ = one iteration (prompt.txt, params.json, notes.json, workflow.json, seed*.png)
journeys/NNN-slug/            one character exploring their world, chapter by chapter (chNN/chapter.json + sN.png scenes)
musicvideos/NNN-slug/         one music-video project: mv.json, audio/, sbNN/ storyboards, edit.json, cut/ (gitignored: your own work)
explore/                      NevNovella: the two starter atlases (tracked); episodes and sagas/ are gitignored
workflows/base/               ComfyUI workflow templates (never edited directly — copied per render)
gallery/                      generated: index.html + data.json
tools/                        build_gallery.py, serve_gallery.py, run_version.py, run_video.py, run_journey.py, feedback.py, ...
feedback/                     local-only state: marks, comments, pins, the render-queue registry (gitignored)
subjects.json                 the character cast(s) used across style versions
config.json                   your local machine config (gitignored; see config.example.json)
```

## License

MIT (see `LICENSE`) for this repo's code and docs. The ComfyUI workflow templates in `workflows/base/` come from
ComfyUI's template library and stay under their original license; the sample images were generated with Qwen
Image 2.1.
