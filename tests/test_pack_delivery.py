"""How a pack reaches a pilot, and the build that no longer happens.

THE MODEL, IN ONE LINE: the product ships THIN and content is uploaded.

`scripts/build_pack.py` produces a `.sspack`; somebody uploads it through
`/admin`; the server serves bytes. No packs in the image, none in the release
zip, none in git. A syllabus is either PUBLISHED or it is flown one ride at a
time — and the eleven-missions-in-one-request build that took the machine down
is deleted rather than cached around.

This file replaces `test_prebuilt_tracks.py` (a cache of a computation) and
`test_bundled_packs.py` (content welded into the image). Both were answers to
the same question and this is the third one, which is the one Rob asked for:
thin architecture, packs uploaded.
"""
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from missiongen import packfmt as F                            # noqa: E402

MIZ = b"PK\x05\x06" + b"\0" * 18


@pytest.fixture()
def server(tmp_path, monkeypatch):
    """A server with an EMPTY pack volume — a fresh deploy, in other words."""
    from fastapi.testclient import TestClient
    from missiongen import packs
    import server.app as A
    monkeypatch.setattr(packs, "DATA_DIR", tmp_path / "packs")
    (tmp_path / "packs").mkdir()
    monkeypatch.setenv("ADMIN_PASSWORD", "t3st")
    c = TestClient(A.app)
    c.post("/admin/login", data={"password": "t3st"}, follow_redirects=False)
    return c


def _pack_bytes(pid="hist_set", n=3, label="A Historical Set"):
    """A pack of the shape somebody hand-builds in the Mission Editor."""
    files = {f"{i:02d}_mission.miz": MIZ for i in range(1, n + 1)}
    files.update({f"brief_{i:02d}.pdf": b"%PDF" for i in range(1, n + 1)})
    files["Squadron Guide.pdf"] = b"%PDF"
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for k, v in files.items():
            z.writestr(f"{pid}/{k}", v)
    return b.getvalue()


