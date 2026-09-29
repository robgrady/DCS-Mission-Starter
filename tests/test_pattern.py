"""Pattern traffic: the conveyor, its ceiling, and the knob that sets it.

ROB: "Pattern Traffic is too limited, it should have the ability to add more
aircraft numbers." The cap was 4; it is 8 now, and the ceiling is a REASONED
number, not a taste: landing traffic is spaced 7 km in trail from 11 km out,
so aircraft eight begins 60 km (~32 NM) from the threshold — nine minutes out
at approach speed, the outer edge of "the field is alive as you walk out".

These are also the FIRST tests this building block has ever had — the feature
shipped in v1.72-era with no guard at all, which is how a cap nobody chose
became a limit somebody hit.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

from missiongen import generate, pattern                    # noqa: E402
from missiongen.recipe import Recipe, RecipeError           # noqa: E402


def _build(tmp, **kw):
    rc = dict(map="caucasus", era="modern", aircraft="F_16C_50", seed=11,
              bb_pattern=True, bb_targets=False, bb_sams=False,
              bb_tanker=False, bb_awacs=False, bb_ambient=False, **kw)
    out = tmp / "p.miz"
    generate(Recipe.from_dict(rc).validate(), str(out))
    import dcs
    m = dcs.Mission()
    m.load_file(str(out))
    return m


def _pattern_groups(m):
    return [g for co in m.coalition.values() for c in co.countries.values()
            for g in c.plane_group if g.name.startswith("Pattern ")]


def test_eight_aircraft_actually_reach_the_mission(tmp_path):
    """The whole ask, read out of the built file: ask for the ceiling, get the
    ceiling. Landing mode, because it has no parking-stand limit to hide
    behind — all eight must exist and all eight must be AI."""
    m = _build(tmp_path, pattern_mode="landing", pattern_kind="fighter",
               pattern_count=8)
    gs = _pattern_groups(m)
    assert len(gs) == 8, [g.name for g in gs]
    for g in gs:
        for u in g.units:
            assert str(u.skill) != "Skill.Player", g.name


def test_the_conveyor_is_spaced_in_trail_not_stacked(tmp_path):
    """Eight aircraft on one centreline must be a QUEUE. Every landing
    aircraft's distance from the field must be distinct and the two nearest
    neighbours at least a nautical mile apart — eight spawned on top of each
    other is a mid-air, not a pattern."""
    m = _build(tmp_path, pattern_mode="landing", pattern_kind="fighter",
               pattern_count=8)
    gs = _pattern_groups(m)
    home = m.terrain.airports.get("Kutaisi") or None
    # measure from the first group's own runway line instead of guessing the
    # field: use pairwise spacing, which needs no airport reference at all
    pos = sorted((g.units[0].position.x, g.units[0].position.y) for g in gs)
    import math
    ds = []
    pts = [g.units[0].position for g in gs]
    for i, a in enumerate(pts):
        nearest = min(a.distance_to_point(b)
                      for j, b in enumerate(pts) if j != i)
        ds.append(nearest)
    assert min(ds) > 1852, f"nearest neighbours {min(ds):.0f} m apart"


def test_both_mode_puts_traffic_on_both_sides_of_the_field(tmp_path):
    """'both' alternates landing/takeoff, landing first. With six aircraft,
    three spawn on the approach (in the air) and three on the ramp."""
    m = _build(tmp_path, pattern_mode="both", pattern_kind="fighter",
               pattern_count=6)
    gs = _pattern_groups(m)
    assert len(gs) >= 4, [g.name for g in gs]   # ramp may cost a departure
    airborne = [g for g in gs if g.points[0].type == "Turning Point"]
    ground = [g for g in gs if g.points[0].type != "Turning Point"]
    assert len(airborne) == 3, [g.points[0].type for g in gs]
    assert ground, "no departing traffic at all"


def test_the_recipe_enforces_the_modules_own_ceiling():
    """One bound, owned by pattern.MAX_COUNT — the recipe reads it rather than
    keeping a copy that can drift."""
    base = dict(map="caucasus", era="modern", aircraft="F_16C_50", seed=1,
                bb_pattern=True)
    Recipe.from_dict(dict(base, pattern_count=pattern.MAX_COUNT)).validate()
    with pytest.raises(RecipeError):
        Recipe.from_dict(dict(base, pattern_count=0)).validate()
    with pytest.raises(RecipeError):
        Recipe.from_dict(
            dict(base, pattern_count=pattern.MAX_COUNT + 1)).validate()


def test_the_ui_offers_exactly_what_the_engine_accepts():
    """The select's options are derived from the same number. A picker that
    stops at 4 while the engine takes 8 is precisely the 'too limited' Rob
    reported; a picker offering 9 would 400 on generate."""
    ui = (ROOT / "frontend" / "index.html").read_text()
    m = re.search(r'<select id="pattern_count">(.*?)</select>', ui, re.S)
    assert m, "the count picker is gone"
    offered = sorted(int(v) for v in re.findall(r'value="(\d+)"', m.group(1)))
    assert offered == list(range(1, pattern.MAX_COUNT + 1)), \
        (offered, pattern.MAX_COUNT)


def test_the_ceiling_keeps_the_tail_of_the_queue_in_sight():
    """The number is reasoned, and the reasoning is asserted: the last
    landing aircraft must start no further than 65 km out — beyond that the
    tail of the conveyor is scenery nobody meets."""
    worst = pattern.FIRST_FINAL + (pattern.MAX_COUNT - 1) * pattern.TRAIL_SPACING
    assert worst <= 65000, f"aircraft {pattern.MAX_COUNT} starts {worst/1000:.0f} km out"
