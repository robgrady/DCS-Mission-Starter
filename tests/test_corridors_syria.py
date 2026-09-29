"""Levant corridors: the Authentic standard map detail on the Syria map.

Rob (v1.101.0): "let's refer to this map detail as the authentic standard map
detail. Let's now do the research and create it for the Syria map."

WHAT THIS FILE HOLDS THE PRODUCT TO
-----------------------------------
  1. the Syria data is whole under the same schema as Nevada: every corridor
     point and gate a known fix, every cluster plan naming known corridors,
     the published facts (J14, W74, L200, the Al-Tanf 55 km zone) present;
  2. the home decides the cluster: the Galilee fields are Israel, Akrotiri
     is Cyprus, Incirlik is Turkey, Azraq is Jordan; a field in no cluster
     (Damascus) and a target in no sector get the generic route; the modern
     era's 'high' road falls back to the only road the data has;
  3. a built mission from each of Ramat David, Akrotiri and Incirlik carries
     the corridor waypoints, WP1 at the plan's gate, the Levant section in
     the brief with the map's own wording, the lanes and gates on the F10
     map, and the chart page in the kneeboard;
  4. the chart is the standard detail: sea fill inside the bounds with the
     land back on top, four terminal panels in a 2x2 grid, the overview
     decluttered of the fixes a panel draws, per-panel label placement, and
     the same bytes on every render — the site serves it at
     /api/corridors/syria/chart.* and docs/img/syria_corridors.* is the
     renderer's output.
"""
from __future__ import annotations

import io
import random
import zipfile
from pathlib import Path

import pytest

from dcs import mapping
from dcs.mapping import LatLng
from dcs.terrain.syria import Syria

from missiongen import Recipe, generate, corridors, corridor_chart as cc
from test_nttr import _player_points


D = corridors.data("syria")
TERRAIN = Syria()


def _pt(lat, lon):
    return mapping.Point.from_latlng(LatLng(lat, lon), TERRAIN)


def _home(name):
    f = D["fixes"][name]
    return _pt(f["lat"], f["lon"])


def _plan(home, target_lat, target_lon, era="coldwar"):
    return corridors.plan_route(_home(home), _pt(target_lat, target_lon), era,
                                random.Random(1), TERRAIN, "syria", home_name=home.title())


# --------------------------------------------------------------------------- #
# 1. the data
# --------------------------------------------------------------------------- #
def test_syria_is_a_corridor_map_and_nevada_still_is():
    assert corridors.maps()[:2] == ("nevada", "syria")
    assert corridors.has("syria") and corridors.has("nevada") and not corridors.has("caucasus")


def test_every_corridor_point_gate_and_plan_names_known_fixes():
    fixes = D["fixes"]
    ids = {c["id"] for c in D["corridors"]}
    for c in D["corridors"]:
        assert c["role"] in ("departure", "transit", "recovery")
        for p in c["points"]:
            assert p in fixes, f"{c['id']} names unknown fix {p!r}"
        lo, hi = c["block_ft"]
        assert 0 <= lo < hi <= 45000 and 3 <= c["width_nm"] <= 12 and c["src"]
    for g in D["gates"]:
        assert g in fixes
    for cid, sectors in D["plans"].items():
        assert cid in D["clusters"]
        for sector, modes in sectors.items():
            for p in modes.values():
                assert set(p["out"]) <= ids and p["back"] in ids, (cid, sector)
                assert p["gate_in"] in D["gates"] and p["gate_out"] in fixes
    for pn in D["chart"]["panels"]:
        assert pn["cluster"] in D["clusters"]
        assert set(pn["lanes"]) <= ids
        for cid in pn.get("labels", {}):
            assert cid in ids
    for cid in D["chart"].get("labels", {}):
        assert cid in ids


def test_the_published_facts_are_in_the_data():
    names = {c["name"] for c in D["corridors"]}
    assert "J14 north - Rosh Pina" in names and "W74 east - the Northern Watch road" in names
    assert any("L200" in n for n in names) and "The Bekaa road" in names
    dcz = next(a for a in D["chart"]["areas"] if a["id"] == "DCZ")
    assert "55 km" in dcz["alt"] and len(dcz["poly"]) >= 24
    assert D["fixes"]["AT TANF"]["kind"] == "gate" and not D["fixes"]["AT TANF"].get("approx")
    assert D["fixes"]["HERMON"].get("approx"), "a reported road on a summit is curated"
    assert D["text"]["chart_title"] == "LEVANT CORRIDORS"
    assert set(D["sectors"]["labels"]) >= {"lebanon", "damascus", "coast", "north", "east", "central"}


