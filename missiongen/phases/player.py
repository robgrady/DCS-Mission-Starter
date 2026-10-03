from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING
from dcs.mission import StartType
from dcs.unitgroup import FlyingGroup
from ..build_context import WorldContext, EraViolation, _scenario_templates
from ..resolver import load_json, UnknownUnitError
from .. import dressing, loadouts
from .carrier import CarrierPlacement
if TYPE_CHECKING:
    from ..builder import StarterBuilder

START_TYPES = {"cold": StartType.Cold, "warm": StartType.Warm, "runway": StartType.Runway}

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


@dataclass(frozen=True)
class PlayerPlacement:
    """Facts passed to subsequent phases; mission/stat mutations stay ordered."""
    home: object
    player_group: FlyingGroup | None
    air_start_mode: str | None
    bfm_heading: float | None


def place_player(builder: StarterBuilder, ctx: WorldContext, carrier: CarrierPlacement) -> PlayerPlacement:
    self = builder
    r = builder.recipe
    away_bearing = ctx.away_bearing
    brc = carrier.brc
    carrier_home = ctx.carrier_home
    comms = ctx.comms
    crew_ops = ctx.crew_ops
    csg = carrier.group
    formation_stage = ctx.formation_stage
    hull_key = carrier.hull_key
    m = ctx.mission
    own_center = ctx.own_center
    own_country = ctx.own_country
    own_fields = ctx.own_fields
    stats = ctx.stats
    threat_bearing = ctx.threat_bearing
    home = ctx.home
    # --- player flight (unless a template pack owns the player) ---------
    # Flight callsign: user's choice, else the airframe's authentic default
    # (callsigns.json — VF-32 "Gypsy", Jolly Rogers "Victory", Misty for
    # the F-100, bort numbers for the red side). "Viper 1" is dead.
    # ...AND THEN MAPPED TO ONE DCS CAN SAY (v1.92.0, Rob: "always map").
    # The sim's radio speaks eight fighter names; the authentic one stays
    # as the heritage line in the brief. See callsign.py.
    from .. import callsign as _csn
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
    from .. import wk as _wk_pre
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
        from .. import formation as _form
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
        from .. import cq as _cq, cq_route as _cqr
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
        from ..dressing import _offset as _as_off
        helo = getattr(aircraft, "helicopter", False)
        # AIRFRAME-CORRECT block. The fixed 4500 m / 800 km/h here was a
        # fast-jet number: an A-10 does not cruise at 430 kt and a warbird
        # cannot. formation.cruise_for() derives both from the airframe's
        # own max_speed and exists because exactly this kind of hard-coded
        # constant once made the product "an F-16 tool".
        from ..formation import cruise_for as _cruise
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
                from .. import aar as _aar0
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
        if formation_stage and not r.veteran_wingmen:
            pass          # formation.build already seated you as Dash 2
        else:
            from ..player_seats import assign_seats, flight_summary
            assign_seats(player_group, r)
            if r.veteran_wingmen:
                stats["flight_composition"] = flight_summary(r)
        fc = comms.freq("flight_common")
        # A VHF-ONLY JET GETS A VHF FLIGHT FREQUENCY. The self-check found
        # this on its first run: a P-51D with its wingman on 305.725 and a
        # card that said so. Now the ladder yields to the airframe's band.
        from .. import saydo as _sdb
        fc, ft, _swapped = _sdb.in_band_flight_freqs(
            aircraft, fc, comms.freq("tactical"))
        try:
            player_group.set_frequency(fc)
        except Exception:
            pass
        from ..acnames import display as _ac_display
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
            from ..scenario_payloads import resolve_fit
            fit = resolve_fit(r, aircraft.id, year=m.start_time.year)
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
                from .. import wk as _wkfit
                _pyl = _wkfit.loadout_for(_wkr_ride)
                if _pyl:
                    _pyl = {int(st): cl for st, cl in loadouts.dated_fit(
                        {'pylons': _pyl}, aircraft.id, m.start_time.year)['pylons'].items()}
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

    return PlayerPlacement(home, player_group, air_start_mode, bfm_heading)
