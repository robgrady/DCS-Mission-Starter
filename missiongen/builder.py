"""Orchestrates starter generation from a Recipe. The heavy lifting lives here."""
import io
import math
import random
from datetime import datetime

import dcs
from dcs import mapping
from dcs.mission import StartType

from .recipe import Recipe
from .resolver import load_json, resolve, resolve_terrain, resolve_country, UnknownUnitError
from .comms import CommsPlan
from . import dressing, airdefense, support_air, backseat

START_TYPES = {"cold": StartType.Cold, "warm": StartType.Warm, "runway": StartType.Runway}
TIME_PRESETS = {"dawn": 5, "day": 12, "dusk": 18, "night": 22}


def _bearing(a, b) -> float:
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x)) % 360


def _centroid(points, terrain):
    return mapping.Point(sum(p.x for p in points) / len(points),
                         sum(p.y for p in points) / len(points), terrain)


class StarterBuilder:
    def __init__(self, recipe: Recipe):
        self.recipe = recipe
        self.rng = random.Random(recipe.seed)
        self.maps = load_json("maps")
        self.eras = load_json("eras")
        self.warnings = []

    def build(self) -> dcs.Mission:
        r = self.recipe
        map_cfg = self.maps[r.map]
        era_cfg = self.eras[r.era]
        preset = map_cfg["presets"][r.era]

        terrain = resolve_terrain(map_cfg["terrain_class"])
        m = dcs.Mission(terrain())

        # --- time & weather -------------------------------------------------
        m.start_time = datetime(era_cfg["year"], 6, 21, TIME_PRESETS[r.time_of_day], 0)
        self._apply_weather(m)

        # --- coalitions & airbase ownership ---------------------------------
        blue_country = m.country(resolve_country(preset["blue_country"])().name)
        red_country = m.country(resolve_country(preset["red_country"])().name)

        blue_fields, red_fields = [], []
        for name in preset["blue_airbases"]:
            ap = m.terrain.airports.get(name)
            if ap:
                ap.set_blue()
                blue_fields.append(ap)
            else:
                self.warnings.append(f"blue airbase '{name}' not found on {r.map}")
        for name in preset["red_airbases"]:
            ap = m.terrain.airports.get(name)
            if ap:
                ap.set_red()
                red_fields.append(ap)
            else:
                self.warnings.append(f"red airbase '{name}' not found on {r.map}")

        own_fields = blue_fields if r.coalition == "blue" else red_fields
        enemy_fields = red_fields if r.coalition == "blue" else blue_fields
        own_country = blue_country if r.coalition == "blue" else red_country
        enemy_country = red_country if r.coalition == "blue" else blue_country

        home = next((a for a in own_fields if a.name == r.home_airbase), own_fields[0])
        own_center = _centroid([a.position for a in own_fields], m.terrain)
        enemy_center = _centroid([a.position for a in enemy_fields], m.terrain)
        threat_bearing = _bearing(own_center, enemy_center)
        away_bearing = (threat_bearing + 180) % 360

        comms = CommsPlan()

        # --- player flight (unless a template pack owns the player) ---------
        player_group = None
        if not r.template:
            aircraft = self._resolve_aircraft(r.aircraft)
            player_group = m.flight_group_from_airport(
                own_country, "Viper 1" if r.coalition == "blue" else "Bandit 1",
                aircraft, home,
                start_type=START_TYPES[r.start], group_size=max(1, min(4, r.slots)))
            if r.slots <= 1:
                player_group.units[0].set_player()
            else:
                for u in player_group.units:
                    u.set_client()
            comms.add("Flight", player_group.name, "305.00", "-", aircraft.id)

        # --- building blocks -------------------------------------------------
        stats = {"statics": 0, "sam_sites": [], "support": []}

        if r.bb_dressing:
            for ap in own_fields:
                stats["statics"] += dressing.dress_airfield(
                    m, ap, own_country, era_cfg[r.coalition], r.density, self.rng)
            enemy_side = "red" if r.coalition == "blue" else "blue"
            for ap in enemy_fields:
                stats["statics"] += dressing.dress_airfield(
                    m, ap, enemy_country, era_cfg[enemy_side], r.density, self.rng)

        if r.bb_sams:
            enemy_side = "red" if r.coalition == "blue" else "blue"
            for ap in enemy_fields:
                stats["sam_sites"] += airdefense.defend_airbase(
                    m, enemy_country, ap, era_cfg[enemy_side], self.rng, r.era)
            # friendly SHORAD at home plate only
            stats["sam_sites"] += airdefense.defend_airbase(
                m, own_country, home, era_cfg[r.coalition], self.rng, r.era)

        if r.bb_tanker:
            tk = support_air.add_tanker(m, own_country, r.era, r.coalition,
                                        own_center, away_bearing, comms)
            if tk:
                stats["support"].append(tk.name)
        if r.bb_awacs:
            aw = support_air.add_awacs(m, own_country, r.era, r.coalition,
                                       own_center, away_bearing, comms)
            stats["support"].append(aw.name)

        # --- template packs ---------------------------------------------------
        template_brief = ""
        if r.template == "backseat_izlid":
            target_area = mapping.Point(
                enemy_center.x + self.rng.uniform(-8000, 8000),
                enemy_center.y + self.rng.uniform(-8000, 8000), m.terrain)
            backseat.build_backseat_izlid(m, r, blue_country, red_country, home,
                                          target_area, self.rng, comms)
            template_brief = backseat.BRIEFING_BLOCK

        # --- bullseye ---------------------------------------------------------
        midpoint = mapping.Point((own_center.x + enemy_center.x) / 2,
                                 (own_center.y + enemy_center.y) / 2, m.terrain)
        for coal in m.coalition.values():
            coal.bullseye = {"x": midpoint.x, "y": midpoint.y}

        # --- briefing ----------------------------------------------------------
        if r.bb_briefing:
            m.set_description_text(self._briefing(map_cfg, era_cfg, preset, home,
                                                  comms, stats, template_brief))

        self.stats = stats
        return m

    def _resolve_aircraft(self, name: str):
        for mod in ("planes", "helicopters"):
            try:
                return resolve(f"{mod}.{name}")
            except UnknownUnitError:
                continue
        raise UnknownUnitError(f"Aircraft '{name}' not found in pydcs planes/helicopters")

    def _apply_weather(self, m):
        w = self.recipe.weather
        try:
            if w == "scattered":
                m.weather.clouds_base = 2500
                m.weather.clouds_density = 4
                m.weather.clouds_thickness = 500
            elif w == "overcast":
                m.weather.clouds_base = 1800
                m.weather.clouds_density = 9
                m.weather.clouds_thickness = 900
            elif w == "storm":
                m.weather.clouds_base = 1500
                m.weather.clouds_density = 9
                m.weather.clouds_thickness = 1200
                m.weather.clouds_iprecptns = 1
                m.weather.wind_at_ground.speed = 8
        except AttributeError as e:
            self.warnings.append(f"weather preset partial: {e}")

    def _briefing(self, map_cfg, era_cfg, preset, home, comms, stats, template_brief):
        r = self.recipe
        lines = [
            f"=== DCS MISSION STARTER ===",
            f"{map_cfg['label']} | {era_cfg['label']} | {preset['frontline_hint']}",
            "",
            "This is a STARTER mission: airfields are dressed, air defenses are up,",
            "and support aircraft are on station. No player waypoints have been placed -",
            "open it in the Mission Editor and build your mission on top.",
            "",
            f"Home plate: {home.name}",
            f"Static objects placed: {stats['statics']}",
            f"Air defense groups: {len(stats['sam_sites'])}",
            f"Support flights: {', '.join(stats['support']) or 'none'}",
            "",
        ]
        if r.bb_comms:
            lines.append(comms.card())
        if template_brief:
            lines.append(template_brief)
        lines += ["", f"Generated by DCS Mission Starter | recipe seed {r.seed}"]
        return "\n".join(lines)


def generate(recipe: Recipe, out_path: str) -> dict:
    b = StarterBuilder(recipe)
    m = b.build()
    m.save(out_path)
    return {"stats": b.stats, "warnings": b.warnings, "path": out_path}
