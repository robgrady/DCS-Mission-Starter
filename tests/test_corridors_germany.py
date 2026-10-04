"""Central Region corridors: the Authentic standard map detail on the Cold War
Germany map.

Rob (v1.102.0): "Let's do the Germany map like the previous two."

WHAT THIS FILE HOLDS THE PRODUCT TO
-----------------------------------
  1. the Germany data is whole under the shared schema, and the published
     structure is in it: the ADIZ at 40 km, the HAWK and Nike belts, the
     three 20-mile Berlin corridors and the Control Zone, the LFAs and the
     ED-R ranges with printed vertices, the GDR flight-restriction line, the
     Soviet ranges - every road placed on a town flagged curated;
  2. it is a two-sided front: the NATO clusters (Eifel, Hunsrück, Pfalz,
     Rhein-Main, Rhineland, Weser, Elbe) plan to the GDR sectors and the
     Warsaw Pact clusters (Berlin, the southern fields, Mecklenburg) plan to
     the FRG sectors; every out-chain ends on its gate; the six gates are
     shared; the structure belongs to the Cold War era only;
  3. built missions from Bitburg, Hahn, Nörvenich and (flying red) Werneuchen
     carry the corridor waypoints, WP1 at the gate, the Central Region
     section in the brief with the map's own words, the lanes on the F10
     map and the chart page in the kneeboard; a modern-era Germany mission
     keeps the generic route;
  4. the chart is the standard detail: eight terminal panels in a four-column
     grid, a panel that serves several clusters, the legal corridors as
     areas and the roads as lanes, deterministic bytes, served by the site
     and committed under docs/img.
"""
from __future__ import annotations

import io
import random
import zipfile
from pathlib import Path

import pytest

from dcs import mapping
from dcs.mapping import LatLng
from dcs.terrain.germany import Germany

from missiongen import Recipe, generate, corridors, corridor_chart as cc
from test_nttr import _player_points


D = corridors.data("germany")
TERRAIN = Germany()


def _pt(lat, lon):
    return mapping.Point.from_latlng(LatLng(lat, lon), TERRAIN)


def _home(name):
    f = D["fixes"][name]
    return _pt(f["lat"], f["lon"])


def _plan(home, target_lat, target_lon, era="coldwar", home_name=None):
    return corridors.plan_route(_home(home), _pt(target_lat, target_lon), era,
                                random.Random(1), TERRAIN, "germany", home_name=home_name or home.title())


# --------------------------------------------------------------------------- #
# 1. the data
# --------------------------------------------------------------------------- #
def test_germany_is_the_third_corridor_map():
    assert corridors.maps() == ("nevada", "syria", "germany")
    assert corridors.has("germany") and D["eras"] == ["coldwar"]


def test_every_corridor_point_gate_plan_and_panel_names_known_things():
    fixes = D["fixes"]
    ids = {c["id"] for c in D["corridors"]}
    for c in D["corridors"]:
        assert c["role"] in ("departure", "transit", "recovery")
        for p in c["points"]:
            assert p in fixes, f"{c['id']} names unknown fix {p!r}"
        lo, hi = c["block_ft"]
        assert 0 <= lo < hi <= 12000 and 3 <= c["width_nm"] <= 8 and c["src"]
    for g in D["gates"]:
        assert g in fixes and fixes[g]["kind"] == "gate" and fixes[g].get("approx"), "every gate is a curated crossing"
    for cid, sectors in D["plans"].items():
        assert cid in D["clusters"]
        for sector, modes in sectors.items():
            assert list(modes) == ["low"], "the Cold War has one road"
            p = modes["low"]
            assert set(p["out"]) <= ids and p["back"] in ids, (cid, sector)
            assert p["gate_in"] in D["gates"] and p["gate_out"] in D["gates"]
    for pn in D["chart"]["panels"]:
        for cl in pn.get("clusters", [pn["cluster"]]):
            assert cl in D["clusters"]
        assert set(pn["lanes"]) <= ids
        assert set(pn.get("labels", {})) <= ids
    assert set(D["chart"].get("labels", {})) <= ids


def test_every_out_chain_ends_on_its_gate_and_joins_up():
    by = {c["id"]: c for c in D["corridors"]}
    for cid, sectors in D["plans"].items():
        for sector, modes in sectors.items():
            p = modes["low"]
            prev = None
            for oid in p["out"]:
                c = by[oid]
                if prev is not None:
                    assert c["points"][0] == prev, f"{cid}/{sector}: {oid} does not start where the last road ended"
                prev = c["points"][-1]
            assert prev == p["gate_in"], f"{cid}/{sector}: the out-chain ends at {prev}, not the gate {p['gate_in']}"
            assert by[p["back"]]["role"] == "recovery" and by[p["out"][0]]["role"] == "departure"


