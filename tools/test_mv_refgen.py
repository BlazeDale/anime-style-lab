"""Tests for the 🖼 reference-request flow: /api/mv ref_gen_request / ref_gen_cancel (second server on a spare port, everything redirected to a
temp dir, gallery rebuild stubbed), feedback.py inbox / mvs / mvgen, watch_feedback classification, mv_ref_gen helpers.
Run: python tools/test_mv_refgen.py   (no GPU, never touches the real musicvideos/ or feedback/; the server part is skipped with a
message when serve_gallery cannot be used)"""
import functools
import http.server
import io
import json
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
PASS = FAIL = 0


class SIO(io.StringIO):
    def reconfigure(self, **kw):
        pass


def ok(c, m):
    global PASS, FAIL
    print(("PASS " if c else "FAIL ") + m)
    PASS += bool(c)
    FAIL += not c


import mv_ref_gen as rg  # noqa: E402
try:
    import serve_gallery as sg  # noqa: E402
    import feedback as fb  # noqa: E402
    import watch_feedback as wf  # noqa: E402
    assert all(hasattr(sg, n) for n in ("MVDIR", "MVS", "mv_save", "Handler", "LOG")) and hasattr(fb, "gen_line") and hasattr(fb, "mvgen")
except Exception as e:  # the server part needs the music-video API of serve_gallery / feedback
    sg = None
    print("SKIP server / feedback section (%s)" % e)

# mv_ref_gen helpers (pure)
m = {"style": "3D render of {subject}, soft", "ref_notes": {}}
ok(rg.aspect_name("16:9") == "16:9 (Widescreen)" and rg.aspect_name(None) == "3:4 (Portrait Standard)" and rg.aspect_name("1:1 (Square)") == "1:1 (Square)", "aspect names")
_t = Path(tempfile.mkdtemp(prefix="mvgen_"))
(_t / "refs").mkdir()
(_t / "refs" / "gen_1.png").write_bytes(b"x")
ok(rg.next_out(_t / "refs").name == "gen_2.png" and rg.next_out(_t / "refs", "x").name == "x.png", "next free gen_<n>.png / --out")
shutil.rmtree(_t, ignore_errors=True)
p = rg.prompt_of(m, "Bob, full body", ["a.png"])
ok(p.endswith("3D render of Bob, full body, soft") and p.startswith("Reference image 1 shows"), "prompt = style with {subject} filled, reference preface")
ok(rg.prompt_of(m, "Bob", []) == "3D render of Bob, soft", "no refs: no preface")

