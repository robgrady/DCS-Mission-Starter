from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from ..build_context import WorldContext, _scenario_templates
if TYPE_CHECKING:
    from ..builder import StarterBuilder
from .player import PlayerPlacement

@dataclass(frozen=True)
class RoutePlacement:
    """Facts passed to subsequent phases; mission/stat mutations stay ordered."""
    wk_ride: str | None
    wk_rows: list
    cq_rows: list
    route_rows: list | None


def place_routes(builder: StarterBuilder, ctx: WorldContext, gfx: dict, player: PlayerPlacement) -> RoutePlacement:
    self = builder
    r = builder.recipe
    comms = ctx.comms
    home = player.home
    m = ctx.mission
    own_country = ctx.own_country
    player_group = player.player_group
    stats = ctx.stats
    _cq_rows = []
    # --- player flight plan ----------------------------------------------
    # THE ONLY PLACE PLAYER WAYPOINTS EXIST, and it happens for exactly two
    # reasons, both of them a request:
    #
    #   * a scenario template declares "route": "strike" — a routed strike
    #     is the mission FORMAT there, the way a Case recovery is the format
    #     for a carrier template;
    #   * the user ticked `bb_route`.
    #
    # Default behavior is unchanged: no tick, no template, no waypoints.
    # See routing.py for what the north star actually says. Runs after
    # bb_targets so the route can aim at a real target package.
    # Resolved once, ABOVE the routing block, because both the flight plan
    # and the briefing need it and the routing block runs first.
    _wk_ride = (_scenario_templates().get(r.template) or {}).get("wk_ride") \
        if r.template else None
    route_rows = None
    # CASE III: the flight plan IS the approach plate. Laid first, for the
    # same reason the White Knights route is — so the generic router below
    # cannot also fire and give the flight two overlapping plans — and off
    # the CARRIER rather than a home field, because every fix in a recovery
    # is a radial and a DME from the ship.
    _cq_rows = []
    if player_group is not None and r.cq_ride and self._csg is not None:
        from .. import cq as _cq2, cq_route as _cqr2, cq_coach as _cqc
        _cq_rows = _cqr2.apply(player_group, r.cq_ride,
                               self._csg.units[0].position, self._brc)
        if _cq_rows:
            stats["cq_route"] = _cq_rows
        stats["cq_ride"] = r.cq_ride
        stats["cq_requires"] = _cq2.REQUIRES_MODULE
        # The cues and the grades. Attached AFTER the route because the
        # brief prints them alongside it, and never raising because a
        # recovery without coaching is a worse mission, not a failed build.
        _mother = next((fq for ag, cs_, fq, *_ in comms.entries
                        if ag == "Carrier"), None)
        try:
            _mother_mhz = float(_mother) if _mother else None
        except (TypeError, ValueError):
            _mother_mhz = None
        try:
            _ac_id = self._resolve_aircraft(r.aircraft).id
        except Exception:
            _ac_id = r.aircraft
        _cqc.attach(m, player_group, self._csg, r.cq_ride, self.warnings,
                    aircraft=_ac_id, mother_mhz=_mother_mhz)
        # The gate is installed after the radios are programmed (below),
        # so its reminder can name the channel that really holds Mother.
        self._cq_gate = (_ac_id, _mother_mhz) if _mother_mhz else None

    # WHITE KNIGHTS: a bespoke flight plan whose geometry IS the lesson.
    # The generic strike router cannot produce an IP at the delivery
    # sheet's own pull-up distance or a split point at the range the
    # squadron's guide names, because it has never read the document.
    # Laid FIRST so `wants_route` below cannot also fire and give the
    # flight two overlapping plans.
    _wk_rows = []
    if player_group is not None and _wk_ride:
        from .. import wk_route as _wkr
        _wk_rows = _wkr.apply(player_group, home.position, _wk_ride,
                              r.map, home_airport=home)
        if _wk_rows:
            stats["wk_route"] = _wk_rows
        # THE AIRPLANE EVERY CARD PROMISED is seat two of your own
        # flight now — created with the group, armed with the group,
        # parked by the group (which is also what keeps a static out of
        # his shelter: both stands are claimed before the ramp dressing
        # runs).
        stats["wk_counterpart"] = len(player_group.units) > 1
        # THE COACHED RIDE. Cues at every decision in the B'NAI, on the
        # same leg table the waypoints came from, and a re-arm after
        # egress so the whole thing can be flown again without reloading.
        # Attached AFTER the route, because it places its zones on the
        # points the route just laid.
        from .. import wk_coach as _wkc
        from .. import wk_brief as _wkb
        # THE BRIEF GOES FIRST, and not only for tidiness: it owns the
        # coaching's arm flag. If it attached, the cues stay dark until
        # the pilot presses SPACE on the last page and gets his controls
        # back — otherwise the coaching's own timer would start calling
        # the attack while he was still reading who he is.
        _n_brief = _wkb.attach(m, player_group, _wk_ride, _wkc.F_ARM,
                               warnings=self.warnings)
        if _n_brief:
            stats["wk_brief_triggers"] = _n_brief
        _n_cues = _wkc.attach(m, player_group, _wk_ride, r.map,
                              home.position, warnings=self.warnings,
                              armed_externally=bool(_n_brief),
                              ring=getattr(r, "coach_ring", "red"))
        if _n_cues:
            stats["wk_coach_triggers"] = _n_cues
        # No wingman-hold trigger any more: seat two is in YOUR group,
        # so he waits because you wait — the brief holds the flight by
        # holding you, which is what "held" should have meant all along.
        # THE NAVIGATION SQUARES. Rob asked for "the green navigation
        # boxes" — DCS's helper gates, the fly-through squares from the
        # training missions — and they are a NATIVE Mission Editor action
        # (`a_show_route_gates_for_unit`), not Lua: the gates render along
        # the unit's own flight plan, which for this ride IS the lesson
        # geometry. Shown when the brief hands the airplane over, so the
        # boxes appear at the same instant the coaching arms; on a
        # brief-less build they show a second in.
        if getattr(r, "coach_gates", False):
            from dcs import action as _A2, condition as _C2
            from dcs import triggers as _Tr2
            _me_id = player_group.units[0].id
            _g = _Tr2.TriggerOnce(comment="WK gates: navigation squares")
            if _n_brief:
                _g.rules.append(_C2.FlagIsTrue(_wkb.F_DONE))
            else:
                _g.rules.append(_C2.TimeAfter(1))
            _g.actions.append(_A2.ShowHelperGatesForUnit(_me_id, 1))
            # PIN THE POINTER. Rob: "the navigation aids don't fly to the
            # target" — the gates drew, but the line they traced was not
            # the lesson. The gates render from the unit's ACTIVE route
            # point, and after minutes held on the ramp reading the brief,
            # where DCS thinks you are on your own plan is anybody's
            # guess. So the active gate is set explicitly: to the low
            # level when you take the airplane, and forward from the
            # coaching's own phase flags as you earn each cue — the boxes
            # and the WSO advance from the same facts. (First pass only:
            # the phase flags re-fire on the re-attack but a TriggerOnce
            # is spent; the second run is flown on the cues, which is the
            # point of a second run.) Route points: 0 parking,
            # 1 departure, 2 low level, 3 trail, 4 IP, 5 pull-up,
            # 6 target, 7 egress, 8 recovery.
            _g.actions.append(_A2.SetActiveHelperGateToPoint(_me_id, 2))
            m.triggerrules.triggers.append(_g)
            from .. import wk_coach as _wkc2
            _gate_wp = {"lowlevel": 3, "trail": 4, "ip": 5, "runin": 5,
                        "pup": 6, "release": 7, "pullout": 7,
                        "egress": 8}
            for _key, _wp in sorted(_gate_wp.items()):
                _t2 = _Tr2.TriggerOnce(
                    comment=f"WK gates: next box after {_key}")
                _t2.rules.append(_C2.FlagIsTrue(
                    _wkc2.F_PHASE + _wkc2.IDX[_key]))
                _t2.actions.append(
                    _A2.SetActiveHelperGateToPoint(_me_id, _wp))
                m.triggerrules.triggers.append(_t2)
    wants_route = (not _wk_ride) and (bool(getattr(r, "bb_route", False)) or (
        r.template and _scenario_templates().get(r.template, {}).get("route") == "strike"))
    if player_group is not None and wants_route and gfx["targets"]:
        from .. import routing
        tgt_pos, tgt_label = gfx["targets"][0]
        # Where the map has published corridors (corridors.py: Nevada,
        # Syria) the plan is threaded through them - departure, corridor,
        # entry gate as WP1, IP, TARGET, exit gate, recovery. Everywhere
        # else, and for a target inside the home's terminal area, the
        # generic three-point route.
        from .. import corridors as _nttr
        self._nttr = _nttr.plan_route(home.position, tgt_pos, r.era,
                                      self.rng, m.terrain, r.map,
                                      home_name=home.name) if r.published_corridors else None
        legs = (self._nttr["legs"] if self._nttr else
                routing.route_for(home.position, tgt_pos, r.era, self.rng,
                                  m.terrain))
        if legs:
            landed = routing.apply(legs=legs, player_group=player_group,
                                   home_airport=home)
            route_rows = routing.leg_card(home.position, legs, home.name)
            stats["route"] = routing.summary(legs, tgt_label, home.name)
            stats["route_legs"] = route_rows
            stats["route_target"] = tgt_label
            if self._nttr:
                _nttr.draw(m, self._nttr, r.map)
                stats["nttr"] = {
                    "map": r.map,
                    "title": _nttr.data(r.map).get("text", {}).get("md_title", "Corridors"),
                    "sector": self._nttr["sector"], "mode": self._nttr["mode"],
                    "corridors": list(self._nttr["corridors"]),
                    "gate_in": self._nttr["gate_in"], "gate_out": self._nttr["gate_out"],
                    "summary": _nttr.summary(self._nttr),
                    "brief": _nttr.brief_lines(self._nttr),
                    "md_line": _nttr.md_line(self._nttr),
                    "approx": _nttr.approx_fixes(self._nttr),
                }
            # THE CLOCK ON THE CARD. Every routed flight plan is timed
            # (timing.py): leg, cumulative and ETA per point, anchored on
            # takeoff unless the recipe anchors it on the push or the TOT
            # — in which case the mission clock is solved backwards and
            # MOVED here, before anything prints it.
            self._timing = self._time_the_route(m, stats, route_rows,
                                                player_group, own_country,
                                                home)
            if not landed:
                self.warnings.append(
                    "the flight plan has no recovery point: this airfield "
                    "would not accept a landing waypoint. The outbound "
                    "route is unaffected.")
    elif player_group is not None and getattr(r, "bb_route", False):
        # Asked for and not delivered. Silence here would look like a bug —
        # the box is ticked and the F10 map is empty.
        self.warnings.append(
            "automatic waypoints were requested but this mission has no "
            "target to route to. Turn on strike target packages, or pick a "
            "card that places a target.")

    return RoutePlacement(_wk_ride, _wk_rows, _cq_rows, route_rows)
