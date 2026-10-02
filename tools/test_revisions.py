"""Tests for the 🕘 past-revisions viewer: build_gallery.collect_revs + serve_gallery.restore_revision + POST /api/revision/restore.
Run: python tools/test_revisions.py     Works on a temp tree with synthetic files (and a second server instance on a free port with ROOT/feedback
pointed at it, rebuild stubbed); nothing under the real evolutions/, journeys/, musicvideos/ is touched."""
import functools
import http.server
import json
import socket
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import build_gallery as bg  # noqa: E402
import serve_gallery as sg  # noqa: E402

PASS = FAIL = 0


def stamp_ts(stamp):
    """YYYYMMDD-HHMMSS -> 'YYYY-MM-DD HH:MM:SS' (what collect_revs reports)"""
    d, t = stamp.split("-")
    return f"{d[:4]}-{d[4:6]}-{d[6:]} {t[:2]}:{t[2:4]}:{t[4:]}"


def free_port():
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0))
        return so.getsockname()[1]


PORT = free_port()


def ok(c, m):
    global PASS, FAIL
    print(("PASS " if c else "FAIL ") + m)
    PASS += bool(c)
    FAIL += not c


tmp = Path(tempfile.mkdtemp(prefix="revtest_"))
evo = tmp / "evolutions" / "999-x" / "v01"
jch = tmp / "journeys" / "998-j" / "ch01"
mvf = tmp / "musicvideos" / "997-m" / "sb01"
for d in (evo, jch, mvf):
    (d / "_rerolled").mkdir(parents=True)
(evo / "params.json").write_text("{}", encoding="utf-8")
(jch / "chapter.json").write_text("{}", encoding="utf-8")


def put(p, txt):
    p.write_bytes(txt.encode())


# evolutions: seed image with a per-image workflow and two archived revisions; one archive whose current image is gone; a junk file
put(evo / "f-x@c~1_seed1001.png", "CUR")
put(evo / "f-x@c~1_seed1001.workflow.json", "WFCUR")
put(evo / "_rerolled" / "f-x@c~1_seed1001__20210101-010101.png", "OLD1")
put(evo / "_rerolled" / "f-x@c~1_seed1001.workflow__20210101-010101.json", "WFOLD1")
put(evo / "_rerolled" / "f-x@c~1_seed1001__20210202-020202.png", "OLD2")
put(evo / "_rerolled" / "gone_seed1__20210101-010101.png", "X")
put(evo / "_rerolled" / "s1_v1.png", "junk")
put(jch / "s3.png", "JCUR")
put(jch / "_rerolled" / "s3__20210303-030303.png", "JOLD")
put(mvf / "s1.png", "MCUR")
put(mvf / "_rerolled" / "s1__20210404-040404.png", "MOLD")

r = bg.collect_revs(tmp)
k = "evolutions/999-x/v01/f-x@c~1_seed1001.png"
ok(set(r) == {k, "journeys/998-j/ch01/s3.png", "musicvideos/997-m/sb01/s1.png"}, "collector: one key per current image with archives; missing current + junk names skipped: %s" % sorted(r))
ok([x["ts"] for x in r[k]] == [stamp_ts("20210202-020202"), stamp_ts("20210101-010101")], "collector: newest first, ts parsed from the stamp")
ok(r[k][0]["src"] == "../evolutions/999-x/v01/_rerolled/f-x@c~1_seed1001__20210202-020202.png", "collector: src is the ../-relative archive path")

# restore swap
res = sg.restore_revision(k, "evolutions/999-x/v01/_rerolled/f-x@c~1_seed1001__20210101-010101.png", root=tmp, now=1780000000)
cur = evo / "f-x@c~1_seed1001.png"
ok(cur.read_bytes() == b"OLD1" and (evo / "f-x@c~1_seed1001.workflow.json").read_bytes() == b"WFOLD1", "restore: chosen revision + its workflow are back under the current names")
arch = sorted(p.name for p in (evo / "_rerolled").iterdir())
ok(not any("20210101-010101" in n and "seed1001" in n for n in arch), "restore: the chosen archive entry moved out of _rerolled")
new = evo / "_rerolled" / res["archived"]
ok(new.read_bytes() == b"CUR" and (evo / "_rerolled" / res["archived"].replace("_seed1001__", "_seed1001.workflow__").replace(".png", ".json")).read_bytes() == b"WFCUR",
   "restore: the replaced picture + workflow are archived (nothing deleted): %s" % res["archived"])
