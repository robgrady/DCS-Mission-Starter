#!/usr/bin/env python3
"""Build the two First Flight DCS sorties, campaign descriptor, and briefing facts.

Run from the project root with PYTHONPATH=.:vendor. This content build uses the
vendored PyDCS writer and native Mission Editor rules. It reports authored file
facts; a current DCS/VNAO installation is needed to fly and accept the package.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from dcs import action, condition, lua, mapping, task, triggers
from dcs.drawing.drawing import Rgba
from dcs.goals import Goal
from dcs.mission import Mission, StartType
from dcs.planes import PlaneType
from dcs.terrain import Caucasus
from dcs.terrain.terrain import Airport, MapView

from missiongen.artifacts import _normalize_zip_times
from missiongen.resolver import load_json

TITLE = "First Flight - Familiarization"
NATIVE_TYPE = "T-45"
MOD_VERSION = "1.02"
MOD_SOURCE = "https://forum.dcs.world/topic/203816-vnao-t-45-goshawk/?comment=5571117&do=findComment"
AIRFIELD_CHART = "https://server.3rd-wing.net/public/Manuels%20DCS/Aerodrome%20Charts%20EN.pdf"
DATE = datetime(2019, 9, 18, 11, 0, tzinfo=timezone.utc)
NM = 1852
FEET_TO_METRES = 0.3048
HELP = 203
STEP = 201
DWELL = 202
DONE = 299
HELP_ITEM = "FAM: Show current step"
BASE_POINTS = 50
COMPLETION_POINTS = 50
AIR_START_SPEED_KT = 240
AIR_START_ALT_FT = 3500
LEVEL_LOW_FT = 3000
LEVEL_HIGH_FT = 4000
LEVEL_SECONDS = 20
HOLD_SECONDS = 3
FUEL_KG = 950


class Goshawk(PlaneType):
    """Package-local PyDCS descriptor, without adding a global catalog entry."""

    id = NATIVE_TYPE
    name = "VNAO T-45C Goshawk"
    flyable = True
    task_default = task.Nothing
    tasks = [task.Nothing]
    payloads = {}


def point_facts(point: mapping.Point) -> dict:
    latlng = point.latlng()
    return {"x": point.x, "y": point.y, "lat": latlng.lat, "lon": latlng.lng}


def route_point(name: str, point: mapping.Point, altitude_m: float) -> dict:
    return {"name": name, **point_facts(point), "altitude_m": altitude_m}


def make_mission() -> tuple[Mission, Airport]:
    mission = Mission(Caucasus())
    mission.start_time = DATE
    # Matches the native requirement in VNAO v1.02’s Caucasus ILS QuickStart.
    mission.required_modules = {NATIVE_TYPE: NATIVE_TYPE}
    mission.usedModules = {}
    home = mission.terrain.airports["Kobuleti"]
    home.set_blue()
    return mission, home


def init_player(group, heading: float):
    unit = group.units[0]
    unit.set_player()
    unit.heading = heading
    unit.psi = -math.radians(heading)
    unit.fuel = FUEL_KG
    unit.gun = 0
    unit.reset_loadout()
    group.manualHeading = True  # Keep the apron facing instead of aiming at the next waypoint.
    group.hidden = False
    group.hidden_on_planner = False
    return unit


def rule(mission: Mission, trigger_type, name: str, conditions, actions) -> None:
    trigger = trigger_type(comment=name)
    for item in conditions:
        trigger.add_condition(item)
    for item in actions:
        trigger.add_action(item)
    mission.triggerrules.triggers.append(trigger)


def caption(mission: Mission, text: str, seconds: int = 14):
    return action.MessageToAll(mission.string(text), seconds, True)


def coach(mission: Mission, steps: list[str], completion: str) -> None:
    initial = [
        action.SetFlagValue(STEP, 1),
        action.AddRadioItem(mission.string(HELP_ITEM), HELP, 1),
    ]
    rule(mission, triggers.TriggerStart, "FAM - initialize", [], initial)
    rule(mission, triggers.TriggerOnce, "FAM - opening cue", [condition.TimeAfter(2)], [
        caption(mission, steps[0] + "  F10 Other: " + HELP_ITEM + ".", 20),
    ])
    for index, text in enumerate(steps, 1):
        rule(mission, triggers.TriggerContinious, f"FAM - help step {index}", [
            condition.FlagIsTrue(HELP), condition.FlagEquals(STEP, index),
            condition.FlagIsFalse(DONE),
        ], [action.ClearFlag(HELP), caption(mission, text)])
    rule(mission, triggers.TriggerContinious, "FAM - help after completion", [
        condition.FlagIsTrue(HELP), condition.FlagIsTrue(DONE),
    ], [action.ClearFlag(HELP), caption(mission, completion)])
    baseline = Goal("FAM - retry score", BASE_POINTS)
    baseline.rules.append(condition.TimeAfter(1))
    mission.goals.add_offline(baseline)
    passed = Goal("FAM - objectives complete", COMPLETION_POINTS)
    passed.rules.append(condition.FlagIsTrue(DONE))
    mission.goals.add_offline(passed)


def dwell(mission: Mission, name: str, step: int, qualified: list, disqualified: list,
          seconds: int, next_step: str) -> None:
    active = condition.FlagEquals(STEP, step)
    rule(mission, triggers.TriggerContinious, f"FAM - {name} timer", [
        active, condition.FlagIsFalse(DWELL), *qualified,
    ], [action.SetFlag(DWELL)])
    for index, rejected in enumerate(disqualified, 1):
        rule(mission, triggers.TriggerContinious, f"FAM - {name} reset {index}", [
            active, condition.FlagIsTrue(DWELL), rejected,
        ], [action.ClearFlag(DWELL)])
    rule(mission, triggers.TriggerOnce, f"FAM - {name} complete", [
        active, condition.FlagIsTrue(DWELL), condition.TimeSinceFlag(DWELL, seconds), *qualified,
    ], [action.ClearFlag(DWELL), action.SetFlagValue(STEP, step + 1), caption(mission, next_step)])


def circle(mission: Mission, name: str, point: mapping.Point, radius: float) -> dict:
    zone = mission.triggers.add_triggerzone(point, radius=radius, hidden=True, name=name)
    layer = mission.drawings.get_layer_by_name("Common")
    outline = Rgba(160, 222, 252, 255)
    fill = Rgba(31, 78, 137, 60)
    layer.add_circle(point, radius, color=outline, fill=fill, line_thickness=2)
    layer.add_text_box(point.point_from_heading(0, radius), name,
                       color=outline, fill=Rgba(0, 32, 91, 200), font_size=16)
    return {"id": zone.id, "name": name, **point_facts(point), "radius_m": radius}


def add_map_label(mission: Mission, point: mapping.Point, label: str) -> None:
    mission.drawings.get_layer_by_name("Common").add_text_box(
        point, label, color=Rgba(160, 222, 252, 255), fill=Rgba(0, 32, 91, 200), font_size=16,
    )


def briefing(mission: Mission, facts: dict) -> None:
    mission.set_sortie_text(f"{facts['id']} {facts['title']}")
    mission.set_description_bluetask_text(facts["objective"])
    mission.set_description_text("\n\n".join([
        f"{TITLE} | {facts['id']} {facts['title']}",
        "Solo, unarmed DCS training in a VNAO T-45C Goshawk v1.02 on Caucasus.",
        facts["start"],
        "\n".join(f"{i}. {step}" for i, step in enumerate(facts["steps"], 1)),
        facts["completion"],
        f"F10 Other: {HELP_ITEM}. {facts['retry']}",
        "FAM-inspired DCS adaptation of CNATRA P-1212 (Rev. 02-19).",
    ]))


def first_flight() -> tuple[Mission, dict]:
    mission, home = make_mission()
    aircraft_start = home.position.point_from_heading(275, 9 * NM)
    level_mark = aircraft_start.point_from_heading(270, 2 * NM)
    turn_mark = level_mark.point_from_heading(330, 6 * NM)
    altitude = AIR_START_ALT_FT * FEET_TO_METRES
    speed_kmh = AIR_START_SPEED_KT * 1.852
    group = mission.flight_group_inflight(
        mission.country("USA"), "FAM-01 Player", Goshawk, aircraft_start, altitude, speed=speed_kmh,
    )
    unit = init_player(group, 270)
    group.points[0].name = "START"
    group.add_waypoint(level_mark, altitude, speed=speed_kmh, name="LEVEL REFERENCE")
    group.add_waypoint(turn_mark, altitude, speed=speed_kmh, name="TURN GATE")
    mission.map = MapView(level_mark, mission.terrain, zoom=48000)
    add_map_label(mission, aircraft_start, "START")
    gate = circle(mission, "TURN GATE", turn_mark, 1.45 * NM)
    band_min = LEVEL_LOW_FT * FEET_TO_METRES
    band_max = LEVEL_HIGH_FT * FEET_TO_METRES
    gate.update({"min_altitude_msl_m": 2000 * FEET_TO_METRES, "max_altitude_msl_m": 6000 * FEET_TO_METRES})
    steps = [
        f"Hold {LEVEL_LOW_FT:,} to {LEVEL_HIGH_FT:,} ft MSL with bank within 10 degrees for {LEVEL_SECONDS} seconds.",
        "Turn right toward TURN GATE on the F10 map. Cross it between 2,000 and 6,000 ft MSL.",
    ]
    completion = "FAM-01 complete. End the sortie to see the DCS debrief. Landing is optional."
    retry = "Use the DCS Restart command to practice again. Check pitch, roll and throttle bindings if the jet is hard to settle."
    coach(mission, steps, completion)
    dwell(mission, "level flight", 1, [
        condition.UnitAlive(unit.id), condition.TimeAfter(6),
        condition.UnitAltitudeHigher(unit.id, band_min),
        condition.UnitAltitudeLower(unit.id, band_max),
        condition.UnitBankWithin(unit.id, -10, 10),
    ], [
        condition.UnitAltitudeLower(unit.id, band_min),
        condition.UnitAltitudeHigher(unit.id, band_max),
        condition.UnitBankWithin(unit.id, -180, -10),
        condition.UnitBankWithin(unit.id, 10, 180),
    ], LEVEL_SECONDS, steps[1])
    rule(mission, triggers.TriggerOnce, "FAM - turn gate complete", [
        condition.FlagEquals(STEP, 2), condition.UnitAlive(unit.id),
        condition.UnitInZone(unit.id, gate["id"]),
        condition.UnitAltitudeHigher(unit.id, gate["min_altitude_msl_m"]),
        condition.UnitAltitudeLower(unit.id, gate["max_altitude_msl_m"]),
    ], [action.SetFlag(DONE), caption(mission, completion, 24)])
    facts = {
        "id": "FAM-01", "title": "First Flight", "filename": "FAM-01-First-Flight.miz",
        "start": f"Airborne offshore at {AIR_START_ALT_FT:,} ft MSL and {AIR_START_SPEED_KT} kt TAS.",
        "start_mode": "air", "start_altitude_ft_msl": AIR_START_ALT_FT,
        "start_speed_kt_tas": AIR_START_SPEED_KT, "start_heading_deg_grid": 270,
        "objective": "Settle into level flight and fly one coached turn to the offshore gate.",
        "steps": steps, "gates": [gate], "completion": completion, "retry": retry,
        "level_flight": {
            "min_altitude_ft_msl": LEVEL_LOW_FT, "max_altitude_ft_msl": LEVEL_HIGH_FT,
            "max_abs_bank_deg": 10, "seconds": LEVEL_SECONDS, "enabled_after_seconds": 6,
        },
        "estimated_minutes": "5-7",
        "source_sections": "CNATRA P-1212 (Rev. 02-19), §§301-303 (printed pp. 3-1 to 3-6).",
        "route": [
            route_point("START", aircraft_start, altitude),
            route_point("LEVEL REFERENCE", level_mark, altitude),
            route_point("TURN GATE", turn_mark, altitude),
        ],
    }
    briefing(mission, facts)
    return mission, facts


def ramp_to_air() -> tuple[Mission, dict]:
    mission, home = make_mission()
    terrain = mission.terrain
    stand = next(slot for slot in home.parking_slots if slot.slot_name == "31" and slot.airplanes)
    heading = load_json("parking_headings")["caucasus"]["Kobuleti"]["slots"][stand.slot_name]
    # WGS84 positions from the DCS Kobuleti GND 01 ground chart, rev 3.5.0.
    threshold_07 = mapping.Point.from_latlng(mapping.LatLng(41 + 55.640 / 60, 41 + 50.975 / 60), terrain)
    threshold_25 = mapping.Point.from_latlng(mapping.LatLng(41 + 55.952 / 60, 41 + 52.642 / 60), terrain)
    p3 = mapping.Point.from_latlng(mapping.LatLng(41 + 55.867 / 60, 41 + 52.345 / 60), terrain)
    runway_heading = threshold_25.heading_between_point(threshold_07)
    sea_mark = threshold_07.point_from_heading(runway_heading, 7.5 * NM)
    group = mission.flight_group_from_airport(
        mission.country("USA"), "FAM-02 Player", Goshawk, home, start_type=StartType.Warm, parking_slots=[stand],
    )
    unit = init_player(group, heading)
    unit.alt = group.points[0].alt = 18
    group.points[0].name = "HOT PARK 31"
    group.add_waypoint(threshold_07, 180, speed=185, name="AIRBORNE")
    group.add_waypoint(sea_mark, 600, speed=410, name="SEA GATE")
    mission.map = MapView(home.position, terrain, zoom=24000)
    hold = circle(mission, "P3 HOLD B", p3, 55)
    hold.update({"max_altitude_agl_m": 8, "max_speed_mps": 2, "seconds": HOLD_SECONDS})
    add_map_label(mission, stand.position, "HOT PARK 31")
    takeoff = circle(mission, "AIRBORNE", threshold_07, 2200)
    takeoff.update({"min_altitude_agl_m": 80 * FEET_TO_METRES, "max_altitude_agl_m": 1300 * FEET_TO_METRES})
    depart = circle(mission, "SEA GATE", sea_mark, 2700)
    depart.update({"min_altitude_agl_m": 1000 * FEET_TO_METRES, "max_altitude_agl_m": 3600 * FEET_TO_METRES})
    runway_center = threshold_25.lerp(threshold_07, 0.5)
    corners = [
        threshold_25.point_from_heading(runway_heading + 90, 36),
        threshold_07.point_from_heading(runway_heading + 90, 36),
        threshold_07.point_from_heading(runway_heading - 90, 36),
        threshold_25.point_from_heading(runway_heading - 90, 36),
    ]
    runway = mission.triggers.add_triggerzone_quad(
        runway_center, corners, hidden=True, name="RWY 25 rolling zone",
    )
    steps = [
        f"Follow the paved taxiway to P3 HOLD B on the F10 map. Stop there for {HOLD_SECONDS} seconds.",
        "Take off on runway 25 and climb through AIRBORNE between 80 and 1,300 ft AGL.",
        "Continue offshore to SEA GATE. Cross it between 1,000 and 3,600 ft AGL.",
    ]
    completion = "FAM-02 complete. End the sortie to see the DCS debrief. Landing is optional."
    retry = "Restart from parking if you leave without registering P3 HOLD B or AIRBORNE. The F10 reminder shows the current step."
    coach(mission, steps, completion)
    dwell(mission, "hold-point stop", 1, [
        condition.UnitAlive(unit.id), condition.UnitInZone(unit.id, hold["id"]),
        condition.UnitAltitudeLowerAGL(unit.id, hold["max_altitude_agl_m"]),
        condition.UnitSpeedLower(unit.id, hold["max_speed_mps"]),
    ], [
        condition.UnitOutsideZone(unit.id, hold["id"]),
        condition.UnitAltitudeHigherAGL(unit.id, hold["max_altitude_agl_m"]),
        condition.UnitSpeedHigher(unit.id, hold["max_speed_mps"]),
    ], HOLD_SECONDS, steps[1])
    runway_roll = 204
    rule(mission, triggers.TriggerOnce, "FAM - runway 25 roll", [
        condition.FlagEquals(STEP, 2), condition.UnitAlive(unit.id),
        condition.UnitInZone(unit.id, runway.id),
        condition.UnitAltitudeLowerAGL(unit.id, 8), condition.UnitSpeedHigher(unit.id, 12),
        condition.UnitHeadingWithin(unit.id, runway_heading - 40, runway_heading + 40),
    ], [action.SetFlag(runway_roll)])
    rule(mission, triggers.TriggerOnce, "FAM - airborne gate", [
        condition.FlagEquals(STEP, 2), condition.FlagIsTrue(runway_roll),
        condition.UnitAlive(unit.id), condition.UnitInZone(unit.id, takeoff["id"]),
        condition.UnitAltitudeHigherAGL(unit.id, takeoff["min_altitude_agl_m"]),
        condition.UnitAltitudeLowerAGL(unit.id, takeoff["max_altitude_agl_m"]),
    ], [action.SetFlagValue(STEP, 3), caption(mission, steps[2])])
    rule(mission, triggers.TriggerOnce, "FAM - sea gate complete", [
        condition.FlagEquals(STEP, 3), condition.UnitAlive(unit.id),
        condition.UnitInZone(unit.id, depart["id"]),
        condition.UnitAltitudeHigherAGL(unit.id, depart["min_altitude_agl_m"]),
        condition.UnitAltitudeLowerAGL(unit.id, depart["max_altitude_agl_m"]),
    ], [action.SetFlag(DONE), caption(mission, completion, 24)])
    facts = {
        "id": "FAM-02", "title": "Ramp to Air", "filename": "FAM-02-Ramp-to-Air.miz",
        "start": "Hot parking at Kobuleti stand 31. The jet starts with its engine running.",
        "start_mode": "hot_parking", "parking_id": stand.slot_name,
        "parking_crossroad_idx": stand.crossroad_idx, "start_heading_deg_grid": heading,
        "objective": "Taxi to the training stop, depart runway 25 and climb through the offshore gate.",
        "steps": steps, "gates": [hold, takeoff, depart], "completion": completion,
        "retry": retry, "estimated_minutes": "8-12",
        "source_sections": "CNATRA P-1212 (Rev. 02-19), §§103-105, 201, 204.",
        "runway": {
            "designator": "25", "threshold_07": point_facts(threshold_07),
            "threshold_25": point_facts(threshold_25), "heading_deg_grid": runway_heading,
            "roll_zone_id": runway.id, "source": "Kobuleti GND 01, rev 3.5.0 (12 Mar 2012)",
            "source_url": AIRFIELD_CHART,
        },
        "route": [
            route_point("HOT PARK 31", stand.position, 18),
            route_point("P3 HOLD B", p3, 18),
            route_point("RWY 25", threshold_25, 18),
            route_point("AIRBORNE", threshold_07, 180),
            route_point("SEA GATE", sea_mark, 600),
        ],
    }
    briefing(mission, facts)
    return mission, facts


def write_campaign(out_dir: Path, mission_facts: list[dict]) -> None:
    description = "Two single-player, unarmed sorties in the VNAO T-45C Goshawk at Kobuleti, Caucasus."
    config = {
        "name": TITLE, "name_EN": TITLE, "description": description, "description_EN": description,
        "version": 1, "startStage": 1, "necessaryUnits": {NATIVE_TYPE: NATIVE_TYPE},
        "stages": {
            index: {
                "name": f"{facts['id']} {facts['title']}",
                "missions": {1: {
                    "file": facts["filename"], "description": facts["objective"],
                    "interval": {1: 0, 2: 100}, "skipScore": 100,
                }},
            }
            for index, facts in enumerate(mission_facts, 1)
        },
    }
    text = lua.dumps(config, "campaign", 1)
    if lua.loads(text)["campaign"] != config:
        raise ValueError("Campaign descriptor did not round-trip through the Lua table parser.")
    for facts in mission_facts:
        if not (out_dir / facts["filename"]).is_file():
            raise FileNotFoundError(facts["filename"])
    (out_dir / "First-Flight.cmp").write_text(text, encoding="utf-8")


def build(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    mission_facts = []
    for make_sortie in (first_flight, ramp_to_air):
        mission, facts = make_sortie()
        path = out_dir / facts["filename"]
        mission.save(str(path))
        _normalize_zip_times(str(path))
        mission_facts.append(facts)
    write_campaign(out_dir, mission_facts)
    facts = {
        "campaign_title": TITLE, "campaign_filename": "First-Flight.cmp",
        "aircraft": {"name": Goshawk.name, "native_type": NATIVE_TYPE, "version": MOD_VERSION, "source_url": MOD_SOURCE},
        "terrain": "Caucasus", "terrain_key": "caucasus", "airfield": "Kobuleti",
        "weather": "Clear daylight, calm wind", "mission_date": DATE.date().isoformat(),
        "start_time_local": DATE.strftime("%H:%M"), "pilot_mode": "Single-player, front seat",
        "coach": {"help_label": HELP_ITEM, "help_menu": "F10 Other", "delivery": "on-screen text"},
        "scores": {"practice": BASE_POINTS, "complete": BASE_POINTS + COMPLETION_POINTS},
        "source": "CNATRA P-1212 (Rev. 02-19), Familiarization T-45 Strike",
        "missions": mission_facts,
    }
    (out_dir / "facts.json").write_text(json.dumps(facts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir", type=Path)
    build(parser.parse_args().out_dir)
