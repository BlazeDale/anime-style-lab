---
description: Read the gallery inbox and act on every open request (marks, 📌 sets, 🧭 journeys, 🎵 music videos, 📖 Nev Novel, comments)
---
Run `python tools/feedback.py inbox`. For each item it reports, follow AGENTS.md ("Which events need you" and the
section for that kind of request): do the work, then reply with the matching feedback.py command (reply / sreply /
jreply / creply) so it clears from the inbox. If the gallery server or `tools/watch_feedback.py` isn't running,
start it in the background first. Finish with a short summary of what you did and what's still rendering.
