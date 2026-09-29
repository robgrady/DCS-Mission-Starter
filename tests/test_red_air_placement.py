"""Where the enemy's airplanes are when the mission starts.

ROB: "let's not add a single random red aircraft at the beginning of a mission
in the blue area."

`add_enemy_cap` stationed each flight at `rng.uniform(0.40, 0.65)` of the way
from the friendly center to the enemy center. Measured over 2,000 seeds, that
band put the station on the BLUE side of the midpoint **42% of the time** — a
coin-flip, not an edge case, and on a Persian Gulf mission it meant a red
two-ship orbiting nearer the player's own airfields than the enemy's before he
had released brakes. The band is 0.55-0.80 now: past the midpoint by enough
that the racetrack and the lateral jitter (both PERPENDICULAR to the axis, so
neither moves the fraction) leave the station in the half it defends, and short
of the enemy fields themselves where the airbase SAMs already live. They still
come to meet you — `max_engage_distance` is 55 km — but they come from their
own side.

TWO DEFINITIONS, BECAUSE THERE ARE TWO KINDS OF RED AEROPLANE, and one rule
would be wrong for one of them:

  * AIRBORNE red aircraft are the contacts a pilot sees at mission start.
    They must station nearer the enemy centroid than the friendly one.
  * GROUND-STARTED red aircraft (ambient transports) are parked. Centroid
    distance is the wrong question for them — a red field at one end of a
    long coast can be nearer the blue centroid than the red one purely by
    the geometry of averaging. What matters is whose airfield they are on.
"""
import math
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

from missiongen import generate                                # noqa: E402
from missiongen.recipe import Recipe                           # noqa: E402

# Two theaters with very different shapes: the Gulf is a long narrow water gap
# with both sides strung along facing coasts (where the old band bit hardest),
# Caucasus is a broad land front.
CASES = [("persiangulf", "modern", s) for s in (42, 3, 55, 900, 7)] + \
        [("caucasus", "modern", s) for s in (11, 23)]


def _built(map_key, era, seed):
    r = Recipe.from_dict(dict(map=map_key, era=era, aircraft="F_16C_50",
                              seed=seed, bb_targets=True,
                              bb_ambient=True)).validate()
    out = Path(tempfile.mkdtemp()) / "t.miz"
    generate(r, str(out))
    import dcs
    m = dcs.Mission()
    m.load_file(str(out))
    return m


def _centres(m):
    blue = [a for a in m.terrain.airport_list() if a.is_blue()]
    red = [a for a in m.terrain.airport_list() if a.is_red()]
    assert blue and red
    c = lambda fs: (sum(a.position.x for a in fs) / len(fs),      # noqa: E731
                    sum(a.position.y for a in fs) / len(fs))
    return c(blue), c(red)


def _red_groups(m):
    return [g for c in m.coalition["red"].countries.values()
            for g in c.plane_group]


def _airborne(g):
    """A flight created inflight has a Turning Point first; a ground start has
    a TakeOff* point."""
    return bool(g.points) and not str(g.points[0].type).startswith("TakeOff")


@pytest.mark.parametrize("map_key,era,seed", CASES)
def test_no_airborne_red_flight_starts_on_the_friendly_side(map_key, era, seed):
    """THE BUG ROB FLEW INTO. Read out of the built mission, not out of the
    roll: every airborne red flight must be nearer the enemy centroid than the
    friendly one."""
    m = _built(map_key, era, seed)
    bc, rc = _centres(m)
    wrong = []
    for g in _red_groups(m):
        if not _airborne(g):
            continue
        p = g.units[0].position
        db = math.dist((p.x, p.y), bc)
        dr = math.dist((p.x, p.y), rc)
        if db < dr:
            wrong.append((g.name, round(db / 1852), round(dr / 1852)))
    assert not wrong, \
        f"{map_key}/{seed}: red air on the blue side (NM from blue, red): {wrong}"


@pytest.mark.parametrize("map_key,era,seed", CASES)
def test_no_red_aircraft_is_parked_on_a_friendly_airfield(map_key, era, seed):
    """The other half, and the one that would look worst from the ramp: a red
    transport starting up on the field the player is sitting on."""
    m = _built(map_key, era, seed)
    blue_fields = [a for a in m.terrain.airport_list() if a.is_blue()]
    wrong = []
    for g in _red_groups(m):
        if _airborne(g):
            continue
        p = g.units[0].position
        near = min(blue_fields,
                   key=lambda a: math.dist((a.position.x, a.position.y),
                                           (p.x, p.y)))
        d = math.dist((near.position.x, near.position.y), (p.x, p.y))
        if d < 3000:
            wrong.append((g.name, near.name, round(d)))
    assert not wrong, f"{map_key}/{seed}: red aircraft on a blue field: {wrong}"


def test_the_cap_station_band_stays_in_the_enemy_half():
    """The band itself, asserted where it is written. `frac` is the only thing
    that decides which half a CAP stations in, so the guard that survives a
    refactor of the geometry is the one on the number: it must not reach the
    midpoint. Reading the source is deliberate — the constant has no accessor,
    and inventing one for a test would be a second place for it to live."""
    import re
    src = (ROOT / "missiongen" / "threats.py").read_text()
    # SCOPED TO add_enemy_cap. `threats.py` has three `frac = rng.uniform(...)`
    # rolls — the other two are the SAM and AAA belts' no-enemy-airfield
    # fallbacks, which place GROUND units and are a different question. An
    # unscoped regex here read the first of them (0.25) and failed on code it
    # was never aimed at.
    i = src.index("def add_enemy_cap(")
    j = src.index("\ndef ", i)
    m = re.search(r"frac = rng\.uniform\(([\d.]+), ([\d.]+)\)", src[i:j])
    assert m, "the CAP station band is gone from add_enemy_cap"
    lo, hi = float(m.group(1)), float(m.group(2))
    assert lo > 0.5, f"a CAP can station on the friendly side (low end {lo})"
    assert hi <= 0.85, f"a CAP stations on top of the enemy fields (high end {hi})"


def test_the_enemy_cap_is_still_actually_placed():
    """The cheapest way to pass every guard above is to stop making enemy air
    at all. At maximum intensity there must be a CAP."""
    m = _built("persiangulf", "modern", 42)
    airborne = [g for g in _red_groups(m) if _airborne(g)]
    assert airborne, "no airborne red air anywhere in the mission"
