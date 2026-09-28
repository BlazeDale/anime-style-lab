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
  - Optional, for `tools/run_video.py`: image-to-video models matching one of the two templates in
    `workflows/base/` (FastVideo FastH3, or MiniMax H3 + a 4-step lightx2v LoRA)
- **Python 3.10+** and **Node.js** (only for running `tools/test_gallery.js`; no npm packages needed).
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

Scans `evolutions/` and `journeys/`, writes `gallery/index.html` + `gallery/data.json`, and regenerates each
lineage's `README.md`. `serve_gallery.py` and `run_version.py` call this automatically after a render, so you
rarely need to run it by hand — but it's harmless (and fast) to run any time.

## Tests

```
node tools/test_gallery.js gallery/index.html
```

Runs a battery of logic checks against the built gallery page using a stub DOM. All should PASS; check the PASS
count, not just "no FAIL lines" — a JS syntax error crashes the run with zero output, which can look green if you
only grep for FAIL.

## Layout

```
evolutions/NNN-slug/          one prompt lineage; vNN/ = one iteration (prompt.txt, params.json, notes.json, workflow.json, seed*.png)
journeys/NNN-slug/            one character exploring their world, chapter by chapter (chNN/chapter.json + sN.png scenes)
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