def server_section(tmp):
    sg.FB, sg.LOG, sg.MVS, sg.MVDIR = tmp / "fb", tmp / "fb" / "log.jsonl", tmp / "fb" / "mvs.json", tmp / "musicvideos"
    sg.rebuild_bg = lambda: None
    d = sg.MVDIR / "900-t"
    d.mkdir(parents=True)
    sg.mv_save(d, {"title": "T", "refs": ["a.png"], "markers": [], "name": "Alice", "cast": {"Bob": "white shirt"}, "style": "3D render of {subject}, soft", "ref_notes": {}})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(sg.Handler, directory=str(sg.ROOT)))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    def post(body):
        req = urllib.request.Request("http://127.0.0.1:%d/api/mv" % port, data=json.dumps(body).encode(), method="POST", headers={"Content-Type": "application/json"})
        try:
            return 200, json.loads(urllib.request.urlopen(req, timeout=20).read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    c, j = post({"op": "ref_gen_request", "mv": "900-t", "text": "  Bob full body  ", "for": "Bob"})
    g = (j.get("mv") or {}).get("gen_requests") or []
    ok(c == 200 and len(g) == 1 and g[0]["id"] == "g1" and g[0]["text"] == "Bob full body" and g[0]["for"] == "Bob" and g[0]["status"] == "open", "request stored as g1/open")
    c, j = post({"op": "ref_gen_request", "mv": "900-t", "text": "the mic", "for": "Alice"})
    g = j["mv"]["gen_requests"]
    ok(c == 200 and g[1]["id"] == "g2" and g[1]["for"] == "", "second request g2; the lead (by name) is stored as empty")
    ok(post({"op": "ref_gen_request", "mv": "900-t", "text": ""})[0] == 400 and post({"op": "ref_gen_request", "mv": "900-t", "text": "x" * 501})[0] == 400, "empty / >500 chars refused")
    ok(post({"op": "ref_gen_request", "mv": "900-t", "text": "x", "for": "Nobody"})[0] == 400 and post({"op": "ref_gen_request", "mv": "nope", "text": "x"})[0] == 400, "unknown character / music video refused")
    ev = [json.loads(l) for l in sg.LOG.read_text(encoding="utf-8").splitlines()]
    ok([e["kind"] for e in ev if e.get("event") == "mv"] == ["ref_request", "ref_request"] and ev[0]["id"] == "g1" and ev[0]["text"] == "Bob full body" and not any(e["event"].startswith("mv-ref") for e in ev), "ref_request events logged (no stray mv-ref event)")
    ok(not wf.is_info(ev[0]) and wf.fmt(json.dumps(ev[0])).startswith("[ACT]") and wf.is_info({"event": "mv", "kind": "ref_request_cancel"}) and not wf.is_info({"event": "mv", "kind": "submit"}) and wf.is_info({"event": "mv", "kind": "start"}), "watcher: ref_request = ACT, cancel / start = info")

    # feedback.py against the temp tree
    fb.MVD, fb.ROOT, fb.MVS, fb.COMMENTS, fb.STATE, fb.SETS, fb.JOURNEYS = sg.MVDIR, tmp, sg.MVS, tmp / "c.json", tmp / "s.json", tmp / "se.json", tmp / "j.json"
    fb.rebuild = lambda: None
    sys.argv = ["feedback.py", "inbox"]
    buf = SIO()
    with redirect_stdout(buf):
        fb.main()
    out = buf.getvalue()
    ok("2 🖼 reference request(s)" in out and "🖼 ref request 900-t g1 for Bob: Bob full body" in out and "🖼 ref request 900-t g2 for the singer: the mic" in out, "inbox lists open requests")
    sys.argv = ["feedback.py", "mvs"]
    buf = SIO()
    with redirect_stdout(buf):
        fb.main()
    ok("ref request 900-t g1" in buf.getvalue(), "mvs lists them too")

    c, j = post({"op": "ref_gen_cancel", "mv": "900-t", "id": "g2"})
    ok(c == 200 and j["mv"]["gen_requests"][1]["status"] == "cancelled" and post({"op": "ref_gen_cancel", "mv": "900-t", "id": "g2"})[0] == 400 and post({"op": "ref_gen_cancel", "mv": "900-t", "id": "zz"})[0] == 400, "cancel works once; unknown / already cancelled refused")
    ok(json.loads(sg.LOG.read_text(encoding="utf-8").splitlines()[-1])["kind"] == "ref_request_cancel", "cancel event logged")

    c, j = post({"op": "ref_gen_request", "mv": "900-t", "text": "front view, eyes open", "src": "a.png"})
    g3 = (j.get("mv") or {}).get("gen_requests", [{}])[-1]
    ok(c == 200 and g3.get("src") == "a.png" and post({"op": "ref_gen_request", "mv": "900-t", "text": "x", "src": "not/a/ref.png"})[0] == 400, "request from a reference stores src; a src that is not one of the refs is refused")
    ok("[from a.png: render with --ref a.png]" in fb.gen_line("900-t", g3), "feedback shows 'from <src>'")
    post({"op": "ref_gen_cancel", "mv": "900-t", "id": g3["id"]})

    png = d / "refs" / "gen_1.png"
    png.parent.mkdir()
    png.write_bytes(b"\x89PNG fake")
    sys.argv = ["feedback.py", "mvgen", "900-t", "g1", str(png), "here you go"]
    buf = SIO()
    with redirect_stdout(buf):
        fb.main()
    m = json.loads((d / "mv.json").read_text(encoding="utf-8"))
    g1 = m["gen_requests"][0]
    ok(g1["status"] == "done" and g1["result"] == "musicvideos/900-t/refs/gen_1.png" and g1["reply"] == "here you go" and g1.get("done_ts"), "mvgen marks the request done with result / reply / done_ts")
    rel = g1["result"]
    ok(rel in m["refs"] and m["ref_notes"][rel] == "Bob full body" and m["ref_for"][rel] == "Bob", "result added to refs with the request text as note and the cast member as target")
    fb.mvgen("900-t", "g1", str(png))
    ok(json.loads((d / "mv.json").read_text(encoding="utf-8"))["refs"].count(rel) == 1, "mvgen twice does not duplicate the ref")
    sys.argv = ["feedback.py", "inbox"]
    buf = SIO()
    with redirect_stdout(buf):
        fb.main()
    ok("reference request" not in buf.getvalue() and buf.getvalue() == "", "inbox is silent once requests are done / cancelled")


tmp = Path(tempfile.mkdtemp(prefix="mvgen_"))
try:
    if sg:
        server_section(tmp)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print(f"{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
