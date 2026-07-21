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

# CREW-OPS templates own the player flight themselves (backseat/RIO branches).
# SCENARIO templates (mission_templates.json) are lighter: a recipe preset the
# frontend pre-fills + a suggested-tasking briefing block, with a NORMAL player
# flight. Keep the two sets distinct so scenario templates don't skip the flight.
CREW_OPS_TEMPLATES = ("backseat_izlid", "backseat_intercept", "rio_fleet_defense")

# templates are era-gated too. F-14B(U) flag-API missions are modern-only
# (the B(U) upgrade is a mid-90s+ airframe); fleet defense runs on today's
# F-14A (coldwar) / F-14B (modern). Scenario templates carry their own eras.
TEMPLATE_ERAS = {"backseat_izlid": ("modern",),
                 "backseat_intercept": ("modern",),
                 "rio_fleet_defense": ("coldwar", "modern")}


def _scenario_templates():
    try:
        return {k: v for k, v in load_json("mission_templates").items()
                if not k.startswith("_")}
    except Exception:
        return {}


def _template_eras(key):
    """Allowed eras for any template key (crew-ops table or scenario data)."""
    if key in TEMPLATE_ERAS:
        return tuple(TEMPLATE_ERAS[key])
    return tuple(_scenario_templates().get(key, {}).get("eras", ()))


class EraViolation(Exception):
    """Hard era gate: the selection is not plausible for the mission period."""