def test_the_published_structure_is_in_the_data():
    areas = {a["id"]: a for a in D["chart"]["areas"]}
    assert "40 km" in areas["ADIZ"]["alt"] and areas["ADIZ"].get("approx"), "the ADIZ is a band on a schematic border"
    assert areas["HAWK"]["kind"] == "moa" and areas["NIKE"]["kind"] == "alert"
    for k in ("CORR-N", "CORR-C", "CORR-S"):
        assert areas[k]["kind"] == "tma" and "20 SM" in areas[k]["label"] and "exercise" in areas[k]["label"] and areas[k].get("approx")
    assert len(areas["BCZ"]["poly"]) == 36
    assert len(areas["ED-R 37"]["poly"]) == 24 and not areas["ED-R 37"].get("approx"), "a printed circle"
    assert len(areas["ED-R 31"]["poly"]) == 11 and len(areas["LFA3"]["poly"]) == 53, "printed vertices, every one"
    for k in ("WITTSTOCK", "LETZLINGEN", "LIEBEROSE", "RETZOW", "ED-R 116", "ED-R 136", "TRA LAUTER", "FRBR41"):
        assert areas[k].get("approx"), f"{k} is a box or a ring on a printed point - curated"
    line = next(l for l in D["chart"]["lines"] if l["kind"] == "deconfliction")
    assert len(line["pts"]) == 27, "the 27 Grenzsperrstreifen reference towns"
    assert D["fixes"]["NTM"]["lat"] == 50.0159 and not D["fixes"]["NTM"].get("approx"), "a navaid as printed"
    assert D["fixes"]["HAGENOW"].get("approx") and "Grenzsperrstreifen" in D["fixes"]["HAGENOW"]["src"]
    names = {c["name"] for c in D["corridors"]}
    assert "The Fulda Gap - LLTR to Point Alpha" in names and "The A2 - Porta to Helmstedt" in names
    assert "The south corridor axis - Herleshausen to Berlin" in names
    assert D["text"]["chart_title"] == "CENTRAL REGION CORRIDORS"
    assert set(D["sectors"]["labels"]) >= {"gdr_north", "berlin", "altmark", "saxony", "gdr_south", "frg_north", "hannover", "ruhr", "hessen", "pfalz"}


# --------------------------------------------------------------------------- #
# 2. a two-sided front
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("home,lat,lon,want", [
    ("Bitburg", 49.945, 6.564, ("eifel", True)),
    ("Hahn", 49.948, 7.264, ("hunsruck", True)),
    ("Ramstein", 49.437, 7.600, ("pfalz", True)),
    ("Wiesbaden", 50.050, 8.326, ("rheinmain", True)),
    ("Norvenich", 50.831, 6.659, ("rhineruhr", True)),
    ("Gutersloh", 51.923, 8.304, ("rhineruhr", True)),
    ("Fassberg", 52.919, 10.185, ("heath", True)),      # its own cluster since 1.104: the Lüneburg Heath
    ("Hamburg", 53.627, 9.981, ("elbe", True)),
    ("Werneuchen", 52.632, 13.769, ("berlin", True)),
    ("Merseburg", 51.364, 11.950, ("gdr_south", True)),
    ("Parchim", 53.428, 11.787, ("gdr_north", True)),
    ("Kastrup", 55.619, 12.652, (None, False)),
])
def test_the_home_field_picks_the_cluster(home, lat, lon, want):
    assert corridors.cluster_for_home(home, lat, lon, "germany") == want


@pytest.mark.parametrize("lat,lon,want", [
    (53.43, 11.79, "gdr_north"),     # Parchim
    (52.63, 13.77, "berlin"),        # Werneuchen
    (52.63, 11.82, "altmark"),       # Stendal
    (51.05, 13.74, "saxony"),        # Dresden
    (51.36, 11.95, "gdr_south"),     # Merseburg
    (53.63, 9.98, "frg_north"),      # Hamburg
    (52.46, 9.43, "hannover"),       # Wunstorf
    (50.83, 6.66, "ruhr"),           # Nörvenich
    (51.08, 9.42, "hessen"),         # Fritzlar
    (49.44, 7.60, "pfalz"),          # Ramstein
    (55.6, 12.65, "none"),           # Copenhagen
])
def test_the_sector_picker_puts_both_germanies_where_they_are(lat, lon, want):
    assert corridors.sector_for(lat, lon, "germany") == want


