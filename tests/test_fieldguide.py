"""The airfield guide — the Doc folder's first new page — and the elevation
bug it uncovered.

Every number on the guide is read from the terrain or from a cited table,
and these tests check it against the SAME terrain object DCS will use, so a
printed ATC frequency, runway or elevation cannot be one the field does not
have. The elevation half pins the defect: pydcs's ParkingSlot.height is a
stand's clearance height, not the field's elevation, and pattern.py used it
to place airborne traffic — fifty feet wrong on the Caucasus, 1,800 ft
underground at Nellis.
"""
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import dcs.lua as lua                                        # noqa: E402
from dcs.terrain import caucasus, nevada                     # noqa: E402
from missiongen import fieldguide as fg, generate, pattern   # noqa: E402
from missiongen.recipe import Recipe                         # noqa: E402
from missiongen.resolver import load_json                    # noqa: E402

NEV = nevada.Nevada()
CAU = caucasus.Caucasus()
NELLIS = next(a for a in NEV.airports.values() if a.name == "Nellis")
KUTAISI = next(a for a in CAU.airports.values() if a.name == "Kutaisi")


# --- the data is the terrain's --------------------------------------------

def test_atc_frequencies_are_the_fields_own():
    a = fg.atc(NELLIS)
    assert a["uhf"] == pytest.approx(NELLIS.atc_radio.uhf_hz / 1e6)
    assert a["vhf"] == pytest.approx(NELLIS.atc_radio.vhf_high_hz / 1e6)
    assert fg.fmt_mhz(a["uhf"]) == "327.000"


def test_runways_carry_both_ends_with_headings():
    r = fg.row(NELLIS)
    names = [rw["name"] for rw in r["runways"]]
    assert "03L-21R" in names and "03R-21L" in names
    ends = {n: h for rw in r["runways"] for n, h in rw["ends"]}
    assert ends["03L"] == 30 and ends["21R"] == 210
    assert fg.fmt_rwy(r, first_only=True) == "03L/21R"
    assert "03R/21L" in fg.fmt_rwy(r)
    assert "03L (030) / 21R (210)" in fg.fmt_rwy(r, with_heading=True)


def test_divert_order_is_home_first_then_by_range():
    own = [a for a in NEV.airports.values() if a.name in ("Nellis", "Creech", "Groom Lake", "McCarran International")]
    t = fg.rows(own, NELLIS, map_key="nevada")
    names = [r["name"] for r in t["own"]]
    assert names[0] == "Nellis" and t["own"][0]["home"]
    ranges = [r["range_nm"] for r in t["own"][1:]]
    assert ranges == sorted(ranges) and ranges[0] > 5
    assert all(0 <= r["bearing"] < 360 for r in t["own"][1:])


# --- elevation: a table, never the stand ----------------------------------

def test_stand_height_is_not_elevation():
    """The defect, stated as a fact about the data: every stand at Nellis
    reports a height a few metres tall, and the field is 570 m up."""
    hs = {p.height for p in NELLIS.parking_slots}
    assert max(hs) < 30, hs
    assert fg.elevation_ft(NELLIS, "nevada") == 1868
    assert fg.elevation_ft(KUTAISI, "caucasus") == 148


def test_every_field_on_a_covered_map_has_an_elevation():
    """A map in the table covers ALL of its fields: a missing field is a
    pattern-landing silently skipped for a typo."""
    table = load_json("airfield_elevations")
    for key, terr in (("nevada", NEV), ("caucasus", CAU)):
        missing = [a.name for a in terr.airports.values() if a.name not in table[key]["fields"]]
        assert not missing, f"{key}: {missing}"
        for v in table[key]["fields"].values():
            assert isinstance(v, int) and -100 < v < 15000


def test_unknown_field_prints_a_dash_not_a_number():
    class Fake:
        name = "Nowhere Strip"; parking_slots = NELLIS.parking_slots; runways = []
        atc_radio = None; position = NELLIS.position
    assert fg.elevation_ft(Fake(), "nevada") is None
    assert fg.row(Fake())["elev_ft"] is None