# --------------------------------------------------------------------------- #
# 1. The product ships thin
# --------------------------------------------------------------------------- #
def test_the_docker_image_carries_no_content():
    """Content baked into an image can only change by deploying, and a
    corrected premise line is not a deploy. Tried the other way for exactly one
    release: the image gained 44 MB and the release zip reached 59 MB, which is
    large enough that it stopped being handable over a normal channel."""
    live = [ln.strip() for ln in (ROOT / "Dockerfile").read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")]
    assert not [ln for ln in live if "build_pack.py" in ln], live
    assert not [ln for ln in live if ln.startswith("COPY packs")], live


def test_the_release_zip_carries_no_packs():
    pkg = (ROOT / "scripts" / "package.sh").read_text()
    manifest = pkg[pkg.index("MANIFEST=("):pkg.index(")", pkg.index("MANIFEST=("))]
    # ENTRIES, not the word. The block carries prose explaining why packs are
    # absent, and a substring check on "packs" fails on the explanation — which
    # would be a test that punishes the comment for existing.
    entries = [ln.strip().split()[0] for ln in manifest.splitlines()[1:]
               if ln.strip() and not ln.strip().startswith("#")]
    assert "packs" not in entries, entries


def test_packs_are_not_committed():
    assert "packs/" in (ROOT / ".gitignore").read_text()
    tracked = subprocess.run(["git", "ls-files", "packs"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    assert not tracked, tracked


def test_the_producer_still_exists_and_runs():
    """Thin does not mean the syllabi stop being producible — it means they are
    produced and then uploaded, rather than produced and then baked in."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_pack.py"), "--list"],
        cwd=ROOT, capture_output=True, text=True,
        env={"PYTHONPATH": f"{ROOT}:{ROOT / 'vendor'}",
             "PATH": "/usr/bin:/bin", "HOME": "/tmp"})
    assert r.returncode == 0, r.stderr[-1200:]
    assert "wk_proud_phantom" in r.stdout


# --------------------------------------------------------------------------- #
# 2. No request builds a syllabus, ever again
# --------------------------------------------------------------------------- #
def test_an_unpublished_syllabus_refuses_instead_of_building(server,
                                                             monkeypatch):
    """THE WHOLE POINT. Not "it is cached" — the build is GONE. `generate` is
    replaced with something that raises, so if the request builds a single
    mission this fails with that exception rather than a timing wobble."""
    import server.app as A

    def boom(*a, **k):
        raise AssertionError("a mission was built inside the request")
    monkeypatch.setattr(A, "generate", boom)

    r = server.get("/api/track/wk_proud_phantom/all.zip")
    assert r.status_code == 409, r.status_code
    # 409, not 404: the syllabus exists, it simply is not published here, and
    # the message has to send the pilot somewhere real.
    assert "ride" in r.json()["detail"].lower()


def test_the_old_query_parameters_still_resolve(server):
    """Every share link and bookmark from before the pack model. They are
    accepted and ignored; what they used to do is the thing that had to stop."""
    r = server.get("/api/track/wk_proud_phantom/all.zip"
                   "?era=coldwar&aircraft=F_4E_45MC&tanker=kc135")
    assert r.status_code == 409


def test_a_track_that_does_not_exist_is_still_a_404(server):
    assert server.get("/api/track/not_a_track/all.zip").status_code == 404


def test_the_in_request_syllabus_builder_is_gone():
    """A guard against it coming back the next time somebody wants a
    convenience. The function that assembled eleven missions in a request had a
    name; nothing should have it again."""
    src = (ROOT / "server" / "app.py").read_text()
    assert "_track_zip_path" not in src, "the in-request builder is back"


# --------------------------------------------------------------------------- #
# 3. Upload, and it is published
# --------------------------------------------------------------------------- #
def test_uploading_a_pack_publishes_the_syllabus(server):
    """The whole workflow, in one test: a fresh server has nothing, an upload
    makes it real, and the download that answered 409 answers bytes."""
    assert server.get("/api/track/hist_set/all.zip").status_code == 404
    r = server.post("/admin/packs",
                    files={"file": ("hist_set.zip", _pack_bytes())},
                    data={"pack_id": "", "label": ""}, follow_redirects=False)
    assert r.status_code == 303, r.status_code
    assert "/edit" in r.headers["location"], r.headers["location"]

    opts = server.get("/api/options").json()
    card = opts["templates"]["pack_hist_set"]
    assert len(card["pack"]["events"]) == 3
    assert card["pack"]["source"] == "installed"
    z = server.get("/api/pack/hist_set/all.zip")
    assert z.status_code == 200 and len(z.content) > 200


def test_a_published_pack_takes_over_its_track_card(server):
    """A pack and a track sharing an id are the same syllabus. Two cards for
    one thing makes the pilot learn an implementation detail."""
    opts = server.get("/api/options").json()
    assert opts["tracks"]["wk_proud_phantom"]["published"] is False
    assert opts["tracks"]["wk_proud_phantom"]["superseded_by_pack"] is False

    with open(ROOT / "packs" / "wk_proud_phantom.sspack", "rb") as f:
        raw = f.read()
    server.post("/admin/packs",
                files={"file": ("wk_proud_phantom.sspack", raw)},
                data={"pack_id": "", "label": ""}, follow_redirects=False)

    opts = server.get("/api/options").json()
    assert opts["tracks"]["wk_proud_phantom"]["published"] is True
    assert opts["tracks"]["wk_proud_phantom"]["superseded_by_pack"] is True
    assert server.get("/api/track/wk_proud_phantom/all.zip").status_code == 200


test_a_published_pack_takes_over_its_track_card = pytest.mark.skipif(
    not (ROOT / "packs" / "wk_proud_phantom.sspack").is_file(),
    reason="no produced packs in this tree — run scripts/build_pack.py --all"
)(test_a_published_pack_takes_over_its_track_card)


def test_the_whole_syllabus_button_only_exists_when_a_pack_does():
    """A button that answers 409 is worse than the 502 it replaced: at least
    the 502 looked like a failure."""
    ui = (ROOT / "frontend" / "index.html").read_text()
    assert ui.count("tr.published") >= 2, "the button is not gated"
    assert "all.zip'+trackQuery()" not in ui, \
        "the button still sends a combination the server no longer honours"


# --------------------------------------------------------------------------- #
# 4. One implementation of "zip up a pack"
# --------------------------------------------------------------------------- #
def test_the_pack_bundle_is_zipped_in_exactly_one_place():
    """It was zipped in the server for the pack route and again in `packref`
    for the track route — the twin-function shape this codebase has paid for
    twice."""
    app_src = (ROOT / "server" / "app.py").read_text()
    ref_src = (ROOT / "server" / "packref.py").read_text()
    assert "_packs.all_zip" in app_src, "the server does not use the helper"
    assert "all_zip" in ref_src, "the track route does not use the helper"
    # Neither caller may build the archive itself. The server legitimately zips
    # OTHER things (briefs, kneeboards), so the check is scoped to the pack
    # bundle rather than to the word ZipFile.
    assert "ZipFile" not in ref_src, "packref zips a pack itself"
    i = app_src.index("def _pack_all_zip")
    assert "ZipFile" not in app_src[i:i + 900], "the server zips a pack again"


def test_the_bundle_is_rebuilt_when_the_manifest_is_edited(server, tmp_path):
    """An author fixes the titles on the review screen; the download must carry
    the fix. A cache keyed on anything but the files would serve his old
    words."""
    from missiongen import packs
    server.post("/admin/packs",
                files={"file": ("hist_set.zip", _pack_bytes())},
                data={"pack_id": "", "label": ""}, follow_redirects=False)
    first = packs.all_zip("hist_set").read_bytes()
    man = json.loads(zipfile.ZipFile(io.BytesIO(first)).read(
        "hist_set/pack.json"))
    assert man["label"] != "Corrected"

    # NO SLEEP. The point is that an edit made in the same second as the last
    # download must still invalidate the bundle — a test that waits a second
    # first would pass against the bug it exists to catch.
    packs.update_manifest("hist_set", {"label": "Corrected"})
    again = packs.all_zip("hist_set").read_bytes()
    man2 = json.loads(zipfile.ZipFile(io.BytesIO(again)).read(
        "hist_set/pack.json"))
    assert man2["label"] == "Corrected"
