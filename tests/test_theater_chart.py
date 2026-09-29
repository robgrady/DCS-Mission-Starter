"""The theater chart's land/water base.

ROB: "When I download the map for a persian gulf mission thats been generated,
the map is reversed with blue being land and water being brown."

He was right and it was not a color swap — the POLYGON was wrong. The chart
starts as a tan land plate, floods `coastlines.json`'s `water` rings, then
draws `islands` back on top. Persian Gulf's water ring traced the Arabian
shore, jumped to three box corners at (22,64) (30,64) (30,48), then traced the
Iranian coast — and that box edge across latitude 30 swept the whole of Iran
into the flood. Measured on the rendered page: **67.9% of the chart base was
sea**. Iran and inland UAE were painted water; the Gulf of Oman and the Strait
of Hormuz were painted land. Reversed, exactly as reported.

Re-authored as one simple ring — Arabian shore west to east and around
Musandam, down the Oman coast, out into the Arabian Sea, back along the
Makran and Iranian coasts to the head of the Gulf, then down the Saudi coast
to close — plus an island polygon for each of the seven island airfields that
had none. The same pass fixed five marginal cases on Syria (Cyprus's Akrotiri
peninsula, the Lebanese coast at Wujah Al Hajar, Gazipasa on the Turkish
shore). Persian Gulf now renders 31.4% water; Syria moved 26.4% -> 25.6%,
which is the measurement that says Syria was only ever marginally off.

THE GUARDS ARE DERIVED, NOT LISTED. Every airfield this product actually
stations aircraft at — read out of the presets and lineups in `maps.json` —
must land on land. That is exhaustive over what we ship and it cannot drift
when a preset gains a field.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

from missiongen.resolver import load_json                      # noqa: E402

COAST = json.loads((ROOT / "missiongen" / "data" / "coastlines.json").read_text())
CHARTED = [k for k in COAST if not k.startswith("_")]


def _inside(poly, lat, lon):
    """Even-odd ray cast — the same winding-agnostic rule PIL's polygon fill
    uses, so this answers the question the renderer will answer."""
    n = len(poly)
    c = False
    j = n - 1
    for i in range(n):
        yi, xi = poly[i]
        yj, xj = poly[j]
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi):
            c = not c
        j = i
    return c


def _is_water(map_key, lat, lon):
    c = COAST[map_key]
    return (any(_inside(p, lat, lon) for p in c.get("water", []))
            and not any(_inside(p, lat, lon) for p in c.get("islands", [])))


def _preset_fields(map_key):
    """Every airfield name the product can station aircraft at on this map."""
    cfg = load_json("maps")[map_key]
    names = set()
    for pr in cfg["presets"].values():
        names |= set(pr.get("blue_airbases", []))
        names |= set(pr.get("red_airbases", []))
        names |= set(pr.get("civilian_airbases", []))
    for lu in (cfg.get("lineups") or {}).values():
        names |= set(lu.get("blue_airbases", []))
        names |= set(lu.get("red_airbases", []))
    return names


@pytest.mark.parametrize("map_key", CHARTED)
def test_no_airfield_we_use_is_drawn_in_the_sea(map_key):
    """THE EXHAUSTIVE ONE. Nine Persian Gulf fields failed this before the
    fix — seven island airfields with no island polygon (Kish, Lavan, Sirri,
    Abu Musa, both Tunbs, Sir Abu Nuayr) and two coastal fields the shoreline
    cut inland of (Bandar Lengeh, Bandar-e-Jask).

    Scoped to the fields our PRESETS name, deliberately: DCS's own airport
    list includes genuinely offshore helipads on Syria (`H_med_orig_07` sits
    in the Mediterranean and belongs there), so "every airport pydcs knows"
    would be the wrong question."""
    from missiongen.builder import resolve_terrain
    cfg = load_json("maps")[map_key]
    want = _preset_fields(map_key)
    terrain = resolve_terrain(cfg["terrain_class"])()
    seen, wet = set(), []
    for a in list(terrain.airport_list()):
        if a.name not in want:
            continue
        seen.add(a.name)
        ll = a.position.latlng()
        if _is_water(map_key, ll.lat, ll.lng):
            wet.append((a.name, round(ll.lat, 2), round(ll.lng, 2)))
    assert seen, f"{map_key}: no preset field resolved on the terrain"
    assert not wet, f"{map_key}: airfields drawn in open water: {wet}"


PERSIAN_GULF_PROBES = [
    # (name, lat, lon, is_water) — checked against the real geography
    ("the Gulf between Bahrain and Bushehr", 27.50, 51.50, True),
    ("the Strait of Hormuz",                 26.60, 56.45, True),
    ("the Gulf of Oman",                     24.50, 58.50, True),
    ("the head of the Gulf off Kuwait",      29.30, 49.00, True),
    ("open water off Abu Dhabi",             25.00, 53.50, True),
    ("Saudi interior",                       24.70, 46.70, False),
    ("Iran: Shiraz",                         29.60, 52.50, False),
    ("Iran: Kerman",                         29.00, 57.00, False),
    ("Iran: Jiroft",                         28.72, 57.68, False),
    ("Oman interior",                        22.50, 57.00, False),
    ("UAE: Al Ain",                          24.20, 55.70, False),
    ("Qatar: Doha",                          25.28, 51.53, False),
    ("the Musandam peninsula",               26.20, 56.30, False),
]


@pytest.mark.parametrize("name,lat,lon,water", PERSIAN_GULF_PROBES)
def test_the_persian_gulf_knows_its_own_geography(name, lat, lon, water):
    """Named places, checked both ways. Five of these were wrong before the
    fix — and the two halves matter equally: a chart that floods Iran is as
    broken as one that paves the Strait of Hormuz."""
    assert _is_water("persiangulf", lat, lon) is water, name


def test_the_islands_sit_in_water_and_carry_their_airfields():
    """An island polygon drawn over land is a tan blob on a tan plate — it
    proves nothing and hides a real error. Every island must be surrounded by
    the water ring, and the seven island airfields must sit on one."""
    c = COAST["persiangulf"]
    for i, isl in enumerate(c["islands"]):
        clat = sum(p[0] for p in isl) / len(isl)
        clon = sum(p[1] for p in isl) / len(isl)
        assert any(_inside(p, clat, clon) for p in c["water"]), \
            f"island {i} at {clat:.2f},{clon:.2f} is not in the sea"
    for nm, lat, lon in [("Kish", 26.53, 53.98), ("Lavan", 26.81, 53.35),
                         ("Sirri", 25.91, 54.54), ("Abu Musa", 25.88, 55.03),
                         ("Greater Tunb", 26.26, 55.32),
                         ("Lesser Tunb", 26.24, 55.15),
                         ("Sir Abu Nuayr", 25.22, 54.23),
                         ("Qeshm", 26.75, 55.90)]:
        assert any(_inside(p, lat, lon) for p in c["islands"]), \
            f"{nm} has no island under it"


@pytest.mark.parametrize("map_key,lo,hi", [("persiangulf", 15, 50),
                                           ("syria", 12, 45)])
def test_the_rendered_chart_is_not_mostly_sea(map_key, lo, hi):
    """READ OFF THE RENDERED PAGE, not the data — because the data being
    right and the page being right are two claims.

    The base plate is only ever TAN or WATER, and only inside the panel, so
    the ratio over the whole image needs no copy of the projection to compute
    (a second copy of that arithmetic is exactly the twin-function shape that
    has cost this codebase two live defects). Measured: Persian Gulf was
    67.9% sea with the broken ring and is 31.4% with the fixed one; Syria
    moved 26.4% -> 25.6%. The band brackets the truth with room either side
    and still fails hard on an inversion."""
    import tempfile
    import missiongen.brief as B
    from missiongen import generate
    from missiongen.recipe import Recipe

    cap = {}
    orig = B.page_theater_chart

    def spy(ctx):
        img = orig(ctx)
        cap["img"] = img
        return img

    B.page_theater_chart = spy
    try:
        r = Recipe.from_dict(dict(map=map_key, era="modern",
                                  aircraft="F_16C_50", seed=42,
                                  bb_targets=True)).validate()
        d = tempfile.mkdtemp()
        generate(r, str(Path(d) / "t.miz"), brief_dir=d)
    finally:
        B.page_theater_chart = orig

    img = cap.get("img")
    assert img is not None, "the chart page was never drawn"
    px = img.convert("RGB").load()
    W, H = img.size
    tan = wet = 0
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            c = px[x, y]
            if c == B.TAN:
                tan += 1
            elif c == B.WATER:
                wet += 1
    assert tan and wet, f"{map_key}: chart has no land/water base at all"
    pct = wet / (wet + tan) * 100
    assert lo <= pct <= hi, f"{map_key}: {pct:.1f}% of the chart base is sea"