def test_the_eifel_flies_the_fulda_gap_to_thuringia_and_the_werra_to_berlin():
    p = _plan("BITBURG", 51.36, 11.95)                  # Merseburg
    assert p["cluster"] == "eifel" and p["sector"] == "gdr_south" and p["mode"] == "low"
    assert p["corridors"] == ["ef_out", "fulda", "ef_home"] and p["gate_in"] == "POINT ALPHA"
    names = [l["name"] for l in p["legs"]]
    assert names[:4] == ["NTM", "BUE", "KOBLENZ", "TAU"]
    assert names[names.index("WP1") - 1] == "HUNFELD" and names[-1] == "NTM2"
    p = _plan("BITBURG", 52.63, 13.77)                  # Werneuchen
    assert p["gate_in"] == "HERLESHAUSEN" and p["corridors"][1] == "werra"
    p = _plan("BITBURG", 51.05, 13.74)                  # Dresden
    assert p["gate_in"] == "HOF" and p["corridors"][1] == "hofroad"


def test_the_north_flies_the_a2_and_the_elbe():
    """The Weser fields take the A2 to Helmstedt whatever the target; the Heath
    road north out of Fassberg (Uelzen, then the Dömitz gate) belongs to the
    Heath cluster, not to Hannover - a Hannover jet never starts at Fassberg."""
    p = _plan("HANNOVER", 52.63, 13.77)
    assert p["cluster"] == "hannover" and p["corridors"] == ["ha_out", "hlz_gate", "ha_home"] and p["gate_in"] == "HELMSTEDT"
    p = _plan("HANNOVER", 53.43, 11.79)
    assert p["corridors"] == ["ha_out", "hlz_gate", "ha_home"] and p["gate_in"] == "HELMSTEDT"
    p = _plan("FASSBERG", 53.43, 11.79)
    assert p["cluster"] == "heath" and p["corridors"] == ["ha_north", "uelzen_gate", "ha_north_home"] and p["gate_in"] == "DOMITZ"
    p = _plan("FASSBERG", 52.63, 13.77)
    assert p["corridors"] == ["he_out", "hlz_gate", "he_home"] and p["gate_in"] == "HELMSTEDT"
    p = _plan("HAMBURG", 53.43, 11.79)
    assert p["cluster"] == "elbe" and p["gate_in"] == "BOIZENBURG"
    p = _plan("NORVENICH", 52.63, 11.82)
    assert p["cluster"] == "rhineruhr" and p["corridors"][0] == "rr_out" and p["gate_in"] == "HELMSTEDT"
    names = [l["name"] for l in p["legs"]]
    assert "PORTA" in names and "HLZ" in names, "the Ruhr road joins the A2 at the Porta"


def test_the_other_side_flies_the_same_gates_the_other_way():
    p = _plan("WERNEUCHEN", 52.46, 9.43)                # Wunstorf, from the Berlin ring
    assert p["cluster"] == "berlin" and p["sector"] == "hannover"
    assert p["corridors"] == ["be_out_w", "r_rathenow", "be_home_w"] and p["gate_in"] == "HELMSTEDT"
    names = [l["name"] for l in p["legs"]]
    assert names[:3] == ["NAUEN", "RATHENOW", "GENTHIN"] and "BERLIN" not in names, "the ring's fields join outside the Control Zone"
    p = _plan("WERNEUCHEN", 53.63, 9.98)
    assert p["gate_in"] == "BOIZENBURG" and p["corridors"][1] == "r_pritzwalk"
    p = _plan("MERSEBURG", 49.44, 7.60)
    assert p["cluster"] == "gdr_south" and p["gate_in"] == "POINT ALPHA" and p["corridors"][1] == "r_fulda"
    p = _plan("PARCHIM", 53.63, 9.98)
    assert p["cluster"] == "gdr_north" and p["gate_in"] == "BOIZENBURG"
    p = _plan("PARCHIM", 52.46, 9.43)
    assert p["gate_in"] == "DOMITZ" and p["corridors"] == ["gn_out", "r_domitz", "gn_home"]


