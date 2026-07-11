"""Backseat Ops template pack — RIO/WSO-driven missions for the Heatblur F-4E.

Emits trigger logic against the Jester/Iceman PROXY flag API (shared by Heatblur/
IronMike for third-party RIO missions). The human flies the back seat; Iceman flies
the jet via flag commands and Jester designates via IZLID.

Flag reference (Heatblur):
  10019  select target from trigger zone
  10046  PROXY_Jester_BU_wpt_from_ggw_target   (0.01-0.99 -> unit "GGWTargetNN", value*100=id)
  10047  PROXY_Jester_BU_izlid_point_zone      (value*60 = lase seconds, -1 continuous, 0 stop)
  10080  PROXY_Iceman_set_heading_absolute
  10081  PROXY_Iceman_set_heading_relative
  10082  PROXY_Iceman_set_speed_absolute
  10083  PROXY_Iceman_set_speed_relative
  10084  PROXY_Iceman_set_altitude_absolute
  10085  PROXY_Iceman_set_altitude_relative
  10086  PROXY_Iceman_nav_fly_to_steerpoint
  10087  PROXY_Iceman_nav_orbit_steerpoint
  10088  PROXY_Iceman_hold_current

NOTE: template packs are the one sanctioned exception to the no-waypoints principle —
Iceman needs steerpoints to fly to. These are template waypoints, not user flight plans.
"""
import random
from dcs import mapping, planes, vehicles
from dcs.mission import StartType
from dcs.triggers import TriggerOnce, TriggerZoneCircular
from dcs.condition import TimeAfter
from dcs.action import SetFlagValue

FLAGS = {
    "ggw_target": 10046,
    "izlid_lase": 10047,
    "iceman_hdg_abs": 10080,
    "iceman_spd_abs": 10082,
    "iceman_alt_abs": 10084,
    "iceman_fly_to_stpt": 10086,
    "iceman_orbit_stpt": 10087,
    "iceman_hold": 10088,
}


def _flag_trigger(m, comment, seconds, flag, value):
    t = TriggerOnce(comment=comment)
    t.rules.append(TimeAfter(seconds))
    t.actions.append(SetFlagValue(flag, value))
    m.triggerrules.triggers.append(t)


def build_backseat_izlid(m, recipe, blue_country, red_country, home_airport,
                         target_area, rng: random.Random, comms):
    """Scenario: WSO IZLID designation run. Iceman flies the profile; the player
    works the back seat while Jester lases a moving target ('GGWTarget01')."""

    # Target: red convoy near the target area, named for the GGW flag convention
    convoy_pos = mapping.Point(
        target_area.x + rng.uniform(-1500, 1500),
        target_area.y + rng.uniform(-1500, 1500), target_area._terrain)
    convoy = m.vehicle_group(red_country, "GGWTarget01",
                             vehicles.Armor.BMP_2, convoy_pos,
                             heading=rng.uniform(0, 360), group_size=4)
    convoy.units[0].name = "GGWTarget01"

    # Trigger zone over the target for the zone-select workflow
    zone = m.triggers.add_triggerzone(convoy_pos, radius=2000, name="IZLID ZONE")

    # Player F-4E, air start 15nm out, steerpoint 2 on the target
    ingress = mapping.Point(target_area.x - 27000, target_area.y - 5000,
                            target_area._terrain)
    f4 = m.flight_group_inflight(
        blue_country, "Rhino 1", planes.F_4E_45MC, ingress,
        altitude=4572, speed=760, group_size=1)
    f4.add_waypoint(target_area, altitude=4572)         # STPT 2: target
    egress = mapping.Point(target_area.x - 30000, target_area.y + 15000,
                           target_area._terrain)
    f4.add_waypoint(egress, altitude=5486)              # STPT 3: egress
    f4.units[0].set_player() if recipe.slots <= 1 else [u.set_client() for u in f4.units]

    # Scripted crew: Iceman flies, Jester designates
    _flag_trigger(m, "Iceman: fly to STPT 2 (target)", 20,
                  FLAGS["iceman_fly_to_stpt"], 2)
    _flag_trigger(m, "Iceman: hold 15k ft", 25, FLAGS["iceman_alt_abs"], 15000)
    _flag_trigger(m, "Jester: source = GGWTarget01", 60,
                  FLAGS["ggw_target"], 0.01)
    _flag_trigger(m, "Jester: IZLID lase 3 min", 90,
                  FLAGS["izlid_lase"], 3.0)
    _flag_trigger(m, "Iceman: orbit STPT 2 during lase", 95,
                  FLAGS["iceman_orbit_stpt"], 2)
    _flag_trigger(m, "Jester: stop lasing", 300, FLAGS["izlid_lase"], 0)
    _flag_trigger(m, "Iceman: egress to STPT 3", 305,
                  FLAGS["iceman_fly_to_stpt"], 3)

    comms.add("Flight", "Rhino 1-1", "305.00", "-", "F-4E Backseat Ops")
    return f4


BRIEFING_BLOCK = """
== BACKSEAT OPS: IZLID DESIGNATION ==
You are the WSO. Iceman has the jet - he will ingress to the target area,
orbit while Jester designates the convoy (GGWTarget01) with the IZLID,
then egress. Work your sensors, monitor the lase, and manage the mission
from the back seat. Do not touch the stick unless things go wrong.

Timeline: T+20s Iceman proceeds to STPT 2 / T+90s IZLID on for 3 min /
T+5min egress to STPT 3.
"""
