"""The Training Pipeline: courses laid over the shelf, the kit, the door.

WHAT THIS FILE HOLDS THE PRODUCT TO
-----------------------------------
  1. every unit in every course resolves against the shelf — an unknown
     card, track, ride range, reading or aircraft is a build error;
  2. the F-4E course has the three schools in order, the history chapter
     in ground school (School 1), a check ride, and its planned units are SHOWN with a
     reason rather than hidden;
  3. the API serves it, refuses what it should (a path in a reading name,
     an unknown course), and the kit zips a program PDF, a gradesheet CSV
     with one row per ride, and the readings;
  4. the site has the fourth door — tab, entry card, section, renderer —
     and the pipeline opens cards with the course's own jet only where the
     card offers it;
  5. the readings say what they must: the T-45 is a mod, progress stays in
     the browser, the standard is the brief.
"""
from __future__ import annotations
from ui_source import ui_source, server_source

import csv
import io
import json
import re
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from missiongen import courses, course_kit, tracks
from missiongen.resolver import load_json

ROOT = Path(__file__).resolve().parent.parent
INDEX = ui_source()


@pytest.fixture(scope="module")
def client():
    import server.app as app_mod
    return TestClient(app_mod.app)


@pytest.fixture(scope="module")
def f4e():
    return courses.resolve("f4e_pipeline")


# --------------------------------------------------------------------------- #
# 1. every course resolves
# --------------------------------------------------------------------------- #
def test_every_course_resolves_against_the_shelf():
    ids = list(courses.all_courses())
    assert ids, "no courses"
    for cid in ids:
        c = courses.resolve(cid)
        assert c["counts"]["units"] > 0
        for s in c["schools"]:
            for p in s["phases"]:
                for u in p["units"]:
                    assert u["kind"] in courses.KINDS
                    assert u["status"] in ("ready", "planned")
                    assert u["uid"].startswith(f"{s['id']}.{p['id']}.")


def test_a_course_cannot_name_what_the_shelf_lacks(monkeypatch):
    bad = json.loads(json.dumps(courses.get("f4e_pipeline")))
    bad["schools"][0]["phases"][0]["units"].append(
        {"kind": "card", "id": "ghost", "key": "no_such_card"})
    monkeypatch.setattr(courses, "get", lambda cid: bad)
    with pytest.raises(ValueError, match="unknown card"):
        courses.resolve("f4e_pipeline")


def test_a_course_cannot_prefer_a_jet_the_card_does_not_offer(monkeypatch):
    bad = json.loads(json.dumps(courses.get("f4e_pipeline")))
    bad["schools"][0]["phases"][1]["units"][0]["aircraft"] = "Su_25T"
    monkeypatch.setattr(courses, "get", lambda cid: bad)
    with pytest.raises(ValueError, match="cannot be flown"):
        courses.resolve("f4e_pipeline")


def test_a_ride_range_must_exist_and_a_reading_must_be_on_disk(monkeypatch):
    bad = json.loads(json.dumps(courses.get("f4e_pipeline")))
    bad["schools"][1]["phases"][3]["units"][0]["from"] = 40
    monkeypatch.setattr(courses, "get", lambda cid: bad)
    with pytest.raises(ValueError, match="no rides"):
        courses.resolve("f4e_pipeline")
    bad2 = json.loads(json.dumps(courses.get("f4e_pipeline")))
    bad2["schools"][0]["phases"][0]["units"][0]["doc"] = "not_written"
    monkeypatch.setattr(courses, "get", lambda cid: bad2)
    with pytest.raises(ValueError, match="missing reading"):
        courses.resolve("f4e_pipeline")


def test_unit_ids_are_unique_within_a_course(monkeypatch):
    bad = json.loads(json.dumps(courses.get("f4e_pipeline")))
    u = bad["schools"][0]["phases"][0]["units"]
    u.append(dict(u[0]))
    monkeypatch.setattr(courses, "get", lambda cid: bad)
    with pytest.raises(ValueError, match="used twice"):
        courses.resolve("f4e_pipeline")


