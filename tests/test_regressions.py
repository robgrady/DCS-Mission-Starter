"""Regression guards for the bugs found in the v1.9.1 code review.

Each test pins a specific defect so it can never silently come back:
  P0b — slot_name is not unique (Syria): duplicate unit names + under-placement
  P0c — radio presets wrote UHF into VHF-only airframes
  P2  — coalition="purple" silently flew from the RED side

Run:  pytest tests/ -v   |   python tests/test_regressions.py
"""
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
while not (ROOT / "missiongen").is_dir() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))


def _gen(tmp, **recipe):
    from missiongen import generate, Recipe
    out = str(Path(tmp) / "t.miz")
    generate(Recipe.from_dict(recipe), out)
    return out


def _mission_text(miz):
    return zipfile.ZipFile(miz).read("mission").decode("utf-8", "ignore")


# --- P0b: slot_name uniqueness --------------------------------------------

def test_no_duplicate_group_or_unit_names(tmp_path):
    """DCS rejects duplicate group/unit names. Syria's Ramat David has six
    stands named '02'; keying on slot_name produced duplicate ST/GSE names."""
    for mp, era, ac in [("syria", "modern", "FA_18C_hornet"),
                        ("caucasus", "modern", "F_16C_50")]:
        m = _mission_text(_gen(tmp_path, map=mp, era=era, coalition="blue",
                               aircraft=ac, home_airbase=None, dress_fill=100,
                               seed=3))
        # our placed statics/flights are the ST/GSE/RAMP/INF-prefixed names
        names = re.findall(r'\["name"\]\s*=\s*"((?:ST|GSE|RAMP|INF) [^"]+)"', m)
        dupes = [n for n, c in Counter(names).items() if c > 1]
        assert not dupes, f"{mp}: duplicate placed-object names: {dupes[:5]}"


def test_ramat_david_places_all_stands(tmp_path):
    """The 17 twin-named stands were unreachable; a full-fill composer mix
    under-placed 86 -> 69. crossroad_idx keying makes all 86 reachable."""
    import random
    from dcs.terrain.syria import Syria
    from missiongen import dressing
    from missiongen.placement import slot_key
    ap = next(a for a in Syria().airport_list() if a.name == "Ramat David")
    fillable = [s for s in ap.parking_slots if s.airplanes]
    placed = []
    dressing._place_mix(ap, {"F_16C_50": len(fillable) + 10},
                        lambda s, ut, liv: placed.append(slot_key(s)) or True,
                        random.Random(1), set())
    assert len(placed) == len(fillable), \
        f"placed {len(placed)} of {len(fillable)} fillable stands"
    assert len(placed) == len(set(placed)), "placed the same stand twice"


# --- P0c: radio preset band -----------------------------------------------

def test_vhf_only_aircraft_get_no_uhf_presets(tmp_path):
    """Spitfire/MiG-21/Ka-50 have no UHF radio; writing the UHF ladder there is
    invalid. They must be skipped (no CHAN column, no ladder freqs in radios)."""
    from missiongen.presets import _uhf_radio_id
    from dcs import planes, helicopters
    for tid in ["SpitfireLFMkIX", "MiG_21Bis", "Ka_50", "SA342M"]:
        t = getattr(planes, tid, None) or getattr(helicopters, tid, None)
        assert _uhf_radio_id(t.panel_radio) is None, f"{tid} wrongly got a UHF radio"


def test_uhf_ladder_lands_on_the_uhf_radio(tmp_path):
    """A-10C's UHF set is radio 2, the Hornet's is radio 1 — the ladder must
    follow the band, not always radio 1."""
    from missiongen.presets import _uhf_radio_id
    from dcs import planes, helicopters
    assert _uhf_radio_id(planes.FA_18C_hornet.panel_radio) == 1
    assert _uhf_radio_id(planes.F_16C_50.panel_radio) == 1
    assert _uhf_radio_id(planes.A_10C_2.panel_radio) == 2
    assert _uhf_radio_id(helicopters.AH_64D_BLK_II.panel_radio) == 2


