"""Resolved world state and domain guards for the first generator phase.

Weather and placement retain their original seeded RNG sequence and order.
PyDCS remains the mission model and serializer.
"""
import math
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Callable

import dcs
from dcs import mapping

from .resolver import load_json, resolve_terrain, resolve_country
from .comms import CommsPlan
from .historical_world import HistoricalSnapshot, snapshot

if TYPE_CHECKING:
    from .builder import StarterBuilder

TIME_PRESETS = {"dawn": 5, "day": 12, "dusk": 18, "night": 22}

# CREW-OPS templates own the player flight themselves (backseat/RIO branches).
# SCENARIO templates (mission_templates.json) are lighter: a recipe preset the
# frontend pre-fills + a suggested-tasking briefing block, with a NORMAL player
# flight. Keep the two sets distinct so scenario templates don't skip the flight.
CREW_OPS_TEMPLATES = ("backseat_izlid", "backseat_intercept", "rio_fleet_defense")

# templates are era-gated too. F-14B(U) flag-API missions are modern-only
# (the B(U) upgrade is a mid-90s+ airframe); fleet defense runs on today's
# F-14A (coldwar) / F-14B (modern). Scenario templates carry their own eras.
TEMPLATE_ERAS = {"backseat_izlid": ("modern",),
                 "backseat_intercept": ("modern",),
                 "rio_fleet_defense": ("coldwar", "modern")}


def _scenario_templates():
    try:
        return {k: v for k, v in load_json("mission_templates").items()
                if not k.startswith("_")}
    except Exception:
        return {}


def _template_eras(key):
    """Allowed eras for any template key (crew-ops table or scenario data)."""
    if key in TEMPLATE_ERAS:
        return tuple(TEMPLATE_ERAS[key])
    return tuple(_scenario_templates().get(key, {}).get("eras", ()))


class EraViolation(Exception):
    """Hard era gate: the selection is not plausible for the mission period."""


def aircraft_in_era(aircraft_key: str, era_cfg: dict) -> bool:
    """Service window overlaps era window. Unlisted aircraft pass (data gap, not a block)."""
    service = load_json("aircraft_service").get(aircraft_key)
    window = era_cfg.get("window")
    if not service or not window:
        return True
    frm, to = service
    return frm <= window[1] and (to is None or to >= window[0])


def _bearing(a, b) -> float:
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x)) % 360


def _centroid(points, terrain):
    return mapping.Point(sum(p.x for p in points) / len(points),
                         sum(p.y for p in points) / len(points), terrain)



@dataclass(frozen=True)
class WorldContext:
    """Explicit inputs shared by placement and document phases."""
    map_cfg: dict
    era_cfg: dict
    preset: dict
    terrain: type
    mission: dcs.Mission
    crew_ops: bool
    formation_stage: str | None
    country: Callable[[str, str], object]
    blue_country: object
    red_country: object
    blue_fields: list
    red_fields: list
    own_fields: list
    enemy_fields: list
    own_country: object
    enemy_country: object
    carrier_home: bool
    bb_carrier: bool
    home: object
    own_center: mapping.Point
    enemy_center: mapping.Point
    threat_bearing: float
    away_bearing: float
    comms: CommsPlan
    stats: dict
    historical: HistoricalSnapshot


