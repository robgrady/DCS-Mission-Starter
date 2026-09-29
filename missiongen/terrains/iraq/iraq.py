"""DCS Iraq terrain.

VENDORED FROM pydcs, with ONE adaptation (marked ADAPTED below).

  Source:  https://github.com/dcs-retribution/pydcs
  Commit:  3a79b8edf923042a5b933feb64543da9e6bdfd37 (2026-07-25)
  License: LGPL-3.0 — the same license as vendor/dcs, whose COPYING.LESSER
           and COPYING apply to this package too.

Why it lives here and not in vendor/dcs: our vendored pydcs is a byte-for-byte
mirror of the pydcs/dcs upstream, whose last release predates the Iraq map.
Rather than swap the whole engine to get one terrain — which would also replace
airport data we have hand-measured 9,550 parking headings against — we lift the
terrain package alone. It is self-contained: everything it imports
(Terrain, Airport, ParkingSlot, MapView, TransverseMercator, AtcRadio, beacons)
already exists in our pydcs.

The one adaptation: our pydcs's `Terrain.__init__` takes a required
`utc_offset`; the fork's does not (the two diverged on that signature). Iraq
observes Arabia Standard Time, UTC+3, with no daylight saving. Supplying it is
the whole of the change — the airport data, the projection and every other line
are byte-for-byte upstream.

The same pattern as missiongen/terrains/afghanistan, and the reasoning is in
docs/pydcs-plan-critique.md.
"""
import datetime
from dcs import mapping
from dcs.terrain import Terrain, MapView
from .airports import ALL_AIRPORTS
from .projection import PARAMETERS


class Iraq(Terrain):
    center = {"lat": 30.76, "long": 59.07}
    temperature = [
        (5, 16),
        (6, 19),
        (10, 24),
        (16, 30),
        (21, 37),
        (25, 42),
        (27, 45),
        (26, 44),
        (22, 40),
        (17, 34),
        (10, 24),
        (6, 18),
    ]
    assert len(temperature) == 12

    def __init__(self):
        bounds = mapping.Rectangle(440000.0, -500000.0, -950000.0, 850000.0, self)
        super().__init__(
            "Iraq",
            PARAMETERS,
            bounds=bounds,
            map_view_default=MapView(bounds.center(), self, 1000000),
            # ADAPTED: our pydcs requires utc_offset, the fork's does not.
            # Iraq is Arabia Standard Time (UTC+3), no daylight saving.
            utc_offset=datetime.timezone(datetime.timedelta(hours=3)),
        )
        self.bullseye_blue = {"x": 0, "y": 0}
        self.bullseye_red = {"x": 0, "y": 0}

        self.airports = {a.name: a(self) for a in ALL_AIRPORTS}
