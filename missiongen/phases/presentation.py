from __future__ import annotations
from dataclasses import dataclass
from ..document_facts import MissionFacts
from typing import TYPE_CHECKING
from dcs import mapping
from ..build_context import WorldContext
from .carrier import CarrierPlacement
if TYPE_CHECKING:
    from ..builder import StarterBuilder
from .player import PlayerPlacement
from .training import TrainingPlacement
from .targets import ScenePlacement

@dataclass(frozen=True)
class DocumentPlacement:
    """Facts passed to subsequent phases; mission/stat mutations stay ordered."""
    facts: MissionFacts


def place_presentation(builder: StarterBuilder, ctx: WorldContext, targets: ScenePlacement, training: TrainingPlacement, carrier: CarrierPlacement, gfx: dict, player: PlayerPlacement) -> DocumentPlacement:
    self = builder
    r = builder.recipe
    airspace_brief = targets.airspace_brief
    carrier_home = ctx.carrier_home
    comms = ctx.comms
    crew_flight = training.crew_flight
    csg = carrier.group
    enemy_center = ctx.enemy_center
    enemy_fields = ctx.enemy_fields
    era_cfg = ctx.era_cfg
    home = player.home
    m = ctx.mission
    map_cfg = ctx.map_cfg
    nav_pts = targets.nav_pts
    own_center = ctx.own_center
    own_fields = ctx.own_fields
    player_group = player.player_group
    preset = ctx.preset
    stats = ctx.stats
    template_brief = training.template_brief
    # --- bullseye ---------------------------------------------------------
    midpoint = mapping.Point((own_center.x + enemy_center.x) / 2,
                             (own_center.y + enemy_center.y) / 2, m.terrain)
    for coal in m.coalition.values():
        coal.bullseye = {"x": midpoint.x, "y": midpoint.y}
    gfx["bullseye"] = midpoint

    # --- F10 map graphics layers (the map briefs the mission) -------------
    from .. import graphics
    layers = graphics.effective_layers(r.map_layers)
    if self._corridors:
        layers = set(layers) | {"corridors"}   # a chosen corridor always draws
    drawn = graphics.draw_layers(m, gfx, layers, r.coalition)
    if drawn:
        stats["map_layers"] = drawn

    # --- cockpit radio presets (BB-19): put the comm plan IN the jet ------
    # Programs the module's UHF radio from the ladder actually built above.
    # apply() returns ONLY what it really wrote, so the card/kneeboard CHAN
    # column matches the cockpit exactly (no advertising channels a module
    # doesn't have, and no clobbering an agency with Guard). Crew-ops flights
    # own the player jet (player_group is None) but still need programming —
    # otherwise the kneeboard advertises the comm plan while the cockpit keeps
    # factory defaults (cockpit/card disagree). Program whichever we built.
    radio_group = player_group if player_group is not None else crew_flight
    if radio_group is not None:
        from .. import presets
        chan_rows, guard = presets.plan_from_comms(comms)
        programmed = presets.apply(radio_group, chan_rows, guard)
        if programmed:
            comms.set_channels(programmed)
            stats["radio_presets"] = [
                f"CH{ch} {a}" for a, ch in programmed.items() if a != "Guard"]
        # A card entry this jet's radios cannot reach says so on the card.
        from .. import saydo as _sd0
        stats["comms_unreachable"] = _sd0.mark_unreachable(comms, radio_group)

    # --- Case III readback gate + the sentence that names it -------------
    # WHAT THE MISSION CHECKS, SAID ON THE CARD. Reflected writes
    # "complete every checklist or the mission will not progress"; Fulda
    # gates 13 handoffs a mission and never says so. Both halves here:
    # the gate (installed now, because only now do we know which channel
    # really holds Mother), and the sentence — which is also where an
    # airframe we cannot gate says so honestly instead of promising a
    # check the file cannot make.
    if getattr(self, "_cq_gate", None) and player_group is not None:
        from .. import gates as _gates, cq_coach as _cqc3
        _ac_id, _mother_mhz = self._cq_gate
        _chan = comms.channels.get("Carrier")
        _gates.readback(m, player_group, _ac_id, _mother_mhz, "MOTHER",
                        chan=_chan, warnings=self.warnings)
        _tail = [_gates.brief_line(_ac_id, "MOTHER", _mother_mhz, _chan)]
        if _cqc3.grades_for(r.cq_ride):
            _tail.append(
                f"Scorecard: {_cqc3.DEBRIEF_AFTER_S} seconds after the last "
                f"cue the ride prints its card — base {_cqc3.BASE_SCORE}, "
                f"every grade that fired with its points, and a clean line "
                f"if none did.")
        stats["cq_readback"] = _tail[0]
        stats["cq_card"] = list(stats.get("cq_card", [])) + [""] + _tail
        self._wk_card = stats["cq_card"]
        template_brief = "\n".join(stats["cq_card"])

    # --- what DCS will get wrong, said before the pilot finds out ---------
    # Every expert campaign on the shelf tells the pilot what the sim
    # cannot do (Reflected: "forget about the AI, it cannot fly overhead
    # patterns"; Rampagers: a whole Known Issues page). Ours is generated
    # per mission, because the first line depends on this jet's callsign.
    from .. import saydo as _saydo
    self._comms = comms
    self._player_group = player_group
    _extra_issues = ([stats["cq_readback"]] if
                     ("not available" in str(stats.get("cq_readback", "")))
                     else [])
    if getattr(self, "_timing", None):
        from .. import timing as _tm0
        _extra_issues += _tm0.known_issue_lines(
            self._timing, package=bool(r.timing_package))
    if getattr(self, "_nttr", None):
        from .. import corridors as _nttr0
        _extra_issues += _nttr0.known_issue_lines(self._nttr)
    stats["known_issues"] = _saydo.known_issues(
        player_group, getattr(self, "_flight_name", None),
        extra=_extra_issues or None,
        unreachable=stats.get("comms_unreachable"),
        aircraft=getattr(self._resolve_aircraft(r.aircraft), "id", r.aircraft))

    # --- briefing ----------------------------------------------------------
    if r.bb_briefing:
        brief = self._briefing(map_cfg, era_cfg, preset, home,
                               comms, stats, template_brief)
        if nav_pts:
            from .. import navpoints
            brief += "\n" + navpoints.briefing_block(nav_pts)
        if airspace_brief:
            brief += "\n" + airspace_brief
        m.set_description_text(brief)

    # --- brand splash (cosmetic sponsor logo on launch) ------------------
    # The active sponsor (admin-managed) is baked in; with no sponsor store
    # or branding disabled globally, falls back to the shipped Authentic art.
    if getattr(r, "bb_branding", True):
        try:
            from .. import branding, sponsors
            if sponsors.branding_enabled():
                sp = sponsors.active_splash()
                if sp:
                    if branding.add_brand_splash(m, logo_path=sp["path"], size=sp["size"]):
                        stats["branding"] = sp["id"]     # sponsor id → impressions
                elif sponsors.house_brand_enabled():
                    # OPT-IN only. This used to be the fallback, so with no
                    # sponsor configured every mission carried the Authentic
                    # Media wordmark on launch — including on a fresh deploy,
                    # where the sponsor store starts empty. Nobody chose that.
                    if branding.add_brand_splash(m):
                        stats["branding"] = "house"
        except Exception as _e:
            self.warnings.append(f"brand splash skipped: {_e}")

    self.stats = stats
    # context the Mission Brief (PDF/MD) renderer needs — kb_ctx plus the
    # chart geometry (gfx) and the recipe/stats picture (brief.py).
    from ..document_facts import document_facts
    facts = document_facts(builder, ctx, home, carrier, gfx, midpoint, nav_pts)
    self.document_facts = facts
    self.brief_ctx, self.kb_ctx = facts.brief_context, facts.kneeboard_context
    # --- the say/do check, on ourselves ------------------------------------
    # Runs LAST, on the finished mission, and recomputes the paperwork
    # from the world: every card frequency held by something, the clock
    # the brief prints, the callsign DCS will really use. A finding is a
    # warning that reaches the API response and the tests; the tests hold
    # the shipped library to zero.
    try:
        self.warnings += _saydo.run(m, comms, player_group,
                                    getattr(self, "_flight_name", None), r,
                                    timing=self._timing,
                                    said_hhmm=stats.get("start_clock"))
    except Exception as exc:                          # pragma: no cover
        self.warnings.append(f"say/do self-check did not run: {exc}")
    return DocumentPlacement(facts)