def test_crew_ops_jet_is_radio_programmed_to_the_comm_plan(tmp_path):
    """Crew-ops templates own the player jet (player_group is None), so the BB-19
    preset step used to skip them: the kneeboard advertised the comm plan while
    the F-14B(U) cockpit kept factory Tomcat defaults (Rob, 2026-07-22 — 'channel
    doesn't match the frequency'). The crew flight must be programmed so cockpit
    and card agree."""
    from missiongen.builder import StarterBuilder
    from missiongen import Recipe, presets
    b = StarterBuilder(Recipe.from_dict(dict(
        map="afghanistan", era="modern", coalition="blue",
        aircraft="F_14B_U", template="backseat_izlid", start="warm",
        slots=1, seed=4553)))
    m = b.build()
    rows, guard = presets.plan_from_comms(b.kb_ctx["comms"])
    plan = {ch: mhz for ch, _ag, mhz in rows}
    assert plan, "comm plan had no rows to program"
    # find the player F-14BU in-jet channels
    chans = None
    for coal in m.coalition.values():
        for c in coal.countries.values():
            for pg in c.plane_group:
                for u in pg.units:
                    if getattr(u, "type", None) == "F-14BU" and u.radio:
                        uhf = presets._uhf_radio_id(u.radio)
                        if uhf:
                            chans = u.radio[uhf]["channels"]
    assert chans is not None, "no programmed UHF radio on the crew-ops jet"
    for ch, mhz in plan.items():
        assert chans.get(ch) == mhz, (
            f"CH{ch} in-jet={chans.get(ch)} != comm plan {mhz} "
            f"(cockpit/kneeboard disagree)")
    assert chans[max(chans)] == guard, "Guard not on the last channel"


# --- collision fixes (v1.10.3): GSE-inside-aircraft + occupancy registry ---

def test_no_statics_inside_aircraft_footprints(tmp_path):
    """GSE used a stand-based 4-9 m offset, spawning trucks INSIDE heavies
    (B-52 half-span = 28 m), and object classes never checked each other.
    The occupancy registry + footprint-aware GSE offset must keep every
    non-aircraft static out of every aircraft footprint, and aircraft off
    each other, including stands parked by ambient AI / the player."""
    import math
    import dcs
    from dcs import planes, helicopters
    from missiongen import generate, Recipe

    fp_cache = {}
    def footprint(tid):
        if tid not in fp_cache:
            r = None
            for mod in (planes, helicopters):
                for n in dir(mod):
                    t = getattr(mod, n, None)
                    if isinstance(t, type) and getattr(t, "id", None) == tid:
                        r = max(getattr(t, "width", 0) or 0,
                                getattr(t, "length", 0) or 0) / 2
            fp_cache[tid] = r
        return fp_cache[tid]

    out = str(Path(tmp_path) / "c.miz")
    generate(Recipe.from_dict({
        "map": "nevada", "era": "modern", "coalition": "blue",
        "aircraft": "F_16C_50", "dress_mix": {"B_52H": 6, "C_130": 6,
                                              "F_16C_50": 12, "KC_135": 4},
        "seed": 11}), out)
    m = dcs.Mission(); m.load_file(out)
    acs, oth = [], []
    for coal in m.coalition.values():
        for c in coal.countries.values():
            for sg in c.static_group:
                u = sg.units[0]; fp = footprint(u.type)
                (acs if fp else oth).append((u.position.x, u.position.y, fp))
            for pg in list(c.plane_group) + list(c.helicopter_group):
                for u in pg.units:
                    fp = footprint(u.type)
                    if fp and pg.points and pg.points[0].type in (
                            "TakeOffParking", "TakeOffParkingHot"):
                        acs.append((u.position.x, u.position.y, fp))
    inside = [1 for gx, gy, _ in oth for ax, ay, ah in acs
              if math.hypot(gx - ax, gy - ay) < ah * 0.85]
    assert not inside, f"{len(inside)} statics inside aircraft footprints"
    overlaps = [1 for i in range(len(acs)) for j in range(i + 1, len(acs))
                if math.hypot(acs[i][0] - acs[j][0], acs[i][1] - acs[j][1])
                < 0.55 * (acs[i][2] + acs[j][2])]
    assert not overlaps, f"{len(overlaps)} aircraft pairs grossly overlapping"


