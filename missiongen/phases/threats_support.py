from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from ..build_context import WorldContext, _scenario_templates
from .. import airdefense, support_air
if TYPE_CHECKING:
    from ..builder import StarterBuilder
from .player import PlayerPlacement

@dataclass(frozen=True)
class SupportPlacement:
    """Facts passed to subsequent phases; mission/stat mutations stay ordered."""
    support_names: tuple[str, ...]
    sam_sites: tuple[str, ...]


def place_threats_support(builder: StarterBuilder, ctx: WorldContext, player: PlayerPlacement, gfx: dict) -> SupportPlacement:
    self = builder
    r = builder.recipe
    _get_country = ctx.country
    air_start_mode = player.air_start_mode
    away_bearing = ctx.away_bearing
    carrier_home = ctx.carrier_home
    comms = ctx.comms
    enemy_center = ctx.enemy_center
    enemy_country = ctx.enemy_country
    enemy_fields = ctx.enemy_fields
    era_cfg = ctx.era_cfg
    home = player.home
    m = ctx.mission
    own_center = ctx.own_center
    own_country = ctx.own_country
    player_group = player.player_group
    stats = ctx.stats
    if r.bb_sams:
        from .. import threats
        enemy_side = "red" if r.coalition == "blue" else "blue"
        # base per-airfield defense: SAM kit chosen by the Threat Dial tier
        enemy_kits = threats.sam_kits_for(
            r.era, enemy_side, r.threat_tier,
            era_cfg[enemy_side]["sam_kits"])
        for ap in enemy_fields:
            stats["sam_sites"] += airdefense.defend_airbase(
                m, enemy_country, ap, era_cfg[enemy_side], self.rng, r.era,
                gfx_threats=gfx["threats"], kits_override=enemy_kits)
        # friendly defense at home plate. In the guns tier "no SAMs" means
        # the THEATER: the player's own Hawk battery would be the only
        # radar-guided system in a mission whose premise is that none
        # exist. Guns tier keeps the SHORAD pair (era guns) and drops the
        # site; other tiers are untouched (determinism/share links).
        stats["sam_sites"] += airdefense.defend_airbase(
            m, own_country, home, era_cfg[r.coalition], self.rng, r.era,
            kits_override=[] if r.threat_tier == "guns" else None)

        # --- Threat Dial: extra area SAM belt + enemy CAP (seeded count) --
        tp = threats.plan(r.threat_intensity, self.rng)
        stats["threat_level"] = f"{tp['label']} / {threats.TIER_LABELS.get(r.threat_tier, r.threat_tier)}"
        area = threats.add_area_sams(
            m, enemy_country, r.era, enemy_side, r.threat_tier,
            tp["n_extra_sams"], own_center, enemy_center, self.rng,
            gfx_threats=gfx["threats"], enemy_fields=enemy_fields)
        stats["sam_sites"] += area
        # The area belt is guns when the pilot ASKED for guns — or when
        # this era simply has no SAMs to give, whatever tier was picked.
        # Without the second condition the GWOT era's threat dial is a
        # no-op on every tier but "guns": `add_area_sams` returns nothing,
        # nothing replaces it, and a Maximum-intensity mission generates
        # the same empty map as a Minimal one. An era with no SAM
        # inventory is not an era with no threat.
        no_sams_this_era = not threats.sam_kits_for(
            r.era, enemy_side, r.threat_tier, era_cfg[enemy_side]["sam_kits"])
        if r.threat_tier == "guns" or no_sams_this_era:
            # Guns: the area belt is AAA clusters instead of SAM
            # sites, and DENSER — guns trade reach for numbers. 2n+2 keeps
            # intensity meaningful (Minimal=2 clusters, Maximum=8-12).
            aaa = threats.add_area_aaa(
                m, enemy_country, r.era, enemy_side,
                2 * tp["n_extra_sams"] + 2, own_center, enemy_center,
                self.rng, gfx_threats=gfx["threats"],
                enemy_fields=enemy_fields)
            stats["sam_sites"] += aaa
        cap = threats.add_enemy_cap(
            m, enemy_country, r.era, enemy_side, r.threat_tier,
            tp["n_cap"], own_center, enemy_center, tp["skill"],
            self.rng, gfx=gfx, intensity=r.threat_intensity,
            fits=stats.setdefault("enemy_air", []),
            warnings=self.warnings)
        if cap:
            stats.setdefault("enemy_cap", []).extend(cap)

    # Support flights fly under a nation that actually OPERATES the airframe
    # (US AWACS/tankers, Russian A-50) — added to the coalition if the lead
    # nation doesn't fly it. So an Israeli- or UK-led blue force still gets a
    # valid, ME-editable KC-135/E-3 instead of an airframe its country can't
    # operate. The tanker also matches the PLAYER's receiver (boom vs drogue).
    if r.bb_tanker or r.bb_awacs:
        support_country = _get_country(
            "USA" if r.coalition == "blue" else "Russia", r.coalition)
        try:
            player_id = self._resolve_aircraft(r.aircraft).id
        except Exception:
            player_id = None
    if r.bb_tanker:
        from .. import aar as _aar
        # Which tanker, and at what speed. The receiver decides boom vs
        # drogue; the pilot may override the airframe but never past a
        # mismatch, because a boom tanker and a probe receiver produce a
        # mission where everything works except the refuelling.
        aar_key = _aar.choose(player_id or "", r.era,
                              carrier=carrier_home,
                              preferred=r.tanker_type or None,
                              map_key=r.map)
        if r.tanker_type and not aar_key:
            self.warnings.append(
                f"tanker '{r.tanker_type}' cannot refuel {player_id} in "
                f"{r.era} (boom vs probe, or wrong era) — falling back to "
                f"the matching tanker")
            aar_key = _aar.choose(player_id or "", r.era,
                                  carrier=carrier_home, map_key=r.map)
        no_aar = bool(player_id) and not _aar.can_refuel(player_id)
        if no_aar:
            # And place NOTHING. The first version of this warned "no
            # tanker placed" and then placed one anyway through the legacy
            # fallback — a brief saying the opposite of the file, which is
            # the exact failure tests/test_library_promises.py exists to
            # stop.
            self.warnings.append(
                f"{player_id} cannot air-refuel in DCS — no tanker placed")
            aar_key = ttype = None
        else:
            ttype = (_aar.TANKERS[aar_key]["type"] if aar_key else
                     support_air.tanker_type(r.era, r.coalition, player_id,
                                             carrier_home=carrier_home))
        tk = support_air.add_tanker(
            m, support_country, ttype,
            own_center, away_bearing, comms, gfx=gfx, aar_key=aar_key,
            receiver_id=player_id, map_key=r.map)
        if tk:
            stats["support"].append(tk.name)
            stats["aar"] = aar_key
            if air_start_mode == "astern_tanker" and player_group is not None:
                self._air_start_astern_tanker(player_group, tk, aar_key,
                                              stats, player_id, r.map)
            # Graded AAR rides: wire the trigger-only coach to THIS tanker.
            # Only when the card asked for it, and only when we know which
            # tanker it is — the grader's tolerances are derived from the
            # track speed, so without aar_key there is nothing to grade
            # against and attaching would invent a standard.
            grade = (r.template and (_scenario_templates().get(r.template)
                                     or {}).get("aar_grade"))
            if grade and aar_key and player_group is not None:
                from .. import aar_grade as _agr, aar_hud as _ahud
                # Indicator FIRST: whether it attached decides whether the
                # grader also emits the two continuous text cues, and a
                # pilot seeing both would be told the same thing twice —
                # once where they can read it and once where they cannot.
                hud_on = _ahud.attach(m, player_group, tk, aar_key, grade,
                                      warnings=self.warnings,
                                      receiver_id=player_id, map_key=r.map)
                if _agr.attach(m, player_group, tk, aar_key, grade,
                               warnings=self.warnings, hud=hud_on,
                               receiver_id=player_id, map_key=r.map):
                    stats["aar_grade"] = grade
                    stats["aar_hud"] = hud_on
                if (_scenario_templates().get(r.template)
                        or {}).get("aar_gates"):
                    stats["aar_gates"] = _ahud.attach_gates(
                        m, player_group, tk, aar_key,
                        warnings=self.warnings, map_key=r.map)
            if getattr(ttype, "id", None) == "A6E":
                self.warnings.append(
                    "Carrier tanker is the KA-6D (A-6E) — the air wing's own "
                    "gas. Confirm the buddy-refueling store in-sim (A-6 is an "
                    "AI-only module for now).")
    if r.bb_awacs:
        aw = support_air.add_awacs(
            m, support_country, support_air.awacs_type(r.era, r.coalition),
            own_center, away_bearing, comms, gfx=gfx)
        if aw:
            stats["support"].append(aw.name)

    return SupportPlacement(tuple(stats["support"]), tuple(stats["sam_sites"]))