def aircraft_in_era(aircraft_key: str, era_cfg: dict) -> bool:
    """Service window overlaps era window. Unlisted aircraft pass (data gap, not a block)."""
    service = load_json("aircraft_service").get(aircraft_key)
    window = era_cfg.get("window")
    if not service or not window:
        return True
    frm, to = service
    return frm <= window[1] and (to is None or to >= window[0])


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
        # --- clear guards BEFORE any lookup (else a bad map/era surfaces as a
        # bare KeyError -> a confusing 400 with just the key name) ------------
        if r.map not in self.maps:
            raise EraViolation(f"Unknown map '{r.map}'.")
        if r.era not in self.eras:
            raise EraViolation(f"Unknown era '{r.era}'.")
        map_cfg = self.maps[r.map]
        era_cfg = self.eras[r.era]
        if r.era not in map_cfg["presets"]:
            raise EraViolation(f"{map_cfg['label']} has no {r.era} preset")
        preset = map_cfg["presets"][r.era]

        crew_ops = r.template in CREW_OPS_TEMPLATES
        if not crew_ops and not aircraft_in_era(r.aircraft, era_cfg):
            svc = load_json("aircraft_service").get(r.aircraft)
            raise EraViolation(
                f"{r.aircraft} was not in service during {era_cfg['label']} "
                f"(service {svc[0]}-{svc[1] or 'present'}). Pick a period-correct aircraft.")
        if r.template and r.era not in _template_eras(r.template):
            raise EraViolation(f"Template '{r.template}' is not available in {era_cfg['label']}")

        terrain = resolve_terrain(map_cfg["terrain_class"])
        m = dcs.Mission(terrain())

        # --- time & weather -------------------------------------------------
        m.start_time = datetime(era_cfg["year"], 6, 21, TIME_PRESETS[r.time_of_day], 0)
        self._apply_weather(m)

        # --- coalitions & airbase ownership ---------------------------------
        def _get_country(name, side):
            """Return the pydcs Country for `name`, GUARANTEED to live in the
            requested coalition. pydcs' default mission pre-sorts many countries
            into fixed coalitions (Germany, UK, USA all default to BLUE). On maps
            where the historical alignment differs — WWII Normandy/Channel put
            Germany on RED — we must MOVE the country, not accept pydcs' default
            side. The old code took whatever side pydcs had it on, so red German
            airfields spawned their aircraft under a blue-coalition Germany."""
            cname = resolve_country(name)().name
            other = "red" if side == "blue" else "blue"
            if cname in m.coalition[other].countries:      # default put it on the wrong side
                c = m.coalition[other].remove_country(cname)
                m.coalition[side].add_country(c)
                return c
            if cname in m.coalition[side].countries:        # already correct
                return m.coalition[side].countries[cname]
            c = resolve_country(name)()                     # in neither (e.g. Japan, Argentina)
            m.coalition[side].add_country(c)
            return c

        blue_country = _get_country(preset["blue_country"], "blue")
        red_country = _get_country(preset["red_country"], "red")

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
        # every preset airbase failed to resolve (pydcs terrain drift) — fail
        # clearly instead of an opaque IndexError/ZeroDivisionError downstream
        if not own_fields or not enemy_fields:
            raise EraViolation(
                f"No {'friendly' if not own_fields else 'enemy'} airbases resolved "
                f"on {map_cfg['label']} ({r.era}) — the terrain data may have "
                f"changed. This is a data issue, not your selection.")
        own_country = blue_country if r.coalition == "blue" else red_country
        enemy_country = red_country if r.coalition == "blue" else blue_country

        carrier_home = r.home_airbase == "CARRIER"
        self._carrier_home = carrier_home
        bb_carrier = r.bb_carrier or carrier_home
        home = next((a for a in own_fields if a.name == r.home_airbase), own_fields[0])
        own_center = _centroid([a.position for a in own_fields], m.terrain)
        enemy_center = _centroid([a.position for a in enemy_fields], m.terrain)
        threat_bearing = _bearing(own_center, enemy_center)
        away_bearing = (threat_bearing + 180) % 360

        comms = CommsPlan()
        stats = {"statics": 0, "sam_sites": [], "support": [], "ambient": []}

        # --- carrier strike group (built FIRST so the boat can be home plate) --
        gfx = {"targets": [], "farps": [], "threats": []}   # map-graphics geometry
        csg, brc, hull_key = None, None, None
        if bb_carrier:
            from . import naval, deck
            if r.coalition == "blue":
                default_hull = {"wwii": "essex", "coldwar": "forrestal",
                                "modern": "stennis"}.get(r.era)
                hull_key = r.carrier_hull or default_hull
                csg, brc = naval.add_carrier_group(
                    m, own_country, r.era, "blue", map_cfg, m.weather, comms,
                    self.warnings, hull_key=hull_key)
                if csg:
                    stats["support"].append(csg.name)
                    gfx["carrier"] = (csg.units[0].position, brc, csg.name)
                    n = deck.configure_deck(
                        m, own_country, csg, brc, hull_key, r.carrier_layout,
                        r.carrier_deck_aircraft, r.carrier_equipment,
                        self.rng, self.warnings)
                    stats["deck_statics"] = n
                    carrier_pos = csg.units[0].position
                    # flight ops underway (launch/recovery deck) => the SAR
                    # helo is airborne in Starboard Delta before the first
                    # cat shot ("first off, last on")
                    if r.carrier_layout in ("launch", "recovery"):
                        pg = naval.add_plane_guard(m, own_country, hull_key,
                                                   csg, brc, comms,
                                                   self.warnings)
                        if pg:
                            stats["support"].append(pg.name)
                    if r.carrier_cap:
                        cap = naval.add_carrier_cap(m, own_country, hull_key,
                                                    carrier_pos, brc, threat_bearing,
                                                    comms, self.warnings, gfx=gfx)
                        if cap:
                            stats["support"].append(cap.name)
                    if r.carrier_aew:
                        aew = naval.add_carrier_aew(m, own_country, hull_key,
                                                    carrier_pos, brc, threat_bearing,
                                                    comms, self.warnings, gfx=gfx)
                        if aew:
                            stats["support"].append(aew.name)
            else:
                self.warnings.append("carrier group is blue-only for now - skipped")
        if carrier_home and csg is None:
            raise EraViolation("Carrier home base selected but no carrier strike group "
                               "could be created on this map/era")
        self._csg, self._brc, self._hull_key = csg, brc, hull_key

        # --- player flight (unless a template pack owns the player) ---------
        player_group = None
        if not crew_ops and carrier_home:
            aircraft = self._resolve_aircraft(r.aircraft)
            self._check_carrier_capable(r.aircraft, aircraft, hull_key)
            player_group = m.flight_group_from_unit(
                own_country, "Anytime 1", aircraft, csg,
                start_type=START_TYPES[r.start],
                group_size=max(1, min(4, r.slots)))
        elif not crew_ops:
            aircraft = self._resolve_aircraft(r.aircraft)
            from dcs.terrain.terrain import NoParkingSlotError
            player_group = None
            for field in [home] + [a for a in own_fields if a is not home]:
                try:
                    player_group = m.flight_group_from_airport(
                        own_country, "Viper 1" if r.coalition == "blue" else "Bandit 1",
                        aircraft, field,
                        start_type=START_TYPES[r.start],
                        group_size=max(1, min(4, r.slots)))
                    if field is not home:
                        self.warnings.append(
                            f"no free {aircraft.id} parking at {home.name} - "
                            f"flight placed at {field.name}")
                        home = field
                    break
                except NoParkingSlotError:
                    continue
            if player_group is None:
                raise UnknownUnitError(
                    f"no friendly airbase on this preset has free parking for {aircraft.id}")
        if player_group is not None:
            if r.slots <= 1:
                player_group.units[0].set_player()
            else:
                for u in player_group.units:
                    u.set_client()
            fc = comms.freq("flight_common")
            try:
                player_group.set_frequency(fc)
            except Exception:
                pass
            comms.add("Flight", player_group.name, f"{fc:.3f}", "-", aircraft.id)
            comms.add("Tactical", "-", f"{comms.freq('tactical'):.3f}", "-",
                      "inter-flight coordination")

        # --- building blocks -------------------------------------------------
        # ambient traffic BEFORE dressing so AI aircraft claim parking slots first
        if r.bb_ambient:
            from . import ambient
            enemy_side = "red" if r.coalition == "blue" else "blue"
            stats["ambient"] += ambient.add_ambient_traffic(
                m, own_country, own_fields, era_cfg[r.coalition], r.density,
                self.rng, "friendly")
            stats["ambient"] += ambient.add_ambient_traffic(
                m, enemy_country, enemy_fields, era_cfg[enemy_side], r.density,
                self.rng, "enemy")

        if r.bb_dressing:
            enemy_side = "red" if r.coalition == "blue" else "blue"
            # ramp themes: player's choice for own fields; enemy fields always
            # use their map/era default (era-gated by structure)
            own_tkey, own_theme = dressing.resolve_theme(
                r.era, r.coalition, preset, r.dress_theme, self.warnings)
            _, enemy_theme = dressing.resolve_theme(r.era, enemy_side, preset)
            if own_tkey:
                stats["ramp_theme"] = own_tkey
            dress_kw = dict(fill=r.dress_fill,
                            include_aircraft=r.dress_aircraft,
                            include_gse=r.dress_gse,
                            include_infra=r.dress_infra,
                            aircraft_mode=r.dress_aircraft_mode,
                            livery_style=getattr(r, "dress_livery_style", "squadron"))
            # ONLY MILITARY INSTALLATIONS get ramp dressing. Civilian airports
            # (McCarran, Dubai Intl, Murmansk...) stay undressed — no combat
            # aircraft rows on an airline apron. They remain usable as home
            # plate and for ambient traffic; classification is per map/era
            # (Tinian 1944 is a bomber base; Tinian today is a civil field).
            civilian = set(preset.get("civilian_airbases", []))
            overrides = r.dress_overrides or {}
            # measured painted-line headings for THIS map (parking_headings.json);
            # static aircraft at a listed field face the exact heading instead of
            # the geometric guess. Absent map/field => geometric guess (no change).
            try:
                field_hdgs = load_json("parking_headings").get(r.map, {})
            except Exception:
                field_hdgs = {}
            skipped = []

            def _dress(ap, country, cfg, theme, mix=None):
                ov = overrides.get(ap.name)
                # civilian fields stay empty UNLESS explicitly overridden
                # ("populate anyway"); an override of 0 empties ANY field
                if ov is None and ap.name in civilian:
                    skipped.append(ap.name); return 0
                if ov == 0:
                    skipped.append(ap.name); return 0
                kw = dict(dress_kw)
                if ov is not None:
                    kw["fill"] = ov
                kw["field_heading"] = field_hdgs.get(ap.name)
                kw["mix"] = mix
                kw["map_key"] = r.map
                return dressing.dress_airfield(
                    m, ap, country, cfg, r.density, self.rng, theme=theme, **kw)

            # International Alignment (Theater Identity P1): dress each base with
            # its REAL owning nation's country so statics carry the right national
            # identity + liveries (Israeli base -> Israeli jets, RAF Akrotiri ->
            # RAF, Syrian bases -> Syrian). Additive: no data => side default.
            align_bases = {}
            if r.bb_alignment:
                from . import alignment
                align_bases = alignment.bases(r.map, r.era)
            aligned_used = set()

            def _acountry(ap, default_c, side):
                nat = align_bases.get(ap.name)
                if not nat:
                    return default_c
                try:
                    c = _get_country(nat, side)
                    aligned_used.add(nat)
                    return c
                except Exception:
                    return default_c

            def _atheme(ap, side_theme):
                # aligned base -> that nation's fast-jet roster merged over the
                # side theme (nation-correct TYPES, not just skins). No roster
                # for the nation/era => side theme unchanged.
                nat = align_bases.get(ap.name)
                if not nat:
                    return side_theme
                from . import alignment
                return alignment.roster_theme(r.era, nat, side_theme)

            # the custom mix (Ramp Composer) applies to the PLAYER's own fields;
            # enemy fields always dress from their era/map theme
            for ap in own_fields:
                stats["statics"] += _dress(
                    ap, _acountry(ap, own_country, r.coalition),
                    era_cfg[r.coalition], _atheme(ap, own_theme), mix=r.dress_mix)
            for ap in enemy_fields:
                stats["statics"] += _dress(
                    ap, _acountry(ap, enemy_country, enemy_side),
                    era_cfg[enemy_side], _atheme(ap, enemy_theme))
            if aligned_used:
                stats["alignment"] = sorted(aligned_used)
            if skipped:
                stats["civilian_undressed"] = skipped

        if r.bb_sams:
            from . import threats
            enemy_side = "red" if r.coalition == "blue" else "blue"
            # base per-airfield defense: SAM kit chosen by the Threat Dial tier
            enemy_kits = threats.sam_kits_for(
                r.era, enemy_side, r.threat_tier,
                era_cfg[enemy_side]["sam_kits"])
            for ap in enemy_fields:
                stats["sam_sites"] += airdefense.defend_airbase(
                    m, enemy_country, ap, era_cfg[enemy_side], self.rng, r.era,
                    gfx_threats=gfx["threats"], kits_override=enemy_kits)
            # friendly SHORAD at home plate only
            stats["sam_sites"] += airdefense.defend_airbase(
                m, own_country, home, era_cfg[r.coalition], self.rng, r.era)

            # --- Threat Dial: extra area SAM belt + enemy CAP (seeded count) --
            tp = threats.plan(r.threat_intensity, self.rng)
            stats["threat_level"] = f"{tp['label']} / {threats.TIER_LABELS.get(r.threat_tier, r.threat_tier)}"
            area = threats.add_area_sams(
                m, enemy_country, r.era, enemy_side, r.threat_tier,
                tp["n_extra_sams"], own_center, enemy_center, self.rng,
                gfx_threats=gfx["threats"], enemy_fields=enemy_fields)
            stats["sam_sites"] += area
            cap = threats.add_enemy_cap(
                m, enemy_country, r.era, enemy_side, r.threat_tier,
                tp["n_cap"], own_center, enemy_center, tp["skill"],
                self.rng, gfx=gfx)
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
            tk = support_air.add_tanker(
                m, support_country,
                support_air.tanker_type(r.era, r.coalition, player_id),
                own_center, away_bearing, comms, gfx=gfx)
            if tk:
                stats["support"].append(tk.name)
        if r.bb_awacs:
            aw = support_air.add_awacs(
                m, support_country, support_air.awacs_type(r.era, r.coalition),
                own_center, away_bearing, comms, gfx=gfx)
            if aw:
                stats["support"].append(aw.name)

        nav_pts = []
        if r.bb_navpoints:
            from . import navpoints
            nav_pts = navpoints.add_nav_points(m, r.map)
            if nav_pts:
                stats["nav_points"] = len(nav_pts)

        # Historical airspace overlay (Theater Identity P3): real corridors /
        # no-fly zones for this map+era, drawn on the F10 map + briefed. Off by
        # default (determinism-safe); scenario templates like Berlin Corridor
        # Transit turn it on. Draws nothing if the map/era has no overlay.
        airspace_brief = ""
        if r.bb_historical_airspace:
            from . import airspace
            drawn_as, as_lines = airspace.add_historical_airspace(m, r.map, r.era)
            if drawn_as:
                stats["historical_airspace"] = drawn_as
                airspace_brief = "\n".join(as_lines)

        if r.bb_farps:
            if r.era == "wwii":
                self.warnings.append("FARPs are helicopter-era only - skipped in WWII")
            else:
                from . import farps
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
            from . import targets as tgt
            enemy_side = "red" if r.coalition == "blue" else "blue"
            picks = self.rng.sample(list(tgt.TARGET_PACKAGES), k=2)
            for i, pk in enumerate(picks):
                center = mapping.Point(
                    enemy_center.x + self.rng.uniform(-15000, 15000),
                    enemy_center.y + self.rng.uniform(-15000, 15000), m.terrain)
                label = tgt.add_target_package(m, enemy_country, r.era, pk,
                                               center, self.rng, f"TGT{i+1}")
                stats.setdefault("targets", []).append(label)
                gfx["targets"].append((center, label))

        if r.bb_range:
            from . import targets as tgt
            pos = mapping.Point(
                own_center.x - 0.2 * (enemy_center.x - own_center.x),
                own_center.y - 0.2 * (enemy_center.y - own_center.y), m.terrain)
            tgt.add_practice_range(m, own_country, pos, self.rng, "RNG1")
            stats.setdefault("targets", []).append("practice range")
            gfx["targets"].append((pos, "RNG1 practice range"))

        # --- template packs ---------------------------------------------------
        template_brief = ""
        if r.template in ("backseat_izlid", "backseat_intercept", "rio_fleet_defense"):
            target_area = mapping.Point(
                enemy_center.x + self.rng.uniform(-8000, 8000),
                enemy_center.y + self.rng.uniform(-8000, 8000), m.terrain)
            if r.template == "backseat_izlid":
                backseat.build_backseat_izlid(m, r, blue_country, red_country, home,
                                              target_area, self.rng, comms,
                                              self.warnings)
                template_brief = backseat.BRIEFING_BLOCK
            elif r.template == "backseat_intercept":
                backseat.build_backseat_intercept(m, r, blue_country, red_country,
                                                  home, target_area, self.rng, comms,
                                                  self.warnings)
                template_brief = backseat.INTERCEPT_BRIEFING_BLOCK
            else:
                backseat.build_rio_fleet_defense(m, r, blue_country, red_country,
                                                 home, target_area, self.rng, comms,
                                                 r.era, csg=self._csg if carrier_home else None)
                template_brief = backseat.RIO_BRIEFING_BLOCK
        elif r.template:
            # SCENARIO template: append its suggested-tasking block (no waypoints).
            sc = _scenario_templates().get(r.template)
            if sc and sc.get("brief"):
                template_brief = "\n".join(sc["brief"])

        # --- bullseye ---------------------------------------------------------
        midpoint = mapping.Point((own_center.x + enemy_center.x) / 2,
                                 (own_center.y + enemy_center.y) / 2, m.terrain)
        for coal in m.coalition.values():
            coal.bullseye = {"x": midpoint.x, "y": midpoint.y}
        gfx["bullseye"] = midpoint

        # --- F10 map graphics layers (the map briefs the mission) -------------
        from . import graphics
        layers = graphics.effective_layers(r.map_layers)
        drawn = graphics.draw_layers(m, gfx, layers, r.coalition)
        if drawn:
            stats["map_layers"] = drawn

        # --- cockpit radio presets (BB-19): put the comm plan IN the jet ------
        # Programs the module's UHF radio from the ladder actually built above.
        # apply() returns ONLY what it really wrote, so the card/kneeboard CHAN
        # column matches the cockpit exactly (no advertising channels a module
        # doesn't have, and no clobbering an agency with Guard).
        if player_group is not None:
            from . import presets
            chan_rows, guard = presets.plan_from_comms(comms)
            programmed = presets.apply(player_group, chan_rows, guard)
            if programmed:
                comms.set_channels(programmed)
                stats["radio_presets"] = [
                    f"CH{ch} {a}" for a, ch in programmed.items() if a != "Guard"]

        # --- briefing ----------------------------------------------------------
        if r.bb_briefing:
            brief = self._briefing(map_cfg, era_cfg, preset, home,
                                   comms, stats, template_brief)
            if nav_pts:
                from . import navpoints
                brief += "\n" + navpoints.briefing_block(nav_pts)
            if airspace_brief:
                brief += "\n" + airspace_brief
            m.set_description_text(brief)

        self.stats = stats
        # context the Mission Brief (PDF/MD) renderer needs — kb_ctx plus the
        # chart geometry (gfx) and the recipe/stats picture (brief.py).
        self.brief_ctx = {
            "gfx": gfx, "stats": stats, "recipe": r,
            "map_label": map_cfg["label"], "era_label": era_cfg["label"],
            "era_year": era_cfg["year"], "home": home,
            "carrier_home": carrier_home,
        }
        # context the kneeboard renderer needs after save
        self.kb_ctx = {
            "comms": comms, "own_fields": own_fields, "enemy_fields": enemy_fields,
            "bullseye": {"x": midpoint.x, "y": midpoint.y},
            "map_label": map_cfg["label"], "era_label": era_cfg["label"],
            "era_year": era_cfg["year"],
            "home_name": (csg.units[0].name if carrier_home and csg else home.name),
            "support_names": stats["support"],
            "nav_points": [(n, p) for n, p, _t, _note in nav_pts],
            "qnh_hpa": getattr(self, "_qnh_hpa", None),
        }
        return m

    def _check_carrier_capable(self, key: str, aircraft, hull_key: str):
        """Hard gate: only carrier-capable aircraft can start on the boat."""
        cap = load_json("carrier_capable")
        deck_class = cap["hull_class"].get(hull_key)
        allowed = cap["classes"].get(deck_class, [])
        if key not in allowed:
            from .deck import _load_hull
            raise EraViolation(
                f"{aircraft.id} cannot operate from {_load_hull(hull_key)['label']} "
                f"({deck_class} deck). Carrier-capable options: "
                f"{', '.join(allowed) or 'none for this hull'}.")

    def _resolve_aircraft(self, name: str):
        for mod in ("planes", "helicopters"):
            try:
                return resolve(f"{mod}.{name}")
            except UnknownUnitError:
                continue
        # pending (announced/pre-order) modules with provisional type ids
        from .pending import get_pending
        cls, warning = get_pending(name)
        if cls is not None:
            self.warnings.append(warning)
            return cls
        raise UnknownUnitError(f"Aircraft '{name}' not found in pydcs planes/helicopters")

    def _apply_weather(self, m):
        """Real DCS cloud presets (the same ones the ME weather page uses)."""
        from dcs.cloud_presets import Clouds
        w = self.recipe.weather
        presets = {
            "scattered": (Clouds.LightScattered1, 2500),
            "overcast": (Clouds.Overcast2, 1800),
            "storm": (Clouds.OvercastAndRain2, 1500),
        }
        try:
            if w in presets:
                preset, base = presets[w]
                preset = getattr(preset, "value", preset)   # enum member -> CloudPreset
                base = max(preset.min_base, min(base, preset.max_base))
                m.weather.clouds_preset = preset
                m.weather.clouds_base = base
            if w == "storm":
                m.weather.wind_at_ground.speed = 8
                m.weather.wind_at_ground.direction = int(self.rng.uniform(0, 360))
                m.weather.wind_at_2000.speed = 12
        except AttributeError as e:
            self.warnings.append(f"weather preset partial: {e}")
        # BB-20: realistic, seeded QNH instead of the flat 760 mmHg (=29.92) default
        from . import pressure
        self._qnh_hpa = pressure.roll_qnh_hpa(w, self.rng)
        try:
            m.weather.qnh = pressure.qnh_mmhg(self._qnh_hpa)
        except AttributeError:
            pass

    def _briefing(self, map_cfg, era_cfg, preset, home, comms, stats, template_brief):
        r = self.recipe
        carrier_home = getattr(self, "_carrier_home", False) and self._csg
        where = self._csg.units[0].name if carrier_home else home.name
        if r.template in CREW_OPS_TEMPLATES:
            flight_line = ">> YOUR FLIGHT: see the template briefing below."
        else:
            try:
                ac = self._resolve_aircraft(r.aircraft).id
            except Exception:
                ac = r.aircraft
            flight_line = (f">> YOUR FLIGHT: {ac} at {where}, {r.start} start. "
                           f"It's parked and ready — click Fly, or find it in the "
                           f"Mission Editor.")
            if getattr(comms, "channels", None):
                mother = ""
                if comms.channels.get("Carrier") == 2:
                    boat = next((cs for ag, cs, *_ in comms.entries
                                 if ag == "Carrier"), "Mother")
                    mother = f" {boat} is on CH 2."
                flight_line += (f" COMM1 presets are loaded — see the CHAN column "
                                f"on the comms card.{mother}")
        lines = [
            f"=== DCS MISSION STARTER ===",
            f"{map_cfg['label']} | {era_cfg['label']} | {preset['frontline_hint']}",
            "",
            flight_line,
            "",
            "This is a STARTER, not a scripted mission: the theater is dressed, air",
            "defenses are up, and tanker/AWACS are on station - but there are NO",
            "objectives, tasking or waypoints (no A/A, A/G, SEAD packages). Take off",
            "and free-fly, or open it in the Mission Editor and build your mission on top.",
            "",
            f"Home plate: {where}",
        ]
        qnh_hpa = getattr(self, "_qnh_hpa", None)
        if qnh_hpa:
            from . import pressure
            lines.append(f"Altimeter (QNH): {pressure.format_qnh(qnh_hpa)} "
                         f"- set it before you taxi.")
        lines += [
            f"Static objects placed: {stats['statics']}",
            f"Air defense groups: {len(stats['sam_sites'])}",
            f"Support flights: {', '.join(stats['support']) or 'none'}",
            "",
        ]
        if r.bb_comms:
            lines.append(comms.card())
        if template_brief:
            lines.append(template_brief)
        lines += ["", f"Generated by DCS Mission Starter | variation (seed) {r.seed} — "
                      "same settings + seed rebuild this exact mission; new seed = "
                      "a fresh layout of the same setup"]
        return "\n".join(lines)


