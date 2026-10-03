"""Orchestrate ordered PyDCS placement phases after world resolution.

World/domain setup lives in build_context; artifact rendering and packaging
live in artifacts. Placement order is significant for RNG and parking.
"""
import math
import random

import dcs
from dcs import mapping
from dcs.mission import StartType

from .recipe import Recipe
from .resolver import resolve_terrain, resolve_country, load_json, resolve, UnknownUnitError
from . import dressing, airdefense, support_air, backseat, loadouts

START_TYPES = {"cold": StartType.Cold, "warm": StartType.Warm, "runway": StartType.Runway}
# How far ahead of you the timing package flies (timing_package). Two minutes
# is the classic SEAD-to-striker spacing: their missiles are off before you
# are in the ring, and you are not in their frag.
PACKAGE_LEAD_S = 120

# Compatibility exports for callers that historically imported these here.
from .build_context import (EraViolation, aircraft_in_era, prepare_world,
                            CREW_OPS_TEMPLATES, TEMPLATE_ERAS, TIME_PRESETS,
                            _scenario_templates, _template_eras, _bearing, _centroid)


from .phases.player import _fitting_slots
from .phases.flight_operations import FlightOperations
from .phases.mission_briefing import MissionBriefing
from .phases.player import place_player
from .phases.environment import place_environment
from .phases.threats_support import place_threats_support
from .phases.targets import place_targets
from .phases.routes import place_routes
from .phases.training import place_training
from .phases.presentation import place_presentation

class StarterBuilder(FlightOperations, MissionBriefing):
    def __init__(self, recipe: Recipe):
        self.recipe = recipe
        self._timing = None                 # timing.plan() once a route is laid
        self._nttr = None                   # nttr.plan_route() on the Nevada map
        self.rng = random.Random(recipe.seed)
        self.maps = load_json("maps")
        self.eras = load_json("eras")
        self.warnings = []

    def build(self) -> dcs.Mission:
        ctx = prepare_world(self)
        self.context = ctx
        stats = ctx.stats
        r = self.recipe
        # --- carrier strike group (built FIRST so the boat can be home plate) --
        gfx = {"targets": [], "farps": [], "threats": []}   # map-graphics geometry
        from .phases.carrier import place_carrier
        carrier = place_carrier(ctx, r, self.rng, self.warnings)
        csg, brc, hull_key = carrier.group, carrier.brc, carrier.hull_key
        strike_group = carrier.strike
        stats["support"].extend(carrier.support_names)
        if carrier.deck_statics is not None:
            stats["deck_statics"] = carrier.deck_statics
        gfx.update(carrier.graphics)
        self._csg, self._brc, self._hull_key = csg, brc, hull_key

        player = place_player(self, ctx, carrier)
        environment = place_environment(self, ctx, player)
        threats_support = place_threats_support(self, ctx, player, gfx)
        targets = place_targets(self, ctx, player, gfx)
        routes = place_routes(self, ctx, gfx, player)
        training = place_training(self, ctx, routes, carrier, gfx, player)
        presentation = place_presentation(self, ctx, targets, training, carrier, gfx, player)
        self.phases = (carrier, player, environment, threats_support, targets, routes, training, presentation)
        return ctx.mission

# Historical import compatibility.
from .artifacts import generate, _normalize_zip_times  # noqa: E402,F401