def test_the_structure_belongs_to_the_cold_war():
    assert _plan("BITBURG", 51.36, 11.95, era="coldwar") is not None
    assert _plan("BITBURG", 51.36, 11.95, era="modern") is None, "no ADIZ, no belts, no corridors after 1990"
    assert _plan("BITBURG", 51.36, 11.95, era="wwii") is None
    assert _plan("BITBURG", 49.98, 6.70) is None, "Spangdahlem from Bitburg is local"
    assert _plan("BITBURG", 55.6, 12.65) is None, "Copenhagen is in no sector"
    assert corridors.plan_route(_pt(55.619, 12.652), _pt(52.63, 13.77), "coldwar", random.Random(1), TERRAIN,
                                "germany", home_name="Kastrup") is None, "a field in no cluster"


def test_the_brief_speaks_central_region():
    p = _plan("BITBURG", 51.36, 11.95)
    text = "\n".join(corridors.brief_lines(p))
    assert text.startswith("== CENTRAL REGION CORRIDORS - HOW YOU GET TO THE FIGHT ==")
    assert "Sector: GDR_SOUTH, low road, from the Eifel" in text
    assert "GATE IN (WP1): POINT ALPHA" in text and "GATE OUT: POINT ALPHA" in text
    assert "THE FULDA GAP - LLTR TO POINT ALPHA" in text and "FLYFISH" in text and "Fuchsbau" in text
    assert "RANGE ENTRY" not in text and "PLUTO" not in text
    md = corridors.md_line(p)
    assert md.startswith("**The Eifel road - Nattenheim to the Taunus / The Fulda Gap - LLTR to Point Alpha / Recovery into the Eifel** — Thuringia and the Leipzig basin")
    assert "nobody goes direct across the border" in md and "Bravo" not in md
    ap = corridors.approx_fixes(p)
    assert "POINT ALPHA" in ap and "KOBLENZ" in ap and "NTM" not in ap and "TAU" not in ap
    assert any("FLYFISH" in k for k in corridors.known_issue_lines(p))


# --------------------------------------------------------------------------- #
# 3. built missions
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def eifel(tmp_path_factory):
    d = tmp_path_factory.mktemp("ger")
    out = str(d / "bit.miz")
    rc = dict(map="germany", era="coldwar", seed=12, home_airbase="Spangdahlem", aircraft="F_4E_45MC",
              bb_targets=True, bb_route=True, timing_anchor="tot", timing_at="07:30")
    res = generate(Recipe.from_dict(rc), out, brief_dir=str(d))
    return res, out


def test_a_phantom_from_spangdahlem_flies_the_fulda_gap(eifel):
    res, out = eifel
    n = res["stats"]["nttr"]
    assert n["map"] == "germany" and n["title"] == "Central Region corridors"
    assert n["sector"] == "gdr_south" and n["corridors"] == ["ef_out", "fulda", "ef_home"] and n["gate_in"] == "POINT ALPHA"
    pts, _ = _player_points(out)
    names = [p.get("name") for p in pts]
    assert names[1:8] == ["NTM", "BUE", "KOBLENZ", "TAU", "GELNHAUS", "FULDA", "HUNFELD"]
    assert names[8:12] == ["WP1", "IP", "TARGET", "EXIT"]
    assert names[-2] == "NTM2" and pts[-1].get("type") == "Land"
    tl = res["stats"]["timing"]
    tos = [r["to"] for r in tl["rows"]]
    assert "HUNFELD" in tos and "WP1" in tos and "NTM2" in tos
    md = Path(res["brief_md"]).read_text()
    assert "## Central Region corridors" in md and "nobody goes direct across the border" in md
    assert "- THE FULDA GAP - LLTR TO POINT ALPHA" in md and "GATE IN (WP1): POINT ALPHA" in md
    _, mis = _player_points(out)
    texts = [o["text"] for L in mis.get("drawings", {}).get("layers", {}).values()
             for o in (L.get("objects") or {}).values() if o.get("text")]
    joined = "\n".join(texts)
    assert "The Fulda Gap - LLTR to Point Alpha" in joined and "GATE POINT ALPHA~" in joined
    assert "GATE HELMSTEDT~" in joined, "every gate is curated and marked"
    z = zipfile.ZipFile(out)
    pages = sorted(x for x in z.namelist() if x.startswith("KNEEBOARD/"))
    assert len(pages) == 8, pages
    from PIL import Image
    assert Image.open(io.BytesIO(z.read(pages[-1]))).size == (1024, 1366)
    issues = res["stats"].get("known_issues", [])
    assert any("FLYFISH" in k for k in issues) and any("curated placements" in k for k in issues)


