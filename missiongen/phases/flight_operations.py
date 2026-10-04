"""Orchestrate ordered PyDCS placement phases after world resolution.

World/domain setup lives in build_context; artifact rendering and packaging
live in artifacts. Placement order is significant for RNG and parking.
"""
import math

from dcs import mapping

from ..resolver import load_json, resolve, UnknownUnitError

from ..build_context import EraViolation, _bearing
PACKAGE_LEAD_S = 120

class FlightOperations:
    # Where each target-relative air start puts you, and why.
    #
    #   roll_in           — 11 km out, target off the nose, at a workable
    #                       roll-in block. Inside visual pickup, outside gun
    #                       range: the attack geometry is still yours to fly.
    #   outside_the_ring  — 26 km out, just beyond a short/medium SAM's WEZ.
    #                       The RWR lights up within seconds of the spawn, and
    #                       standing off, notching or going under it IS the
    #                       exercise, so the mission begins at the detection,
    #                       not at the takeoff.
    AIR_START_ON_TARGET = {"roll_in": 11000.0, "outside_the_ring": 26000.0}

    # How far outside a SAM's own weapon envelope the "Beat the SAM" card puts
    # you. Measured from the RING, not from the target: an SA-3 (22 km WEZ) and
    # an SA-10 (75 km) are different exercises, and a fixed distance from the
    # target either drops you inside the envelope of the big one or leaves you
    # a long, dull ride outside the small one. 4 km of margin is close enough
    # that the RWR is already talking at spawn — which is when this mission
    # actually begins — and far enough that the first move is yours.
    RING_MARGIN_M = 4000.0

    # 1 nm astern, 1,000 ft below: the PRE-CONTACT position.
    ASTERN_TANKER_M = 1852.0
    ASTERN_TANKER_BELOW_M = 305.0

    @staticmethod
    def _tanker_track_heading(tanker) -> float:
        """Which way the tanker is actually GOING, from its route.

        THE BUG THIS FIXES, measured out of a built mission: this used to read
        `unit.heading`, which pydcs had not assigned yet when the air start ran.
        It came back 0.0, so "1 nm astern" placed the player due SOUTH of a
        tanker flying 229 degrees — about 49 degrees off its right rear quarter,
        very nearly abeam — and pointed the player due NORTH, 131 degrees away
        from the tanker's direction of flight. The card promised the pre-contact
        position and delivered a rejoin problem.

        Waypoint 0 -> waypoint 1 is authoritative and is populated the moment
        the flight is created, so it cannot be read too early. The unit heading
        stays as a fallback for a tanker with a degenerate route.
        """
        try:
            pts = list(getattr(tanker, "points", []) or [])
            if len(pts) >= 2:
                a, b = pts[0].position, pts[1].position
                if (b.x - a.x) or (b.y - a.y):
                    return math.degrees(math.atan2(b.y - a.y, b.x - a.x)) % 360.0
        except Exception:
            pass
        return math.degrees(getattr(tanker.units[0], "heading", 0.0) or 0.0) % 360.0

    def _air_start_astern_tanker(self, group, tanker, aar_key, stats,
                                 receiver_id="", map_key=""):
        """Start the sortie already in the pre-contact position.

        THE POINT IS TIME. A pilot who wants to practice refuelling wants
        repetitions of the last 30 seconds, and the old tanker card spent
        fifteen minutes getting there — taxi, climb, transit, find a tanker
        somewhere on a 48 km racetrack. That is not practice, it is commuting,
        and it is why people give up on learning this.

        So: 1 nm astern the tanker's first orbit point, 1,000 ft below the
        track, at the track speed. You are in position 3 of the four the
        kneeboard card describes, and the only thing left is the part you came
        to learn.

        BELOW, always — if it goes wrong the escape is down, and the tanker is
        the one thing in the sky you must not climb into."""
        from ..dressing import _offset as _off
        try:
            tk_unit = tanker.units[0]
            tk_pos = tk_unit.position
            hdg = self._tanker_track_heading(tanker)
        except Exception:
            return
        astern = _off(tk_pos, self.ASTERN_TANKER_M, (hdg + 180.0) % 360.0)
        alt = self.ASTERN_TANKER_BELOW_M
        if aar_key:
            from .. import aar as _aar
            alt = _aar.track_alt_m(aar_key, map_key) - self.ASTERN_TANKER_BELOW_M
            # The pre-contact air start must spawn you ON the tanker's actual
            # speed. Using the tanker's default here while the tanker flew a
            # receiver-clamped speed would spawn a Hog 80 kt fast behind a
            # KC-135 — the exact class of bug v1.73.0 existed to kill.
            spd = _aar.track_speed_kmh(aar_key, receiver_id, map_key)
        else:
            alt, spd = 6096 - self.ASTERN_TANKER_BELOW_M, 550
        for u in group.units:
            u.position.x, u.position.y = astern.x, astern.y
            u.alt = alt
            u.heading = hdg % 360.0
            # PSI IS WHAT ORIENTS AN AIR START, and pydcs only syncs it from
            # `heading` when a group has MORE THAN ONE waypoint (see
            # unitgroup.py: `if len(self.points) > 1`). A pre-contact air start
            # leaves exactly one, so psi stayed 0 and the jet spawned facing
            # NORTH behind a tanker flying 229 degrees — pointing 131 degrees
            # away from it, at 300 knots. Setting heading alone looked right in
            # the file and was wrong in the cockpit.
            u.psi = -math.radians(hdg % 360.0)
        group.manualHeading = True
        pts = list(group.points)
        if pts:
            pts[0].position.x, pts[0].position.y = astern.x, astern.y
            pts[0].alt = alt
            pts[0].speed = spd / 3.6
        stats["air_start"] = "pre-contact, 1 nm astern the tanker"

    def _air_start_on_target(self, group, target_pos, home_pos, mode, stats,
                             threats=None):
        """Move an already-created in-flight group onto the target run-in.

        Repositions the units AND waypoint 0 together: DCS reads the unit
        position for the spawn and the route point for the first leg, so moving
        one without the other spawns you correctly and then sends you to the
        old position — which looks exactly like the transit tax we are removing.
        """
        dist = self.AIR_START_ON_TARGET.get(mode)
        if not dist:
            return
        from ..dressing import _offset as _as_off
        # Run in from the friendly side: approach over your own territory
        # rather than starting deep behind the target and egressing outbound.
        anchor = target_pos
        if mode == "outside_the_ring":
            # ANCHOR ON THE RING, NOT THE TARGET. Measuring the standoff from
            # the target put the spawn 16 km from an SA-3 whose envelope is
            # 22 km — i.e. already engaged — because the site sits between the
            # target and home. "Outside the ring" has to mean outside *that
            # ring*, so the geometry is anchored on the threat that defines the
            # exercise: the biggest one covering the target area.
            rings = [(c, rad) for c, rad, _lbl in (threats or [])
                     if rad and math.hypot(target_pos.x - c.x,
                                           target_pos.y - c.y) < 60000]
            if rings:
                anchor, radius = max(rings, key=lambda t: t[1])
                dist = radius + self.RING_MARGIN_M
        brg = _bearing(anchor, home_pos)
        pos = _as_off(anchor, dist, brg)
        heading = _bearing(pos, target_pos)
        for i, u in enumerate(group.units):
            # keep the flight in a line abreast, 150 m apart, facing the target
            u.position = _as_off(pos, 150.0 * i, (heading + 90) % 360)
            u.heading = math.radians(heading)
        if group.points:
            p0 = group.points[0]
            p0.position = mapping.Point(pos.x, pos.y, target_pos._terrain)
            # A roll-in start needs altitude to trade; the outside-the-ring
            # start needs to be high enough that the SAM sees you (that is the
            # point of the exercise) without being a free kill.
            p0.alt = max(int(p0.alt or 0), 3000 if mode == "roll_in" else 4500)
            for u in group.units:
                u.alt = p0.alt
        stats["air_start"] = mode
        stats["air_start_km"] = round(dist / 1000.0, 1)

    def _time_the_route(self, m, stats, route_rows, player_group, own_country,
                        home):
        """Time the card, write the ETAs, launch the package, attach the coach.

        Returns the timeline (timing.plan) or None. NEVER RAISES past the
        plan itself: a route without a clock is the mission we shipped for a
        year; a route that failed to build is not a mission.
        """
        from .. import timing as _tm
        r = self.recipe
        try:
            w = m.weather
            winds = [(2000, w.wind_at_2000.speed, w.wind_at_2000.direction),
                     (8000, w.wind_at_8000.speed, w.wind_at_8000.direction)]
        except Exception:
            winds = None
        tl = _tm.plan(route_rows, start=r.start, era=r.era,
                      anchor=r.timing_anchor, anchor_hhmm=r.timing_at,
                      mission_start=m.start_time,
                      hold_s=int(r.timing_hold_min or 0) * 60, winds=winds)
        if not tl:
            return None
        if tl["shift_s"]:
            # The anchor moved the clock. Everything that prints the start
            # time reads it from the mission from here on (brief._dtg via
            # stats["start_clock"]; the in-game text via saydo.mission_clock),
            # and the say/do clock check is told the same number.
            m.start_time = tl["mission_start"]
            stats["start_clock"] = tl["start_clock"][:5]
        _tm.apply_to_group(player_group, tl, locked=False)
        # JSON-safe copy for the API and the tests: the rows carry pydcs Points.
        stats["timing"] = {k: v for k, v in tl.items() if k not in ("rows", "mission_start")}
        stats["timing"]["rows"] = [{k: v for k, v in t.items() if k != "point"}
                                   for t in tl["rows"]]
        # THE PACKAGE. An AI flight of your own type, launched ahead of you
        # on the same card with every ETA LOCKED: the one thing in the file
        # that really flies the timeline. You fit in behind it.
        pkg = None
        if r.timing_package:
            pkg = self._launch_timing_package(m, stats, own_country, home, tl)
        if r.timing_coach:
            from .. import timing_coach as _tc
            n = _tc.attach(m, player_group, tl, self.warnings,
                           package_group=pkg,
                           package_label=stats.get("timing_package_label", "the package"),
                           check=bool(r.check_ride))
            if n:
                stats["timing_coach_triggers"] = n
        return tl

    def _launch_timing_package(self, m, stats, own_country, home, tl):
        """An AI flight on the player's card, PACKAGE_LEAD_S ahead, ETAs locked."""
        from .. import timing as _tm
        from dcs import action as A
        from dcs import triggers as Tr
        from dcs import condition as C
        r = self.recipe
        lead_s = PACKAGE_LEAD_S
        try:
            cls = self._resolve_aircraft(r.aircraft)
            rows = tl["rows"]
            first = rows[0]
            # Airborne a few miles down the first leg at transit altitude,
            # activated so that its LOCKED WP1 time is reachable.
            spawn = mapping.Point(
                home.position.x + (first["point"].x - home.position.x) * 0.25,
                home.position.y + (first["point"].y - home.position.y) * 0.25,
                home.position._terrain)
            alt_m = first["alt_ft"] * 0.3048
            spd = first["kt"] * 1.852
            g = m.flight_group_inflight(own_country, "Package", cls, spawn,
                                        altitude=alt_m, speed=spd, group_size=2)
            for t in rows:
                g.add_waypoint(t["point"], altitude=t["alt_ft"] * 0.3048,
                               speed=t["kt"] * 1.852, name=t["to"])
            try:
                from ..routing import add_recovery
                carrier_home = self._csg.units[0] if self._carrier_home and self._csg else None
                add_recovery(g, home_airport=home if carrier_home is None else None,
                             home_carrier=carrier_home)
            except Exception:
                pass
            _tm.apply_to_group(g, tl, locked=True, offset_s=-lead_s)
            g.late_activation = True
            # Activate a minute before its first locked time would need it.
            when = max(1, tl["takeoff_s"] - lead_s + 30)
            t = Tr.TriggerOnce(comment="Timing: launch the package")
            t.rules.append(C.TimeAfter(when))
            t.actions.append(A.ActivateGroup(g.id))
            m.triggerrules.triggers.append(t)
            tl["package_lead_s"] = lead_s
            stats["timing"]["package_lead_s"] = lead_s
            stats["timing_package_label"] = f"{cls.id} package"
            stats["support"].append(f"{cls.id} package on locked ETAs "
                                         f"{lead_s // 60} min ahead")
            return g
        except Exception as exc:
            self.warnings.append(f"timing package not launched: {exc}")
            return None

    def _player_fuel_kg(self):
        try:
            return float(getattr(self._resolve_aircraft(self.recipe.aircraft),
                                 "fuel_max", None) or 0) or None
        except Exception:
            return None

    def _check_carrier_capable(self, key: str, aircraft, hull_key: str):
        """Hard gate: only carrier-capable aircraft can start on the boat."""
        cap = load_json("carrier_capable")
        deck_class = cap["hull_class"].get(hull_key)
        allowed = cap["classes"].get(deck_class, [])
        if key not in allowed:
            from ..deck import _load_hull
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
        # modules pydcs has no native class for (verified DCS type ids)
        from ..pending import get_pending
        cls, warning = get_pending(name)
        if cls is not None:
            # _resolve_aircraft is called several times per build (roster gating,
            # the player group, the DTC check, the brief), so a pending module
            # used to stamp the SAME warning four times — 500+ characters of an
            # 900-character header budget spent saying one thing.
            if warning not in self.warnings:
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
        from .. import pressure
        self._qnh_hpa = pressure.roll_qnh_hpa(w, self.rng)
        try:
            m.weather.qnh = pressure.qnh_mmhg(self._qnh_hpa)
        except AttributeError:
            pass
