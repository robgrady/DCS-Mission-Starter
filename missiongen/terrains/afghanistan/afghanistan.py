"""DCS Afghanistan terrain — generated from a real install export (standlist.lua,
2026-07-22, via pydcs tools/airport_import.py; 25 airports incl. Bagram,
Kandahar, Kabul, Camp Bastion, Jalalabad, FOB Salerno). Projection is
provisional until the Part B probe (see projection.py)."""
import datetime

import dcs.mapping as mapping
from dcs.terrain.terrain import Terrain, MapView

from .airports import ALL_AIRPORTS
from .projection import PARAMETERS


class Afghanistan(Terrain):
    center = {"lat": 33.0, "long": 66.0}
    # Kabul-ish continental climate: (min, max) °C per month
    temperature = [
        (-7, 5), (-5, 7), (1, 13), (6, 19), (9, 25), (13, 31),
        (16, 33), (15, 32), (10, 28), (5, 21), (0, 13), (-4, 7)
    ]
    assert len(temperature) == 12

    def __init__(self):
        # airport extents are x -334..218 km / y -390..390 km; pad ~100 km
        bounds = mapping.Rectangle(-440000, -490000, 320000, 490000, self)
        super().__init__(
            "Afghanistan",
            PARAMETERS,
            bounds,
            map_view_default=MapView(bounds.center(), self, 1000000),
            utc_offset=datetime.timezone(datetime.timedelta(hours=4, minutes=30)),
        )
        self.bullseye_blue = {"x": 0, "y": 0}
        self.bullseye_red = {"x": 0, "y": 0}
        self.airports = {a.name: a(self) for a in ALL_AIRPORTS}

    @property
    def miz_theatre_name(self) -> str:
        return "Afghanistan"
