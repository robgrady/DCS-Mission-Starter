"""Crew Ops template packs — F-14 Tomcat crew-AI missions.

THE BACKSEAT CONTRACT: the mission flies the jet; the player runs the mission.
Scenarios are player-paced via the F10 crew menu (see crewops.py), not timers.

PLATFORM (corrected 2026-07-12): the crew-AI mission-command flag API belongs to
the F-14B(U) — note the "BU" in the flag names. Jester is the F-14's AI RIO;
Iceman is the F-14's AI pilot. The F-4E has NO crew AI and needs none: the
Phantom's back seat has full flight controls, so a WSO player simply flies from
the pit. Crew Ops templates are therefore F-14 only.

Two genres on the F-14B(U):
  PILOT-SEAT (AI RIO): command Jester — 10019 zone target select,
    10046 PROXY_Jester_BU_wpt_from_ggw_target (0.01-0.99 -> "GGWTargetNN"),
    10047 PROXY_Jester_BU_izlid_point_zone (value*60 s lase, -1 cont, 0 stop)
  RIO-SEAT (AI pilot): command Iceman — 10080/81 hdg abs/rel, 10082/83 spd,
    10084/85 alt, 10086 fly-to-steerpoint, 10087 orbit steerpoint, 10088 hold

F-14A/B (today, no flag API): rio_fleet_defense — solo via in-cockpit Iceman
(A-menu) or multiplayer human crew.

The F-14B(U) uses the verified DCS type id via the pending-module pattern
(pydcs has no native class yet); it inherits F-14B flight data.

NOTE: templates are the sanctioned exception to the no-waypoints principle —
the AI crew needs steerpoints. These are template waypoints, not user plans.
"""
import math
import random
from dcs import mapping, vehicles
from dcs.action import SetFlagValue
from dcs.mission import StartType

from .crewops import CrewFlow
from .pending import get_pending

_START_TYPES = {"cold": StartType.Cold, "warm": StartType.Warm,
                "runway": StartType.Runway}


def _player_flight(m, recipe, country, name, cls, home_airport, route,
                   group_size=1):
    """Build the player crew-ops flight honoring recipe.start.

    The Crew Ops wizard only ever offers a GROUND start (cold / warm / runway) -
    there is no "air start" option - so the flight must spawn on the ground at the
    home base and fly its route from there. (The old builders always air-started,
    which is why cold/runway/ramp selections were ignored and the jet appeared
    already airborne.)

    route: list of (point, altitude_m, speed_kmh) steerpoints for the air task.
    Ground-starts from home_airport per the wizard when parking is free; only if
    the base has no free parking does it fall back to an air start on the first
    route point. Assigns player/client seats and returns (flight_group, ground).
    """
    from dcs.terrain.terrain import NoParkingSlotError
    gs = max(1, min(2, group_size))
    st = _START_TYPES.get(recipe.start, StartType.Cold)
    ground = True
    try:
        fg = m.flight_group_from_airport(country, name, cls, home_airport,
                                         start_type=st, group_size=gs)
        for pt, alt, spd in route:
            fg.add_waypoint(pt, altitude=alt, speed=spd)
    except NoParkingSlotError:
        ground = False
        first_pt, first_alt, first_spd = route[0]
        fg = m.flight_group_inflight(country, name, cls, first_pt,
                                     altitude=first_alt, speed=first_spd,
                                     group_size=gs)
        for pt, alt, spd in route[1:]:
            fg.add_waypoint(pt, altitude=alt, speed=spd)
    if recipe.slots <= 1:
        fg.units[0].set_player()
    else:
        for u in fg.units:
            u.set_client()
    return fg, ground

FLAGS = {
    "zone_target": 10019, "ggw_target": 10046, "izlid_lase": 10047,
    "iceman_hdg_abs": 10080, "iceman_hdg_rel": 10081,
    "iceman_spd_abs": 10082, "iceman_spd_rel": 10083,
    "iceman_alt_abs": 10084, "iceman_alt_rel": 10085,
    "iceman_fly_to_stpt": 10086, "iceman_orbit_stpt": 10087, "iceman_hold": 10088,
}