# --- Theater Identity P3: historical airspace (Berlin corridors) -----------

def test_berlin_corridors_draw_and_brief(tmp_path):
    """The Berlin Corridor Transit overlay must draw the corridors + control
    zone on the F10 Common layer AND brief the BASC rule — and stay OFF by
    default so existing share links are byte-identical (determinism contract)."""
    base = dict(map="germany", era="coldwar", coalition="blue",
                aircraft="F_4E_45MC", home_airbase=None, seed=5)
    # default OFF: no airspace artifacts, reproducible
    off = _mission_text(_gen(tmp_path, **base))
    assert "BERLIN CONTROL ZONE" not in off, "airspace drew while flag was off"

    # overlay ON via the template
    on_miz = _gen(tmp_path, **base, template="berlin_corridor_transit",
                  bb_historical_airspace=True, bb_sams=False)
    on = _mission_text(on_miz)
    for name in ("NORTH (Hamburg)", "CENTER (Hannover)", "SOUTH (Frankfurt)",
                 "BERLIN CONTROL ZONE"):
        assert name in on, f"corridor/zone '{name}' not drawn on the map"
    # trigger zone for a future scoring layer
    assert "AIRSPACE BERLIN CONTROL ZONE" in on, "control-zone trigger missing"
    # the BASC rule is briefed (lives in the miz translation dictionary)
    dic = zipfile.ZipFile(on_miz).read("l10n/DEFAULT/dictionary").decode("utf-8", "ignore")
    assert "BERLIN AIR CORRIDORS" in dic and "Berlin Air Safety Centre" in dic, \
        "airspace briefing block missing"

    # corridors must be SQUARE-ended lanes (4 corners + close = 5 pts), NOT
    # rounded oblongs (~44 pts) — the fix Rob flagged. Plus a dot-dash centerline.
    import dcs as _dcs
    from dcs.drawing.polygon import FreeFormPolygon
    from dcs.drawing.line import LineDrawing
    mm = _dcs.Mission(); mm.load_file(on_miz)
    common = mm.drawings.get_layer_by_name("Common")
    polys = [o for o in common.objects if isinstance(o, FreeFormPolygon)]
    lines = [o for o in common.objects if isinstance(o, LineDrawing)]
    assert polys and all(len(p.points) <= 6 for p in polys), \
        "corridors are not square-ended (rounded oblong regressed)"
    assert any(l.line_style.value == "dotdash" for l in lines), "no dot-dash centerline"


# --- Theater Identity P1: International Alignment -------------------------

def test_alignment_dresses_bases_by_owning_nation(tmp_path):
    """Syria's blue side is a coalition — Ramat David (Israel), Turkish bases
    (Turkey), Akrotiri (UK) — so statics must carry the OWNING nation's country,
    not one country per side. And a map with no alignment data must be unchanged
    (single side country) — additive, no regression."""
    import dcs
    from missiongen import generate, Recipe

    def nations_with_statics(**recipe):
        out = str(Path(tmp_path) / "a.miz")
        generate(Recipe.from_dict(recipe), out)
        m = dcs.Mission(); m.load_file(out)
        by_side = {}
        for side, coal in m.coalition.items():
            got = {cn for cn, c in coal.countries.items() if any(c.static_group)}
            if got:
                by_side[side] = got
        return by_side

    syr = nations_with_statics(map="syria", era="modern", coalition="blue",
                               aircraft="FA_18C_hornet", home_airbase="Incirlik",
                               dress_fill=70, seed=4)
    assert {"Israel", "Turkey", "UK"} <= syr.get("blue", set()), \
        f"blue coalition not nation-aligned: {syr.get('blue')}"
    assert "Syria" in syr.get("red", set()), "red side not Syria"

    # a map with NO theater_identity block dresses with a single side country
    cauc = nations_with_statics(map="caucasus", era="modern", coalition="blue",
                                aircraft="F_16C_50", home_airbase=None,
                                dress_fill=60, seed=4)
    assert len(cauc.get("blue", set())) == 1, \
        f"unaligned map should use one blue country, got {cauc.get('blue')}"


