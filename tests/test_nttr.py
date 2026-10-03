"""NTTR corridors: every routed flight plan on the Nevada map goes to the
range the way Nellis flights do — through the published corridors.

Rob: "For NTTR there is the Sally corridor and other ways that flights make
their way to the training ... Any mission that includes waypoints should go
through the corridors and not just a couple waypoints."

WHAT THIS FILE HOLDS THE PRODUCT TO
-----------------------------------
  1. the data is whole: every corridor point and gate is a known fix, every
     plan names known corridors and gates, blocks are sane, sources exist;
  2. the sector picker puts the ranges where they are (north, west, far
     west, east) and the Nellis terminal area is 'local';
  3. a plan is departure > corridor > WP1 (the gate) > IP > TARGET > EXIT >
     recovery, with the crossing restrictions (FLEX at or below 4,000, STRYK
     at or above 9,500) honored and the Alamo block used only at FL190+;
  4. the far-west road stays out of R-4808N — the straight line from Indian
     Springs to Beatty does not;
  5. a built Nevada mission carries the corridor waypoints on the player's
     flight, the WP1/IP/TARGET names the timing card and coach hang on, the
     corridor block in the in-game brief, the lanes and gates on the F10 map,
     a flight-plan kneeboard page that fits, and the clock on its own page;
  6. other maps, a target inside the terminal area, and a non-Nellis home
     with nothing to join fall back to the generic three-point route.
"""
from __future__ import annotations

import random
import zipfile

import pytest

import dcs.lua as lua
from dcs import mapping
from dcs.mapping import LatLng
from dcs.terrain.nevada import Nevada

from missiongen import Recipe, generate, nttr, routing
from missiongen.builder import StarterBuilder


D = nttr.data()
TERRAIN = Nevada()


def _pt(lat, lon):
    return mapping.Point.from_latlng(LatLng(lat, lon), TERRAIN)


NELLIS = _pt(D["fixes"]["NELLIS"]["lat"], D["fixes"]["NELLIS"]["lon"])


# --------------------------------------------------------------------------- #
# 1. the data
# --------------------------------------------------------------------------- #
def test_every_corridor_point_and_gate_is_a_known_fix():
    fixes = D["fixes"]
    for c in D["corridors"]:
        for p in c["points"]:
            assert p in fixes, f"{c['id']} names unknown fix {p!r}"
        assert c["block_ft"][0] < c["block_ft"][1] and c["width_nm"] > 0
        assert c.get("src"), f"{c['id']} has no source"
        assert c["role"] in ("departure", "transit", "recovery")
    for g in D["gates"]:
        assert g in fixes, f"gate {g!r} is not a fix"
    for f in fixes.values():
        assert "short" in f and len(f["short"]) <= 8, f
        assert -117.5 < f["lon"] < -114.0 and 35.5 < f["lat"] < 38.5, f


def test_every_plan_names_known_corridors_and_gates():
    ids = {c["id"] for c in D["corridors"]}
    for sector, modes in D["plans"]["nellis"].items():
        if sector.startswith("_"):
            continue
        for mode in ("low", "high"):
            p = modes[mode]
            for cid in p["out"]:
                assert cid in ids, (sector, mode, cid)
            assert p["back"] in ids, (sector, mode)
            assert p["gate_in"] in D["fixes"] and p["gate_out"] in D["fixes"]
            assert nttr.corridor(p["out"][-1])["points"][-1] == p["gate_in"], \
                f"{sector}/{mode}: the outbound corridor must END on the entry gate"
            assert nttr.corridor(p["back"])["role"] == "recovery"


def test_the_published_facts_are_in_the_data():
    flex = D["fixes"]["FLEX"]
    assert flex["cap_ft"] == 4000, "cross FLEX at or below 4,000 (FLIP p14)"
    stryk = D["fixes"]["STRYK"]
    assert stryk["floor_ft"] == 9500, "cross STRYK at or above 9,500 (FLIP p30)"
    assert nttr.corridor("alamo")["block_ft"] == [19000, 21000], "Alamo Corridor FL190-FL210 (Add A Table 2.1 note 3)"
    assert nttr.corridor("sally")["block_ft"][0] >= 10000, "NATCF has no radar below 10,000 (11-250 2.8.1)"
    assert "ALAMO" in nttr.corridor("sally")["points"], "Sally runs up US-93 toward Alamo"
    assert abs(D["fixes"]["FYTTR"]["lat"] - 36.3573) < 0.001 and abs(D["fixes"]["STRYK"]["lon"] + 115.5117) < 0.001, "opennav fix positions"