def _rc(**kw):
    return dict(map="nevada", era="modern", aircraft="F_16C_50", home_airbase="Nellis",
                seed=4, bb_pattern=True, bb_targets=False, bb_sams=False, bb_tanker=False,
                bb_awacs=False, bb_ambient=False, **kw)


def _build(tmp, **kw):
    out = tmp / "p.miz"
    res = generate(Recipe.from_dict(_rc(**kw)), str(out), brief_dir=str(tmp))
    raw = lua.loads(zipfile.ZipFile(out).read("mission").decode())["mission"]
    return raw, res


def _pattern_landers(raw):
    return [g for co in raw["coalition"].values() for c in co["country"].values()
            for g in c.get("plane", {}).get("group", {}).values()
            if str(g.get("name", "")).startswith("Pattern ")
            and g["route"]["points"][1]["type"] == "Turning Point"]


def test_pattern_landers_at_nellis_are_above_the_field(tmp_path):
    raw, res = _build(tmp_path, pattern_mode="landing", pattern_count=3)
    landers = _pattern_landers(raw)
    assert len(landers) == 3
    field_m = 1868 / fg.FT
    for g in landers:
        alt = g["route"]["points"][1]["alt"]
        assert alt > field_m + pattern.MIN_APPROACH_AGL - 1, \
            f"{g['name']} spawns at {alt:.0f} m MSL; Nellis is {field_m:.0f} m"


def test_no_elevation_on_record_means_no_airborne_spawn(tmp_path, monkeypatch):
    """Rather than guess, skip the landers and say so; departures still go."""
    monkeypatch.setattr(fg, "_ELEV", {"nevada": {"fields": {}}})
    raw, res = _build(tmp_path, pattern_mode="both", pattern_count=4)
    assert not _pattern_landers(raw)
    assert any("no field elevation on record for Nellis" in w for w in res["warnings"])
    deps = [g for co in raw["coalition"].values() for c in co["country"].values()
            for g in c.get("plane", {}).get("group", {}).values()
            if str(g.get("name", "")).startswith("Pattern ")]
    assert deps, "departures start on the ramp and need no elevation"


# --- the page, the card and the markdown say the same thing ----------------

def test_brief_and_markdown_carry_the_guide(tmp_path):
    raw, res = _build(tmp_path, pattern_mode="takeoff", pattern_count=1)
    md = Path(res["brief_md"]).read_text()
    assert "## Airfield guide" in md
    assert "| ★ Nellis | 327.000 | 132.550 | 03L/21R  03R/21L | 1868 | 247 |" in md
    assert "NORDO: squawk 7600, return to Nellis, overhead for RWY 03L" in md
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(res["brief_pdf"])
    assert len(pdf) == 5, "airfield guide remains page 4; historical context appends page 5"
    # The brief is drawn with PIL (no text layer), so the page is checked as a
    # picture: it must be a real page — table rows of ink, not the blank
    # paper a skipped renderer would leave — and differ from page 3.
    p3 = pdf[2].render(scale=0.5).to_pil().convert("L")
    p4 = pdf[3].render(scale=0.5).to_pil().convert("L")
    ink = sum(1 for v in p4.getdata() if v < 128) / (p4.width * p4.height)
    assert 0.02 < ink < 0.5, f"page 4 ink fraction {ink:.3f}"
    assert list(p3.getdata()) != list(p4.getdata())
    assert "TACAN/ILS are not printed" in md, "the gap is stated, not hidden"


def test_from_the_boat_the_guide_has_no_from_home_column(tmp_path):
    """Carrier home: no bearing to print, and the brief must still render —
    the first cut formatted None and the whole brief fell over."""
    out = tmp_path / "c.miz"
    res = generate(Recipe.from_dict(dict(map="caucasus", era="modern", aircraft="FA_18C_hornet",
                                         bb_carrier=True, home_airbase="CARRIER",
                                         bb_ambient=False, seed=3)), str(out), brief_dir=str(tmp_path))
    assert "brief_md" in res, res["warnings"]
    md = Path(res["brief_md"]).read_text()
    assert "## Airfield guide" in md and "NORDO: recover at the ship" in md
    assert "| ★" not in md.split("## Airfield guide")[1].split("NORDO")[0], "no field is home"