def test_reading_names_are_bare_names_never_paths():
    for bad in ("../README", "a/b", "..", "", "x\\y"):
        assert courses.reading_path(bad) is None, bad
    # A traversal that would land on a file that EXISTS: the roadmap.
    assert (ROOT / "docs" / "ROADMAP.md").is_file()
    assert courses.reading_path("../../../docs/ROADMAP") is None
    # ...and the absolute-path form of the same file, which has no ".." in it
    assert courses.reading_path(str(ROOT / "docs" / "ROADMAP")) is None
    assert courses.reading_path("f4e_history") is not None


# --------------------------------------------------------------------------- #
# 2. the F-4E course
# --------------------------------------------------------------------------- #
def test_the_f4e_course_is_three_schools_in_pipeline_order(f4e):
    assert [s["id"] for s in f4e["schools"]] == ["upt", "frs", "mqt"]
    assert [s["n"] for s in f4e["schools"]] == [1, 2, 3]
    assert f4e["schools"][0]["module_agnostic"] is True
    assert f4e["schools"][1]["requires_school"] == "upt"
    assert f4e["schools"][2]["requires_school"] == "frs"
    assert f4e["aircraft"] == "F_4E_45MC" and f4e["module"] == "F-4E"


def test_history_is_read_in_ground_school_not_the_frs(f4e):
    # Rob: "History goes in the Learn It section" — the chapter is ground
    # school, School 1; the FRS starts in the jet.
    ground = f4e["schools"][0]["phases"][0]
    docs = [u["doc"] for u in ground["units"] if u["kind"] == "reading"]
    assert "f4e_history" in docs, "the history chapter is in ground school"
    frs = f4e["schools"][1]
    assert all(u["kind"] != "reading" for p in frs["phases"] for u in p["units"]), \
        "the FRS has no readings — you fly the jet there"
    assert frs["phases"][0]["units"][0]["kind"] == "card", "the FRS opens in the cockpit"


def test_the_frs_ends_with_a_check_ride(f4e):
    frs = f4e["schools"][1]
    last = frs["phases"][-1]["units"][-1]
    assert last["kind"] == "card" and last["check"] is True
    assert last["key"] == "pp_8_bnai", "the check ride is the UNCOACHED B'NAI"
    assert not last["graded"]


def test_the_upt_school_flies_existing_tracks_in_the_phantom(f4e):
    upt = f4e["schools"][0]
    by = {u["id"]: u for p in upt["phases"] for u in p["units"]}
    assert by["timing"]["track"] == "timing_f4e" and by["timing"]["rides"] == 4
    assert by["timing_check"]["key"] == "timing_5_check" and by["timing_check"]["check"]
    assert by["aar"]["track"] == "aar_boom" and by["aar"]["aircraft"] == "F_4E_45MC"
    assert by["aar"]["era"] == "coldwar" and by["aar"]["rides"] == 8
    assert by["aar_check"]["ride_keys"] == ["aar_boom_8_qual"] and by["aar_check"]["check"]
    assert by["aar_ops"]["rides"] == 2
    for k in ("form_route", "form_close", "form_energy", "form_rejoin", "form_takeoff",
              "form_precheck", "form_check"):
        assert by[k]["aircraft"] == "F_4E_45MC" and by[k]["graded"]
    assert by["form_check"]["check"] and not by["form_precheck"]["check"]


def test_the_tactical_checkout_is_rides_four_to_eleven(f4e):
    frs = f4e["schools"][1]
    wkc = next(u for p in frs["phases"] for u in p["units"] if u["id"] == "wkc")
    assert wkc["ride_n"] == [4, 11] and wkc["rides"] == 8
    assert wkc["ride_keys"][0] == "wk_4_lineabreast" and wkc["ride_keys"][-1] == "wk_11_bfm"
    pp = next(u for p in frs["phases"] for u in p["units"] if u["id"] == "pp")
    assert "pp_8_bnai" not in pp["ride_keys"], "the check ride is not also a weapons ride"
    assert "pp_8_bnai_coach" in pp["ride_keys"]