def test_unknown_fix_or_corridor_is_an_error():
    with pytest.raises(KeyError):
        nttr.fix("POINT NOWHERE")
    with pytest.raises(KeyError):
        nttr.corridor("m1_motorway")


# --------------------------------------------------------------------------- #
# 2. sectors
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("lat,lon,want", [
    (36.24, -115.03, "local"),    # Nellis
    (36.30, -115.20, "local"),    # the pattern
    (36.35, -115.45, "local"),    # 21 nm out, west of the field: still the terminal area
    (37.30, -115.80, "north"),    # Range 75
    (37.62, -115.75, "north"),    # Rachel / 76
    (36.86, -116.79, "farwest"),  # Beatty
    (38.06, -117.09, "farwest"),  # Tonopah
    (36.75, -115.75, "west"),     # 61-65
    (36.81, -115.94, "west"),     # Frenchman Lake
    (37.79, -114.42, "east"),     # Lincoln County
    (37.35, -114.53, "east"),     # Elgin
])
def test_the_sector_picker_puts_the_ranges_where_they_are(lat, lon, want):
    assert nttr.sector_for(lat, lon) == want


def test_low_and_high_road_follow_the_eras_transit_altitude():
    assert nttr.mode_for("coldwar") == "low", "a Phantom transits below the Alamo shelf"
    assert nttr.mode_for("modern") == "high", "a Viper takes the Alamo Corridor at FL190+"
    assert nttr.mode_for("wwii") == "low"


# --------------------------------------------------------------------------- #
# 3. the plan
# --------------------------------------------------------------------------- #
def _plan(lat, lon, era="coldwar", seed=1, home=NELLIS):
    return nttr.plan_route(home, _pt(lat, lon), era, random.Random(seed), TERRAIN, "nevada")


def test_a_north_range_plan_is_flex_then_sally_then_the_gate():
    p = _plan(37.30, -115.80)
    names = [l["name"] for l in p["legs"]]
    assert names[:5] == ["FLEX", "APEX", "COYOTE", "ALAMO", "WP1"], names
    assert p["legs"][4]["fix"] == "STUDENT GAP", "WP1 is the range entry gate"
    assert names[5:7] == ["IP", "TARGET"]
    assert "EXIT" in names and names[-1] == "MINTT"
    assert p["corridors"] == ["flex", "sally", "mintt"]


def test_the_high_road_takes_the_alamo_corridor():
    p = _plan(37.30, -115.80, era="modern")
    names = [l["name"] for l in p["legs"]]
    assert "DOGBONE" in names and "HAYFORD" in names and "TEXAS LK" not in names[:3]
    assert p["mode"] == "high" and "alamo" in p["corridors"]
    hi = [l for l in p["legs"] if l["corridor"] == "alamo"]
    assert hi and all(19000 <= l["alt"] / 0.3048 <= 21000 for l in hi), "Alamo block FL190-210"


def test_the_crossing_restrictions_are_honoured():
    for era in ("coldwar", "modern"):
        p = _plan(36.86, -116.79, era=era)
        by = {l["name"]: l for l in p["legs"]}
        assert by["FLEX"]["alt"] / 0.3048 <= 4000, "cross FLEX at or below 4,000"
        assert by["STRYK"]["alt"] / 0.3048 >= 9500, "cross STRYK at or above 9,500"
        assert by["STRYK"]["alt"] / 0.3048 <= 12000


def test_the_far_west_road_goes_round_the_box():
    """The straight line Indian Springs -> Beatty crosses R-4808N. The west
    road (Mercury, Amargosa Valley) does not."""
    p = _plan(36.86, -116.79)
    names = [l["name"] for l in p["legs"]]
    assert names[:5] == ["FLEX", "ARC 15", "FYTTR", "INDIAN", "MERCURY"], names
    assert p["gate_in"] == "AMARGOSA VALLEY" and p["gate_out"] == "BEATTY"
    # every corridor leg stays out of the Box polygon
    box = [(36.683333, -115.934167), (36.683333, -116.246667), (36.766667, -116.4425),
           (36.85, -116.4425), (37.3, -116.4425), (37.3, -115.934167)]
    pts = [NELLIS] + [l["point"] for l in p["legs"] if l["corridor"] or l["name"] in ("WP1", "EXIT")]
    for a, b in zip(pts, pts[1:]):
        for k in range(0, 21):
            f = k / 20.0
            q = mapping.Point(a.x + (b.x - a.x) * f, a.y + (b.y - a.y) * f, TERRAIN).latlng()
            assert not _inside(q.lat, q.lng, box), "a corridor leg crosses the Box"
    # and the proof the rule is needed: the straight line does cross it
    ins = _pt(36.585, -115.670)
    bty = _pt(36.8006, -116.7481)
    crossed = any(_inside(*(lambda q: (q.lat, q.lng))(mapping.Point(ins.x + (bty.x - ins.x) * k / 20.0, ins.y + (bty.y - ins.y) * k / 20.0, TERRAIN).latlng()), box) for k in range(21))
    assert crossed, "Indian Springs direct Beatty should cut through R-4808N"


