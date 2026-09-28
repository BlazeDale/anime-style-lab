"""Watch feedback/log.jsonl and print one line per new gallery event (marks sent, sets, journeys, comments, ...).

    python tools/watch_feedback.py            resume where the last watch stopped (catches events sent in between)
    python tools/watch_feedback.py --new      only events from now on
    python tools/watch_feedback.py --all      replay the whole log first

Polls the file every 2 s instead of relying on file-change notifications (`tail -F` misses appends on Windows).
Each printed line is a compact JSON event, cut to ~400 chars; run `python tools/feedback.py inbox` for the full
picture before acting. Works with any agent harness that can stream a background command's stdout.
Standard library only.
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "feedback" / "log.jsonl"
OFFSET = ROOT / "feedback" / "pipeline" / "watch.offset"  # byte offset the last watch had read up to

# events the gallery server handles by itself: shown, but flagged so nobody starts duplicate work
INFO_ONLY = {"reroll", "upscale", "refit", "style_mark", "blur"}


def fmt(line):
    try:
        ev = json.loads(line)
    except json.JSONDecodeError:
        return line[:400]
    tag = "info" if ev.get("event") in INFO_ONLY else "ACT"
    return f"[{tag}] " + json.dumps(ev, ensure_ascii=False)[:400]


def save(pos):
    OFFSET.parent.mkdir(parents=True, exist_ok=True)
    OFFSET.write_text(str(pos))


def main():
    size = LOG.stat().st_size if LOG.exists() else 0
    if "--all" in sys.argv:
        pos = 0
    elif "--new" in sys.argv or not OFFSET.exists():
        pos = size
    else:
        pos = int(OFFSET.read_text() or 0)
        if pos > size:  # log was reset
            pos = 0
    print(f"watching {LOG.relative_to(ROOT)} from byte {pos} (size {size})", flush=True)
    buf = b""
    while True:
        if LOG.exists():
            size = LOG.stat().st_size
            if size < pos:
                pos, buf = 0, b""
            if size > pos:
                with open(LOG, "rb") as f:
                    f.seek(pos)
                    chunk = f.read(size - pos)
                pos = size
                buf += chunk
                *lines, buf = buf.split(b"\n")
                for raw in lines:
                    if raw.strip():
                        print(fmt(raw.decode("utf-8", "replace")), flush=True)
                save(pos - len(buf))
        time.sleep(2)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
