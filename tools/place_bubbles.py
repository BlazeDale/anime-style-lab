"""Set speech-bubble placement on journey scenes after looking at the render.

  python tools/place_bubbles.py journeys/002-x/ch01 s1 "0:2,2,b,30" "1:36,3,b,28"
      each spec  <line index>:<x%>,<y%>,<tail bl|br|b|tl|tr|none>[,<max width %>]
  python tools/place_bubbles.py journeys/002-x/ch01 s2 --who 0 Bram --radio 0 off --text 0 "New line"
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")
chdir, sid, args = ROOT / sys.argv[1], sys.argv[2], sys.argv[3:]
p = chdir / "chapter.json"
ch = json.loads(p.read_text(encoding="utf-8"))
dlg = next(s for s in ch["scenes"] if s["id"] == sid)["dialogue"]
i = 0
while i < len(args):
    a = args[i]
    if a in ("--who", "--text", "--radio"):
        n, v = int(args[i + 1]), args[i + 2]
        if a == "--radio":
            dlg[n].pop("radio", None) if v == "off" else dlg[n].update(radio=True)
        else:
            dlg[n]["who" if a == "--who" else "text"] = v
        i += 3
        continue
    n, spec = a.split(":")
    x, y, tail, *w = spec.split(",")
    dlg[int(n)].update(pos=[float(x), float(y)], tail=tail)
    if w:
        dlg[int(n)]["w"] = float(w[0])
    i += 1
p.write_text(json.dumps(ch, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(dlg, ensure_ascii=False))