def _inside(lat, lon, poly):
    n, inside = len(poly), False
    j = n - 1
    for i in range(n):
        yi, xi = poly[i]
        yj, xj = poly[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def test_the_east_plan_uses_mormon_peak_and_acton():
    p = _plan(37.79, -114.42)
    names = [l["name"] for l in p["legs"]]
    assert names[:3] == ["FLEX", "MORMON", "WP1"] and names[-1] == "ACTON"
    assert p["legs"][2]["fix"] == "ELGIN"


def test_the_ip_is_not_the_direct_radial_from_the_gate():
    p = _plan(37.30, -115.80)
    gate = next(l for l in p["legs"] if l["name"] == "WP1")["point"]
    ip = next(l for l in p["legs"] if l["name"] == "IP")["point"]
    tgt = next(l for l in p["legs"] if l["name"] == "TARGET")["point"]
    a = routing._bearing(gate, tgt)
    b = routing._bearing(ip, tgt)
    assert 15 <= abs((a - b + 180) % 360 - 180) <= 45


def test_no_corridor_for_the_terminal_area_or_other_maps():
    assert _plan(36.30, -115.20) is None, "a pattern ride is not a range sortie"
    assert nttr.plan_route(NELLIS, _pt(37.30, -115.80), "coldwar", random.Random(1), TERRAIN, "caucasus") is None
    assert nttr.plan_route(None, _pt(37.30, -115.80), "coldwar", random.Random(1), TERRAIN, "nevada") is None


def test_from_creech_the_west_road_is_joined_at_indian_springs():
    creech = _pt(36.587, -115.673)
    p = _plan(36.86, -116.79, home=creech)
    names = [l["name"] for l in p["legs"]]
    assert names[0] == "INDIAN" and "FLEX" not in names, names
    assert names[-1] == "EXIT", "from another field the recovery is the exit gate, then home"
    assert p["from_nellis"] is False
    assert _plan(37.79, -114.42, home=creech) is None, "nothing to join eastbound from Creech: generic route"


def test_the_brief_names_the_corridors_the_gates_and_the_curated_fixes():
    p = _plan(37.30, -115.80)
    text = "\n".join(nttr.brief_lines(p))
    assert "SALLY CORRIDOR" in text and "RANGE ENTRY (WP1): STUDENT GAP" in text
    assert "NATCF" in text and "10,000" in text
    assert "Curated positions" in text and "APEX" in text
    assert "NELLISAFBI 11-250" in text
    issues = nttr.known_issue_lines(p)
    assert any("Sally Corridor" in k for k in issues)


# --------------------------------------------------------------------------- #
# 5. a built mission
# --------------------------------------------------------------------------- #
def _player_points(path):
    mis = lua.loads(zipfile.ZipFile(path).read("mission").decode())["mission"]
    for coal in mis["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for g in c.get("plane", {}).get("group", {}).values():
                units = [g["units"][i] for i in sorted(g["units"])]
                if any(u.get("skill") in ("Player", "Client") for u in units):
                    pts = g.get("route", {}).get("points", {})
                    return [pts[i] for i in sorted(pts)], mis
    return None, mis


@pytest.fixture(scope="module")
def farwest(tmp_path_factory):
    d = tmp_path_factory.mktemp("nttr")
    out = str(d / "fw.miz")
    rc = dict(map="nevada", era="coldwar", seed=3, aircraft="F_4E_45MC",
              bb_targets=True, bb_route=True, timing_anchor="tot",
              timing_at="07:30", timing_coach=True)
    res = generate(Recipe.from_dict(rc), out, brief_dir=str(d))
    # the same seed builds the same mission: a builder for the in-memory bits
    b = StarterBuilder(Recipe.from_dict(rc))
    b.build()
    b.res = res
    b.brief_md = open(res["brief_md"]).read()
    return b, out


def test_the_flight_carries_the_corridor_waypoints(farwest):
    b, out = farwest
    pts, _ = _player_points(out)
    names = [p.get("name") for p in pts]
    assert names[1:6] == ["FLEX", "ARC 15", "FYTTR", "INDIAN", "MERCURY"], names
    assert "WP1" in names and "IP" in names and "TARGET" in names and "EXIT" in names
    assert names[-2] == "GASS PK" and pts[-1].get("type") == "Land"
    assert len(names) >= 12, "not just a couple of waypoints"


def test_the_timing_card_and_coach_still_hang_on_wp1_ip_target(farwest):
    b, out = farwest
    tl = b.stats["timing"]
    assert tl["anchor_wp"] == "TARGET" and tl["anchor_clock"] == "07:30:00"
    tos = [r["to"] for r in tl["rows"]]
    assert "FLEX" in tos and "WP1" in tos and "GASS PK" in tos, "every corridor point is on the clock"
    assert b.stats.get("timing_coach_triggers"), "the coach is on"
    by = {p.name: p for p in b._player_group.points if p.name}
    for row in tl["rows"]:
        assert by[row["to"]].ETA == row["eta_s"]


def test_the_stats_and_brief_carry_the_corridors(farwest):
    b, out = farwest
    n = b.stats["nttr"]
    assert n["sector"] == "farwest" and n["corridors"] == ["fyttr", "westroad", "jaysn"]
    assert n["gate_in"] == "AMARGOSA VALLEY" and "AMARGOSA VALLEY" in n["approx"]
    z = zipfile.ZipFile(out)
    dic = lua.loads(z.read("l10n/DEFAULT/dictionary").decode())
    dic = dic.get("dictionary", dic)
    text = "\n".join(v for v in dic.values() if isinstance(v, str))
    assert "NTTR CORRIDORS" in text and "THE WEST ROAD" in text and "JAYSN" in text
    assert "Sally Corridor exists" in text, "the known-issues page says the AI controller does not know the corridors"


def test_the_lanes_and_gates_are_on_the_f10_map(farwest):
    b, out = farwest
    _, mis = _player_points(out)
    texts = []
    for L in mis.get("drawings", {}).get("layers", {}).values():
        for o in (L.get("objects") or {}).values():
            if o.get("text"):
                texts.append(o["text"])
    joined = "\n".join(texts)
    assert "Sally Corridor" in joined and "GATE STUDENT GAP" in joined
    assert "The west road" in joined and "GATE AMARGOSA VALLEY~" in joined, "a curated gate is marked ~"


def test_the_kneeboard_has_a_flight_plan_page_and_a_clock_page(farwest):
    b, out = farwest
    z = zipfile.ZipFile(out)
    pages = [n for n in z.namelist() if n.startswith("KNEEBOARD/")]
    assert len(pages) == 7, pages            # 3 reference + stores + route + timing + chart
    from missiongen import kneeboard as _kb
    rows = b.stats["route_legs"]
    img = _kb.page_route(rows, "x", "Nellis", timing=None, timed_elsewhere=True)
    assert img.size == (_kb.W, _kb.H)
    img2 = _kb.page_timing(b.stats["timing"], "x", "Nellis")
    assert img2.size == (_kb.W, _kb.H)


def test_the_pdf_brief_has_the_corridor_section(farwest):
    b, out = farwest
    md = b.brief_md
    assert "## NTTR corridors" in md and "AMARGOSA VALLEY" in md
    assert "The west road (US-95)" in md and "STRYK" in md
    assert b.res["brief_pdf"].endswith(".pdf") and open(b.res["brief_pdf"], "rb").read(4) == b"%PDF"
    # the chart is page 5 — after the airfield guide (page 4 since v1.107.0)
    from pypdf import PdfReader
    assert len(PdfReader(b.res["brief_pdf"]).pages) == 5


# --------------------------------------------------------------------------- #
# 6. the fallbacks
# --------------------------------------------------------------------------- #
def test_other_maps_keep_the_three_point_route(tmp_path):
    out = str(tmp_path / "c.miz")
    res = generate(Recipe.from_dict(dict(map="caucasus", era="modern", seed=5,
                                         bb_targets=True, bb_route=True)), out)
    pts, _ = _player_points(out)
    assert [p.get("name") for p in pts][1:4] == ["WP1", "IP", "TARGET"]
    assert "nttr" not in res["stats"]


def test_a_short_nevada_plan_keeps_one_kneeboard_page(tmp_path):
    from missiongen import kneeboard as _kb
    rows = routing.leg_card(NELLIS, routing.route_for(NELLIS, _pt(36.6, -115.3), "coldwar", random.Random(1), TERRAIN), "Nellis")
    assert len(rows) == 3
    img = _kb.page_route(rows, "x", "Nellis", timing=None)
    assert img.size == (_kb.W, _kb.H)


# --------------------------------------------------------------------------- #
# 7. the chart
# --------------------------------------------------------------------------- #
def test_the_chart_carries_the_legal_polygons_and_the_curated_flags():
    ch = D["chart"]
    by = {a["id"]: a for a in ch["areas"]}
    assert len(by["R-4807A"]["poly"]) == 27 and not by["R-4807A"].get("approx"), "60 FR 20635 description, 27 vertices"
    assert len(by["R-4808N"]["poly"]) == 14 and not by["R-4808N"].get("approx")
    assert by["R-4808N"]["poly"][0] == [36.68333, -115.93417]
    for a in ch["areas"]:
        if a["id"] not in ("R-4807A", "R-4808N"):
            assert a.get("approx") is True, f"{a['id']} is a curated outline and must say so"
        assert a["kind"] in ("restricted", "restricted_box", "moa", "alert") and a.get("src") and a.get("label_at")
    assert {r["name"] for r in ch["roads"]} == {"I-15", "US-93", "US-95", "SR-375"}
    for c in D["corridors"]:
        assert "label_seg" in c and "label_off" in c


def test_the_chart_renders_deterministically_at_every_size():
    from missiongen import nttr_chart as _nc
    a = _nc.render_panel(600, 500)
    b = _nc.render_panel(600, 500)
    assert a.size == (600, 500) and a.tobytes() == b.tobytes()
    page = _nc.render_page(800, 550)
    assert page.size == (800, 550)
    svg = _nc.render_svg(800, 550)
    assert svg.startswith("<svg") and "Sally Corridor" in svg and "NELLIS TERMINAL AREA" in svg
    assert svg == _nc.render_svg(800, 550), "the SVG is deterministic too"
    term = _nc.render_terminal(400, 260)
    assert term.size == (400, 260)
    # anti-aliased: a diagonal lane edge has intermediate tones, not just two colors
    assert len(a.getcolors(1 << 20)) > 200, "the PNG is supersampled, not aliased"
    p = _plan(36.86, -116.79)
    hot = _nc.render_panel(600, 500, plan=p)
    assert hot.tobytes() != a.tobytes(), "the flown plan is drawn on top"
    # the hot lane color appears only when a plan is drawn
    hot_cols = {c for _, c in hot.getcolors(1 << 20)}
    cold_cols = {c for _, c in a.getcolors(1 << 20)}
    assert (159, 18, 57) in hot_cols and (159, 18, 57) not in cold_cols, "the route line is red"
    assert (250, 214, 224) in hot_cols and (250, 214, 224) not in cold_cols, "the flown LANES are red-filled"
    leg = _nc.legend_lines(p)
    assert leg[0].startswith("RED = this mission") and "60 FR 20635" in " ".join(leg)


def test_the_chart_page_is_in_the_kneeboard_and_the_site(farwest):
    b, out = farwest
    z = zipfile.ZipFile(out)
    from PIL import Image
    import io
    last = sorted(n for n in z.namelist() if n.startswith("KNEEBOARD/"))[-1]
    img = Image.open(io.BytesIO(z.read(last)))
    assert img.size == (1024, 1366)
    from fastapi.testclient import TestClient
    from server.app import app
    r = TestClient(app).get("/api/nttr/chart.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png" and r.content[:4] == b"\x89PNG"
    r = TestClient(app).get("/api/nttr/chart.svg")
    assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml") and r.text.startswith("<svg")


def test_the_docs_chart_is_the_renderers_output():
    """docs/img/nttr_corridors.png is what scripts/build_nttr_chart.py writes
    from the current data — the artifact gate (test_docs_fresh) holds the
    stamp; this holds the bytes."""
    from missiongen import nttr_chart as _nc
    import io
    from pathlib import Path
    buf = io.BytesIO()
    _nc.render_page(1600, 1000).save(buf, format="PNG", optimize=True)
    on_disk = Path("docs/img/nttr_corridors.png").read_bytes()
    assert on_disk == buf.getvalue(), "run scripts/build_nttr_chart.py"
    assert Path("docs/img/nttr_corridors.svg").read_text() == _nc.render_svg(1600, 1000)