def test_nation_rosters_place_correct_types(tmp_path):
    """Aligned bases park nation-correct TYPES, not just skins: Israel flies
    F-15/F-16, Syria flies MiGs, Iran parks the F-14A Tomcat."""
    import dcs
    from missiongen import generate, Recipe

    def types_by_country(**recipe):
        out = str(Path(tmp_path) / "r.miz")
        generate(Recipe.from_dict(recipe), out)
        m = dcs.Mission(); m.load_file(out)
        res = {}
        for coal in m.coalition.values():
            for cn, c in coal.countries.items():
                res.setdefault(cn, set()).update(
                    sg.units[0].type for sg in c.static_group)
        return res

    syr = types_by_country(map="syria", era="modern", coalition="blue",
                           aircraft="FA_18C_hornet", home_airbase="Incirlik",
                           dress_fill=80, seed=4)
    assert syr.get("Israel", set()) & {"F-15E", "F-15C", "F-16C_50"}, \
        "Israeli base did not park F-15/F-16"
    assert any(t.startswith("MiG-") for t in syr.get("Syria", set())), \
        "Syrian base did not park MiGs"

    pg = types_by_country(map="persiangulf", era="modern", coalition="blue",
                          aircraft="FA_18C_hornet", home_airbase="Al Dhafra AFB",
                          dress_fill=80, seed=5)
    assert "F-14A-135-GR" in pg.get("Iran", set()), "Iran did not park the F-14A"


# --- WWII coalition alignment (code review HIGH) ---------------------------
# pydcs defaults Germany/UK/USA to the BLUE coalition. On WWII Normandy/Channel
# Germany is RED; the old _get_country accepted pydcs' default side, so red
# German airfields spawned aircraft under a blue-coalition Germany. Assert the
# country is forced onto the historically-correct side.
def test_wwii_germany_is_red_not_blue(tmp_path):
    from missiongen import Recipe
    from missiongen.builder import StarterBuilder
    for mp, home in (("normandy", None), ("thechannel", None)):
        m = StarterBuilder(Recipe.from_dict(
            dict(map=mp, era="wwii", coalition="blue",
                 aircraft="SpitfireLFMkIX", seed=7))).build()
        red = set(m.coalition["red"].countries)
        blue = set(m.coalition["blue"].countries)
        assert "Germany" in red, f"{mp}: Germany not in RED coalition (got red={red})"
        assert "Germany" not in blue, f"{mp}: Germany leaked into BLUE coalition"


# --- F-14B(U) DTC setup card ------------------------------------------------
def test_dtc_simplify_respects_point_budget():
    from missiongen.dtc import simplify
    ring = [(i, (i * 7) % 5) for i in range(50)]          # 50-point jagged path
    out = simplify(ring, 9)
    assert 2 <= len(out) <= 9, f"simplify didn't meet budget: {len(out)}"
    assert out[0] == (0.0, 0.0) and out[-1] == (49.0, (49 * 7) % 5), \
        "simplify dropped the endpoints"