# --------------------------------------------------------------------------- #
# 2. home -> cluster, target -> sector
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("home,lat,lon,want", [
    ("Ramat David", 32.665, 35.179, ("israel", True)),
    ("Kiryat Shmona", 33.217, 35.597, ("israel", True)),
    ("Akrotiri", 34.590, 32.988, ("cyprus", True)),
    ("Incirlik", 37.002, 35.426, ("turkey", True)),
    ("Muwaffaq Salti", 31.826, 36.787, ("jordan", True)),
    ("Damascus", 33.411, 36.516, (None, False)),
    ("Palmyra", 34.557, 38.317, (None, False)),
])
def test_the_home_field_picks_the_cluster(home, lat, lon, want):
    assert corridors.cluster_for_home(home, lat, lon, "syria") == want


@pytest.mark.parametrize("lat,lon,want", [
    (33.90, 36.00, "lebanon"),       # the Bekaa
    (33.50, 36.30, "damascus"),      # Damascus
    (35.40, 35.95, "coast"),         # Khmeimim
    (36.20, 37.20, "north"),         # Aleppo
    (35.33, 40.15, "east"),          # Deir ez-Zor
    (34.52, 37.63, "central"),       # T-4 / Tiyas
    (32.66, 35.18, "local"),         # Ramat David: inside the cluster
    (35.15, 33.40, "none"),          # Nicosia
])
def test_the_sector_picker_puts_syria_where_it_is(lat, lon, want):
    assert corridors.sector_for(lat, lon, "syria", "israel") == want


def test_the_galilee_plan_goes_up_the_coast_and_over_the_bekaa():
    p = _plan("RAMAT DAVID", 34.52, 37.63)          # T-4
    assert p["cluster"] == "israel" and p["in_cluster"] and p["sector"] == "central"
    assert p["corridors"] == ["il_coast", "il_bekaa", "il_home_coast"]
    names = [l["name"] for l in p["legs"]]
    assert names[:4] == ["NAT", "ATLIT", "HAIFABLK", "R HANIKR"]
    assert names.index("WP1") < names.index("IP") < names.index("TARGET") < names.index("EXIT")
    assert p["legs"][names.index("WP1")]["fix"] == "RAS BAALBEK"
    assert names[-1] == "NAT2", "the recovery fix is renamed so the clock can find it"


def test_the_damascus_plan_goes_over_hermon_and_the_coast_plan_goes_to_sea():
    p = _plan("RAMAT DAVID", 33.50, 36.30)
    assert p["gate_in"] == "HERMON" and "il_golan" in p["corridors"]
    p = _plan("RAMAT DAVID", 35.40, 35.95)
    assert p["gate_in"] == "W TRIPOLI" and p["corridors"][1] == "il_sea"


def test_akrotiri_incirlik_and_azraq_have_their_own_roads():
    p = _plan("AKROTIRI", 35.40, 35.95)
    assert p["cluster"] == "cyprus" and p["gate_in"] == "NIKAS" and p["corridors"][0] == "cy_east"
    p = _plan("INCIRLIK", 36.20, 37.20)
    assert p["cluster"] == "turkey" and p["gate_in"] == "NISAP" and p["corridors"] == ["tr_kilis", "tr_home"]
    p = _plan("INCIRLIK", 35.33, 40.15)
    assert p["gate_in"] == "LESRI" and "tr_w74" in p["corridors"]
    p = _plan("MUWAFFAQ SALTI", 33.50, 36.30)
    assert p["cluster"] == "jordan" and p["gate_in"] == "BUSRA"
    p = _plan("MUWAFFAQ SALTI", 35.33, 40.15)
    assert p["gate_in"] == "AT TANF" and "jo_tanf" in p["corridors"]


def test_the_modern_high_road_falls_back_to_the_only_road_published():
    lo = _plan("RAMAT DAVID", 34.52, 37.63, era="coldwar")
    hi = _plan("RAMAT DAVID", 34.52, 37.63, era="modern")
    assert lo["mode"] == "low" and hi["mode"] == "high"
    assert lo["corridors"] == hi["corridors"], "one road; the era changes the altitude, not the road"