@pytest.mark.parametrize("home,seed,coal,ac,gate,first", [
    ("Hahn", 6, "blue", "F_4E_45MC", "HELMSTEDT", ["HND", "KIR", "TAU"]),
    ("Norvenich", 5, "blue", "F_4E_45MC", "HELMSTEDT", ["COL", "GMH", "HMM"]),
    ("Werneuchen", 3, "red", "MiG_21Bis", "HELMSTEDT", ["NAUEN", "RATHENOW", "GENTHIN"]),
    ("Parchim", 3, "red", "MiG_21Bis", "HELMSTEDT", ["PARCHIM", "PERLEBRG", "OSTERBRG"]),
])
def test_both_sides_build_through_their_gates(tmp_path, home, seed, coal, ac, gate, first):
    out = str(tmp_path / "x.miz")
    res = generate(Recipe.from_dict(dict(map="germany", era="coldwar", seed=seed, home_airbase=home, coalition=coal,
                                         aircraft=ac, bb_targets=True, bb_route=True)), out)
    n = res["stats"]["nttr"]
    assert n["gate_in"] == gate
    pts, _ = _player_points(out)
    names = [p.get("name") for p in pts]
    assert names[1:4] == first and "WP1" in names and pts[-1].get("type") == "Land"


def test_a_modern_germany_mission_keeps_the_generic_route(tmp_path):
    out = str(tmp_path / "m.miz")
    res = generate(Recipe.from_dict(dict(map="germany", era="modern", seed=5, home_airbase="Spangdahlem",
                                         bb_targets=True, bb_route=True)), out)
    assert "nttr" not in res["stats"]
    pts, _ = _player_points(out)
    assert [p.get("name") for p in pts][1:4] == ["WP1", "IP", "TARGET"]


# --------------------------------------------------------------------------- #
# 4. the chart
# --------------------------------------------------------------------------- #
def test_eight_panels_in_four_columns_and_a_panel_for_several_clusters():
    assert cc.page_size("germany") == (2400, 1250)
    top, pad, col_w, ow, oh, placed = cc._layout(2400, 1250, "germany")
    assert len(placed) == 8 and len({x for _, x, *_ in placed}) == 4 and len({y for _, _, y, *_ in placed}) == 2
    assert all(x + w <= col_w for _, x, _, w, _ in placed) and max(y + h for _, _, y, _, h in placed) <= oh
    assert placed[0][0]["id"] == "rheinmain" and placed[1][0]["id"] == "eifel"
    p = _plan("HAHN", 51.36, 11.95)
    assert cc.panel_for_plan("germany", p)["id"] == "eifel", "the Hunsrück shares the 4 ATAF panel (not the first panel by default)"
    assert cc.panel_for_plan("germany", _plan("RAMSTEIN", 51.36, 11.95))["id"] == "eifel"
    assert cc.panel_for_plan("germany", _plan("PARCHIM", 52.46, 9.43))["id"] == "gdr_north"
    assert cc.panel_for_plan("germany", _plan("HAMBURG", 53.43, 11.79))["id"] == "elbe"


def _texts(cv):
    return [op[2] for op in cv.ops if op[0] == "text"]


def test_the_overview_shows_the_structure_and_hides_what_the_panels_draw():
    ov = _texts(cc.overview(1000, 1050, mk="germany"))
    for label in ("ADIZ / FLUGÜBERWACHUNGSZONE", "HAWK BELT (LOMEZ)", "NIKE HERCULES BELT (MEZ)", "NORTH CORRIDOR (Hamburg)",
                  "BERLIN CONTROL ZONE", "ED-R 37", "LFA 3", "GDR FLIGHT-RESTRICTION LINE", "WITTSTOCK POLYGON"):
        assert label in ov, label
    assert "GATE HELMSTEDT~" in ov and "GATE POINT ALPHA~" in ov
    assert "KOBLENZ~" not in ov and "NAUEN~" not in ov, "a panel draws those"
    assert "KASSEL~" in ov and "BERLIN" in ov, "the overview landmarks"
    assert "L200 east - Al-Tanf" not in ov
    berlin = next(p for p in cc.panels("germany") if p["id"] == "berlin")
    tm = _texts(cc.terminal(600, 420, mk="germany", panel=berlin))
    assert "NAUEN~" in tm and "Berlin west - Nauen to Rathenow" in tm
    south = next(p for p in cc.panels("germany") if p["id"] == "gdr_south")
    line = next(l for l in D["chart"]["lines"] if l["kind"] == "deconfliction")
    b = south["bounds"]
    assert b["lat"][0] <= line["label_at"][0] <= b["lat"][1] and b["lon"][0] <= line["label_at"][1] <= b["lon"][1]
    assert "GDR FLIGHT-RESTRICTION LINE" not in _texts(cc.terminal(600, 420, mk="germany", panel=south)), \
        "a line label stays on the overview even where the panel holds its anchor"


