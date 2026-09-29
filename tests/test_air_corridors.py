"""Air corridors: the lane has to point somewhere real.

A corridor is two numbers — a compass BEARING from the friendly base centroid
and a REACH in meters. Selecting one moves the mission's enemy focus to that
point, which swings the threat axis, the enemy CAP and the briefing with it.
Two numbers is a small surface, and both ways it can be wrong are silent:

  * the corridor names a map or an era that does not exist, so it never
    appears in the picker and nobody notices. This is exactly the failure
    v1.67.0 found in `parking_headings.json` — 26 measurements keyed to slots
    that had stopped existing. Orphaned data does not throw; it just quietly
    stops being data.
  * the bearing and reach send the enemy focus off the edge of the theater.
    Nothing crashes: the mission builds, the axis points at empty map, and the
    pilot flies toward nothing.

So: every corridor must resolve, and every corridor's focus must land over the
theater. Then, for the map that has the most of them, the lane actually drawn
on the F10 map must run down the bearing the data claims.
"""
import math

import pytest
from dcs import mapping

from missiongen.resolver import load_json, resolve_terrain

CORRIDORS = load_json("air_corridors")
MAPS = load_json("maps")

# Every (map, corridor) pair, flattened, so a failure names the corridor.
ALL = [(mk, c) for mk, cs in CORRIDORS.items() if not mk.startswith("_")
       for c in cs]

# The furthest any shipped corridor puts its focus from the nearest airfield is
# 151.6 km (Afghanistan, "Hindu Kush Passes" — the passes genuinely are that
# empty). 200 km leaves headroom for a legitimately remote lane while still
# catching a bearing that walks off the map, which is off by hundreds.
MAX_KM_FROM_A_FIELD = 200.0


def _terrain(map_key):
    return resolve_terrain(MAPS[map_key]["terrain_class"])()


def _own_center(terrain, map_key, era):
    pts = [terrain.airports[n].position
           for n in MAPS[map_key]["presets"][era]["blue_airbases"]
           if n in terrain.airports]
    return mapping.Point(sum(p.x for p in pts) / len(pts),
                         sum(p.y for p in pts) / len(pts), terrain)


def _focus(terrain, map_key, era, corridor):
    """Where the builder will put the enemy focus — same maths as
    `builder`'s corridor block via `dressing._offset` (x is north, y is east)."""
    o = _own_center(terrain, map_key, era)
    b = math.radians(corridor["bearing"])
    return mapping.Point(o.x + corridor["reach"] * math.cos(b),
                         o.y + corridor["reach"] * math.sin(b), terrain)


@pytest.mark.parametrize("map_key,corr", ALL,
                         ids=[f"{mk}:{c['name']}" for mk, c in ALL])
def test_a_corridor_names_a_map_and_an_era_that_exist(map_key, corr):
    """An orphaned corridor is invisible: it never renders in the picker and
    `builder` filters it out without a warning."""
    assert map_key in MAPS, f"corridor '{corr['name']}' is filed under no map"
    presets = MAPS[map_key]["presets"]
    assert corr["eras"], f"{corr['name']} claims no era"
    for era in corr["eras"]:
        assert era in presets, (
            f"'{corr['name']}' claims era '{era}', which {map_key} does not "
            f"have (it has {sorted(presets)}) — it can never be selected")
    assert 0 <= corr["bearing"] < 360
    assert corr["reach"] > 0
    assert corr["axis"] and corr["enemy"], "both brief lines are shown to the pilot"


@pytest.mark.parametrize("map_key,corr", ALL,
                         ids=[f"{mk}:{c['name']}" for mk, c in ALL])
def test_a_corridor_points_at_the_theater_not_off_the_edge(map_key, corr):
    """The focus must land over the map. Airfields are the proxy for 'over the
    map and over land' — the same bet `threats.add_area_sams` makes, because
    pydcs exposes no land/water query."""
    terrain = _terrain(map_key)
    fields = list(terrain.airport_list())
    for era in corr["eras"]:
        f = _focus(terrain, map_key, era, corr)
        km = min(math.hypot(a.position.x - f.x, a.position.y - f.y)
                 for a in fields) / 1000.0
        assert km <= MAX_KM_FROM_A_FIELD, (
            f"{map_key}/{era} '{corr['name']}': bearing {corr['bearing']}° x "
            f"{corr['reach']/1000:.0f} km puts the enemy focus {km:.0f} km from "
            f"the nearest airfield — that is off the theater")


def test_iraq_ships_corridors_for_both_its_eras():
    """Iraq arrived in v1.67.0 with no corridors at all, which meant the
    Builder's corridor section was empty on the map with the richest air
    history on the shelf."""
    have = {e for c in CORRIDORS["iraq"] for e in c["eras"]}
    assert have == set(MAPS["iraq"]["presets"]), (
        f"Iraq has corridors for {sorted(have)} but presets for "
        f"{sorted(MAPS['iraq']['presets'])}")


@pytest.mark.parametrize("corr", CORRIDORS["iraq"],
                         ids=[c["name"] for c in CORRIDORS["iraq"]])
def test_the_lane_on_the_f10_map_runs_down_the_bearing_the_data_claims(corr, tmp_path):
    """The pilot's evidence, read back out of a real .miz.

    `builder` draws the corridor as a line from the friendly centroid to the
    enemy focus. If the corridor block stops re-anchoring the focus, that line
    reverts to the raw base-to-base bearing and this fails — which is the whole
    point of asserting on the drawing rather than on the JSON."""
    import zipfile
    import dcs.lua as lua
    from missiongen import Recipe, generate

    era = corr["eras"][0]
    rc = dict(map="iraq", era=era, coalition="blue", slots=1, seed=7,
              aircraft="F_16C_50" if era == "modern" else "F_5E_3",
              corridors=[corr["name"]], map_layers=["corridors"])
    path = str(tmp_path / "corr.miz")
    generate(Recipe.from_dict(rc), path)
    with zipfile.ZipFile(path) as z:
        m = lua.loads(z.read("mission").decode("utf-8"))["mission"]

    lines = []
    for layer in m.get("drawings", {}).get("layers", {}).values():
        for o in layer.get("objects", {}).values():
            pts = o.get("points")
            if isinstance(pts, dict) and len(pts) == 2:
                p1, p2 = pts[1], pts[2]
                lines.append((p2["x"] - p1["x"], p2["y"] - p1["y"]))
    assert lines, f"'{corr['name']}' drew no corridor lane on the F10 map"

    want = corr["bearing"]
    best = min(lines, key=lambda d: abs(
        (math.degrees(math.atan2(d[1], d[0])) - want + 180) % 360 - 180))
    got = math.degrees(math.atan2(best[1], best[0])) % 360
    off = abs((got - want + 180) % 360 - 180)
    assert off <= 1.0, (
        f"'{corr['name']}' is briefed as {want}° but the lane on the F10 map "
        f"runs {got:.1f}° — off by {off:.1f}°")
