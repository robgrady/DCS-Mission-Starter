from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from dcs import mapping
from dcs.unitgroup import FlyingGroup
from ..build_context import WorldContext, _scenario_templates
from .. import backseat
from .carrier import CarrierPlacement
if TYPE_CHECKING:
    from ..builder import StarterBuilder
from .player import PlayerPlacement
from .routes import RoutePlacement

@dataclass(frozen=True)
class TrainingPlacement:
    """Facts passed to subsequent phases; mission/stat mutations stay ordered."""
    crew_flight: FlyingGroup | None
    template_brief: str


def place_training(builder: StarterBuilder, ctx: WorldContext, routes: RoutePlacement, carrier: CarrierPlacement, gfx: dict, player: PlayerPlacement) -> TrainingPlacement:
    self = builder
    r = builder.recipe
    _cq_rows = routes.cq_rows
    _wk_ride = routes.wk_ride
    _wk_rows = routes.wk_rows
    blue_country = ctx.blue_country
    carrier_home = ctx.carrier_home
    comms = ctx.comms
    csg = carrier.group
    enemy_center = ctx.enemy_center
    formation_stage = ctx.formation_stage
    home = player.home
    m = ctx.mission
    own_center = ctx.own_center
    player_group = player.player_group
    red_country = ctx.red_country
    stats = ctx.stats
    strike_group = carrier.strike
    # --- template packs ---------------------------------------------------
    from .. import library_scenarios
    library_lines = library_scenarios.add_actors(ctx, r, player_group, gfx)
    library_lines += library_scenarios.complete_strike(ctx, strike_group, csg, gfx)
    template_brief = ""
    crew_flight = None                     # crew-ops flight owns the player jet
    if r.cq_ride:
        # CASE III. Same reasoning as the White Knights card below — the
        # card is generated because the same ride tells a different truth
        # in a different cockpit: the Tomcat sets ICLS on the ARA-63 panel
        # and the Hornet on the UFC, and on-speed is 15 units in one jet
        # and 8.1 in the other.
        from .. import cq as _cq3, cq_route as _cqr3
        _hull = None
        try:
            _hull = self._csg.units[0].name if self._csg else None
        except Exception:
            _hull = None
        _cq_card = _cq3.brief_lines(
            r.cq_ride, r.aircraft, brc=self._brc, hull_label=_hull)
        _fp = _cqr3.brief_lines(r.cq_ride, _cq_rows, self._brc,
                                (_cq3.ride(r.cq_ride) or {}).get("angels", 6))
        if _fp:
            _cq_card = _cq_card + [""] + _fp
        stats["cq_card"] = _cq_card
        # The kneeboard slot is shared with the White Knights card on
        # purpose: a mission has exactly one ride card, and two modules
        # writing to two slots would eventually put both on the kneeboard.
        self._wk_card = _cq_card
        self._wk_card_title = (
            f"CASE III {(_cq3.ride(r.cq_ride) or {}).get('n', '')}: "
            f"{(_cq3.ride(r.cq_ride) or {}).get('name', '')}")
        template_brief = "\n".join(_cq_card)
    elif _wk_ride:
        # WHITE KNIGHTS: the card is GENERATED, not stored, because the same
        # ride tells a different truth in a different theatre. The low-level
        # floor is the case that forced it — the squadron's own contract
        # says formations work down to 300 ft and West Germany's floor was
        # 500. A stored card would have to pick one and be wrong in the
        # other, which is the say/do gap wearing a period costume.
        #
        # THIS BRANCH IS FIRST ON PURPOSE. It used to sit after `bb_bfm`,
        # and ride 11 sets `bb_bfm` — so the generic BFM standards card
        # silently replaced the squadron's own sixteen directive calls.
        # The card advertised WIS No. 1 and the mission shipped something
        # else, which is exactly the defect class this product exists to
        # remove. `tests/test_wk.py` pins every ride's own title into its
        # own mission so it cannot happen again.
        from .. import wk as _wk
        from .. import wk_route as _wkr
        _wk_card = _wk.brief_lines(
            _wk_ride, map_key=r.map,
            aircraft_id=getattr(self._resolve_aircraft(r.aircraft), "id", ""))
        _disclosure = ((_scenario_templates().get(r.template) or {}).get("library") or {}).get("disclosure")
        if _disclosure:
            _wk_card = [_disclosure, ""] + _wk_card
        _fp = _wkr.brief_lines(_wk_ride, r.map, _wk_rows)
        if _fp:
            _wk_card = _wk_card + [""] + _fp
        stats["wk_card"] = _wk_card
        # ...and onto the KNEEBOARD. Stashed on `self` rather than written
        # into `self.kb_ctx` directly: that dict is BUILT further down, so
        # an assignment here would be silently thrown away.
        self._wk_card = _wk_card
        self._wk_card_title = _wk.RIDES[_wk_ride]["title"]
        # ...and the squadron's own diagram, where the ride flies one of
        # the four attacks. Degrades to no page if the asset is absent.
        _atk = _wk.RIDES[_wk_ride].get("attack")
        if _atk:
            _dp = _wk.diagram_path(_atk)
            if _dp:
                self._wk_diagram = str(_dp)
                self._wk_diagram_cap = _wk.diagram_note(_atk)
        template_brief = "\n".join(_wk_card)
    elif r.template in ("backseat_izlid", "backseat_intercept", "rio_fleet_defense"):
        target_area = mapping.Point(
            enemy_center.x + self.rng.uniform(-8000, 8000),
            enemy_center.y + self.rng.uniform(-8000, 8000), m.terrain)
        if r.template == "backseat_izlid":
            crew_flight = backseat.build_backseat_izlid(
                m, r, blue_country, red_country, home,
                target_area, self.rng, comms, self.warnings)
            template_brief = backseat.BRIEFING_BLOCK
        elif r.template == "backseat_intercept":
            crew_flight = backseat.build_backseat_intercept(
                m, r, blue_country, red_country,
                home, target_area, self.rng, comms, self.warnings)
            template_brief = backseat.INTERCEPT_BRIEFING_BLOCK
        else:
            crew_flight = backseat.build_rio_fleet_defense(
                m, r, blue_country, red_country,
                home, target_area, self.rng, comms,
                r.era, csg=self._csg if carrier_home else None)
            template_brief = backseat.RIO_BRIEFING_BLOCK
    elif formation_stage:
        # The instruction sheet IS the mission. Generated rather than stored
        # in the template so the sight picture matches the aircraft you
        # actually chose — a Phantom wingman and a Viper wingman are looking
        # at completely different things.
        from .. import formation as _form
        aircraft = self._resolve_aircraft(r.aircraft)
        template_brief = "\n".join(
            _form.brief_lines(formation_stage, aircraft.id))
    elif r.bb_bfm:
        # The STANDARDS CARD is the brief for a BFM ride. Generated rather
        # than stored so it matches the rung actually flown — a card that
        # describes the neutral merge while you are on the defensive perch
        # is worse than no card, because a pilot will believe it.
        from .. import bfm as _bfmdoc
        template_brief = "\n".join(_bfmdoc.brief_lines(
            getattr(r, "bfm_setup", "neutral"),
            aircraft_id=getattr(self._resolve_aircraft(r.aircraft), "id", ""),
            guns_only=(r.era == "wwii")))
    elif r.template:
        # SCENARIO template: append its suggested-tasking block (no waypoints).
        sc = _scenario_templates().get(r.template)
        if sc and sc.get("brief"):
            template_brief = "\n".join(sc["brief"])

    # --- AAR: the procedure card for the tanker actually placed ---------
    if stats.get("aar"):
        from .. import aar as _aardoc
        _tk = comms.cfg("tanker")
        _extra = _aardoc.brief_lines(
            stats["aar"],
            receiver_id=getattr(self._resolve_aircraft(r.aircraft), "id", ""),
            freq=f"{_tk['freq']:.3f}", tacan=_tk["tacan"], map_key=r.map)
        # The hardware page rides along on the dedicated AAR cards only.
        # It is read once, on the ground; putting it on every mission with
        # a tanker would bury the procedure under two pages of settings
        # advice the pilot read a month ago.
        if (r.template or "").startswith(("aar_", "qf_tanker")):
            _extra = _extra + [""] + _aardoc.hardware_lines()
        # If the grader attached, the card MUST say what it grades — and
        # more importantly what it does not. A ride that shows a pass
        # message without telling you the plug was never measured is a
        # brief promising what the mission does not contain.
        if stats.get("aar_grade"):
            from .. import aar_grade as _agrdoc
            _extra = _extra + [""] + _agrdoc.brief_lines(stats["aar_grade"])
        if stats.get("aar_hud"):
            from .. import aar_hud as _ahuddoc
            _extra = _extra + [""] + _ahuddoc.brief_lines()
        if stats.get("aar_gates"):
            from .. import aar_hud as _ahuddoc2
            _extra = _extra + [""] + _ahuddoc2.gate_brief_lines()
        template_brief = ((template_brief + "\n\n") if template_brief else "") \
            + "\n".join(_extra)

    disclosure = ((_scenario_templates().get(r.template) or {}).get("library") or {}).get("disclosure")
    if disclosure:
        library_lines.insert(0, disclosure)
    if library_lines:
        stats["scenario_facts"] = library_lines
        template_brief = "\n".join(library_lines) + "\n\n" + (template_brief or "")

    # --- air corridors: brief the lane + enemy picture, draw the axis ------
    if self._corridors:
        names = ", ".join(c["name"] for c in self._corridors)
        lines = ["== AIR CORRIDOR" + ("S" if len(self._corridors) > 1 else "") +
                 ": " + names + " =="]
        for c in self._corridors:
            lines.append(f" {c['name']} — {c.get('axis','')}. Enemy: {c.get('enemy','')}.")
            # A caveat about the ground itself, where one exists. Said in
            # the brief rather than left for the pilot to notice at 500 ft
            # over a stretch of map the terrain author has not finished.
            if c.get("terrain_note"):
                lines.append(f"   NOTE: {c['terrain_note']}")
        lines.append("The threat axis and enemy air defenses are oriented down "
                     "the corridor. Build your own ingress around them.")
        template_brief = (template_brief + "\n\n" if template_brief else "") + "\n".join(lines)
        stats["corridors"] = [c["name"] for c in self._corridors]
        gfx.setdefault("corridors", []).append(
            (own_center, enemy_center, f"CORRIDOR · {names}"))

    return TrainingPlacement(crew_flight, template_brief)
