"""Orchestrate ordered PyDCS placement phases after world resolution.

World/domain setup lives in build_context; artifact rendering and packaging
live in artifacts. Placement order is significant for RNG and parking.
"""
import math
import random

import dcs
from dcs import mapping
from dcs.mission import StartType

from .recipe import Recipe
from .resolver import resolve_terrain, resolve_country, load_json, resolve, UnknownUnitError
from . import dressing, airdefense, support_air, backseat, loadouts

START_TYPES = {"cold": StartType.Cold, "warm": StartType.Warm, "runway": StartType.Runway}
# How far ahead of you the timing package flies (timing_package). Two minutes
# is the classic SEAD-to-striker spacing: their missiles are off before you
# are in the ring, and you are not in their frag.
PACKAGE_LEAD_S = 120

# Compatibility exports for callers that historically imported these here.
from .build_context import (EraViolation, aircraft_in_era, prepare_world,
                            CREW_OPS_TEMPLATES, TEMPLATE_ERAS, TIME_PRESETS,
                            _scenario_templates, _template_eras, _bearing, _centroid)


def _fitting_slots(airport, aircraft_type, count):
    """Parking for the player's flight: the NARROWEST adequate stand first.

    pydcs sorts free parking by `(helicopter, slot_name)`, so among every stand
    an aircraft fits it takes whichever sorts first BY NAME — and stand '01' is
    usually the widest thing on the field. Measured across every airfield we
    ship, 22 of 144 hand the F-16 a heavy-capable stand; Fujairah Intl has
    exactly one, and pydcs gives it to the fighter, leaving the tanker nowhere.

    Adding `width` as the second key is the fix the dcs-retribution fork made
    upstream. We make it here rather than in vendor/dcs, which is a byte-for-
    byte mirror (vendor/dcs/PYDCS_PROVENANCE.md). It is also the same bug
    v1.47.0 fixed by hand for the ramp DRESSING; the player's own parking never
    got the treatment because it goes through pydcs, not through our code.

    The `helicopter` key is kept first, and it means the OPPOSITE of what it
    looks like: `False` sorts before `True`, so it puts plain airplane stands
    ahead of dual-use pads, i.e. it keeps an AIRPLANE off a pad.

    Returns None when the airport cannot seat the flight, so the caller's
    existing NoParkingSlotError path still runs and still tries the next field.
    """
    try:
        free = airport.free_parking_slots(aircraft_type)
    except Exception:
        return None
    if len(free) < count:
        return None
    free = sorted(free, key=lambda s: (s.helicopter, s.width or 0,
                                       str(s.slot_name)))
    return free[:count]


