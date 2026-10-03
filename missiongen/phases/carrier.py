"""Place the carrier before player parking, preserving seeded placement order."""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from dcs.unitgroup import ShipGroup, FlyingGroup

from .. import naval, deck
from ..build_context import WorldContext, EraViolation
from ..recipe import Recipe

@dataclass(frozen=True)
class CarrierPlacement:
    """Only the orchestrator applies these facts to its statistics/context."""
    group: ShipGroup | None
    brc: float | None
    hull_key: str | None
    strike: FlyingGroup | None
    support_names: tuple[str, ...]
    deck_statics: int | None
    graphics: dict


def place_carrier(ctx: WorldContext, recipe: Recipe, rng: Random,
                  warnings: list[str]) -> CarrierPlacement:
    graphics = {}
    group, brc, hull_key, strike, deck_statics = None, None, None, None, None
    support = []
    if ctx.bb_carrier:
        if recipe.coalition == 'blue':
            default_hull = {'wwii': 'essex', 'coldwar': 'forrestal',
                            'modern': 'stennis', 'gwot': 'stennis'}.get(recipe.era)
            hull_key = recipe.carrier_hull or default_hull
            group, brc = naval.add_carrier_group(
                ctx.mission, ctx.own_country, recipe.era, 'blue', ctx.map_cfg,
                ctx.mission.weather, ctx.comms, warnings, hull_key=hull_key)
            if group:
                support.append(group.name)
                graphics['carrier'] = (group.units[0].position, brc, group.name)
                deck_statics = deck.configure_deck(
                    ctx.mission, ctx.own_country, group, brc, hull_key,
                    recipe.carrier_layout, recipe.carrier_deck_aircraft,
                    recipe.carrier_equipment, rng, warnings)
                carrier_pos = group.units[0].position
                # Flight ops => plane guard first, before the first cat shot.
                if recipe.carrier_layout in ('launch', 'recovery'):
                    guard = naval.add_plane_guard(
                        ctx.mission, ctx.own_country, hull_key, group, brc,
                        ctx.comms, warnings)
                    if guard:
                        support.append(guard.name)
                if recipe.carrier_cap:
                    cap = naval.add_carrier_cap(
                        ctx.mission, ctx.own_country, hull_key, carrier_pos, brc,
                        ctx.threat_bearing, ctx.comms, warnings, gfx=graphics)
                    if cap:
                        support.append(cap.name)
                if recipe.carrier_aew:
                    aew = naval.add_carrier_aew(
                        ctx.mission, ctx.own_country, hull_key, carrier_pos, brc,
                        ctx.threat_bearing, ctx.comms, warnings, gfx=graphics)
                    if aew:
                        support.append(aew.name)
                if recipe.carrier_strike:
                    strike = naval.add_carrier_strike(
                        ctx.mission, ctx.own_country, hull_key, carrier_pos, brc,
                        ctx.threat_bearing, ctx.comms, warnings, gfx=graphics)
                    if strike:
                        support.append(strike.name)
        else:
            warnings.append('carrier group is blue-only for now - skipped')
    if ctx.carrier_home and group is None:
        raise EraViolation('Carrier home base selected but no carrier strike group '
                           'could be created on this map/era')
    return CarrierPlacement(group, brc, hull_key, strike, tuple(support),
                            deck_statics, graphics)
