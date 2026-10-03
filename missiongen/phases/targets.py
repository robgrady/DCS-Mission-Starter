from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from dcs import mapping
from ..build_context import WorldContext, _scenario_templates, _bearing
if TYPE_CHECKING:
    from ..builder import StarterBuilder
from .player import PlayerPlacement

@dataclass(frozen=True)
class ScenePlacement:
    """Facts passed to subsequent phases; mission/stat mutations stay ordered."""
    nav_pts: list
    airspace_brief: str


def place_targets(builder: StarterBuilder, ctx: WorldContext, player: PlayerPlacement, gfx: dict) -> ScenePlacement:
    self = builder
    r = builder.recipe
    air_start_mode = player.air_start_mode
    bfm_heading = player.bfm_heading
    comms = ctx.comms
    enemy_center = ctx.enemy_center
    enemy_country = ctx.enemy_country
    enemy_fields = ctx.enemy_fields
    home = player.home
    m = ctx.mission
    own_center = ctx.own_center
    own_country = ctx.own_country
    player_group = player.player_group
    stats = ctx.stats
    nav_pts = []
    if r.bb_navpoints:
        from .. import navpoints
        nav_pts = navpoints.add_nav_points(m, r.map)
        if nav_pts:
            stats["nav_points"] = len(nav_pts)

    # Historical airspace overlay (Theater Identity P3): real corridors /
    # no-fly zones for this map+era, drawn on the F10 map + briefed. Off by
    # default (determinism-safe); scenario templates like Berlin Corridor
    # Transit turn it on. Draws nothing if the map/era has no overlay.
    airspace_brief = ""
    from .. import airspace
    # bb flag on = draw everything for the map/era. Off = still draw the
    # overlays marked "always" (standing real-world airspace: the R-4808N
    # Groom box on Nevada is on every sectional and off-limits even to
    # Red Flag — a Nellis mission without it would be lying by omission).
    drawn_as, as_lines = airspace.add_historical_airspace(
        m, r.map, r.era, only_always=not r.bb_historical_airspace)
    if drawn_as:
        stats["historical_airspace"] = drawn_as
        airspace_brief = "\n".join(as_lines)

    if r.bb_farps:
        if r.era == "wwii":
            self.warnings.append("FARPs are helicopter-era only - skipped in WWII")
        else:
            from .. import farps
            # Visual Fidelity: maps that ship REAL helipad sites (Cold War
            # Germany's 100+ 'H FRG/GDR' pads) use those instead of
            # synthetic pads dropped in a field
            used = farps.helipad_farps(m, own_country, r.coalition,
                                       own_center, enemy_center,
                                       self.rng, comms)
            if used:
                for ap, fname in used:
                    gfx["farps"].append((ap.position, fname))
                stats["support"].append(f"{len(used)}x FARP (real helipad sites)")
            else:
                for i in range(2):
                    pos = mapping.Point(
                        own_center.x + 0.3 * (enemy_center.x - own_center.x)
                        + self.rng.uniform(-6000, 6000),
                        own_center.y + 0.3 * (enemy_center.y - own_center.y)
                        + self.rng.uniform(-6000, 6000), m.terrain)
                    fname = f"FARP {'London Dallas Berlin Paris'.split()[i]}"
                    farps.add_farp(m, own_country, r.coalition, pos, self.rng,
                                   fname, comms)
                    gfx["farps"].append((pos, fname))
                stats["support"].append("2x FARP")

    if r.bb_targets:
        from .. import targets as tgt
        from ..dressing import _offset as _pt_offset
        # A WHITE KNIGHTS ATTACK BOMBS ITS OWN TARGET POINT. The generic
        # placement below anchors packages to ENEMY AIRBASES — under the
        # Proud Phantom lineup those are 60+ NM north-west of Cairo West,
        # while the ride's flight plan runs its TARGET leg the other way.
        # So the brief listed two targets the route never visited, and the
        # route bombed empty sand. Rob: "the coached B'NAI mission doesn't
        # have a target to bomb." One depot, deterministic, standing ON
        # the leg the delivery sheet aims at.
        _wk_key = ((_scenario_templates().get(r.template) or {})
                   .get("wk_ride") if r.template else None)
        _wk_tpos = None
        if _wk_key:
            from .. import wk_route as _wkr0
            _wk_tpos = _wkr0.leg_positions(
                home.position, _wk_key, r.map).get("TARGET")
        if _wk_tpos is not None:
            label = tgt.add_target_package(
                m, enemy_country, r.era, "depot", _wk_tpos,
                self.rng, "TGT1")
            stats.setdefault("targets", []).append(label)
            gfx["targets"].append((_wk_tpos, label))
            picks = []
        # E3/R7: explicit package choice. None = the legacy seeded random
        # two, which is what keeps existing share links byte-stable.
        elif r.target_packages:
            picks = list(r.target_packages)
        else:
            picks = self.rng.sample(list(tgt.TARGET_PACKAGES), k=2)
        # LAND-SAFE: anchor each package to a real enemy airbase (always on
        # land) and push a few km deeper inland (away from friendly lines),
        # instead of the old enemy_center±15km which could drop a C2 site
        # into the sea on coastal maps (Syria/Cyprus, Sinai, Marianas). pydcs
        # exposes no land/water query, so anchoring to airbases is the pattern
        # (see threats.py). Falls back to the centroid if there are no fields.
        ef = list(enemy_fields)
        if ef:
            bases = self.rng.sample(ef, k=min(len(picks), len(ef)))
            while len(bases) < len(picks):
                bases.append(self.rng.choice(ef))
        for i, pk in enumerate(picks):
            if ef:
                base = bases[i].position
                inland = _bearing(own_center, base)   # friendly -> base = inland
                center = _pt_offset(base, self.rng.uniform(4000, 10000), inland)
            else:
                center = mapping.Point(
                    enemy_center.x + self.rng.uniform(-15000, 15000),
                    enemy_center.y + self.rng.uniform(-15000, 15000), m.terrain)
            label = tgt.add_target_package(m, enemy_country, r.era, pk,
                                           center, self.rng, f"TGT{i+1}")
            stats.setdefault("targets", []).append(label)
            gfx["targets"].append((center, label))
            if r.threat_tier == "guns":
                # Guns tier: the target defends ITSELF — two AAA clusters
                # 0.8-2 km off the aim point, exactly where a diving
                # delivery bottoms out. This is the mission: the guns are
                # at the target, not on the way to it.
                from .. import threats as _thr
                for j in range(2):
                    cpos = _pt_offset(center, self.rng.uniform(800, 2000),
                                      self.rng.uniform(0, 360))
                    if _thr.place_aaa_cluster(
                            m, enemy_country, r.era,
                            "red" if r.coalition == "blue" else "blue",
                            cpos, self.rng, f"AAA TGT{i+1}-{j+1}"):
                        gfx["threats"].append((cpos, 3500, "AAA"))

    if r.bb_range:
        from .. import targets as tgt
        pos = mapping.Point(
            own_center.x - 0.2 * (enemy_center.x - own_center.x),
            own_center.y - 0.2 * (enemy_center.y - own_center.y), m.terrain)
        tgt.add_practice_range(m, own_country, pos, self.rng, "RNG1")
        stats.setdefault("targets", []).append("practice range")
        gfx["targets"].append((pos, "RNG1 practice range"))

    # --- INSTANT ACTION: put the flight where the mission starts ----------
    # Measured before this existed: "Kill the Guns" spawned warm on the ramp
    # with the target 133 km away — taxi, take off and cruise for ~18 minutes
    # in an A-10 before the first trigger pull, on a screen whose promise is
    # a fifteen-minute session. "Beat the SAM" was 104 km.
    #
    # The spawn point is the LAST MOMENT BEFORE THE PROBLEM IS YOURS: not the
    # ramp (that is a commute) and not on top of the target (that deletes the
    # skill). You still have to find it, set up and roll in.
    #
    # Why reposition instead of computing the target first: the package
    # anchor is drawn from self.rng (base sample + inland offset), so
    # hoisting it above the player placement would reorder RNG consumption
    # and change the mission for EVERY template that uses target packages.
    # Moving the flight afterwards keeps the blast radius to the two cards
    # this is meant to fix.
    if (air_start_mode in ("roll_in", "outside_the_ring")
            and player_group is not None and gfx["targets"]):
        tpos, _tlabel = gfx["targets"][0]
        self._air_start_on_target(player_group, tpos, home.position,
                                  air_start_mode, stats,
                                  threats=gfx["threats"])

    # --- E2: BFM adversary (Quick Flight merge) ---------------------------
    if r.bb_bfm and player_group is not None:
        from .. import threats as _thr2
        enemy_side2 = "red" if r.coalition == "blue" else "blue"
        ppos = player_group.points[0].position if player_group.points else home.position
        palt = player_group.points[0].alt if player_group.points else 4500
        # adversary skill sits ONE notch below the intensity's engagement
        # skill: DCS AI at Excellent flies physics-blessed BFM — the brief
        # promises a fight, not a humiliation (PRD v2 risk note)
        from dcs.unit import Skill as _Skill
        ladder = [_Skill.Average, _Skill.Good, _Skill.High, _Skill.Excellent]
        base = _thr2.INTENSITY[_thr2.clamp_intensity(r.threat_intensity)]["skill"]
        skill2 = ladder[max(0, ladder.index(base) - 1)] if base in ladder else _Skill.Good
        if bfm_heading is not None:
            # DEGREES. pydcs stores unit.heading in degrees and converts
            # to radians on save; writing radians here produced a heading
            # of 5.6 degrees where the brief said 318.9 (318.9 deg in
            # radians is 5.566, dutifully written as 5.566 DEGREES), so
            # every "off your nose" figure on the standards card described
            # a nose that was not there.
            #
            # manualHeading is belt-and-braces: pydcs recomputes heading
            # from the bearing wp0 -> wp1 when a group has more than one
            # waypoint. A BFM flight has one today, but adding an RTB
            # waypoint later must not silently rotate the briefed picture.
            player_group.manualHeading = True
            for _u in player_group.units:
                _u.heading = bfm_heading % 360.0
        bfm = _thr2.add_bfm_adversary(
            m, enemy_country, r.era, enemy_side2, r.threat_tier,
            ppos, palt, skill2, self.rng,
            guns_only=(r.era == "wwii" or r.player_fit == "guns"),
            intensity=r.threat_intensity,
            fits=stats.setdefault("enemy_air", []),
            warnings=self.warnings,
            setup=getattr(r, "bfm_setup", "neutral"),
            player_heading=bfm_heading)
        stats["bfm_setup"] = getattr(r, "bfm_setup", "neutral")
        if bfm:
            stats.setdefault("enemy_cap", []).extend(bfm)
            stats["bfm"] = bfm[0]

    return ScenePlacement(nav_pts, airspace_brief)