def test_no_cluster_or_no_sector_means_the_generic_route():
    assert corridors.plan_route(_home("DAM"), _pt(35.4, 35.95), "coldwar", random.Random(1), TERRAIN,
                                "syria", home_name="Damascus") is None
    assert _plan("RAMAT DAVID", 32.66, 35.18) is None, "a target in Israel has no sector"
    assert corridors.plan_route(_home("RAMAT DAVID"), _pt(34.52, 37.63), "coldwar", random.Random(1),
                                TERRAIN, "caucasus") is None


def test_the_brief_uses_the_maps_own_words():
    p = _plan("RAMAT DAVID", 34.52, 37.63)
    text = "\n".join(corridors.brief_lines(p))
    assert text.startswith("== LEVANT CORRIDORS - HOW YOU GET TO THE FIGHT ==")
    assert "Sector: CENTRAL, low road, from northern Israel" in text
    assert "ENTRY GATE (WP1): RAS BAALBEK" in text and "EXIT GATE: RAS BAALBEK" in text
    assert "THE BEKAA ROAD" in text and "PLUTO" in text
    assert "RANGE ENTRY" not in text, "that is Nevada's word"
    md = corridors.md_line(p)
    assert md.startswith("**The coast road north / The Bekaa road / Recovery down the coast** — central Syria")
    assert "nobody goes direct across the border" in md and "Bravo" not in md
    assert corridors.sector_label(p) == "central Syria - Homs, Hama and the desert fields"
    assert "HERMON" not in corridors.approx_fixes(p) and "RAS BAALBEK" in corridors.approx_fixes(p)
    assert any("PLUTO" in k for k in corridors.known_issue_lines(p))


def test_nevada_keeps_its_own_words():
    from missiongen import nttr
    from dcs.terrain.nevada import Nevada
    nv = Nevada()
    home = mapping.Point.from_latlng(LatLng(36.2362, -115.0342), nv)
    p = nttr.plan_route(home, mapping.Point.from_latlng(LatLng(37.30, -115.80), nv), "coldwar", random.Random(1), nv)
    text = "\n".join(nttr.brief_lines(p))
    assert "RANGE ENTRY (WP1): STUDENT GAP" in text and "RANGE EXIT:" in text
    assert corridors.md_line(p).endswith("nobody leaves the Bravo direct to the target.")
    assert corridors.sector_label(p) == "north ranges"


# --------------------------------------------------------------------------- #
# 3. built missions
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def galilee(tmp_path_factory):
    d = tmp_path_factory.mktemp("syr")
    out = str(d / "rd.miz")
    rc = dict(map="syria", era="modern", seed=7, home_airbase="Ramat David",
              bb_targets=True, bb_route=True, timing_anchor="tot", timing_at="07:30")
    res = generate(Recipe.from_dict(rc), out, brief_dir=str(d))
    return res, out


def test_the_galilee_flight_carries_the_sea_road(galilee):
    res, out = galilee
    n = res["stats"]["nttr"]
    assert n["map"] == "syria" and n["title"] == "Levant corridors"
    assert n["sector"] == "north" and n["corridors"] == ["il_coast", "il_sea", "il_home_coast"]
    pts, _ = _player_points(out)
    names = [p.get("name") for p in pts]
    assert names[1:8] == ["NAT", "ATLIT", "HAIFABLK", "R HANIKR", "OFFSIDON", "OFFBEIRU", "OFFTRIPO"]
    assert names[8:12] == ["WP1", "IP", "TARGET", "EXIT"]
    assert names[-2] == "NAT2" and pts[-1].get("type") == "Land"
    assert len(names) >= 14, "not just a couple of waypoints"
    assert n["md_line"].startswith("**The coast road north / The sea road - west of Tripoli / Recovery down the coast** — northern Syria")
    tl = res["stats"]["timing"]
    tos = [r["to"] for r in tl["rows"]]
    assert "OFFSIDON" in tos and "WP1" in tos and "NAT2" in tos, "every corridor point is on the clock"


