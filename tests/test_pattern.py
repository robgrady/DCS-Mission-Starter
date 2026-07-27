"""BB-23 'aircraft in the pattern': AI traffic recovering into / departing from
the player's own field at mission start.

What these pin:
  * the option is OFF by default and adds nothing to the .miz when off
  * landing traffic spawns AIRBORNE on the extended centreline and ends in a
    Land waypoint at the player's field (not somewhere else)
  * takeoff traffic spawns at PARKING (engines running) and flies a circuit
  * the type category is era-correct (no Vipers in 1944, no helos in WWII)
  * recipe validation rejects bad mode/kind/count
  * same recipe + seed still rebuilds byte-identical (determinism contract)

Run:  pytest tests/test_pattern.py -v
"""
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
while not (ROOT / "missiongen").is_dir() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

BASE = dict(map="caucasus", era="modern", coalition="blue",
            aircraft="F_16C_50", seed=11, bb_kneeboard=False)


def _gen(tmp, name="t.miz", **over):
    from missiongen import generate, Recipe
    out = str(Path(tmp) / name)
    r = Recipe.from_dict({**BASE, **over})
    return out, generate(r, out)


def _text(miz):
    return zipfile.ZipFile(miz).read("mission").decode("utf-8", "ignore")


_GNAME = re.compile(r'\["name"\]\s*=\s*"(Pattern \d+)"\s*,')


def _pattern_groups(text):
    """Slice the lua for each 'Pattern N' group. pydcs writes keys in
    alphabetical order, so ["name"] comes before ["route"] and ["units"] —
    a forward window from one group name to the next is that whole group.
    ("Pattern 1 Pilot #1" is a unit name and never matches _GNAME.)"""
    out = {}
    for m in _GNAME.finditer(text):
        # walk forward from the name balancing braces; the group's dict ends
        # when we fall out of its enclosing table
        depth, i = 0, m.end()
        while i < len(text):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                if depth == 0:
                    break
                depth -= 1
            i += 1
        out[m.group(1)] = text[m.start():i]
    return out


def _briefing(miz):
    """The mission briefing lives in the l10n dictionary, not the result dict."""
    return zipfile.ZipFile(miz).read(
        "l10n/DEFAULT/dictionary").decode("utf-8", "ignore")


# --- off by default ---------------------------------------------------------

def test_off_by_default(tmp_path):
    from missiongen import Recipe
    assert Recipe().bb_pattern is False
    miz, res = _gen(tmp_path)
    assert "pattern" not in res["stats"]
    assert "Pattern 1" not in _text(miz)


# --- landing leg ------------------------------------------------------------

def test_landing_traffic_spawns_airborne_and_lands_at_home(tmp_path):
    miz, res = _gen(tmp_path, bb_pattern=True, pattern_mode="landing",
                    pattern_kind="fighter", pattern_count=3,
                    home_airbase="Kutaisi")
    pat = res["stats"]["pattern"]
    assert len(pat["names"]) == 3
    assert pat["field"] == "Kutaisi"
    text = _text(miz)
    groups = _pattern_groups(text)
    assert len(groups) == 3
    for name, body in groups.items():
        # airborne start: a Turning Point first point, never a parking action
        assert "From Parking Area" not in body, f"{name} started on the ramp"
        assert '"Landing"' in body, f"{name} has no landing waypoint"


def test_landing_traffic_is_on_the_extended_centreline(tmp_path):
    """Geometry check without DCS: the spawn point must sit on the approach
    side of the runway, not the departure side, or the AI flies a 180 first."""
    import random
    from dcs.terrain.caucasus import Caucasus
    from missiongen import pattern
    ap = next(a for a in Caucasus().airport_list() if a.name == "Kutaisi")
    hdg = ap.runways[0].heading
    approach = ap.position.point_from_heading((hdg + 180) % 360, pattern.FIRST_FINAL)
    depart = ap.position.point_from_heading(hdg, pattern.FIRST_FINAL)
    # the module's own first-aircraft position
    spawn = ap.position.point_from_heading((hdg + 180) % 360,
                                           pattern.FIRST_FINAL + 0 * pattern.TRAIL_SPACING)
    assert spawn.distance_to_point(approach) < 1.0
    assert spawn.distance_to_point(depart) > pattern.FIRST_FINAL


def test_spawn_altitude_clears_the_field(tmp_path):
    """Field elevation comes from a parking stand; a fixed MSL number would
    bury traffic underground at a high-elevation base."""
    from dcs.terrain.caucasus import Caucasus
    from missiongen import pattern
    for name in ("Kutaisi", "Mineralnye Vody"):
        ap = next(a for a in Caucasus().airport_list() if a.name == name)
        elev = pattern._field_elevation(ap)
        assert elev >= 0
        # every aircraft in the stream sits above the field, never in it
        for slot in range(pattern.MAX_COUNT):
            dist = pattern.FIRST_FINAL + slot * pattern.TRAIL_SPACING
            assert pattern._approach_agl(dist) >= pattern.MIN_APPROACH_AGL