def _pt(base, dx, dy):
    return mapping.Point(base.x + dx, base.y + dy, base._terrain)


def _f14bu(warnings):
    cls, warning = get_pending("F_14B_U")
    if warning:
        warnings.append(warning)
    return cls


# --------------------------------------------- PILOT + JESTER: IZLID strike
def build_backseat_izlid(m, recipe, blue_country, red_country, home_airport,
                         target_area, rng: random.Random, comms, warnings):
    """F-14B(U) PILOT-seat mission: you fly, Jester (AI RIO) works the pod.
    Player-paced: you call the sparkle and the cease from the F10 crew menu."""
    cls = _f14bu(warnings)

    convoy_pos = _pt(target_area, rng.uniform(-1500, 1500), rng.uniform(-1500, 1500))
    convoy = m.vehicle_group(red_country, "GGWTarget01", vehicles.Armor.BMP_2,
                             convoy_pos, heading=rng.uniform(0, 360), group_size=4)
    convoy.units[0].name = "GGWTarget01"
    m.triggers.add_triggerzone(convoy_pos, radius=2000, name="IZLID ZONE")

    ingress = _pt(target_area, -27000, -5000)
    egress = _pt(target_area, -30000, 15000)
    # STPT 1 ingress, 2 target, 3 egress. Ground-start from home per the wizard.
    f14, _ground = _player_flight(
        m, recipe, blue_country, "Victory 1", cls, home_airport,
        route=[(ingress, 4572, 760), (target_area, 4572, 600),
               (egress, 5486, 600)],
        group_size=1)

    flow = CrewFlow(m, recipe.crew_difficulty)
    flow.message_at_start(
        "CREW OPS - JESTER IZLID STRIKE (F-14B(U)). You have the jet; Jester has\n"
        "the back seat. Fly the profile to steerpoint 2 and run Jester's IZLID\n"
        "from the F10 CREW menu: sparkle, confirm effect, cease. Your calls.")

    lase = flow.add_command(
        "JESTER: IZLID on - sparkle the convoy",
        [SetFlagValue(FLAGS["ggw_target"], 0.01),
         SetFlagValue(FLAGS["izlid_lase"], 3.0)],
        feedback="Jester: IZLID on, sparkle on the convoy (GGWTarget01).",
        hint="Fly to the target area, then call JESTER on the F10 menu to lase.")

    flow.add_command(
        "JESTER: Cease lase",
        [SetFlagValue(FLAGS["izlid_lase"], 0)],
        after_flag=lase,
        feedback="Jester: IZLID off.")

    flow.on_group_dead("GGWTarget01", [],
                       feedback="GOOD EFFECT ON TARGET - convoy destroyed. Egress when ready.")

    comms.add("Flight", "Victory 1-1", f"{comms.freq('flight_common'):.3f}", "-",
              "F-14B(U) + Jester (crew menu on F10)")
    return f14


BRIEFING_BLOCK = """
== CREW OPS: JESTER IZLID STRIKE (F-14B(U), PILOT SEAT) ==
You fly; Jester works the back seat. Ingress to steerpoint 2, then run the
designation from the F10 CREW menu: IZLID on, confirm effect, cease. The
mission commands Jester through the Heatblur flag API on your calls.
"""