class StarterBuilder:
    def __init__(self, recipe: Recipe):
        self.recipe = recipe
        self._timing = None                 # timing.plan() once a route is laid
        self._nttr = None                   # nttr.plan_route() on the Nevada map
        self.rng = random.Random(recipe.seed)
        self.maps = load_json("maps")
        self.eras = load_json("eras")
        self.warnings = []

    def build(self) -> dcs.Mission:
        ctx = prepare_world(self)
        self.context = ctx
        r = self.recipe
        map_cfg = ctx.map_cfg
        era_cfg = ctx.era_cfg
        preset = ctx.preset
        terrain = ctx.terrain
        m = ctx.mission
        crew_ops = ctx.crew_ops
        formation_stage = ctx.formation_stage
        _get_country = ctx.country
        blue_country = ctx.blue_country
        red_country = ctx.red_country
        blue_fields = ctx.blue_fields
        red_fields = ctx.red_fields
        own_fields = ctx.own_fields
        enemy_fields = ctx.enemy_fields
        own_country = ctx.own_country
        enemy_country = ctx.enemy_country
        carrier_home = ctx.carrier_home
        bb_carrier = ctx.bb_carrier
        home = ctx.home
        own_center = ctx.own_center
        enemy_center = ctx.enemy_center
        threat_bearing = ctx.threat_bearing
        away_bearing = ctx.away_bearing
        comms = ctx.comms
        stats = ctx.stats

        # --- carrier strike group (built FIRST so the boat can be home plate) --
        gfx = {"targets": [], "farps": [], "threats": []}   # map-graphics geometry
        csg, brc, hull_key = None, None, None
        strike_group = None
        if bb_carrier:
            from . import naval, deck
            if r.coalition == "blue":
                default_hull = {"wwii": "essex", "coldwar": "forrestal",
                                "modern": "stennis", "gwot": "stennis"}.get(r.era)
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
                    if r.carrier_strike:
                        stk = naval.add_carrier_strike(m, own_country, hull_key,
                                                       carrier_pos, brc, threat_bearing,
                                                       comms, self.warnings, gfx=gfx)
                        if stk:
                            strike_group = stk
                            stats["support"].append(stk.name)
            else:
                self.warnings.append("carrier group is blue-only for now - skipped")
        if carrier_home and csg is None:
            raise EraViolation("Carrier home base selected but no carrier strike group "
                               "could be created on this map/era")
        self._csg, self._brc, self._hull_key = csg, brc, hull_key

        # --- player flight (unless a template pack owns the player) ---------
        # Flight callsign: user's choice, else the airframe's authentic default
        # (callsigns.json — VF-32 "Gypsy", Jolly Rogers "Victory", Misty for
        # the F-100, bort numbers for the red side). "Viper 1" is dead.
        # ...AND THEN MAPPED TO ONE DCS CAN SAY (v1.92.0, Rob: "always map").
        # The sim's radio speaks eight fighter names; the authentic one stays
        # as the heritage line in the brief. See callsign.py.
        from . import callsign as _csn
        def _flight_callsign():
            table = load_json("callsigns")
            e = table.get(r.aircraft)
            if not e or "cs" not in e:
                e = table.get("_fallback_red" if r.coalition == "red"
                              else "_fallback_blue", {"cs": "Colt"})
            wanted = (r.callsign or e["cs"]).strip()
            squadron = e.get("unit") if not r.callsign else None
            _numeric = not getattr(own_country, "use_western_callsigns", True)
            if _csn.is_bort(wanted) and _numeric:
                # bort-number calls ARE the full call ("231"), and DCS says
                # the number for this nation, so nothing to map
                return wanted, wanted, None
            if _numeric:
                # A named callsign on a nation whose radio speaks numbers:
                # the number is what you will hear. Keep the name as heritage.
                num = table.get("_fallback_red", {}).get("cs", "201")
                return num, num, _csn.heritage_line(wanted, num, squadron)
            used = _csn.dcs_name(wanted)
            return f"{used} 1", used, _csn.heritage_line(wanted, used, squadron)
        flight_name, self._callsign_used, _heritage = _flight_callsign()
        self._flight_name = flight_name
        stats["callsign"] = flight_name
        if _heritage:
            stats["callsign_heritage"] = _heritage
        # Does this ride fly with a second airplane? One predicate — the same
        # one the kneeboard's promise is printed from.
        _wk_ride_pre = ((_scenario_templates().get(r.template) or {})
                        .get("wk_ride") if r.template else None)
        from . import wk as _wk_pre
        _wk_two_ship = bool(_wk_ride_pre
                            and _wk_pre.has_counterpart(_wk_ride_pre, r.map))
        player_group = None
        air_start_mode = None      # set by the air-start branch; drives the
                                   # target-relative reposition further down
        bfm_heading = None         # the player's briefed heading for BFM setups
        if formation_stage:
            # Formation training owns the player flight: you are DASH 2 on an AI
            # lead. Every other branch below makes you element lead, which is
            # the one thing a formation-keeping sortie cannot be.
            from . import formation as _form
            aircraft = self._resolve_aircraft(r.aircraft)
            player_group, _fstats = _form.build(
                m, r, own_country, home, formation_stage, aircraft,
                self.warnings)
            stats.update(_fstats)
        elif not crew_ops and carrier_home and r.cq_ride:
            # CASE III: the ride begins in the procedure, not on the deck.
            #
            # Every other carrier mission starts you parked, because "air" has
            # no meaning on the boat. A recovery is the opposite shape: the
            # whole lesson happens between the marshal fix and the ramp, and a
            # ride that made you launch first would spend fifteen minutes
            # getting to the part being taught. So the flight spawns airborne
            # at a point computed from the SHIP'S OWN BRC — a radial and a DME,
            # which is the only way a carrier fix is ever expressed.
            from . import cq as _cq, cq_route as _cqr
            aircraft = self._resolve_aircraft(r.aircraft)
            self._check_carrier_capable(r.aircraft, aircraft, hull_key)
            _st = _cqr.start_state(r.cq_ride, csg.units[0].position, brc)
            if _st is None:
                raise EraViolation(
                    f"cq_ride={r.cq_ride!r} produced no start point")
            _p, _alt_ft, _ias, _hdg = _st
            # KM/H for the group speed, metres for the altitude. Indicated in,
            # true out — the same conversion the route uses, so the airplane
            # is not handed a speed its own flight plan disagrees with.
            player_group = m.flight_group_inflight(
                own_country, flight_name, aircraft, _p,
                int(_alt_ft * _cq.FT_M),
                speed=int(_cqr.ias_to_tas_kt(_ias, _alt_ft) * _cq.KT_KMH),
                # SINGLE AIRCRAFT. NATOPS 6.4: "Night/IMC Case III recoveries
                # shall be made with single aircraft." A wingman in the stack
                # would be teaching the wrong thing, and DCS's AI cannot fly a
                # Case III anyway — it reverts to Case I in the pattern.
                group_size=1)
            self._cq_start_heading = _hdg
            air_start_mode = "cq"
        elif not crew_ops and carrier_home:
            aircraft = self._resolve_aircraft(r.aircraft)
            self._check_carrier_capable(r.aircraft, aircraft, hull_key)
            player_group = m.flight_group_from_unit(
                own_country, flight_name, aircraft, csg,
                # "air" has no meaning on the boat: deck starts only. Warm is
                # the closest intent (ready now), not a KeyError.
                start_type=START_TYPES.get(r.start, StartType.Warm),
                group_size=max(1, min(4, r.slots)))
        elif not crew_ops and r.start == "air":
            # --- E1 air start (PRD v2): spawn airborne, no transit tax -------
            # Position comes from the template's air_start flag:
            #   "tanker"  = 7 km short of the tanker's orbit anchor at FL200,
            #               so the join-up is a gentle closure, not a chase
            #   "merge"   = toward the threat axis at combat altitude; the
            #               BFM block (bb_bfm) puts the bandit 2 nm abeam
            #   "roll_in" / "outside_the_ring" = TARGET-RELATIVE, and the
            #               target does not exist yet at this point in the
            #               build — a provisional position goes down here and
            #               `_air_start_on_target` moves the flight once the
            #               package is placed. See that function for why the
            #               target isn't simply computed earlier.
            #   default   = 15 km off home plate toward the theater, cruise alt
            # Helicopters spawn low and slow regardless.
            aircraft = self._resolve_aircraft(r.aircraft)
            sc_air = (_scenario_templates().get(r.template, {}) or {}).get(
                "air_start") if r.template else None
            from .dressing import _offset as _as_off
            helo = getattr(aircraft, "helicopter", False)
            # AIRFRAME-CORRECT block. The fixed 4500 m / 800 km/h here was a
            # fast-jet number: an A-10 does not cruise at 430 kt and a warbird
            # cannot. formation.cruise_for() derives both from the airframe's
            # own max_speed and exists because exactly this kind of hard-coded
            # constant once made the product "an F-16 tool".
            from .formation import cruise_for as _cruise
            _alt_ft, _kt = _cruise(aircraft)
            cruise_alt = int(_alt_ft * 0.3048)          # ft -> m
            cruise_spd = int(_kt * 1.852)               # kt -> km/h
            if sc_air in ("tanker", "astern_tanker"):
                pos = _as_off(own_center, 48000, away_bearing)
                # The tanker's OWN block, not a fast-jet constant. FL200 at
                # 380 kt put a Hornet 8,000 ft above and 100 kt faster than a
                # KC-130 it was supposed to be joining.
                alt, spd = 6096, 700
                try:
                    from . import aar as _aar0
                    _k = _aar0.choose(aircraft.id, r.era, carrier=carrier_home,
                                      preferred=r.tanker_type or None,
                                      map_key=r.map) \
                         or _aar0.choose(aircraft.id, r.era,
                                         carrier=carrier_home, map_key=r.map)
                    if _k:
                        alt = int(_aar0.track_alt_m(_k, r.map))
                        spd = int(_aar0.track_speed_kmh(_k, aircraft.id, r.map))
                except Exception:
                    pass
            elif sc_air == "merge":
                pos = _as_off(home.position, 22000, threat_bearing)
                alt, spd = cruise_alt, cruise_spd
                # YOUR NOSE, briefed. The BFM setups are stated relative to it
                # ("1.2 nm off your nose, 30 degrees angle off"), so it cannot
                # be whatever pydcs defaults to — the geometry would be a
                # different ride every time and the brief would be fiction.
                bfm_heading = threat_bearing
            else:
                pos = _as_off(home.position, 15000, away_bearing)
                alt, spd = cruise_alt, cruise_spd
            if helo:
                alt, spd = 300, 200
            player_group = m.flight_group_inflight(
                own_country, flight_name,
                aircraft, pos, alt, speed=spd,
                group_size=max(2 if _wk_two_ship else 1, min(4, r.slots)))
            air_start_mode = sc_air
            # home plate stays the RTB field: kneeboard, comms and briefing
            # all reference it, and DCS lets an airborne flight land anywhere.
        elif not crew_ops:
            aircraft = self._resolve_aircraft(r.aircraft)
            from dcs.terrain.terrain import NoParkingSlotError
            player_group = None
            for field in [home] + [a for a in own_fields if a is not home]:
                try:
                    # THE WINGMAN IS IN YOUR FLIGHT. Three separate-flight
                    # designs in a row failed the same way — Rob: "the other
                    # REX flight doesn't fly with me at all" — because DCS
                    # gives an independent flight no way to hold position on a
                    # human. The one native mechanism that flies WITH you is a
                    # unit in your own group: he taxis with you, forms on your
                    # wing, rejoins, and attacks on your radio call. So a ride
                    # with a counterpart is built as a TWO-SHIP, and the old
                    # scripted second flight is gone.
                    _n_ship = max(2 if _wk_two_ship else 1, min(4, r.slots))
                    player_group = m.flight_group_from_airport(
                        own_country, flight_name,
                        aircraft, field,
                        start_type=START_TYPES[r.start],
                        group_size=_n_ship,
                        parking_slots=_fitting_slots(
                            field, aircraft, _n_ship))
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
            # The callsign the FILE carries is the one the paperwork prints.
            # pydcs writes only the name string; DCS reads the index. Both now.
            _csn.apply(player_group, self._callsign_used)
            if formation_stage:
                pass          # formation.build already seated you as Dash 2
            elif r.slots <= 1:
                player_group.units[0].set_player()
                # The White Knights wingman: seat 2 is the AI on your wing.
                from dcs.unit import Skill as _Skill
                for _u in player_group.units[1:]:
                    _u.skill = _Skill.Excellent
            else:
                for u in player_group.units:
                    u.set_client()
            fc = comms.freq("flight_common")
            # A VHF-ONLY JET GETS A VHF FLIGHT FREQUENCY. The self-check found
            # this on its first run: a P-51D with its wingman on 305.725 and a
            # card that said so. Now the ladder yields to the airframe's band.
            from . import saydo as _sdb
            fc, ft, _swapped = _sdb.in_band_flight_freqs(
                aircraft, fc, comms.freq("tactical"))
            try:
                player_group.set_frequency(fc)
            except Exception:
                pass
            from .acnames import display as _ac_display
            _band_note = " · this aircraft's band" if _swapped else ""
            comms.add("Flight", player_group.name, f"{fc:.3f}", "-",
                      _ac_display(r.aircraft, aircraft.id) + _band_note)
            comms.add("Tactical", "-", f"{ft:.3f}", "-",
                      "inter-flight coordination" + _band_note)

            # --- YOUR loadout ------------------------------------------------
            # The player's jet used to spawn with empty pylons, on every mission
            # kind, and that was described as a feature ("your loadout is yours
            # to set in the Mission Editor"). It was never a decision — it is
            # the same missing payload data that left the bandits clean until
            # v1.44.0, since pydcs's `load_task_default_loadout()` is a silent
            # no-op without a DCS install to read payload .lua files from.
            #
            # Now the mission kind picks the fit. It is still yours to change in
            # the Mission Editor, and `player_arm=False` turns it off entirely
            # for people who would rather start from a clean jet.
            if r.player_arm:
                from .scenario_payloads import resolve_fit
                fit = resolve_fit(r, aircraft.id)
                label = loadouts.apply_fit(player_group, fit, aircraft.id,
                                           self.warnings)
                if label:
                    stats["player_loadout"] = label
                    stats["player_loadout_role"] = loadouts.KIND_ROLE.get(
                        r.mission_kind, loadouts.ROLE_CAP)
                    # Station-by-station, for the kneeboard. The engine has
                    # known exactly what is on each pylon since v1.48.0 and
                    # printed it precisely nowhere the pilot could reach in
                    # flight — the summary string went in the PDF brief, which
                    # is on the desktop behind the sim.
                    stats["player_pylons"] = loadouts.station_list(fit)
                # WHITE KNIGHTS: the delivery sheet wins. `mission_kind` was
                # never set on these cards, so a ride briefing "6 x MK-82LD"
                # composed the air-to-air fit and flew with nothing to drop.
                # Setting mission_kind would only trade one generic fit for
                # another; the card names specific stores, so the card's stores
                # go on the jet.
                _wkr_ride = (_scenario_templates().get(r.template) or {}) \
                    .get("wk_ride") if r.template else None
                _pyl = None
                if _wkr_ride:
                    from . import wk as _wkfit
                    _pyl = _wkfit.loadout_for(_wkr_ride)
                    if _pyl:
                        # CLEAR FIRST. The composed CAP fit already ran, and
                        # merely adding a MER on top left four Sparrows, a
                        # tank and a pair of AIM-9P5s hanging beside it — so
                        # the STORES block on the card listed one thing and
                        # the jet wore another. The P5 is an anachronism here
                        # too; the sheet fit carries the period AIM-9J.
                        for _u in player_group.units:
                            _u.pylons = {}
                        for _st, _cl in sorted(_pyl.items()):
                            try:
                                player_group.load_pylon(
                                    (int(_st), {"clsid": _cl}), int(_st))
                            except Exception as _e:
                                self.warnings.append(
                                    f"station {_st} would not take {_cl}: {_e}")
                        self._wk_pylons = _pyl
                        stats["player_pylons"] = [
                            (st, _pyl[st]) for st in sorted(_pyl)]
                # WARN ONLY IF THE JET IS ACTUALLY EMPTY.
                #
                # This `else` used to hang off `if _wkr_ride:`, so EVERY
                # mission that was not a White Knights ride got told "your jet
                # starts clean" — including the ones that had just been armed
                # two lines earlier and printed their stores on the kneeboard.
                # The brief said clean, the card listed four BDU-45s and two
                # tanks, and the airplane wore the four BDU-45s. A warning
                # that contradicts the mission is the same defect as a card
                # that contradicts the mission, and it had been shouting on
                # every carrier sortie anyone generated.
                if not label and not _pyl:
                    self.warnings.append(
                        f"No loadout could be composed for {aircraft.id} "
                        f"({r.mission_kind}, {r.era}) - your jet starts clean. "
                        f"Set it in the Mission Editor.")

            # --- YOUR livery -------------------------------------------------
            # Nothing is written while the livery pack is unverified: a livery
            # id is a folder name on a disk and cannot be checked from a server.
            # Once scripts/dump_liveries.py has read the real names off an
            # install, the era-correct squadron marking appears here.
            liv = dressing.player_livery(
                aircraft.id, r.era, getattr(own_country, "name", None),
                getattr(r, "dress_livery_style", "squadron"))
            if liv:
                for u in player_group.units:
                    u.livery_id = liv
                stats["player_livery"] = liv

        # --- building blocks -------------------------------------------------
        # Does the enemy fly at all? `threats.TIER_CAP` is the single source of
        # truth, and in the GWOT era the answer is no. Read once, here, because
        # three separate things downstream depend on it: enemy ambient traffic,
        # the SITUATION paragraph, and (via the empty SAM pools) whether the
        # area threat belt is guns.
        _enemy_side_key = "red" if r.coalition == "blue" else "blue"
        from . import threats as _thr_amb
        enemy_flies = bool(_thr_amb.cap_types_for(r.era, _enemy_side_key, "auto"))
        stats["no_enemy_air"] = not enemy_flies

        # ambient traffic BEFORE dressing so AI aircraft claim parking slots first
        if r.bb_ambient:
            from . import ambient
            enemy_side = _enemy_side_key
            stats["ambient"] += ambient.add_ambient_traffic(
                m, own_country, own_fields, era_cfg[r.coalition], r.density,
                self.rng, "friendly")
            # Enemy ambience only where the enemy HAS an air force. The GWOT
            # era's red parked_planes are derelict Iraqi Air Force airframes
            # left where they stood; ambient traffic would taxi them out and
            # fly them, which is the single most wrong thing this era could do.
            if enemy_flies:
                stats["ambient"] += ambient.add_ambient_traffic(
                    m, enemy_country, enemy_fields, era_cfg[enemy_side], r.density,
                    self.rng, "enemy")

        # BB-23: aircraft in the pattern at the player's own field. Also before
        # dressing, so departing traffic gets its parking stand first. Skipped
        # when home plate is the boat (no runway pattern to fly).
        if getattr(r, "bb_pattern", False) and not carrier_home and home is not None:
            from . import pattern
            _lineup_on = bool(getattr(r, "pattern_lineup", False))
            names = pattern.add_pattern_traffic(
                m, own_country, home, era_cfg[r.coalition],
                r.pattern_mode, r.pattern_kind, r.pattern_count,
                self.rng, self.warnings, lineup=_lineup_on, map_key=r.map)
            if names:
                _nm = set(names)
                _ac = sum(len(g.units) for g in (list(own_country.plane_group)
                                                  + list(own_country.helicopter_group))
                          if g.name in _nm)
                stats["pattern"] = {
                    "names": names, "mode": r.pattern_mode,
                    "kind": r.pattern_kind, "field": home.name,
                    "lineup": _lineup_on, "aircraft": _ac or len(names)}

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
                            ramp_heavies=getattr(r, "ramp_heavies", "auto"),
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

            # Bases with covered parking (sun-shelters over the stands, e.g.
            # Kandahar): the per-aircraft GSE truck is offset to the side of the
            # jet and lands on the shelter's curved roof — DCS clamps it to that
            # sloped mesh so the truck sits tilted on top. We have no scenery
            # geometry to place around, so GSE is suppressed at these bases;
            # aircraft (placed AT the stand, which fits under the arch) are kept.
            covered_ramp = set(map_cfg.get("covered_ramp", []))

            def _dress(ap, country, cfg, theme, side, mix=None):
                ov = overrides.get(ap.name)
                # civilian fields stay empty UNLESS explicitly overridden
                # ("populate anyway"); an override of 0 empties ANY field
                if ov is None and ap.name in civilian:
                    skipped.append(ap.name); return 0
                if ov == 0:
                    skipped.append(ap.name); return 0
                kw = dict(dress_kw)
                if ap.name in covered_ramp:
                    kw["include_gse"] = False       # trucks would clip the shelters
                if ov is not None:
                    kw["fill"] = ov
                kw["field_heading"] = field_hdgs.get(ap.name)
                kw["mix"] = mix
                kw["map_key"] = r.map
                # Per-FIELD ramp identity: Nellis is the Red Flag ramp, the test
                # sites that share the map are not. Only consulted when the map
                # actually names this field — otherwise the caller's theme wins,
                # because it may already carry something more specific.
                #
                # `side` is PASSED IN, not inferred. v1.47.0 worked it out with
                # `theme is own_theme`, an identity check against a value the
                # caller had already transformed: `_atheme()` merges an aligned
                # nation's roster over the side theme and returns a NEW dict, so
                # the check was false for every internationally-aligned base and
                # flipped it to the enemy side. Incirlik — blue, Turkish, NATO —
                # came out parked with A-50s, Il-76s, Su-24s and MiG-29s.
                # ONLY the per-field table may override, and only for a field it
                # actually names. The caller's `theme` has already been through
                # resolve_theme (with the user's explicit choice) and then
                # through _atheme, which merges an aligned nation's roster over
                # it. Re-resolving here for any other reason throws that away —
                # which is the second instance of the same bug, and would have
                # put the map's default ramp on Akrotiri the moment someone
                # picked a theme in the Builder.
                per_field = ((preset.get(f"{side}_field_themes") or {})
                             .get(ap.name))
                field_theme = None
                if per_field and not align_bases.get(ap.name):
                    _k, field_theme = dressing.resolve_theme(
                        r.era, side, preset, None, airport_name=ap.name)
                return dressing.dress_airfield(
                    m, ap, country, cfg, r.density, self.rng,
                    theme=field_theme or theme, **kw)

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
                    era_cfg[r.coalition], _atheme(ap, own_theme),
                    r.coalition, mix=r.dress_mix)
            for ap in enemy_fields:
                stats["statics"] += _dress(
                    ap, _acountry(ap, enemy_country, enemy_side),
                    era_cfg[enemy_side], _atheme(ap, enemy_theme), enemy_side)
            from .dressing import livery_pack_verified as _lv
            if r.dress_livery_style != "clean" and not _lv():
                self.warnings.append(
                    "Parked statics use DCS stock skins: the curated livery pack "
                    "is unverified, so its names are not written. Run "
                    "scripts/dump_liveries.py --merge against your DCS install "
                    "to enable nation-correct skins.")
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
            from . import aar as _aar
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
                    from . import aar_grade as _agr, aar_hud as _ahud
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
        from . import airspace
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
            from .dressing import _offset as _pt_offset
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
                from . import wk_route as _wkr0
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
                    from . import threats as _thr
                    for j in range(2):
                        cpos = _pt_offset(center, self.rng.uniform(800, 2000),
                                          self.rng.uniform(0, 360))
                        if _thr.place_aaa_cluster(
                                m, enemy_country, r.era,
                                "red" if r.coalition == "blue" else "blue",
                                cpos, self.rng, f"AAA TGT{i+1}-{j+1}"):
                            gfx["threats"].append((cpos, 3500, "AAA"))

        if r.bb_range:
            from . import targets as tgt
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
            from . import threats as _thr2
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

        # --- player flight plan ----------------------------------------------
        # THE ONLY PLACE PLAYER WAYPOINTS EXIST, and it happens for exactly two
        # reasons, both of them a request:
        #
        #   * a scenario template declares "route": "strike" — a routed strike
        #     is the mission FORMAT there, the way a Case recovery is the format
        #     for a carrier template;
        #   * the user ticked `bb_route`.
        #
        # Default behavior is unchanged: no tick, no template, no waypoints.
        # See routing.py for what the north star actually says. Runs after
        # bb_targets so the route can aim at a real target package.
        # Resolved once, ABOVE the routing block, because both the flight plan
        # and the briefing need it and the routing block runs first.
        _wk_ride = (_scenario_templates().get(r.template) or {}).get("wk_ride") \
            if r.template else None
        route_rows = None
        # CASE III: the flight plan IS the approach plate. Laid first, for the
        # same reason the White Knights route is — so the generic router below
        # cannot also fire and give the flight two overlapping plans — and off
        # the CARRIER rather than a home field, because every fix in a recovery
        # is a radial and a DME from the ship.
        _cq_rows = []
        if player_group is not None and r.cq_ride and self._csg is not None:
            from . import cq as _cq2, cq_route as _cqr2, cq_coach as _cqc
            _cq_rows = _cqr2.apply(player_group, r.cq_ride,
                                   self._csg.units[0].position, self._brc)
            if _cq_rows:
                stats["cq_route"] = _cq_rows
            stats["cq_ride"] = r.cq_ride
            stats["cq_requires"] = _cq2.REQUIRES_MODULE
            # The cues and the grades. Attached AFTER the route because the
            # brief prints them alongside it, and never raising because a
            # recovery without coaching is a worse mission, not a failed build.
            _mother = next((fq for ag, cs_, fq, *_ in comms.entries
                            if ag == "Carrier"), None)
            try:
                _mother_mhz = float(_mother) if _mother else None
            except (TypeError, ValueError):
                _mother_mhz = None
            try:
                _ac_id = self._resolve_aircraft(r.aircraft).id
            except Exception:
                _ac_id = r.aircraft
            _cqc.attach(m, player_group, self._csg, r.cq_ride, self.warnings,
                        aircraft=_ac_id, mother_mhz=_mother_mhz)
            # The gate is installed after the radios are programmed (below),
            # so its reminder can name the channel that really holds Mother.
            self._cq_gate = (_ac_id, _mother_mhz) if _mother_mhz else None

        # WHITE KNIGHTS: a bespoke flight plan whose geometry IS the lesson.
        # The generic strike router cannot produce an IP at the delivery
        # sheet's own pull-up distance or a split point at the range the
        # squadron's guide names, because it has never read the document.
        # Laid FIRST so `wants_route` below cannot also fire and give the
        # flight two overlapping plans.
        _wk_rows = []
        if player_group is not None and _wk_ride:
            from . import wk_route as _wkr
            _wk_rows = _wkr.apply(player_group, home.position, _wk_ride,
                                  r.map, home_airport=home)
            if _wk_rows:
                stats["wk_route"] = _wk_rows
            # THE AIRPLANE EVERY CARD PROMISED is seat two of your own
            # flight now — created with the group, armed with the group,
            # parked by the group (which is also what keeps a static out of
            # his shelter: both stands are claimed before the ramp dressing
            # runs).
            stats["wk_counterpart"] = len(player_group.units) > 1
            # THE COACHED RIDE. Cues at every decision in the B'NAI, on the
            # same leg table the waypoints came from, and a re-arm after
            # egress so the whole thing can be flown again without reloading.
            # Attached AFTER the route, because it places its zones on the
            # points the route just laid.
            from . import wk_coach as _wkc
            from . import wk_brief as _wkb
            # THE BRIEF GOES FIRST, and not only for tidiness: it owns the
            # coaching's arm flag. If it attached, the cues stay dark until
            # the pilot presses SPACE on the last page and gets his controls
            # back — otherwise the coaching's own timer would start calling
            # the attack while he was still reading who he is.
            _n_brief = _wkb.attach(m, player_group, _wk_ride, _wkc.F_ARM,
                                   warnings=self.warnings)
            if _n_brief:
                stats["wk_brief_triggers"] = _n_brief
            _n_cues = _wkc.attach(m, player_group, _wk_ride, r.map,
                                  home.position, warnings=self.warnings,
                                  armed_externally=bool(_n_brief),
                                  ring=getattr(r, "coach_ring", "red"))
            if _n_cues:
                stats["wk_coach_triggers"] = _n_cues
            # No wingman-hold trigger any more: seat two is in YOUR group,
            # so he waits because you wait — the brief holds the flight by
            # holding you, which is what "held" should have meant all along.
            # THE NAVIGATION SQUARES. Rob asked for "the green navigation
            # boxes" — DCS's helper gates, the fly-through squares from the
            # training missions — and they are a NATIVE Mission Editor action
            # (`a_show_route_gates_for_unit`), not Lua: the gates render along
            # the unit's own flight plan, which for this ride IS the lesson
            # geometry. Shown when the brief hands the airplane over, so the
            # boxes appear at the same instant the coaching arms; on a
            # brief-less build they show a second in.
            if getattr(r, "coach_gates", False):
                from dcs import action as _A2, condition as _C2
                from dcs import triggers as _Tr2
                _me_id = player_group.units[0].id
                _g = _Tr2.TriggerOnce(comment="WK gates: navigation squares")
                if _n_brief:
                    _g.rules.append(_C2.FlagIsTrue(_wkb.F_DONE))
                else:
                    _g.rules.append(_C2.TimeAfter(1))
                _g.actions.append(_A2.ShowHelperGatesForUnit(_me_id, 1))
                # PIN THE POINTER. Rob: "the navigation aids don't fly to the
                # target" — the gates drew, but the line they traced was not
                # the lesson. The gates render from the unit's ACTIVE route
                # point, and after minutes held on the ramp reading the brief,
                # where DCS thinks you are on your own plan is anybody's
                # guess. So the active gate is set explicitly: to the low
                # level when you take the airplane, and forward from the
                # coaching's own phase flags as you earn each cue — the boxes
                # and the WSO advance from the same facts. (First pass only:
                # the phase flags re-fire on the re-attack but a TriggerOnce
                # is spent; the second run is flown on the cues, which is the
                # point of a second run.) Route points: 0 parking,
                # 1 departure, 2 low level, 3 trail, 4 IP, 5 pull-up,
                # 6 target, 7 egress, 8 recovery.
                _g.actions.append(_A2.SetActiveHelperGateToPoint(_me_id, 2))
                m.triggerrules.triggers.append(_g)
                from . import wk_coach as _wkc2
                _gate_wp = {"lowlevel": 3, "trail": 4, "ip": 5, "runin": 5,
                            "pup": 6, "release": 7, "pullout": 7,
                            "egress": 8}
                for _key, _wp in sorted(_gate_wp.items()):
                    _t2 = _Tr2.TriggerOnce(
                        comment=f"WK gates: next box after {_key}")
                    _t2.rules.append(_C2.FlagIsTrue(
                        _wkc2.F_PHASE + _wkc2.IDX[_key]))
                    _t2.actions.append(
                        _A2.SetActiveHelperGateToPoint(_me_id, _wp))
                    m.triggerrules.triggers.append(_t2)
        wants_route = (not _wk_ride) and (bool(getattr(r, "bb_route", False)) or (
            r.template and _scenario_templates().get(r.template, {}).get("route") == "strike"))
        if player_group is not None and wants_route and gfx["targets"]:
            from . import routing
            tgt_pos, tgt_label = gfx["targets"][0]
            # Where the map has published corridors (corridors.py: Nevada,
            # Syria) the plan is threaded through them - departure, corridor,
            # entry gate as WP1, IP, TARGET, exit gate, recovery. Everywhere
            # else, and for a target inside the home's terminal area, the
            # generic three-point route.
            from . import corridors as _nttr
            self._nttr = _nttr.plan_route(home.position, tgt_pos, r.era,
                                          self.rng, m.terrain, r.map,
                                          home_name=home.name) if r.published_corridors else None
            legs = (self._nttr["legs"] if self._nttr else
                    routing.route_for(home.position, tgt_pos, r.era, self.rng,
                                      m.terrain))
            if legs:
                landed = routing.apply(legs=legs, player_group=player_group,
                                       home_airport=home)
                route_rows = routing.leg_card(home.position, legs, home.name)
                stats["route"] = routing.summary(legs, tgt_label, home.name)
                stats["route_legs"] = route_rows
                stats["route_target"] = tgt_label
                if self._nttr:
                    _nttr.draw(m, self._nttr, r.map)
                    stats["nttr"] = {
                        "map": r.map,
                        "title": _nttr.data(r.map).get("text", {}).get("md_title", "Corridors"),
                        "sector": self._nttr["sector"], "mode": self._nttr["mode"],
                        "corridors": list(self._nttr["corridors"]),
                        "gate_in": self._nttr["gate_in"], "gate_out": self._nttr["gate_out"],
                        "summary": _nttr.summary(self._nttr),
                        "brief": _nttr.brief_lines(self._nttr),
                        "md_line": _nttr.md_line(self._nttr),
                        "approx": _nttr.approx_fixes(self._nttr),
                    }
                # THE CLOCK ON THE CARD. Every routed flight plan is timed
                # (timing.py): leg, cumulative and ETA per point, anchored on
                # takeoff unless the recipe anchors it on the push or the TOT
                # — in which case the mission clock is solved backwards and
                # MOVED here, before anything prints it.
                self._timing = self._time_the_route(m, stats, route_rows,
                                                    player_group, own_country,
                                                    home)
                if not landed:
                    self.warnings.append(
                        "the flight plan has no recovery point: this airfield "
                        "would not accept a landing waypoint. The outbound "
                        "route is unaffected.")
        elif player_group is not None and getattr(r, "bb_route", False):
            # Asked for and not delivered. Silence here would look like a bug —
            # the box is ticked and the F10 map is empty.
            self.warnings.append(
                "automatic waypoints were requested but this mission has no "
                "target to route to. Turn on strike target packages, or pick a "
                "card that places a target.")

        # --- template packs ---------------------------------------------------
        from . import library_scenarios
        library_lines = library_scenarios.add_actors(ctx, r, player_group, gfx)
        library_lines += library_scenarios.complete_strike(ctx, strike_group, csg, gfx)
        template_brief = ""
        crew_flight = None                     # crew-ops flight owns the player jet
        if r.cq_ride:
            # CASE III. Same reasoning as the White Knights card below — the
            # card is generated because the same ride tells a different truth
            # in a different cockpit: the Tomcat sets ICLS on the ARA-63 panel
            # and the Hornet on the UFC, and on-speed is 15 units in one jet
            # and 8.1 in the other.
            from . import cq as _cq3, cq_route as _cqr3
            _hull = None
            try:
                _hull = self._csg.units[0].name if self._csg else None
            except Exception:
                _hull = None
            _cq_card = _cq3.brief_lines(
                r.cq_ride, r.aircraft, brc=self._brc, hull_label=_hull)
            _fp = _cqr3.brief_lines(r.cq_ride, _cq_rows, self._brc,
                                    (_cq3.ride(r.cq_ride) or {}).get("angels", 6))
            if _fp:
                _cq_card = _cq_card + [""] + _fp
            stats["cq_card"] = _cq_card
            # The kneeboard slot is shared with the White Knights card on
            # purpose: a mission has exactly one ride card, and two modules
            # writing to two slots would eventually put both on the kneeboard.
            self._wk_card = _cq_card
            self._wk_card_title = (
                f"CASE III {(_cq3.ride(r.cq_ride) or {}).get('n', '')}: "
                f"{(_cq3.ride(r.cq_ride) or {}).get('name', '')}")
            template_brief = "\n".join(_cq_card)
        elif _wk_ride:
            # WHITE KNIGHTS: the card is GENERATED, not stored, because the same
            # ride tells a different truth in a different theatre. The low-level
            # floor is the case that forced it — the squadron's own contract
            # says formations work down to 300 ft and West Germany's floor was
            # 500. A stored card would have to pick one and be wrong in the
            # other, which is the say/do gap wearing a period costume.
            #
            # THIS BRANCH IS FIRST ON PURPOSE. It used to sit after `bb_bfm`,
            # and ride 11 sets `bb_bfm` — so the generic BFM standards card
            # silently replaced the squadron's own sixteen directive calls.
            # The card advertised WIS No. 1 and the mission shipped something
            # else, which is exactly the defect class this product exists to
            # remove. `tests/test_wk.py` pins every ride's own title into its
            # own mission so it cannot happen again.
            from . import wk as _wk
            from . import wk_route as _wkr
            _wk_card = _wk.brief_lines(
                _wk_ride, map_key=r.map,
                aircraft_id=getattr(self._resolve_aircraft(r.aircraft), "id", ""))
            _disclosure = ((_scenario_templates().get(r.template) or {}).get("library") or {}).get("disclosure")
            if _disclosure:
                _wk_card = [_disclosure, ""] + _wk_card
            _fp = _wkr.brief_lines(_wk_ride, r.map, _wk_rows)
            if _fp:
                _wk_card = _wk_card + [""] + _fp
            stats["wk_card"] = _wk_card
            # ...and onto the KNEEBOARD. Stashed on `self` rather than written
            # into `self.kb_ctx` directly: that dict is BUILT further down, so
            # an assignment here would be silently thrown away.
            self._wk_card = _wk_card
            self._wk_card_title = _wk.RIDES[_wk_ride]["title"]
            # ...and the squadron's own diagram, where the ride flies one of
            # the four attacks. Degrades to no page if the asset is absent.
            _atk = _wk.RIDES[_wk_ride].get("attack")
            if _atk:
                _dp = _wk.diagram_path(_atk)
                if _dp:
                    self._wk_diagram = str(_dp)
                    self._wk_diagram_cap = _wk.diagram_note(_atk)
            template_brief = "\n".join(_wk_card)
        elif r.template in ("backseat_izlid", "backseat_intercept", "rio_fleet_defense"):
            target_area = mapping.Point(
                enemy_center.x + self.rng.uniform(-8000, 8000),
                enemy_center.y + self.rng.uniform(-8000, 8000), m.terrain)
            if r.template == "backseat_izlid":
                crew_flight = backseat.build_backseat_izlid(
                    m, r, blue_country, red_country, home,
                    target_area, self.rng, comms, self.warnings)
                template_brief = backseat.BRIEFING_BLOCK
            elif r.template == "backseat_intercept":
                crew_flight = backseat.build_backseat_intercept(
                    m, r, blue_country, red_country,
                    home, target_area, self.rng, comms, self.warnings)
                template_brief = backseat.INTERCEPT_BRIEFING_BLOCK
            else:
                crew_flight = backseat.build_rio_fleet_defense(
                    m, r, blue_country, red_country,
                    home, target_area, self.rng, comms,
                    r.era, csg=self._csg if carrier_home else None)
                template_brief = backseat.RIO_BRIEFING_BLOCK
        elif formation_stage:
            # The instruction sheet IS the mission. Generated rather than stored
            # in the template so the sight picture matches the aircraft you
            # actually chose — a Phantom wingman and a Viper wingman are looking
            # at completely different things.
            from . import formation as _form
            aircraft = self._resolve_aircraft(r.aircraft)
            template_brief = "\n".join(
                _form.brief_lines(formation_stage, aircraft.id))
        elif r.bb_bfm:
            # The STANDARDS CARD is the brief for a BFM ride. Generated rather
            # than stored so it matches the rung actually flown — a card that
            # describes the neutral merge while you are on the defensive perch
            # is worse than no card, because a pilot will believe it.
            from . import bfm as _bfmdoc
            template_brief = "\n".join(_bfmdoc.brief_lines(
                getattr(r, "bfm_setup", "neutral"),
                aircraft_id=getattr(self._resolve_aircraft(r.aircraft), "id", ""),
                guns_only=(r.era == "wwii")))
        elif r.template:
            # SCENARIO template: append its suggested-tasking block (no waypoints).
            sc = _scenario_templates().get(r.template)
            if sc and sc.get("brief"):
                template_brief = "\n".join(sc["brief"])

        # --- AAR: the procedure card for the tanker actually placed ---------
        if stats.get("aar"):
            from . import aar as _aardoc
            _tk = comms.cfg("tanker")
            _extra = _aardoc.brief_lines(
                stats["aar"],
                receiver_id=getattr(self._resolve_aircraft(r.aircraft), "id", ""),
                freq=f"{_tk['freq']:.3f}", tacan=_tk["tacan"], map_key=r.map)
            # The hardware page rides along on the dedicated AAR cards only.
            # It is read once, on the ground; putting it on every mission with
            # a tanker would bury the procedure under two pages of settings
            # advice the pilot read a month ago.
            if (r.template or "").startswith(("aar_", "qf_tanker")):
                _extra = _extra + [""] + _aardoc.hardware_lines()
            # If the grader attached, the card MUST say what it grades — and
            # more importantly what it does not. A ride that shows a pass
            # message without telling you the plug was never measured is a
            # brief promising what the mission does not contain.
            if stats.get("aar_grade"):
                from . import aar_grade as _agrdoc
                _extra = _extra + [""] + _agrdoc.brief_lines(stats["aar_grade"])
            if stats.get("aar_hud"):
                from . import aar_hud as _ahuddoc
                _extra = _extra + [""] + _ahuddoc.brief_lines()
            if stats.get("aar_gates"):
                from . import aar_hud as _ahuddoc2
                _extra = _extra + [""] + _ahuddoc2.gate_brief_lines()
            template_brief = ((template_brief + "\n\n") if template_brief else "") \
                + "\n".join(_extra)

        disclosure = ((_scenario_templates().get(r.template) or {}).get("library") or {}).get("disclosure")
        if disclosure:
            library_lines.insert(0, disclosure)
        if library_lines:
            stats["scenario_facts"] = library_lines
            template_brief = "\n".join(library_lines) + "\n\n" + (template_brief or "")

        # --- air corridors: brief the lane + enemy picture, draw the axis ------
        if self._corridors:
            names = ", ".join(c["name"] for c in self._corridors)
            lines = ["== AIR CORRIDOR" + ("S" if len(self._corridors) > 1 else "") +
                     ": " + names + " =="]
            for c in self._corridors:
                lines.append(f" {c['name']} — {c.get('axis','')}. Enemy: {c.get('enemy','')}.")
                # A caveat about the ground itself, where one exists. Said in
                # the brief rather than left for the pilot to notice at 500 ft
                # over a stretch of map the terrain author has not finished.
                if c.get("terrain_note"):
                    lines.append(f"   NOTE: {c['terrain_note']}")
            lines.append("The threat axis and enemy air defenses are oriented down "
                         "the corridor. Build your own ingress around them.")
            template_brief = (template_brief + "\n\n" if template_brief else "") + "\n".join(lines)
            stats["corridors"] = [c["name"] for c in self._corridors]
            gfx.setdefault("corridors", []).append(
                (own_center, enemy_center, f"CORRIDOR · {names}"))

        # --- bullseye ---------------------------------------------------------
        midpoint = mapping.Point((own_center.x + enemy_center.x) / 2,
                                 (own_center.y + enemy_center.y) / 2, m.terrain)
        for coal in m.coalition.values():
            coal.bullseye = {"x": midpoint.x, "y": midpoint.y}
        gfx["bullseye"] = midpoint

        # --- F10 map graphics layers (the map briefs the mission) -------------
        from . import graphics
        layers = graphics.effective_layers(r.map_layers)
        if self._corridors:
            layers = set(layers) | {"corridors"}   # a chosen corridor always draws
        drawn = graphics.draw_layers(m, gfx, layers, r.coalition)
        if drawn:
            stats["map_layers"] = drawn

        # --- cockpit radio presets (BB-19): put the comm plan IN the jet ------
        # Programs the module's UHF radio from the ladder actually built above.
        # apply() returns ONLY what it really wrote, so the card/kneeboard CHAN
        # column matches the cockpit exactly (no advertising channels a module
        # doesn't have, and no clobbering an agency with Guard). Crew-ops flights
        # own the player jet (player_group is None) but still need programming —
        # otherwise the kneeboard advertises the comm plan while the cockpit keeps
        # factory defaults (cockpit/card disagree). Program whichever we built.
        radio_group = player_group if player_group is not None else crew_flight
        if radio_group is not None:
            from . import presets
            chan_rows, guard = presets.plan_from_comms(comms)
            programmed = presets.apply(radio_group, chan_rows, guard)
            if programmed:
                comms.set_channels(programmed)
                stats["radio_presets"] = [
                    f"CH{ch} {a}" for a, ch in programmed.items() if a != "Guard"]
            # A card entry this jet's radios cannot reach says so on the card.
            from . import saydo as _sd0
            stats["comms_unreachable"] = _sd0.mark_unreachable(comms, radio_group)

        # --- Case III readback gate + the sentence that names it -------------
        # WHAT THE MISSION CHECKS, SAID ON THE CARD. Reflected writes
        # "complete every checklist or the mission will not progress"; Fulda
        # gates 13 handoffs a mission and never says so. Both halves here:
        # the gate (installed now, because only now do we know which channel
        # really holds Mother), and the sentence — which is also where an
        # airframe we cannot gate says so honestly instead of promising a
        # check the file cannot make.
        if getattr(self, "_cq_gate", None) and player_group is not None:
            from . import gates as _gates, cq_coach as _cqc3
            _ac_id, _mother_mhz = self._cq_gate
            _chan = comms.channels.get("Carrier")
            _gates.readback(m, player_group, _ac_id, _mother_mhz, "MOTHER",
                            chan=_chan, warnings=self.warnings)
            _tail = [_gates.brief_line(_ac_id, "MOTHER", _mother_mhz, _chan)]
            if _cqc3.grades_for(r.cq_ride):
                _tail.append(
                    f"Scorecard: {_cqc3.DEBRIEF_AFTER_S} seconds after the last "
                    f"cue the ride prints its card — base {_cqc3.BASE_SCORE}, "
                    f"every grade that fired with its points, and a clean line "
                    f"if none did.")
            stats["cq_readback"] = _tail[0]
            stats["cq_card"] = list(stats.get("cq_card", [])) + [""] + _tail
            self._wk_card = stats["cq_card"]
            template_brief = "\n".join(stats["cq_card"])

        # --- what DCS will get wrong, said before the pilot finds out ---------
        # Every expert campaign on the shelf tells the pilot what the sim
        # cannot do (Reflected: "forget about the AI, it cannot fly overhead
        # patterns"; Rampagers: a whole Known Issues page). Ours is generated
        # per mission, because the first line depends on this jet's callsign.
        from . import saydo as _saydo
        self._comms = comms
        self._player_group = player_group
        _extra_issues = ([stats["cq_readback"]] if
                         ("not available" in str(stats.get("cq_readback", "")))
                         else [])
        if getattr(self, "_timing", None):
            from . import timing as _tm0
            _extra_issues += _tm0.known_issue_lines(
                self._timing, package=bool(r.timing_package))
        if getattr(self, "_nttr", None):
            from . import corridors as _nttr0
            _extra_issues += _nttr0.known_issue_lines(self._nttr)
        stats["known_issues"] = _saydo.known_issues(
            player_group, getattr(self, "_flight_name", None),
            extra=_extra_issues or None,
            unreachable=stats.get("comms_unreachable"),
            aircraft=getattr(self._resolve_aircraft(r.aircraft), "id", r.aircraft))

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

        # --- brand splash (cosmetic sponsor logo on launch) ------------------
        # The active sponsor (admin-managed) is baked in; with no sponsor store
        # or branding disabled globally, falls back to the shipped Authentic art.
        if getattr(r, "bb_branding", True):
            try:
                from . import branding, sponsors
                if sponsors.branding_enabled():
                    sp = sponsors.active_splash()
                    if sp:
                        if branding.add_brand_splash(m, logo_path=sp["path"], size=sp["size"]):
                            stats["branding"] = sp["id"]     # sponsor id → impressions
                    elif sponsors.house_brand_enabled():
                        # OPT-IN only. This used to be the fallback, so with no
                        # sponsor configured every mission carried the Authentic
                        # Media wordmark on launch — including on a fresh deploy,
                        # where the sponsor store starts empty. Nobody chose that.
                        if branding.add_brand_splash(m):
                            stats["branding"] = "house"
            except Exception as _e:
                self.warnings.append(f"brand splash skipped: {_e}")

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
            "era_year": era_cfg["year"], "map_key": r.map,
            "home_name": (csg.units[0].name if carrier_home and csg else home.name),
            "support_names": stats["support"],
            "nav_points": [(n, p) for n, p, _t, _note in nav_pts],
            "qnh_hpa": getattr(self, "_qnh_hpa", None),
            # D-4: the in-jet theater page now carries the SAME threat picture
            # as the PDF chart (it used to omit threats entirely — the one
            # place you'd want them). Targets ride along for the aim point.
            "threats": gfx.get("threats", []),
            "targets": gfx.get("targets", []),
            # JOKER/BINGO planning defaults: internal fuel from the pydcs
            # airframe (kg). None = the documents keep blank boxes.
            "fuel_max_kg": self._player_fuel_kg(),
            # what the bandits are CARRYING — briefed, not just correct
            "enemy_air": stats.get("enemy_air") or [],
            # The generated ride card, paginated onto kneeboard pages. Read
            # off `self` because the card is built above and this dict below.
            "card": getattr(self, "_wk_card", None),
            "card_title": getattr(self, "_wk_card_title", None),
            "diagram": getattr(self, "_wk_diagram", None),
            "diagram_caption": getattr(self, "_wk_diagram_cap", None),
            # Auto flight plan (bb_route / a "route": "strike" card). Absent on
            # every other mission, which is what keeps the kneeboard at its
            # three reference pages by default.
            "route": stats.get("route_legs"),
            "route_target": stats.get("route_target"),
            # The clock column on the flight-plan page (timing.py).
            "timing": stats.get("timing"),
            # The NTTR corridor chart page (nttr_chart.py) when the plan flew
            # the corridors.
            "nttr_plan": getattr(self, "_nttr", None),
            # What is on YOUR pylons. Absent when `player_arm` is off, which is
            # correct: a clean jet needs no stores card.
            "pylons": stats.get("player_pylons"),
            "loadout_label": stats.get("player_loadout"),
            "loadout_role": stats.get("player_loadout_role"),
            "aircraft_id": getattr(self._resolve_aircraft(r.aircraft), "id",
                                   r.aircraft),
        }
        # --- the say/do check, on ourselves ------------------------------------
        # Runs LAST, on the finished mission, and recomputes the paperwork
        # from the world: every card frequency held by something, the clock
        # the brief prints, the callsign DCS will really use. A finding is a
        # warning that reaches the API response and the tests; the tests hold
        # the shipped library to zero.
        try:
            self.warnings += _saydo.run(m, comms, player_group,
                                        getattr(self, "_flight_name", None), r,
                                        timing=self._timing,
                                        said_hhmm=stats.get("start_clock"))
        except Exception as exc:                          # pragma: no cover
            self.warnings.append(f"say/do self-check did not run: {exc}")
        return m

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
        from .dressing import _offset as _off
        try:
            tk_unit = tanker.units[0]
            tk_pos = tk_unit.position
            hdg = self._tanker_track_heading(tanker)
        except Exception:
            return
        astern = _off(tk_pos, self.ASTERN_TANKER_M, (hdg + 180.0) % 360.0)
        alt = self.ASTERN_TANKER_BELOW_M
        if aar_key:
            from . import aar as _aar
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
        from .dressing import _offset as _as_off
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
        from . import timing as _tm
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
            from . import timing_coach as _tc
            n = _tc.attach(m, player_group, tl, self.warnings,
                           package_group=pkg,
                           package_label=stats.get("timing_package_label", "the package"),
                           check=bool(r.check_ride))
            if n:
                stats["timing_coach_triggers"] = n
        return tl

    def _launch_timing_package(self, m, stats, own_country, home, tl):
        """An AI flight on the player's card, PACKAGE_LEAD_S ahead, ETAs locked."""
        from . import timing as _tm
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
                g.land_at(home)
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
        # modules pydcs has no native class for (verified DCS type ids)
        from .pending import get_pending
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
            if r.cq_ride:
                # A CASE III RIDE IS NOT PARKED, and saying so would be the
                # exact defect this product exists to remove. You begin
                # airborne, in the procedure, at a radial and a DME off the
                # ship — because the lesson is entirely between the marshal
                # fix and the ramp, and a ride that made you launch first
                # would spend fifteen minutes getting to it.
                from . import cq as _cqb
                _rd = _cqb.ride(r.cq_ride) or {}
                flight_line = (
                    f">> YOUR FLIGHT: {ac}, airborne, recovering aboard "
                    f"{where}. CASE III {_rd.get('n', '')} of "
                    f"{len(_cqb.RIDES)} — {_rd.get('name', '')}. You start in "
                    f"the procedure, not on the deck. "
                    f"REQUIRES {_cqb.REQUIRES_MODULE}.")
            else:
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
        from . import saydo as _sd
        _clock = _sd.mission_clock(self._mission) if getattr(self, "_mission", None) else None
        _heritage = stats.get("callsign_heritage")
        lines = [
            f"=== DCS SORTIE STARTER ===",
            f"{map_cfg['label']} | {era_cfg['label']} | {preset['frontline_hint']}",
            # THE CLOCK, IN THE BRIEF. Two of the four commercial campaigns on
            # the shelf brief a start time that is not the mission's. Ours is
            # read from the file at the moment the brief is written.
            (f"Mission clock: {_clock} local, {self._mission.start_time.day} "
             f"{self._mission.start_time.strftime('%b').upper()} "
             f"{self._mission.start_time.year}") if _clock else "",
            "",
            flight_line,
            f"Callsign: {stats.get('callsign', '')}." + (f" {_heritage}" if _heritage else ""),
            "",
        ]
        if r.cq_ride:
            # THE STARTER PARAGRAPH IS FALSE ON A TRAINING RIDE. "No objectives,
            # tasking or waypoints" describes a sandbox; this mission has a
            # flight plan, a procedure and grades. Printing the sandbox text
            # over a syllabus ride is a card describing a different mission.
            lines += [
                "This is a TRAINING RIDE, not a sandbox: a flight plan, cues at",
                "each gate, and grades on the parts DCS does not check for",
                "itself. The full card is below.",
                "",
                f"Recovering aboard: {where}",
            ]
        else:
            lines += [
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
        ]
        if stats.get("nttr"):
            # THE CORRIDORS, in the text the pilot reads in the sim.
            lines += [""] + list(stats["nttr"]["brief"])
        if getattr(self, "_timing", None):
            # THE CLOCK ON THE CARD, in the text the pilot reads in the sim.
            # Same rows the kneeboard and the PDF print, from one plan.
            from . import timing as _tm1
            lines += [""] + _tm1.brief_lines(self._timing, where)
            if r.timing_coach:
                from . import timing_coach as _tc1
                lines += [""] + _tc1.brief_lines(self._timing,
                                                 package=bool(r.timing_package))
        if stats.get("known_issues"):
            lines += ["", "WHAT DCS WILL GET WRONG:"]
            lines += [f"- {k}" for k in stats["known_issues"]]
        if stats.get("no_enemy_air"):
            # The single most important line in a GWOT brief, and it belongs in
            # the .miz text the pilot actually reads in DCS — not only in the
            # PDF. Silence here reads as "we forgot to list the enemy air",
            # which is the opposite of the intelligence.
            lines += [
                "",
                "NO ENEMY AIR FORCE. Nothing will contest you in the air. Every",
                "threat in this theater fires from the ground and most of it is",
                "optically aimed, which is why the transit altitude is high.",
            ]
        pat = stats.get("pattern")
        if pat:
            from .pattern import activity_line
            lines.append(activity_line(pat))
        lines += [""]
        if r.bb_comms:
            lines.append(comms.card())
        if template_brief:
            lines.append(template_brief)
        lines += ["", f"Generated by DCS Sortie Starter | variation (seed) {r.seed} — "
                      "same settings + seed rebuild this exact mission; new seed = "
                      "a fresh layout of the same setup"]
        return "\n".join(lines)


# Public compatibility exports; packaging no longer lives in the orchestrator.
from .artifacts import generate, _normalize_zip_times  # noqa: E402,F401
