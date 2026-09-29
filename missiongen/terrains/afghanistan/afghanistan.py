"""DCS Afghanistan terrain.

VENDORED FROM pydcs, with ONE adaptation (marked ADAPTED below).

  Source:  https://github.com/dcs-retribution/pydcs
  Commit:  3a79b8edf923042a5b933feb64543da9e6bdfd37 (2026-07-25)
  License: LGPL-3.0 — the same license as vendor/dcs, whose COPYING.LESSER
           and COPYING apply to this package too.

This REPLACES the hand-built Afghanistan we shipped from v1.31.0 to v1.67.0:
4,602 lines produced by running pydcs' importer against our own standlist.lua
export, with a projection our own source marked *provisional*. The official
export is the same data with a longer paper trail, so we take theirs.

What actually changed, measured airport-by-airport (25 of ours, 26 of theirs):

  * **Nothing was lost.** Every airport we had is present; every parking slot
    we had is present under the same name. That matters because
    `data/parking_headings.json` carries 460 hand-measured Afghanistan slot
    headings keyed by (field, slot name), and `tests/test_parking_headings.py`
    fails if any measured slot stops existing. It passes across the swap.
  * **Zaranj** is new — a 26th airfield in the south-west, on the Iranian
    border, which our export missed entirely.
  * **Khost** gains three stands (13, 14, 15).
  * **Stands got wider, never narrower**: Ghazni Heliport 17 -> 23 m (8 pads),
    Khost 22 -> 24 m (7), Shindand 24 -> 41 m (6). Widening is the safe
    direction — it can only let *more* airframes park, and `builder`'s new
    narrowest-stand-first sort is unaffected because no stand shrank.
  * **Positions move by metres, not kilometres**: 6 Bagram slots by <= 6 m,
    12 Shindand slots by <= 21 m, and Ghazni Heliport's airport reference
    point by 122 m. Ramp dressing is placed relative to the slot, so these are
    invisible in the sim.
  * `center` becomes the surveyed 33.9346N 66.24705E instead of our round-number
    33/66, and `bounds` is corrected — ours had top and bottom transposed
    (top=-440 km, bottom=+320 km), which pydcs uses only for the default map
    view, so the bug was never visible.
  * The **projection is the same projection**. Ours, derived from an in-sim
    probe, agreed to 2.3e-5 m of false easting and 3.8e-5 m of false northing,
    with an identical central meridian and scale factor. Our "provisional"
    label was over-cautious rather than wrong.
  * The `temperature` table is theirs verbatim, INCLUDING an oddity: June's
    minimum (23 C) is warmer than July's (18 C). We have deliberately not
    hand-smoothed it. The point of taking an export is to take the export; a
    silent local "fix" is how a vendored file stops being vendored. It feeds
    only `random_season_temperature`, i.e. the .miz season block.

The one adaptation: our pydcs's `Terrain.__init__` takes a required
`utc_offset`; the fork's does not (the two libraries diverged on that
signature, and ours is the side that has it). Afghanistan Time is UTC+4:30,
year-round, with no daylight saving. Supplying it is the whole delta.
"""
import datetime

from dcs import mapping
from dcs.terrain import Terrain, MapView
from .airports import ALL_AIRPORTS
from .projection import PARAMETERS


class Afghanistan(Terrain):
    center = {"lat": 33.9346, "long": 66.24705}
    temperature = [
        (-5, 6),
        (-3, 8),
        (2, 14),
        (7, 21),
        (11, 26),
        (23, 31),
        (18, 33),
        (16, 32),
        (11, 28),
        (5, 22),
        (0, 14),
        (-4, 9)
    ]
    assert len(temperature) == 12

    def __init__(self):
        bounds = mapping.Rectangle(532000.0, -534000.0, -512000.0, 757000.0, self)
        super().__init__(
            "Afghanistan",
            PARAMETERS,
            bounds=bounds,
            map_view_default=MapView(bounds.center(), self, 1000000),
            # ADAPTED: not in the fork's copy — its Terrain has no utc_offset.
            # Afghanistan Time, UTC+04:30, no daylight saving.
            utc_offset=datetime.timezone(datetime.timedelta(hours=4, minutes=30)),
        )
        self.bullseye_blue = {"x": 0, "y": 0}
        self.bullseye_red = {"x": 0, "y": 0}

        self.airports = {a.name: a(self) for a in ALL_AIRPORTS}