def test_a_sub_area_without_a_label_rides_on_its_neighbour():
    ov = cc.overview(1000, 1050, mk="germany")
    texts = _texts(ov)
    assert "ED-R 34" in texts and texts.count("FL 80 / GND") == 0, "ED-R 34C has no label of its own"


def test_a_plan_is_red_and_the_chart_is_deterministic():
    p = _plan("BITBURG", 52.63, 13.77)
    cv = cc.overview(1000, 1050, p, mk="germany")
    assert any(op[0] == "poly" and op[2] == cc.HOT_FILL for op in cv.ops)
    assert "WP1" in _texts(cv) and "TARGET" in _texts(cv)
    assert cc.legend_lines(p, "germany")[0].startswith("RED = this mission: The Eifel road")
    a = cc.render_svg(*cc.page_size("germany"), mk="germany")
    assert a == cc.render_svg(*cc.page_size("germany"), mk="germany") and "CENTRAL REGION CORRIDORS" in a
    i1 = cc.render_page(1200, 620, mk="germany"); i2 = cc.render_page(1200, 620, mk="germany")
    assert i1.size == (1200, 620) and i1.tobytes() == i2.tobytes()


def test_the_site_serves_the_germany_chart_and_the_docs_image_is_the_renderers():
    from fastapi.testclient import TestClient
    from server.app import app
    c = TestClient(app)
    r = c.get("/api/corridors/germany/chart.svg")
    assert r.status_code == 200 and r.text.startswith("<svg") and "CENTRAL REGION CORRIDORS" in r.text
    assert c.get("/api/corridors/germany/chart.png").content[:4] == b"\x89PNG"
    buf = io.BytesIO()
    cc.render_page(*cc.page_size("germany"), mk="germany").save(buf, format="PNG", optimize=True)
    assert Path("docs/img/germany_corridors.png").read_bytes() == buf.getvalue(), "run scripts/build_corridor_charts.py"
    assert Path("docs/img/germany_corridors.svg").read_text() == cc.render_svg(*cc.page_size("germany"), mk="germany")


def test_the_kneeboard_and_brief_pages_take_the_germany_plan():
    from missiongen import kneeboard as _kb, brief as _br
    p = _plan("WERNEUCHEN", 52.46, 9.43)
    assert _kb.page_nttr_chart(p).size == (_kb.W, _kb.H)
    assert _br.page_nttr_chart(p).size == (1448, 2048)


def test_corridors_can_be_switched_off_and_the_timing_syllabus_does(tmp_path):
    """Recipe.corridors=False keeps the generic four-point plan. The five
    timing rides (Fassberg, Cold War) teach a card with WP1, IP and TARGET
    on it and stay under 25 minutes - they opt out in the template.

    1.104 renamed the threading switch from `corridors` (which shadowed the
    Air Corridor list of the same name) to `published_corridors` and the five
    templates kept the old key, so they threaded by default and Timing 1 became
    a 51-minute corridor nav. Pinned here against the new name."""
    import json
    t = json.load(open("missiongen/data/mission_templates.json"))
    for k in ("timing_1_flythecard", "timing_2_hitthetot", "timing_3_thepackage", "timing_4_absorbtheearly", "timing_5_check"):
        assert t[k]["recipe"].get("published_corridors") is False, k
    out = str(tmp_path / "off.miz")
    res = generate(Recipe.from_dict(dict(map="germany", era="coldwar", seed=12, home_airbase="Spangdahlem", aircraft="F_4E_45MC",
                                         bb_targets=True, bb_route=True, published_corridors=False)), out)
    assert "nttr" not in res["stats"]
    pts, _ = _player_points(out)
    assert [p.get("name") for p in pts][1:4] == ["WP1", "IP", "TARGET"]
    assert Recipe.from_dict(dict(map="germany", era="coldwar")).published_corridors is True, "on by default"
    # the OLD name is the threat-axis list: a `corridors: false` in a template no longer opts out
    # of threading, which is exactly how the timing rides grew to 51 minutes in 1.104
    assert Recipe.from_dict(dict(map="germany", era="coldwar")).corridors == []
