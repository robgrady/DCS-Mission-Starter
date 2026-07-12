"""Crew Ops template packs — RIO/WSO-driven missions.

THE BACKSEAT CONTRACT: the mission flies the jet; the player runs the mission.
Scenarios are player-paced via the F10 crew menu (see crewops.py), not timers.

WSO (F-4E, available today): Iceman flies via the Heatblur PROXY flag API,
Jester designates. Shared by IronMike for third-party RIO missions.
RIO (F-14, available today in MULTIPLAYER): one jet, human pilot + human RIO.
Solo F-14 RIO waits on the F-14B(U)'s new crew AI — same template machinery
will drive it when Heatblur ships the flags (pending-module pattern).

Heatblur flag reference:
  10019 zone target select | 10046 GGW target (0.01-0.99 -> "GGWTargetNN")
  10047 IZLID lase (value*60s, -1 cont, 0 stop)
  10080/81 hdg abs/rel | 10082/83 spd abs/rel | 10084/85 alt abs/rel
  10086 fly-to-stpt | 10087 orbit stpt | 10088 hold
NOTE: templates are the sanctioned exception to the no-waypoints principle —
the AI pilot needs steerpoints. These are template waypoints, not user plans.
"""
import math
import random
from dcs import mapping, planes, vehicles
from dcs.action import SetFlagValue

from .crewops import CrewFlow

FLAGS = {
    "ggw_target": 10046, "izlid_lase": 10047,
    "iceman_hdg_abs": 10080, "iceman_spd_abs": 10082, "iceman_alt_abs": 10084,
    "iceman_fly_to_stpt": 10086, "iceman_orbit_stpt": 10087, "iceman_hold": 10088,
}


def _pt(base, dx, dy):
    return mapping.Point(base.x + dx, base.y + dy, base._terrain)


# ---------------------------------------------------------------- WSO: IZLID
def build_backseat_izlid(m, recipe, blue_country, red_country, home_airport,
                         target_area, rng: random.Random, comms):
    """WSO IZLID designation run — player-paced. You call the ingress, the
    lase, and the egress from the back seat; Iceman and Jester execute."""
    convoy_pos = _pt(target_area, rng.uniform(-1500, 1500), rng.uniform(-1500, 1500))
    convoy = m.vehicle_group(red_country, "GGWTarget01", vehicles.Armor.BMP_2,
                             convoy_pos, heading=rng.uniform(0, 360), group_size=4)
    convoy.units[0].name = "GGWTarget01"
    m.triggers.add_triggerzone(convoy_pos, radius=2000, name="IZLID ZONE")

    ingress = _pt(target_area, -27000, -5000)
    f4 = m.flight_group_inflight(blue_country, "Rhino 1", planes.F_4E_45MC,
                                 ingress, altitude=4572, speed=760, group_size=1)
    f4.add_waypoint(target_area, altitude=4572)          # STPT 2: target
    f4.add_waypoint(_pt(target_area, -30000, 15000), altitude=5486)  # STPT 3: egress
    f4.units[0].set_player() if recipe.slots <= 1 else [u.set_client() for u in f4.units]

    flow = CrewFlow(m, recipe.crew_difficulty)
    flow.message_at_start(
        "BACKSEAT OPS - IZLID DESIGNATION. You are the WSO; Iceman has the jet.\n"
        "Run the mission from the F10 CREW menu: commit, lase, egress - your calls.")

    commit = flow.add_command(
        "CREW: Commit - Iceman, take us to the target",
        [SetFlagValue(FLAGS["iceman_fly_to_stpt"], 2),
         SetFlagValue(FLAGS["iceman_alt_abs"], 15000)],
        feedback="Iceman: roger, coming on course for steerpoint 2, base plus fifteen.",
        hint="Open the F10 menu and COMMIT when your systems are set up.")

    lase = flow.add_command(
        "JESTER: IZLID on - sparkle the convoy",
        [SetFlagValue(FLAGS["ggw_target"], 0.01),
         SetFlagValue(FLAGS["izlid_lase"], 3.0),
         SetFlagValue(FLAGS["iceman_orbit_stpt"], 2)],
        after_flag=commit,
        feedback="Jester: IZLID on, sparkle on the convoy. Iceman holding overhead.",
        hint="In the target area, call JESTER to put the IZLID on. Watch the sparkle.")

    flow.add_command(
        "JESTER: Cease lase",
        [SetFlagValue(FLAGS["izlid_lase"], 0)],
        after_flag=lase,
        feedback="Jester: IZLID off.")

    flow.add_command(
        "CREW: Egress - take us home",
        [SetFlagValue(FLAGS["izlid_lase"], 0),
         SetFlagValue(FLAGS["iceman_fly_to_stpt"], 3)],
        after_flag=commit,
        feedback="Iceman: roger, egressing to steerpoint 3.")

    flow.on_group_dead("GGWTarget01", [],
                       feedback="GOOD EFFECT ON TARGET - convoy destroyed. "
                                "Call the egress when you're ready.")

    comms.add("Flight", "Rhino 1-1", f"{comms.freq('flight_common'):.2f}", "-",
              "F-4E Backseat Ops (crew menu on F10)")
    return f4


BRIEFING_BLOCK = """
== BACKSEAT OPS: IZLID DESIGNATION (WSO) ==
You are the WSO. Iceman has the jet - YOU run the mission from the F10 CREW
menu: commit the ingress, put Jester's IZLID on the convoy (GGWTarget01),
confirm effect, call the egress. The jet responds to your calls, not a script.
"""