ok(abs(cur.stat().st_mtime - time.time()) < 30, "restore: restored png mtime = now")
meta = json.loads((evo / "params.json").read_text(encoding="utf-8"))
ok(meta["restores"][cur.name][0]["from"].endswith("20210101-010101.png"), "restore: params.json restores logged")
r2 = bg.collect_revs(tmp)
ok(len(r2[k]) == 2 and any(x["src"].endswith(res["archived"]) for x in r2[k]), "collector after restore: still 2 revisions, the old current is listed")
# undo: restore again gets the original back
sg.restore_revision(k, "evolutions/999-x/v01/_rerolled/" + res["archived"], root=tmp)
ok(cur.read_bytes() == b"CUR" and (evo / "f-x@c~1_seed1001.workflow.json").read_bytes() == b"WFCUR", "restore again = undo")
# two restores in one second get different archive names
ok(len({p.name for p in (evo / "_rerolled").glob("*.png")}) == len(list((evo / "_rerolled").glob("*.png"))), "archive names unique")

# validation
bad = [(k, "evolutions/999-x/v01/f-x@c~1_seed1001__20210202-020202.png"),           # not inside _rerolled
       (k, "evolutions/999-x/v01/_rerolled/s1_v1.png"),                                # not a stamped name
       (k, "evolutions/999-x/v01/_rerolled/gone_seed1__20210101-010101.png"),          # another image's archive
       (k, "evolutions/999-x/v01/_rerolled/../../../../x.png"),                        # traversal
       ("evolutions/999-x/v01/nope.png", "evolutions/999-x/v01/_rerolled/nope__20210101-010101.png"),
       ("evolutions/999-x/params.json", "evolutions/999-x/v01/_rerolled/x__20210101-010101.png"),
       ("../../../Windows/x.png", "evolutions/999-x/v01/_rerolled/x__20210101-010101.png")]
for a, b in bad:
    try:
        sg.restore_revision(a, b, root=tmp)
        ok(False, "validation accepted %s" % b)
    except ValueError:
        ok(True, "validation refused %s" % b)

# journey scene: chapter.json restores
sg.restore_revision("journeys/998-j/ch01/s3.png", "journeys/998-j/ch01/_rerolled/s3__20210303-030303.png", root=tmp)
ok((jch / "s3.png").read_bytes() == b"JOLD" and "s3.png" in json.loads((jch / "chapter.json").read_text(encoding="utf-8"))["restores"], "journey scene swap + chapter.json restores (no workflow json present: fine)")

# HTTP endpoint on a second instance pointed at the temp tree
fb = Path(tempfile.mkdtemp(prefix="revfb_"))
sg.ROOT, sg.FB, sg.LOG = tmp, fb, fb / "log.jsonl"
sg.rebuild_bg = lambda: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(sg.Handler, directory=str(tmp)))
threading.Thread(target=srv.serve_forever, daemon=True).start()


def post(body):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/api/revision/restore", data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
    try:
        return 200, json.loads(urllib.request.urlopen(req, timeout=20).read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


code, j = post({"src": "../musicvideos/997-m/sb01/s1.png?v=1", "rev": "../musicvideos/997-m/sb01/_rerolled/s1__20210404-040404.png"})
ok(code == 200 and j.get("ok") and (mvf / "s1.png").read_bytes() == b"MOLD" and "ts" in j, "POST restore on a music-video frame: %s %s" % (code, j))
code, j = post({"src": "musicvideos/997-m/sb01/s1.png", "rev": "musicvideos/997-m/sb01/s1.png"})
ok(code == 400, "POST with a non-archive rev -> 400")
ev = [json.loads(line) for line in (fb / "log.jsonl").read_text(encoding="utf-8").splitlines()]
ok(len(ev) == 1 and ev[0]["event"] == "revision_restore" and ev[0]["src"] == "musicvideos/997-m/sb01/s1.png", "log.jsonl got one revision_restore event (only the successful one)")
srv.shutdown()

import shutil  # noqa: E402
shutil.rmtree(tmp, ignore_errors=True)
shutil.rmtree(fb, ignore_errors=True)
print("PASS %d FAIL %d" % (PASS, FAIL))
sys.exit(1 if FAIL else 0)