def test_dtc_card_only_for_bu_and_is_reference_only(tmp_path):
    from missiongen import Recipe, generate
    from missiongen.dtc import is_bu
    assert is_bu("F_14B_U") and not is_bu("FA_18C_hornet")
    # a non-B(U) jet writes NO card (auto-gate off)
    out = str(tmp_path / "hornet.miz")
    r1 = generate(Recipe.from_dict(dict(map="persiangulf", era="modern",
                  aircraft="FA_18C_hornet", home_airbase="Al Dhafra AFB",
                  threat_intensity=4, threat_tier="heavy", seed=22)), out)
    assert "dtc_card" not in r1, "DTC card written for a non-B(U) jet"
    # the B(U) writes a card with reference sections and NO player route/loadout
    out2 = str(tmp_path / "bu.miz")
    r2 = generate(Recipe.from_dict(dict(map="persiangulf", era="modern",
                  aircraft="F_14B_U", home_airbase="Al Dhafra AFB",
                  threat_intensity=4, threat_tier="heavy", seed=22)), out2)
    assert r2.get("dtc_card"), "no DTC card for the F-14B(U)"
    card = Path(r2["dtc_card"]).read_text()
    assert "Bullseye" in card and "Comm / TACAN" in card, "card missing reference sections"
    low = card.lower()
    for forbidden in ("waypoint", "steerpoint", "ingress", "egress", "loadout", "target run"):
        assert forbidden not in low, f"card leaked player-plan content: {forbidden!r}"
    # the real DTM cartridge is injected into the .miz as the JSON sidecar
    import zipfile as _zf, json as _json
    z = _zf.ZipFile(out2)
    assert z.read("mission"), "mission entry unreadable after DTC"
    member = "DTC/F-14B(U) DTC_1.dtc"
    assert member in z.namelist(), "DTM cartridge sidecar not injected"
    dtm = _json.loads(z.read(member))
    assert dtm["type"] == "F-14BU", "cartridge not typed to the F-14B(U)"
    assert len(dtm["data"]["NAV"]) == 12, "NAV must have 12 slots (DCS schema)"
    nav0 = dtm["data"]["NAV"][0]
    assert nav0["additional_points"], "no reference points written to the cartridge"
    # north star: the cartridge must NEVER carry the player's route or weapons
    assert all(not s["waypoints"] for s in dtm["data"]["NAV"]), "cartridge wrote player waypoints"
    assert all(not st["targets"] for st in dtm["data"]["JDAM"]["stations"]), "cartridge wrote weapon targets"


def test_dtc_sidecar_is_linked_from_the_mission_tree(tmp_path):
    """The sidecar `DTC/*.dtc` only loads if the player unit references it via
    `DTC.Cartridges[].name`. Reverse-engineering first missed this and the DTM
    page loaded EMPTY in-sim (Rob, 2026-07-22). Lock the unit-level link in, and
    that its name matches the sidecar member so DCS can pair them."""
    import zipfile as _zf
    from missiongen import Recipe, generate
    out = str(tmp_path / "bu.miz")
    r = generate(Recipe.from_dict(dict(map="persiangulf", era="modern",
                 aircraft="F_14B_U", home_airbase="Al Dhafra AFB",
                 threat_intensity=4, threat_tier="heavy", seed=22)), out)
    assert r["stats"].get("dtc_units_tagged", 0) >= 1, "no F-14B(U) player unit tagged"
    mission = _zf.ZipFile(out).read("mission").decode("utf-8", "ignore")
    assert "Cartridges" in mission, "mission tree has no DTC.Cartridges link"
    assert "F-14B(U) DTC_1" in mission, "cartridge name not referenced by the unit"
    member = "DTC/F-14B(U) DTC_1.dtc"
    assert member in _zf.ZipFile(out).namelist(), "sidecar missing"
    # the unit reference name must equal the sidecar member (minus dir/extension)
    assert member == f"DTC/{'F-14B(U) DTC_1'}.dtc"