# ------------------------------------------------ RIO + ICEMAN: GCI intercept
def build_backseat_intercept(m, recipe, blue_country, red_country, home_airport,
                             target_area, rng: random.Random, comms, warnings):
    """F-14B(U) RIO-seat mission: Iceman (AI pilot) flies YOUR calls.
    He holds CAP until you commit from the F10 crew menu."""
    from dcs import planes as _planes
    cls = _f14bu(warnings)

    cap = mapping.Point((home_airport.position.x + target_area.x) / 2,
                        (home_airport.position.y + target_area.y) / 2,
                        target_area._terrain)
    bombers = m.flight_group_inflight(
        red_country, "Vandal 1", _planes.Tu_22M3,
        _pt(target_area, 60000, 40000), altitude=9000, speed=900, group_size=2)
    bombers.add_waypoint(home_airport.position, altitude=9000)

    # STPT 1 ingress, 2 CAP anchor, 3 threat axis. Ground-start from home.
    f14, _ground = _player_flight(
        m, recipe, blue_country, "Anytime 1", cls, home_airport,
        route=[(cap, 6096, 740), (cap, 6096, 600), (target_area, 7620, 600)],
        group_size=1)

    threat_brg = round(math.degrees(math.atan2(
        target_area.y - cap.y, target_area.x - cap.x)) % 360)

    flow = CrewFlow(m, recipe.crew_difficulty)
    flow.message_at_start(
        "CREW OPS - RIO GCI INTERCEPT (F-14B(U)). You're the RIO; Iceman has the\n"
        "jet and holds CAP until YOU commit from the F10 CREW menu. Work the\n"
        "AWG-9, build the picture, run the intercept. Two Backfires inbound.")
    from dcs.triggers import TriggerOnce
    from dcs.condition import TimeAfter
    t = TriggerOnce(comment="Iceman: establish CAP")
    t.rules.append(TimeAfter(15))
    t.actions.append(SetFlagValue(FLAGS["iceman_orbit_stpt"], 2))
    m.triggerrules.triggers.append(t)

    commit = flow.add_command(
        f"CREW: Commit - Iceman, vector {threat_brg:03d} on the raid",
        [SetFlagValue(FLAGS["iceman_hdg_abs"], threat_brg),
         SetFlagValue(FLAGS["iceman_spd_abs"], 550),
         SetFlagValue(FLAGS["iceman_alt_abs"], 25000)],
        feedback=f"Iceman: committing, heading {threat_brg:03d}, gate, climbing.",
        hint="Sort the raid in TWS. When you have the picture, COMMIT on the F10 menu.")

    flow.add_command(
        "CREW: Skip it - Iceman, back to CAP",
        [SetFlagValue(FLAGS["iceman_orbit_stpt"], 2)],
        after_flag=commit,
        feedback="Iceman: roger, resuming CAP orbit at steerpoint 2.")

    flow.add_command(
        "CREW: Iceman, hold what you've got",
        [SetFlagValue(FLAGS["iceman_hold"], 1)],
        after_flag=commit,
        feedback="Iceman: holding current heading and altitude.")

    flow.on_group_dead("Vandal 1", [],
                       feedback="SPLASH THE RAID - both Backfires down. "
                                "Send Iceman back to CAP or call the egress.")

    comms.add("Flight", "Anytime 1-1", f"{comms.freq('flight_common'):.3f}", "-",
              "F-14B(U) RIO + Iceman (crew menu on F10)")
    return f14


INTERCEPT_BRIEFING_BLOCK = """
== CREW OPS: RIO GCI INTERCEPT (F-14B(U), RIO SEAT) ==
You are the RIO; Iceman (AI pilot) flies your calls through the F10 CREW
menu: commit on the raid, hold, or recommit CAP. Two Backfires inbound high
and fast - find them on the AWG-9, build the geometry, run the intercept.
"""


