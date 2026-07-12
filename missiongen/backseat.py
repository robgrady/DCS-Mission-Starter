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

The F-14B(U) is pre-release: templates use the provisional type id (pending-
module pattern) and generation attaches a warning until Heatblur ships.

NOTE: templates are the sanctioned exception to the no-waypoints principle —
the AI crew needs steerpoints. These are template waypoints, not user plans.
"""
import math
import random
from dcs import mapping, vehicles
from dcs.action import SetFlagValue

from .crewops import CrewFlow
from .pending import get_pending

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
    f14 = m.flight_group_inflight(blue_country, "Victory 1", cls,
                                  ingress, altitude=4572, speed=760, group_size=1)
    f14.add_waypoint(target_area, altitude=4572)          # STPT 2: target
    f14.add_waypoint(_pt(target_area, -30000, 15000), altitude=5486)  # STPT 3: egress
    f14.units[0].set_player() if recipe.slots <= 1 else [u.set_client() for u in f14.units]

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

    comms.add("Flight", "Victory 1-1", f"{comms.freq('flight_common'):.2f}", "-",
              "F-14B(U) + Jester (crew menu on F10)")
    return f14


BRIEFING_BLOCK = """
== CREW OPS: JESTER IZLID STRIKE (F-14B(U), PILOT SEAT) ==
You fly; Jester works the back seat. Ingress to steerpoint 2, then run the
designation from the F10 CREW menu: IZLID on, confirm effect, cease. The
mission commands Jester through the Heatblur flag API on your calls.
NOTE: F-14B(U) is pre-release - this mission uses the provisional type id.
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

    f14 = m.flight_group_inflight(blue_country, "Anytime 1", cls,
                                  cap, altitude=6096, speed=740, group_size=1)
    f14.add_waypoint(cap, altitude=6096)          # STPT 2: CAP anchor
    f14.add_waypoint(target_area, altitude=7620)  # STPT 3: threat axis
    f14.units[0].set_player() if recipe.slots <= 1 else [u.set_client() for u in f14.units]

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

    comms.add("Flight", "Anytime 1-1", f"{comms.freq('flight_common'):.2f}", "-",
              "F-14B(U) RIO + Iceman (crew menu on F10)")
    return f14


INTERCEPT_BRIEFING_BLOCK = """
== CREW OPS: RIO GCI INTERCEPT (F-14B(U), RIO SEAT) ==
You are the RIO; Iceman (AI pilot) flies your calls through the F10 CREW
menu: commit on the raid, hold, or recommit CAP. Two Backfires inbound high
and fast - find them on the AWG-9, build the geometry, run the intercept.
NOTE: F-14B(U) is pre-release - provisional type id; Iceman flag value units
(kts/ft assumed) pending Heatblur confirmation.
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
    if csg is not None:
        f14 = m.flight_group_from_unit(
            blue_country, "Anytime 1", cat, csg,
            start_type=StartType.Warm, group_size=1 if solo else 2)
    else:
        f14 = m.flight_group_inflight(blue_country, "Anytime 1", cat,
                                      cap, altitude=7620, speed=740,
                                      group_size=1 if solo else 2)
    f14.add_waypoint(cap, altitude=7620)
    f14.add_waypoint(target_area, altitude=9144)
    if solo:
        f14.units[0].set_player()
    else:
        for u in f14.units:
            u.set_client()

    threat_brg = round(math.degrees(math.atan2(
        target_area.y - cap.y, target_area.x - cap.x)) % 360)

    flow = CrewFlow(m, recipe.crew_difficulty)
    if solo and csg is not None:
        flow.message_at_start(
            "CREW OPS - FLEET DEFENSE (SOLO RIO, CARRIER START). You're on the boat.\n"
            "Cat-shot yourself, climb out, get level and trimmed - then JUMP TO THE\n"
            "BACK SEAT and Iceman takes the stick (A-menu: heading/altitude/speed).\n"
            "Run the AWG-9, sort the raid in TWS. GCI on the F10 menu.")
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

    comms.add("Flight", "Anytime 1-1", f"{comms.freq('flight_common'):.2f}", "-",
              f"{cat.id} (RIO crew mission)")
    return f14


RIO_BRIEFING_BLOCK = """
== CREW OPS: FLEET DEFENSE (RIO) ==
Four Backfires inbound on the force. The RIO owns the AWG-9: build the
picture in TWS, sort the raid, time the shots. GCI on the F10 menu.

SOLO (slots=1): you air-start level on CAP (or cat-shot from the boat if the
carrier is home). Trim, jump to the back seat, and Iceman holds it - command
him with the A-menu (Ctrl+1-8). MULTIPLAYER (slots=2): two crew jets, human
pilot + human RIO each. (F-14B(U) adds full mission-scripted crew AI.)
"""