def test_approach_profile_descends_and_stacks(tmp_path):
    """The stream must step DOWN toward the runway (no diving at the threshold)
    and each trailing aircraft must sit ABOVE the one in front of it."""
    from missiongen import pattern
    alts = [pattern._approach_agl(pattern.FIRST_FINAL + s * pattern.TRAIL_SPACING)
            for s in range(pattern.MAX_COUNT)]
    gate = pattern._approach_agl(pattern.SHORT_FINAL)
    assert gate < alts[0], "gate waypoint is not below the lead's spawn"
    assert alts == sorted(alts), f"trailing aircraft are not stacked: {alts}"
    # the descent from the gate to the runway is a sane angle, not a dive
    assert gate / pattern.SHORT_FINAL <= 0.09
    # helicopters run the pattern low and flat
    assert (pattern._approach_agl(pattern.FIRST_FINAL, helo=True)
            < pattern._approach_agl(pattern.FIRST_FINAL))
    assert pattern._approach_agl(999999) == pattern.MAX_APPROACH_AGL
    assert pattern._approach_agl(1, helo=True) == pattern.MIN_HELO_AGL


# --- takeoff leg ------------------------------------------------------------

def test_takeoff_traffic_starts_at_parking(tmp_path):
    miz, res = _gen(tmp_path, bb_pattern=True, pattern_mode="takeoff",
                    pattern_kind="fighter", pattern_count=2,
                    home_airbase="Kutaisi")
    assert len(res["stats"]["pattern"]["names"]) == 2
    groups = _pattern_groups(_text(miz))
    assert len(groups) == 2
    for name, body in groups.items():
        assert "From Parking Area Hot" in body, f"{name} is not a warm start"
        assert '"Landing"' in body, f"{name} never closes the circuit"


def test_both_mixes_the_legs(tmp_path):
    miz, res = _gen(tmp_path, bb_pattern=True, pattern_mode="both",
                    pattern_kind="fighter", pattern_count=4,
                    home_airbase="Kutaisi")
    groups = _pattern_groups(_text(miz))
    ramp = sum(1 for b in groups.values() if "From Parking Area Hot" in b)
    air = len(groups) - ramp
    assert ramp >= 1 and air >= 1, f"'both' produced {ramp} departing / {air} arriving"


# --- type categories are era-correct ----------------------------------------

def test_categories_are_era_gated():
    from missiongen import pattern
    from missiongen.resolver import load_json
    eras = load_json("eras")
    wwii = eras["wwii"]["blue"]
    modern = eras["modern"]["blue"]
    # 1944 has no helicopters at all -> empty category, caller warns + skips
    assert pattern.types_for(wwii, "helicopter") == []
    # fighters exclude the transports that also live in parked_large
    assert "planes.C_130" not in pattern.types_for(modern, "fighter")
    assert "planes.C_130" in pattern.types_for(modern, "cargo")
    assert "planes.F_16C_50" in pattern.types_for(modern, "fighter")
    # WWII fighters are period aircraft, never jets
    assert all("F_16" not in t and "FA_18" not in t
               for t in pattern.types_for(wwii, "fighter"))
    # mixed is the union
    assert set(pattern.types_for(modern, "mixed")) >= set(
        pattern.types_for(modern, "cargo"))


def test_helicopters_in_wwii_warn_instead_of_crashing(tmp_path):
    _, res = _gen(tmp_path, map="normandy", era="wwii", aircraft="P_51D",
                  bb_pattern=True, pattern_mode="takeoff",
                  pattern_kind="helicopter", pattern_count=2)
    assert "pattern" not in res["stats"]
    assert any("helicopter" in w for w in res["warnings"])


# --- recipe validation ------------------------------------------------------

@pytest.mark.parametrize("bad", [
    {"pattern_mode": "orbit"},
    {"pattern_kind": "bomber"},
    {"pattern_count": 0},
    {"pattern_count": 9},
])
def test_bad_pattern_fields_are_rejected(bad):
    from missiongen import Recipe
    from missiongen.recipe import RecipeError
    with pytest.raises(RecipeError):
        Recipe.from_dict({**BASE, "bb_pattern": True, **bad})


# --- determinism ------------------------------------------------------------

def test_same_seed_same_mission(tmp_path):
    a, _ = _gen(tmp_path, "a.miz", bb_pattern=True, pattern_mode="both",
                pattern_kind="mixed", pattern_count=4, home_airbase="Kutaisi")
    b, _ = _gen(tmp_path, "b.miz", bb_pattern=True, pattern_mode="both",
                pattern_kind="mixed", pattern_count=4, home_airbase="Kutaisi")
    assert _text(a) == _text(b)


def test_briefing_mentions_field_activity(tmp_path):
    miz, res = _gen(tmp_path, bb_pattern=True, pattern_mode="landing",
                    pattern_kind="cargo", pattern_count=2,
                    home_airbase="Kutaisi", bb_briefing=True)
    text = _briefing(miz)
    assert "Field activity" in text
    assert "Kutaisi" in text


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
