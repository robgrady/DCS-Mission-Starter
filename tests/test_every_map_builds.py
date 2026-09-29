"""Every map we advertise must actually build a mission.

Found while adding Iraq (v1.67.0): **nothing in the suite built every map.**
The map-level tests all pin one theater — Nevada for ramp heavies, Syria for
alignment — so a newly added map, or a map broken by a terrain change, would
have shipped with no test saying otherwise. Iraq was verified by hand, which is
not a guard.

This is the cheapest possible statement of the product's core promise: the map
list in `/api/options` is a list of maps you can fly. One seed per map/era, so
it costs about as much as the docs build and names the theater in the failure.
"""
import os
import tempfile
import zipfile

import pytest

from missiongen import Recipe, generate
from missiongen.resolver import load_json

MAPS = load_json("maps")
ERA_AIRCRAFT = {"wwii": "P_51D", "coldwar": "F_5E_3", "modern": "F_16C_50",
                "gwot": "A_10C_2"}

CASES = [(mk, era) for mk, cfg in MAPS.items() if not mk.startswith("_")
         for era in cfg.get("presets", {})]


@pytest.mark.parametrize("map_key,era", CASES,
                         ids=[f"{m}-{e}" for m, e in CASES])
def test_the_map_builds_a_flyable_mission(map_key, era):
    rc = dict(map=map_key, era=era, aircraft=ERA_AIRCRAFT[era],
              coalition="blue", slots=1, seed=7)
    out = os.path.join(tempfile.mkdtemp(), f"{map_key}_{era}.miz")
    generate(Recipe.from_dict(rc), out)
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert "mission" in names, f"{map_key}/{era}: no mission file in the .miz"
        # a mission with no briefing dictionary is one DCS will open blank
        assert any("dictionary" in n for n in names), \
            f"{map_key}/{era}: no l10n dictionary — the briefing would be empty"
        assert z.getinfo("mission").file_size > 20_000, \
            f"{map_key}/{era}: suspiciously small mission file"


@pytest.mark.parametrize("map_key", sorted(m for m in MAPS if not m.startswith("_")))
def test_every_preset_airbase_exists_on_the_terrain(map_key):
    """A preset naming an airbase the terrain does not have degrades silently:
    the builder warns and carries on with fewer fields, so the mission still
    generates and the map is quietly smaller than advertised."""
    from missiongen.resolver import resolve_terrain
    cfg = MAPS[map_key]
    terrain = resolve_terrain(cfg["terrain_class"])()
    have = {a.name for a in terrain.airport_list()}
    bad = {}
    for era, preset in cfg.get("presets", {}).items():
        named = (set(preset.get("blue_airbases", []))
                 | set(preset.get("red_airbases", []))
                 | set(preset.get("civilian_airbases", [])))
        missing = sorted(named - have)
        if missing:
            bad[era] = missing
    assert not bad, f"{map_key}: presets name airbases the terrain lacks: {bad}"


@pytest.mark.parametrize("map_key", sorted(m for m in MAPS if not m.startswith("_")))
def test_both_sides_have_somewhere_to_fly_from(map_key):
    """The builder raises if either side has no field; catching it here names
    the map instead of surfacing as a generation error in someone's browser."""
    for era, preset in MAPS[map_key].get("presets", {}).items():
        assert preset.get("blue_airbases"), f"{map_key}/{era}: no blue airbases"
        assert preset.get("red_airbases"), f"{map_key}/{era}: no red airbases"
        assert preset.get("blue_country") and preset.get("red_country"), \
            f"{map_key}/{era}: a side has no country"