# ------------------------------------------------------------ WSO: intercept
def build_backseat_intercept(m, recipe, blue_country, red_country, home_airport,
                             target_area, rng: random.Random, comms):
    """WSO GCI intercept — player-paced. Iceman holds CAP until YOU commit."""
    from dcs import planes as _planes
    cap = mapping.Point((home_airport.position.x + target_area.x) / 2,
                        (home_airport.position.y + target_area.y) / 2,
                        target_area._terrain)
    bombers = m.flight_group_inflight(
        red_country, "Vandal 1", _planes.Tu_22M3,
        _pt(target_area, 60000, 40000), altitude=9000, speed=900, group_size=2)
    bombers.add_waypoint(home_airport.position, altitude=9000)

    f4 = m.flight_group_inflight(blue_country, "Rhino 1", planes.F_4E_45MC,
                                 cap, altitude=6096, speed=740, group_size=1)
    f4.add_waypoint(cap, altitude=6096)
    f4.add_waypoint(target_area, altitude=7620)
    f4.units[0].set_player() if recipe.slots <= 1 else [u.set_client() for u in f4.units]

    threat_brg = round(math.degrees(math.atan2(
        target_area.y - cap.y, target_area.x - cap.x)) % 360)

    flow = CrewFlow(m, recipe.crew_difficulty)
    flow.message_at_start(
        "BACKSEAT OPS - GCI INTERCEPT. Two Backfires inbound. Iceman holds CAP\n"
        "until YOU commit from the F10 CREW menu. Find them, build the geometry,\n"
        "run the intercept from the back seat.")
    # Iceman establishes the CAP orbit immediately
    flow.on_flag(0, [], comment="noop")
    from dcs.triggers import TriggerOnce
    from dcs.condition import TimeAfter
    t = TriggerOnce(comment="Iceman: establish CAP")
    t.rules.append(TimeAfter(15))
    t.actions.append(SetFlagValue(FLAGS["iceman_orbit_stpt"], 2))
    m.triggerrules.triggers.append(t)

    commit = flow.add_command(
        f"CREW: Commit - vector {threat_brg:03d} on the raid",
        [SetFlagValue(FLAGS["iceman_hdg_abs"], threat_brg),
         SetFlagValue(FLAGS["iceman_spd_abs"], 550),
         SetFlagValue(FLAGS["iceman_alt_abs"], 25000)],
        feedback=f"Iceman: committing, heading {threat_brg:03d}, gate, climbing to base plus 25.",
        hint="Work the radar. When you have the picture, COMMIT from the F10 menu.")

    flow.add_command(
        "CREW: Skip it - back to CAP",
        [SetFlagValue(FLAGS["iceman_orbit_stpt"], 2)],
        after_flag=commit,
        feedback="Iceman: roger, resuming CAP orbit.")

    flow.on_group_dead("Vandal 1", [],
                       feedback="SPLASH THE RAID - both Backfires down. "
                                "Take us back to CAP or call the egress.")

    comms.add("Flight", "Rhino 1-1", f"{comms.freq('flight_common'):.2f}", "-",
              "F-4E GCI Intercept (crew menu on F10)")
    return f4


INTERCEPT_BRIEFING_BLOCK = """
== BACKSEAT OPS: GCI INTERCEPT (WSO) ==
You are the WSO. Iceman holds CAP until YOU commit from the F10 CREW menu.
Two Backfires inbound high and fast - find them on the radar, commit the
intercept, direct the engagement. Iceman flies your calls.
NOTE: Iceman speed/altitude flag units assumed kts/ft pending Heatblur docs.
"""


# ---------------------------------------------------- RIO: fleet defense (MP)
def build_rio_fleet_defense(m, recipe, blue_country, red_country, home_airport,
                            target_area, rng: random.Random, comms, era, csg=None):
    """RIO fleet defense — MULTIPLAYER crew mission (human pilot + human RIO in
    one Tomcat). The classic AWG-9 problem: a regimental Backfire raid inbound
    on the force. GCI picture and commit calls come through the F10 crew menu."""
    from dcs import planes as _planes
    cat = _planes.F_14A_135_GR if era == "coldwar" else _planes.F_14B

    cap = mapping.Point((home_airport.position.x + target_area.x) / 2,
                        (home_airport.position.y + target_area.y) / 2,
                        target_area._terrain)
    raid = m.flight_group_inflight(
        red_country, "Raid 1", _planes.Tu_22M3,
        _pt(target_area, 80000, 50000), altitude=10000, speed=950, group_size=4)
    raid.add_waypoint(home_airport.position, altitude=10000)

    solo = recipe.slots <= 1
    from dcs.mission import StartType
    if csg is not None:
        # CARRIER START: the mission begins on the boat. Solo RIOs cat-shot
        # themselves, level off, then swap seats for Iceman.
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
        # SOLO RIO: air start = level flight = Iceman-ready. Spawn in the front,
        # trim level, jump to the back seat; Iceman holds the jet (A-menu commands).
        f14.units[0].set_player()
    else:
        for u in f14.units:
            u.set_client()      # MP: human pilot + human RIO crew each jet

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
              f"{cat.id} x2 crew jets (pilot+RIO per jet, multiplayer)")
    return f14


RIO_BRIEFING_BLOCK = """
== CREW OPS: FLEET DEFENSE (RIO) ==
Four Backfires inbound on the force. The RIO owns the AWG-9: build the
picture in TWS, sort the raid, time the shots. GCI on the F10 menu.

SOLO (slots=1): you air-start level on CAP. Trim the jet, jump to the back
seat, and Iceman holds it - command him with the A-menu (heading/altitude/
speed, Ctrl+1-8). He is a basic autopilot: set his course, then work the
radar. MULTIPLAYER (slots=2): two crew jets, human pilot + human RIO each.
(Mission-scripted pilot control arrives with the F-14B(U)'s new crew AI.)
"""