def test_the_galilee_brief_f10_and_kneeboard_carry_the_levant(galilee):
    res, out = galilee
    md = Path(res["brief_md"]).read_text()
    assert "## Levant corridors" in md and "nobody goes direct across the border" in md
    assert "- THE SEA ROAD - WEST OF TRIPOLI" in md and "ENTRY GATE (WP1): W TRIPOLI" in md
    assert "## NTTR" not in md and "Bravo" not in md
    _, mis = _player_points(out)
    texts = [o["text"] for L in mis.get("drawings", {}).get("layers", {}).values()
             for o in (L.get("objects") or {}).values() if o.get("text")]
    joined = "\n".join(texts)
    assert "The sea road - west of Tripoli" in joined and "GATE W TRIPOLI~" in joined
    assert "GATE AT TANF" in joined and "GATE AT TANF~" not in joined, "a published gate is not marked curated"
    z = zipfile.ZipFile(out)
    pages = sorted(n for n in z.namelist() if n.startswith("KNEEBOARD/"))
    assert len(pages) == 7, pages
    from PIL import Image
    img = Image.open(io.BytesIO(z.read(pages[-1])))
    assert img.size == (1024, 1366)
    issues = res["stats"].get("known_issues", [])
    assert any("PLUTO" in k for k in issues) and any("curated placements" in k for k in issues)


@pytest.mark.parametrize("home,seed,era,gate,first", [
    ("Akrotiri", 1, "modern", "NIKAS", ["AKROTIRI", "IREFA", "WP1"]),
    ("Incirlik", 12, "modern", "TUNLA", ["ADA", "HTY", "WP1"]),
])
def test_the_other_clusters_build_through_their_own_gates(tmp_path, home, seed, era, gate, first):
    out = str(tmp_path / "x.miz")
    res = generate(Recipe.from_dict(dict(map="syria", era=era, seed=seed, home_airbase=home,
                                         bb_targets=True, bb_route=True)), out)
    n = res["stats"]["nttr"]
    assert n["gate_in"] == gate
    pts, _ = _player_points(out)
    names = [p.get("name") for p in pts]
    assert names[1:4] == first and pts[-1].get("type") == "Land"


def test_a_syria_mission_without_a_route_has_no_corridors(tmp_path):
    out = str(tmp_path / "n.miz")
    res = generate(Recipe.from_dict(dict(map="syria", era="modern", seed=3, home_airbase="Ramat David")), out)
    assert "nttr" not in res["stats"]


# --------------------------------------------------------------------------- #
# 4. the chart
# --------------------------------------------------------------------------- #
def test_the_page_is_sized_by_the_data():
    assert cc.page_size("syria") == (1800, 1040) and cc.page_size("nevada") == (1600, 1000)
    top, pad, col_w, ow, oh, placed = cc._layout(1800, 1040, "syria")
    assert [p["id"] for p, *_ in placed] == ["israel", "cyprus", "turkey", "jordan"], "all four panels fit"
    xs = sorted({x for _, x, *_ in placed}); ys = sorted({y for _, _, y, *_ in placed})
    assert len(xs) == 2 and len(ys) == 2, "a 2x2 grid"
    assert all(x + w <= col_w for _, x, _, w, _ in placed)
    assert max(y + h for _, _, y, _, h in placed) <= oh
    _, _, ncol, _, _, nplaced = cc._layout(1600, 1000, "nevada")
    assert len(nplaced) == 1 and nplaced[0][3] == ncol, "Nevada keeps the single stacked panel"


def test_the_sea_is_painted_inside_the_bounds_and_the_land_on_top():
    ov = cc.overview(900, 800, mk="syria")
    polys = [op for op in ov.ops if op[0] == "poly"]
    sea = [p for p in polys if p[2] == cc.SEA_FILL]
    assert len(sea) == 1
    xs = [x for x, _ in sea[0][1]]
    assert min(xs) > 0 and max(xs) < 900, "the letterbox margin stays paper"
    i_sea = polys.index(sea[0])
    land = [p for p in polys[i_sea + 1:i_sea + 3] if p[2] == cc.PAPER]
    assert len(land) == 2, "the mainland and Cyprus, straight after the sea"
    nv = cc.overview(900, 800, mk="nevada")
    assert not [op for op in nv.ops if op[0] == "poly" and op[2] == cc.SEA_FILL]


def _texts(cv):
    return [op[2] for op in cv.ops if op[0] == "text"]


