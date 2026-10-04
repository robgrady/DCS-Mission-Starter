"""One resolved factual context supplies all document renderers."""
from dataclasses import dataclass
from datetime import date
from typing import Mapping
from .build_context import WorldContext
from .historical_world import HistoricalSnapshot
from .phases.carrier import CarrierPlacement

@dataclass(frozen=True)
class MissionFacts:
    mission_date: date
    historical: HistoricalSnapshot
    start_clock: int
    home: object
    comms: object
    route: list | None
    timing: dict | None
    fuel_max_kg: float | None
    brief_context: dict
    kneeboard_context: dict


def document_facts(builder, ctx: WorldContext, home, carrier: CarrierPlacement,
                   gfx: dict, midpoint, nav_pts: list) -> MissionFacts:
    self = builder
    r = builder.recipe
    map_cfg, era_cfg = ctx.map_cfg, ctx.era_cfg
    comms = ctx.comms
    stats = ctx.stats
    own_fields, enemy_fields = ctx.own_fields, ctx.enemy_fields
    carrier_home = ctx.carrier_home
    csg = carrier.group
    brief_context = {
        "gfx": gfx, "stats": stats, "recipe": r,
        "map_label": map_cfg["label"], "era_label": era_cfg["label"],
        "era_year": ctx.mission.start_time.year, "mission_date": ctx.mission.start_time.date(), "home": home,
        "carrier_home": carrier_home,
    }
    # context the kneeboard renderer needs after save
    kneeboard_context = {
        "comms": comms, "own_fields": own_fields, "enemy_fields": enemy_fields,
        "bullseye": {"x": midpoint.x, "y": midpoint.y},
        "map_label": map_cfg["label"], "era_label": era_cfg["label"],
        "era_year": ctx.mission.start_time.year, "map_key": r.map,
        "home_name": (csg.units[0].name if carrier_home and csg else home.name),
        "support_names": stats["support"],
        "nav_points": [(n, p) for n, p, _t, _note in nav_pts],
        "qnh_hpa": getattr(self, "_qnh_hpa", None),
        # D-4: the in-jet theater page now carries the SAME threat picture
        # as the PDF chart (it used to omit threats entirely — the one
        # place you'd want them). Targets ride along for the aim point.
        "threats": gfx.get("threats", []),
        "targets": gfx.get("targets", []),
        # JOKER/BINGO planning defaults: internal fuel from the pydcs
        # airframe (kg). None = the documents keep blank boxes.
        "fuel_max_kg": self._player_fuel_kg(),
        # what the bandits are CARRYING — briefed, not just correct
        "enemy_air": stats.get("enemy_air") or [],
        # The generated ride card, paginated onto kneeboard pages. Read
        # off `self` because the card is built above and this dict below.
        "card": getattr(self, "_wk_card", None),
        "card_title": getattr(self, "_wk_card_title", None),
        "diagram": getattr(self, "_wk_diagram", None),
        "diagram_caption": getattr(self, "_wk_diagram_cap", None),
        # Auto flight plan (bb_route / a "route": "strike" card). Absent on
        # every other mission, which is what keeps the kneeboard at its
        # three reference pages by default.
        "route": stats.get("route_legs"),
        "route_target": stats.get("route_target"),
        # The clock column on the flight-plan page (timing.py).
        "timing": stats.get("timing"),
        # The NTTR corridor chart page (nttr_chart.py) when the plan flew
        # the corridors.
        "nttr_plan": getattr(self, "_nttr", None),
        # What is on YOUR pylons. Absent when `player_arm` is off, which is
        # correct: a clean jet needs no stores card.
        "pylons": stats.get("player_pylons"),
        "loadout_label": stats.get("player_loadout"),
        "loadout_role": stats.get("player_loadout_role"),
        "aircraft_id": getattr(self._resolve_aircraft(r.aircraft), "id",
                               r.aircraft),
    }
    from .historical_world import brief_lines
    from .historical_library import reference_lines
    kneeboard_context['historical_notes'] = (brief_lines(ctx.historical)
        + reference_lines(stats.get('historical_references', []))
        + list(stats.get('airspace_notes', [])))
    return MissionFacts(ctx.mission.start_time.date(), ctx.historical, ctx.mission.start_time.hour * 3600
                        + ctx.mission.start_time.minute * 60 + ctx.mission.start_time.second,
                        home, comms, stats.get('route_legs'), stats.get('timing'),
                        kneeboard_context['fuel_max_kg'], brief_context, kneeboard_context)