def test_planned_units_are_shown_with_a_reason_not_hidden(f4e):
    planned = [u for s in f4e["schools"] for p in s["phases"] for u in p["units"]
               if u["status"] == "planned"]
    assert len(planned) == f4e["counts"]["planned"] >= 3
    for u in planned:
        assert u["kind"] == "planned" and len(u["why"]) > 30, u
    assert f4e["counts"]["ready"] + f4e["counts"]["planned"] == f4e["counts"]["units"]


def test_the_counts_add_up(f4e):
    units = [u for s in f4e["schools"] for p in s["phases"] for u in p["units"]]
    assert f4e["counts"]["rides"] == sum(u.get("rides", 0) for u in units)
    # a reading or a planned unit is not a ride
    assert all(u.get("rides", 0) == 0 for u in units if u["kind"] in ("reading", "planned"))
    assert all(u["rides"] == 1 for u in units if u["kind"] == "card")
    assert f4e["counts"]["readings"] == 3
    assert f4e["counts"]["rides"] >= 40


def test_every_ride_the_course_names_is_a_real_template(f4e):
    tpls = load_json("mission_templates")
    for r in courses.gradesheet_rows(f4e):
        if r["kind"] == "ride":
            assert r["ride"] in tpls, r


# --------------------------------------------------------------------------- #
# 3. the API and the kit
# --------------------------------------------------------------------------- #
def test_the_api_lists_and_serves_the_course(client):
    r = client.get("/api/courses")
    assert r.status_code == 200 and "f4e_pipeline" in r.json()
    s = r.json()["f4e_pipeline"]
    assert s["counts"]["units"] > 0 and len(s["schools"]) == 3
    r = client.get("/api/course/f4e_pipeline")
    assert r.status_code == 200 and r.json()["schools"][1]["id"] == "frs"
    assert client.get("/api/course/no_such").status_code == 404
    assert "courses" in client.get("/api/options").json()


def test_the_api_serves_readings_and_refuses_paths(client):
    r = client.get("/api/course/f4e_pipeline/reading/f4e_history")
    assert r.status_code == 200
    j = r.json()
    assert j["title"].startswith("The Phantom") and "<h3>" in j["html"] and "# The Phantom" in j["md"]
    assert "<i>" in j["html"], "italics are rendered"
    assert "<script" not in j["html"]
    assert client.get("/api/course/f4e_pipeline/reading/..%2F..%2FREADME").status_code == 404
    assert client.get("/api/course/f4e_pipeline/reading/README").status_code == 404
    assert client.get("/api/course/f4e_pipeline/reading/not_a_reading").status_code == 404
    # A chapter on disk that no course lists is not served either — a draft
    # is not a publication.
    draft = courses.DOCS / "zz_draft_for_test.md"
    draft.write_text("# draft\n\nnot published\n")
    try:
        assert courses.reading_path("zz_draft_for_test") is not None
        assert client.get("/api/course/f4e_pipeline/reading/zz_draft_for_test").status_code == 404
    finally:
        draft.unlink()


def test_the_kit_carries_programme_gradesheet_and_readings_but_no_missions(client, f4e):
    r = client.get("/api/course/f4e_pipeline/kit.zip")
    assert r.status_code == 200
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    assert "Program.pdf" in names and "Gradesheet.csv" in names and "README.txt" in names
    assert "readings/f4e_history.md" in names and "readings/aviation_basics.md" in names
    assert not [n for n in names if n.endswith(".miz")]
    assert z.read("Program.pdf")[:5] == b"%PDF-"
    rows = list(csv.DictReader(io.StringIO(z.read("Gradesheet.csv").decode("utf-8"))))
    rides = [x for x in rows if x["kind"] == "ride"]
    assert len(rides) == f4e["counts"]["rides"]
    assert sum(1 for x in rides if x["check_ride"] == "yes") == 4, "one check per phase that has one"
    assert {"sim_grade_UFGE", "ip_grade_UFGE", "check_result_Q_Qminus_U", "instructor", "date"} <= set(rows[0])
    assert any(x["ride_key"] == "wk_4_lineabreast" for x in rides)