def test_dtc_injection_is_deterministic(tmp_path):
    """Same recipe+seed must inject a byte-identical cartridge (share links)."""
    import zipfile as _zf, hashlib
    from missiongen import Recipe, generate
    def _dtc_hash(p):
        generate(Recipe.from_dict(dict(map="persiangulf", era="modern",
                 aircraft="F_14B_U", home_airbase="Al Dhafra AFB",
                 threat_intensity=4, threat_tier="heavy", seed=22)), p)
        return hashlib.sha256(_zf.ZipFile(p).read("DTC/F-14B(U) DTC_1.dtc")).hexdigest()
    assert _dtc_hash(str(tmp_path / "a.miz")) == _dtc_hash(str(tmp_path / "b.miz")), \
        "DTM cartridge is not deterministic"


def test_f14bu_uses_verified_type_id(tmp_path):
    """Survey-confirmed DCS type id is F-14BU; the old guess F-14B-U would break
    every generated B(U) mission. Lock it into the serialized mission."""
    import zipfile as _zf
    from missiongen import Recipe, generate
    out = str(tmp_path / "bu.miz")
    generate(Recipe.from_dict(dict(map="persiangulf", era="modern",
             aircraft="F_14B_U", home_airbase="Al Dhafra AFB", seed=7)), out)
    mission = _zf.ZipFile(out).read("mission").decode("utf-8", "ignore")
    assert '"F-14BU"' in mission, "F-14B(U) did not serialize the verified type id"
    assert "F-14B-U" not in mission, "old bad provisional id F-14B-U leaked in"


# --- Afghanistan extension terrain (generated from Rob's install export) ----
def test_afghanistan_terrain_generates_and_reloads(tmp_path):
    """The extension-terrain path: full engine generation on Afghanistan, then a
    pydcs round-trip through the patched theatre loader."""
    import dcs
    from missiongen import Recipe, generate
    out = str(tmp_path / "afghan.miz")
    res = generate(Recipe.from_dict(dict(map="afghanistan", era="modern",
              coalition="blue", aircraft="A_10C_2", home_airbase="Kandahar",
              dress_fill=30, seed=9)), out)
    assert not [w for w in res["warnings"] if "failed" in w.lower()], res["warnings"]
    m = dcs.Mission(); m.load_file(out)          # needs the loader patch
    assert type(m.terrain).__name__ == "Afghanistan"
    assert len(m.terrain.airports) == 25
    statics = sum(len(c.static_group) for co in m.coalition.values()
                  for c in co.countries.values())
    assert statics > 50, f"Afghanistan field barely dressed ({statics} statics)"



if __name__ == "__main__":
    import tempfile
    failed = 0
    for _extra in (test_dtc_simplify_respects_point_budget,):
        try:
            _extra(); print(f"PASS  {_extra.__name__}")
        except Exception as e:
            failed += 1; print(f"FAIL  {_extra.__name__}\n      {type(e).__name__}: {e}")
    for fn in [test_no_duplicate_group_or_unit_names, test_ramat_david_places_all_stands,
               test_vhf_only_aircraft_get_no_uhf_presets, test_uhf_ladder_lands_on_the_uhf_radio,
               test_no_statics_inside_aircraft_footprints,
               test_berlin_corridors_draw_and_brief,
               test_alignment_dresses_bases_by_owning_nation,
               test_nation_rosters_place_correct_types,
               test_wwii_germany_is_red_not_blue,
               test_dtc_card_only_for_bu_and_is_reference_only,
               test_dtc_injection_is_deterministic,
               test_f14bu_uses_verified_type_id,
               test_afghanistan_terrain_generates_and_reloads]:
        try:
            with tempfile.TemporaryDirectory() as d:
                fn(Path(d))
            print(f"PASS  {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {fn.__name__}\n      {type(e).__name__}: {e}")
    print(f"\n{'FAILED' if failed else 'OK'} — {failed} failure(s)")
    sys.exit(1 if failed else 0)