def prepare_world(builder: "StarterBuilder") -> WorldContext:
    r = builder.recipe
    # --- clear guards BEFORE any lookup (else a bad map/era surfaces as a
    # bare KeyError -> a confusing 400 with just the key name) ------------
    if r.map not in builder.maps:
        raise EraViolation(f"Unknown map '{r.map}'.")
    if r.era not in builder.eras:
        raise EraViolation(f"Unknown era '{r.era}'.")
    map_cfg = builder.maps[r.map]
    era_cfg = builder.eras[r.era]
    if r.era not in map_cfg["presets"]:
        raise EraViolation(f"{map_cfg['label']} has no {r.era} preset")
    preset = map_cfg["presets"][r.era]
    # A NAMED ORDER OF BATTLE, layered over the era's. The era says when;
    # this says who. Merged rather than replacing, so a lineup only has to
    # state what it changes and inherits the map's carrier anchor, civilian
    # fields and themes. `Recipe.validate` has already checked that the
    # lineup exists on this map and covers this era.
    if r.lineup:
        preset = {**preset, **(map_cfg.get("lineups") or {})[r.lineup]}

    crew_ops = r.template in CREW_OPS_TEMPLATES
    formation_stage = getattr(r, "formation", None)
    if not crew_ops and not aircraft_in_era(r.aircraft, era_cfg):
        svc = load_json("aircraft_service").get(r.aircraft)
        raise EraViolation(
            f"{r.aircraft} was not in service during {era_cfg['label']} "
            f"(service {svc[0]}-{svc[1] or 'present'}). Pick a period-correct aircraft.")
    if r.template and r.era not in _template_eras(r.template):
        raise EraViolation(f"Template '{r.template}' is not available in {era_cfg['label']}")

    terrain = resolve_terrain(map_cfg["terrain_class"])
    m = dcs.Mission(terrain())

    # --- time & weather -------------------------------------------------
    m.start_time = datetime(era_cfg["year"], 6, 21, TIME_PRESETS[r.time_of_day], 0)
    builder._mission = m
    builder._apply_weather(m)

    # --- coalitions & airbase ownership ---------------------------------
    def _get_country(name, side):
        """Return the pydcs Country for `name`, GUARANTEED to live in the
        requested coalition. pydcs' default mission pre-sorts many countries
        into fixed coalitions (Germany, UK, USA all default to BLUE). On maps
        where the historical alignment differs — WWII Normandy/Channel put
        Germany on RED — we must MOVE the country, not accept pydcs' default
        side. The old code took whatever side pydcs had it on, so red German
        airfields spawned their aircraft under a blue-coalition Germany."""
        cname = resolve_country(name)().name
        other = "red" if side == "blue" else "blue"
        if cname in m.coalition[other].countries:      # default put it on the wrong side
            c = m.coalition[other].remove_country(cname)
            m.coalition[side].add_country(c)
            return c
        if cname in m.coalition[side].countries:        # already correct
            return m.coalition[side].countries[cname]
        c = resolve_country(name)()                     # in neither (e.g. Japan, Argentina)
        m.coalition[side].add_country(c)
        return c

    blue_country = _get_country(preset["blue_country"], "blue")
    red_country = _get_country(preset["red_country"], "red")

    blue_fields, red_fields = [], []
    for name in preset["blue_airbases"]:
        ap = m.terrain.airports.get(name)
        if ap:
            ap.set_blue()
            blue_fields.append(ap)
        else:
            builder.warnings.append(f"blue airbase '{name}' not found on {r.map}")
    for name in preset["red_airbases"]:
        ap = m.terrain.airports.get(name)
        if ap:
            ap.set_red()
            red_fields.append(ap)
        else:
            builder.warnings.append(f"red airbase '{name}' not found on {r.map}")

    own_fields = blue_fields if r.coalition == "blue" else red_fields
    enemy_fields = red_fields if r.coalition == "blue" else blue_fields
    # every preset airbase failed to resolve (pydcs terrain drift) — fail
    # clearly instead of an opaque IndexError/ZeroDivisionError downstream
    if not own_fields or not enemy_fields:
        raise EraViolation(
            f"No {'friendly' if not own_fields else 'enemy'} airbases resolved "
            f"on {map_cfg['label']} ({r.era}) — the terrain data may have "
            f"changed. This is a data issue, not your selection.")
    own_country = blue_country if r.coalition == "blue" else red_country
    enemy_country = red_country if r.coalition == "blue" else blue_country

    carrier_home = r.home_airbase == "CARRIER"
    builder._carrier_home = carrier_home
    bb_carrier = r.bb_carrier or carrier_home
    # A NAMED HOME FIELD THAT IS NOT ON YOUR SIDE IS AN ERROR, NOT A HINT.
    #
    # This line used to end `, own_fields[0])` — a silent fallback to
    # whatever field happened to be first. Every Proud Phantom ride asks for
    # Cairo West; Sinai's Cold War preset is the 1973 order of battle, where
    # Cairo West is EGYPTIAN and red. So eleven missions sold as "flown from
    # the base they actually deployed to" quietly took off from Hatzor, in
    # Israel, with the 70th TFS registered as an Israeli squadron, to bomb
    # the base they were supposed to be living on. Nothing warned. The
    # fallback was doing exactly what it was written to do.
    #
    # Twenty-two template/map/era combinations named a home field that was
    # not on the player's side when this check was added, and twenty-one of
    # them were this bug. The twenty-second was 'Nellis AFB' on Nevada,
    # where the airfield is called 'Nellis' — dead for however long.
    if r.home_airbase and r.home_airbase != "CARRIER":
        home = next((a for a in own_fields if a.name == r.home_airbase), None)
        if home is None:
            on_map = {a.name for a in m.terrain.airport_list()}
            why = ("is on the other side in this order of battle"
                   if r.home_airbase in {a.name for a in enemy_fields}
                   else ("exists on this map but is in neither side's "
                         "preset" if r.home_airbase in on_map
                         else "is not an airfield on this map"))
            raise EraViolation(
                f"home_airbase {r.home_airbase!r} {why}"
                f"{f' ({r.lineup})' if r.lineup else ''}. Your side holds: "
                f"{', '.join(a.name for a in own_fields)}.")
    else:
        home = own_fields[0]
    own_center = _centroid([a.position for a in own_fields], m.terrain)
    enemy_center = _centroid([a.position for a in enemy_fields], m.terrain)
    # Air Corridors (v2): a selected lane re-anchors the enemy focus down its
    # compass bearing, so the threat axis and the CAP/SAM concentration follow
    # the corridor instead of the raw base-centroid line. No player waypoints.
    builder._corridors = []
    if r.corridors:
        try:
            _corr = load_json("air_corridors").get(r.map, [])
            chosen = [c for c in _corr if c["name"] in r.corridors
                      and r.era in c.get("eras", [])]
            if chosen:
                from .dressing import _offset
                fxs = [_offset(own_center, c["reach"], c["bearing"]) for c in chosen]
                enemy_center = mapping.Point(
                    sum(p.x for p in fxs) / len(fxs),
                    sum(p.y for p in fxs) / len(fxs), m.terrain)
                builder._corridors = chosen
        except Exception as _e:
            builder.warnings.append(f"air corridor apply failed: {_e}")
    threat_bearing = _bearing(own_center, enemy_center)
    away_bearing = (threat_bearing + 180) % 360

    # The pilot's comm table rides in here and nowhere else (commplan.py):
    # every agency below reads its frequency through this object.
    comms = CommsPlan(r.comms)
    stats = {"statics": 0, "sam_sites": [], "support": [], "ambient": []}
    if comms.overrides:
        from . import commplan as _cp
        stats["comms_custom"] = _cp.describe(comms.overrides)


    return WorldContext(
        map_cfg=map_cfg,
        era_cfg=era_cfg,
        preset=preset,
        terrain=terrain,
        mission=m,
        crew_ops=crew_ops,
        formation_stage=formation_stage,
        country=_get_country,
        blue_country=blue_country,
        red_country=red_country,
        blue_fields=blue_fields,
        red_fields=red_fields,
        own_fields=own_fields,
        enemy_fields=enemy_fields,
        own_country=own_country,
        enemy_country=enemy_country,
        carrier_home=carrier_home,
        bb_carrier=bb_carrier,
        home=home,
        own_center=own_center,
        enemy_center=enemy_center,
        threat_bearing=threat_bearing,
        away_bearing=away_bearing,
        comms=comms,
        stats=stats,
        historical=snapshot(r.map, r.era, m.start_time.date(), preset),
    )