# ---------------------------------------------- RIO: fleet defense (today's F-14)
def build_rio_fleet_defense(m, recipe, blue_country, red_country, home_airport,
                            target_area, rng: random.Random, comms, era, csg=None):
    """RIO fleet defense on TODAY'S F-14A/B (no flag API needed): solo via the
    in-cockpit Iceman (A-menu), or multiplayer human crew. The classic AWG-9
    problem: a regimental Backfire raid inbound on the force."""
    from dcs import planes as _planes
    from dcs.mission import StartType
    cat = _planes.F_14A_135_GR if era == "coldwar" else _planes.F_14B

    cap = mapping.Point((home_airport.position.x + target_area.x) / 2,
                        (home_airport.position.y + target_area.y) / 2,
                        target_area._terrain)
    raid = m.flight_group_inflight(
        red_country, "Raid 1", _planes.Tu_22M3,
        _pt(target_area, 80000, 50000), altitude=10000, speed=950, group_size=4)
    raid.add_waypoint(home_airport.position, altitude=10000)

    solo = recipe.slots <= 1
    from_deck = False
    if csg is not None:
        f14 = m.flight_group_from_unit(
            blue_country, "Anytime 1", cat, csg,
            start_type=StartType.Warm, group_size=1 if solo else 2)
        f14.add_waypoint(cap, altitude=7620)
        f14.add_waypoint(target_area, altitude=9144)
        if solo:
            f14.units[0].set_player()
        else:
            for u in f14.units:
                u.set_client()
        from_deck = True
        ground = True
    else:
        # Land base: ground-start from home per the wizard (cold/warm/runway).
        f14, ground = _player_flight(
            m, recipe, blue_country, "Anytime 1", cat, home_airport,
            route=[(cap, 7620, 740), (cap, 7620, 600), (target_area, 9144, 600)],
            group_size=1 if solo else 2)

    threat_brg = round(math.degrees(math.atan2(
        target_area.y - cap.y, target_area.x - cap.x)) % 360)

    flow = CrewFlow(m, recipe.crew_difficulty)
    if solo and from_deck:
        flow.message_at_start(
            "CREW OPS - FLEET DEFENSE (SOLO RIO, CARRIER START). You're on the boat.\n"
            "Cat-shot yourself, climb out, get level and trimmed - then JUMP TO THE\n"
            "BACK SEAT and Iceman takes the stick (A-menu: heading/altitude/speed).\n"
            "Run the AWG-9, sort the raid in TWS. GCI on the F10 menu.")
    elif solo and ground:
        flow.message_at_start(
            "CREW OPS - FLEET DEFENSE (SOLO RIO). You start on the ramp at home:\n"
            "start up, take off, get level and trimmed on the CAP leg - then JUMP\n"
            "TO THE BACK SEAT and Iceman takes the stick (A-menu: heading/altitude/\n"
            "speed). Run the AWG-9, sort the raid in TWS. GCI on the F10 menu.")
    elif solo:
        flow.message_at_start(
            "CREW OPS - FLEET DEFENSE (SOLO RIO). You're air-started level on CAP:\n"
            "trim the jet, then JUMP TO THE BACK SEAT - Iceman takes the stick.\n"
            "Command him with the A-menu (heading/altitude/speed). Run the AWG-9,\n"
            "sort the raid in TWS, time the Phoenix shots. GCI on the F10 menu.")
    else:
        flow.message_at_start(
            "CREW OPS - FLEET DEFENSE (RIO). Multiplayer crew mission: pilot up front,\n"
            "RIO in back. Four Backfires inbound on the force. RIO runs the AWG-9,\n"
            "sorts the raid in TWS, times the Phoenix shots. GCI on the F10 menu.")

    flow.add_command(
        "GCI: Picture",
        [],
        feedback=f"GCI: raid of four, BRA {threat_brg:03d} for 60, angels 33, "
                 f"speed 950. Backfires, hot on the force.",
        hint="RIO: call PICTURE from the F10 menu, then sort the raid in TWS.")

    flow.on_group_dead("Raid 1", [],
                       feedback="GRAND SLAM - raid destroyed. The force is safe. RTB.")

    comms.add("Flight", "Anytime 1-1", f"{comms.freq('flight_common'):.3f}", "-",
              f"{cat.id} (RIO crew mission)")
    return f14


RIO_BRIEFING_BLOCK = """
== CREW OPS: FLEET DEFENSE (RIO) ==
Four Backfires inbound on the force. The RIO owns the AWG-9: build the
picture in TWS, sort the raid, time the shots. GCI on the F10 menu.

SOLO (slots=1): you start on the ground at home (cold/warm/runway per your
pick) - take off and get level on the CAP leg, or cat-shot from the boat if the
carrier is home. Trim, jump to the back seat, and Iceman holds it - command
him with the A-menu (Ctrl+1-8). MULTIPLAYER (slots=2): two crew jets, human
pilot + human RIO each. (F-14B(U) adds full mission-scripted crew AI.)
"""