def generate(recipe: Recipe, out_path: str, brief_dir: str = None) -> dict:
    b = StarterBuilder(recipe)
    m = b.build()
    m.save(out_path)
    if recipe.bb_kneeboard:
        try:
            from .kneeboard import build_kneeboard
            n = build_kneeboard(out_path, **b.kb_ctx)
            b.stats["kneeboard_pages"] = n
        except Exception as e:
            b.warnings.append(f"kneeboard rendering failed: {e}")
    result = {"stats": b.stats, "warnings": b.warnings, "path": out_path}

    # F-14B(U) DTC setup card (schema-independent Day-0 artifact). Defensive:
    # any failure is a warning, never a broken mission. Auto-on for the B(U).
    from . import dtc as _dtc
    _dtc_on = recipe.bb_dtc if recipe.bb_dtc is not None else _dtc.is_bu(recipe.aircraft)
    if _dtc_on:
        try:
            from pathlib import Path as _P
            cart = _dtc.build_cartridge(b.brief_ctx["gfx"], b.kb_ctx, recipe)
            card_md = _dtc.cartridge_card_md(cart)
            dest = _P(brief_dir) if brief_dir else _P(out_path).parent
            card_path = str(dest / "DTC_Setup_Card.md")
            with open(card_path, "w") as _f:
                _f.write(card_md)
            result["dtc_card"] = card_path
            b.stats["dtc_card"] = {
                "fix_points": len(cart["fix_points"]),
                "threat_areas": len(cart["threat_areas"]),
                "comms": len(cart["comms"])}
        except Exception as e:
            b.warnings.append(f"DTC setup card failed: {e}")

    if brief_dir:
        # Mission Starter Brief: printable PDF + shareable MD alongside the .miz
        try:
            from pathlib import Path as _P
            from .brief import build_brief
            pdf = str(_P(brief_dir) / "Mission_Brief.pdf")
            md = str(_P(brief_dir) / "Mission_Brief.md")
            build_brief(b.brief_ctx, b.kb_ctx, pdf, md)
            result["brief_pdf"], result["brief_md"] = pdf, md
        except Exception as e:
            b.warnings.append(f"brief rendering failed: {e}")
    return result