def test_the_overview_is_decluttered_and_the_panels_are_not():
    ov = _texts(cc.overview(900, 800, mk="syria"))
    assert "TUDMU" in ov and "KTN" in ov, "a fix outside every panel is drawn"
    assert "MERVA" not in ov and "GAFAZ" not in ov, "fixes a panel draws are left to the panel"
    assert "GATE HAIFA BLOCK~" in ov, "gates always show"
    assert "ROSH HANIKRA~" in ov and "BAALBEK" in ov, "the overview landmarks"
    assert "Tyre" not in ov and "Zahle" not in ov, "minor places wait for the panel"
    israel = next(p for p in cc.panels("syria") if p["id"] == "israel")
    tm = _texts(cc.terminal(600, 400, mk="syria", panel=israel))
    assert "MERVA" in tm and "GAFAZ" in tm and "KEREN" in tm and "Tyre" in tm


def test_the_label_overrides_move_and_hide_corridor_names():
    ov = _texts(cc.overview(900, 800, mk="syria"))
    assert "The Bekaa road" in ov and "L200 east - Al-Tanf" not in ov, "the Jordan panel carries L200"
    jordan = next(p for p in cc.panels("syria") if p["id"] == "jordan")
    tm = _texts(cc.terminal(600, 400, mk="syria", panel=jordan))
    assert "L200 east - Al-Tanf" in tm and "Amman TMA departure" in tm
    # a nudge moves the label by pixels; a hide leaves the lane but not the name
    cyprus = next(p for p in cc.panels("syria") if p["id"] == "cyprus")
    plain = dict(cyprus); plain["labels"] = {}
    unnudged = dict(cyprus); unnudged["labels"] = {k: {kk: vv for kk, vv in v.items() if kk != "nudge"}
                                                  for k, v in cyprus["labels"].items()}
    nudge = cyprus["labels"]["cy_east"]["nudge"]

    def where(panel):
        return sorted(op[1] for op in cc.terminal(600, 400, mk="syria", panel=panel).ops
                      if op[0] == "text" and op[2] == "EAST SID 3 - IREFA")
    a, b, c = where(cyprus), where(plain), where(unnudged)
    assert a and b and c and a != b and a != c
    assert [(round(x - u, 6), round(y - v, 6)) for (x, y), (u, v) in zip(a, c)] == [tuple(nudge)] * len(a)


def test_a_plan_is_red_on_the_syria_chart():
    p = _plan("RAMAT DAVID", 34.52, 37.63)
    cv = cc.overview(900, 800, p, mk="syria")
    assert any(op[0] == "poly" and op[2] == cc.HOT_FILL for op in cv.ops), "the flown road is hot"
    assert "WP1" in _texts(cv) and "TARGET" in _texts(cv)
    assert cc.panel_for_plan("syria", p)["id"] == "israel"
    assert cc.legend_lines(p, "syria")[0].startswith("RED = this mission: The coast road north")


def test_the_chart_renders_deterministically():
    a = cc.render_svg(*cc.page_size("syria"), mk="syria")
    b = cc.render_svg(*cc.page_size("syria"), mk="syria")
    assert a == b and a.startswith("<svg") and "LEVANT CORRIDORS" in a and "AKROTIRI - SIDs" in a
    p1 = cc.render_page(900, 520, mk="syria"); p2 = cc.render_page(900, 520, mk="syria")
    assert p1.size == (900, 520) and p1.tobytes() == p2.tobytes()


def test_the_site_serves_the_syria_chart_and_the_docs_image_is_the_renderers():
    from fastapi.testclient import TestClient
    from server.app import app
    c = TestClient(app)
    r = c.get("/api/corridors/syria/chart.svg")
    assert r.status_code == 200 and r.text.startswith("<svg") and "LEVANT CORRIDORS" in r.text
    r = c.get("/api/corridors/syria/chart.png")
    assert r.status_code == 200 and r.content[:4] == b"\x89PNG"
    assert c.get("/api/corridors/caucasus/chart.svg").status_code == 404
    buf = io.BytesIO()
    cc.render_page(*cc.page_size("syria"), mk="syria").save(buf, format="PNG", optimize=True)
    assert Path("docs/img/syria_corridors.png").read_bytes() == buf.getvalue(), "run scripts/build_corridor_charts.py"
    assert Path("docs/img/syria_corridors.svg").read_text() == cc.render_svg(*cc.page_size("syria"), mk="syria")


def test_the_kneeboard_and_brief_pages_take_the_syria_plan():
    from missiongen import kneeboard as _kb, brief as _br
    p = _plan("RAMAT DAVID", 34.52, 37.63)
    img = _kb.page_nttr_chart(p)
    assert img.size == (_kb.W, _kb.H)
    pg = _br.page_nttr_chart(p)
    assert pg.size == (1448, 2048)