def test_the_program_pdf_prints_the_syllabus_and_the_readings(tmp_path, f4e):
    from pypdf import PdfReader
    pdf = course_kit.program_pdf(f4e, "0.0.0", tmp_path / "p.pdf")
    text = "\n".join(pg.extract_text() for pg in PdfReader(str(pdf)).pages)
    for s in f4e["schools"]:
        assert s["label"] in text
    assert "CHECK RIDE" in text and "PLANNED" in text and "Gradesheet" in text
    assert "U — out of parameters" in text and "Q- — qualified with discrepancies" in text
    assert "An interceptor the Navy did not order" in text, "the history chapter is in the kit"
    assert "the six numbers you fly by" in text
    assert "carries no mission files" in text


# --------------------------------------------------------------------------- #
# 4. the door
# --------------------------------------------------------------------------- #
def test_the_site_has_the_fourth_door():
    assert 'data-v="pipeline"' in INDEX and ">Train<" in INDEX
    assert 'onclick="showView(\'pipeline\')"' in INDEX
    assert '<section id="pipeline">' in INDEX
    assert "function renderPipeline" in INDEX and "function openReading" in INDEX
    assert "pipeline:'Training Pipeline'" in INDEX
    assert 'class="epaths four"' in INDEX
    assert "Train in the Pipeline" in INDEX


def test_progress_is_local_and_the_kit_is_a_download():
    assert "localStorage.setItem(pKey(cid)" in INDEX
    assert "/kit.zip" in INDEX
    assert "this browser only" in INDEX
    # no course progress ever leaves the browser
    assert not re.search(r"fetch\([^)]*progress", INDEX)


def test_the_pipeline_opens_cards_with_the_courses_jet_only_where_offered():
    assert "function openDetail(k, pref)" in INDEX
    assert "acChoices(t, libState.era).includes(pref.aircraft)" in INDEX
    assert "function openTrack(id, pref)" in INDEX
    assert "pk[era][pref.aircraft]" in INDEX


def test_a_fixed_track_has_no_empty_series_wizard():
    """Found while building the door: the White Knights track panel drew
    three empty rows and 'undefined behind a undefined'."""
    assert "const fixed=!tr.configurable;" in INDEX
    assert "if(!(OPT.tracks[s.id]||{}).configurable) return '';" in INDEX


def test_the_guide_describes_the_door():
    md = (ROOT / "docs" / "USER_GUIDE.md").read_text()
    assert "## The four doors" in md and "Training Pipeline" in md and "squadron kit" in md
    pdf = _guide_text()
    assert "The four doors" in pdf and "Training Pipeline" in pdf


def _guide_text():
    reader = pytest.importorskip("pypdf").PdfReader(ROOT / "docs" / "DCS_Mission_Starter_Guide.pdf")
    return re.sub(r"\s+", " ", " ".join(page.extract_text() for page in reader.pages))


# --------------------------------------------------------------------------- #
# 5. the readings say what they must
# --------------------------------------------------------------------------- #
def test_the_readings_are_honest_about_what_they_are():
    howto = courses.reading_text("pipeline_howto")
    assert "lives in your browser and nowhere else" in howto
    assert "not built yet" in howto and "The brief on each ride is the standard" in howto
    hist = courses.reading_text("f4e_history")
    assert "## Sources" in hist and "Osprey" in hist and "Heatblur" in hist
    assert "27 May 1958" in hist and "30 June 1967" in hist and "5,195" in hist
    assert "fifteen units" in hist, "the rudder rule the checkout teaches"
    basics = courses.reading_text("aviation_basics")
    assert "Groundspeed" in basics and "angle of attack" in basics.lower()
    assert "true headings" in basics.lower()


def test_the_tagline_is_one_line_everywhere():
    """Rob: "Learn it, fly it, fight it" — the door, the course, the reading,
    the guide. One line, spelled one way."""
    tag = "Learn it, fly it, fight it"
    assert INDEX.count(tag) >= 2
    assert courses.get("f4e_pipeline")["tagline"] == tag + "."
    assert tag in courses.resolve("f4e_pipeline")["premise"]
    assert tag in courses.reading_text("pipeline_howto")
    assert tag in (ROOT / "docs" / "USER_GUIDE.md").read_text()
    assert tag in _guide_text()
