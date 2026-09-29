"""BB-11..12: AI support flights — tanker and AWACS with correct orbits, TACAN, freqs."""
from dcs import mapping, planes
from dcs.mission import StartType

from .dressing import _offset

AWACS_TYPES = {
    "wwii": {"blue": None, "red": None},          # no AWACS in 1944
    "coldwar": {"blue": planes.E_3A, "red": planes.A_50},
    "modern": {"blue": planes.E_3A, "red": planes.A_50},
    # Red has no AWACS because red has no air force (threats.TIER_CAP).
    "gwot": {"blue": planes.E_3A, "red": None},
}
# Receivers that take the flying BOOM (need a boom tanker, e.g. KC-135); everything
# else refuels probe-and-drogue. Giving an F-16 a drogue tanker (the old bug) left
# it unable to refuel at all.
BOOM_RECEIVERS = {
    "F-16C_50", "F-16A", "F-16A MLU", "F-15C", "F-15E", "F-15ESE",
    "A-10C", "A-10C_2", "A-10A", "F-4E-45MC", "B-1B", "B-52H", "F-117A",
}


def tanker_type(era, side, player_id, carrier_home=False):
    """Match the tanker to the PLAYER's receiver: boom -> KC-135, probe -> drogue.
    Off the boat in the Cold War the organic tanker is the KA-6D (the A-6's tanker
    variant) — the real carrier air wing's own gas, not a land-based KC-135."""
    if era == "wwii" or side != "blue":
        return None                               # no blue-only asset for this case
    if carrier_home and era == "coldwar":
        return planes.A6E                          # KA-6D organic carrier tanker
    if player_id in BOOM_RECEIVERS:
        return planes.KC_135                       # flying boom (USAF)
    if era in ("modern", "gwot"):
        return planes.KC135MPRS                    # probe-and-drogue
    return planes.KC130


def awacs_type(era, side):
    return AWACS_TYPES[era][side]


# knots/feet converted: pydcs wants m and km/h-ish speeds; keep its sane defaults where possible
TANKER_ALT = 6096   # 20,000 ft
AWACS_ALT = 9144    # 30,000 ft


def add_tanker(m, country, ttype, anchor, heading_away_deg, comms, gfx=None,
               aar_key=None, receiver_id="", map_key=""):
    """Put a tanker on a track the receiver can actually fly.

    `aar_key` selects the operating point from `missiongen.aar`. Without it the
    old behavior applies — 6,096 m at 550 km/h, which measures **217 KIAS at
    20,000 ft** and is a third slower than boom AAR wants. That default is kept
    only so a share link minted before v1.73.0 rebuilds byte-identically; every
    caller in the product now passes a key."""
    if ttype is None:
        return None
    tk_cfg = comms.cfg("tanker")
    freq = tk_cfg["freq"]
    tacan = tk_cfg["tacan"]
    pos = _offset(anchor, 55000, heading_away_deg)   # 30nm behind friendly lines
    alt, spd = TANKER_ALT, 550
    label = "FL200"
    if aar_key:
        from . import aar as _aar
        alt = _aar.track_alt_m(aar_key, map_key)
        spd = _aar.track_speed_kmh(aar_key, receiver_id or "", map_key)
        # The label must quote the speed the tanker actually flies. It used to
        # print the tanker's DEFAULT, which is a different number the moment
        # the receiver's band clamps it — a chart disagreeing with the mission.
        label = (f"FL{_aar.track_alt_ft(aar_key, map_key) // 100:03d} "
                 f"{_aar.track_ias_kt(aar_key, receiver_id or '')} KIAS")
    tk = m.refuel_flight(
        country, "Texaco", ttype, airport=None, position=pos,
        race_distance=48000, heading=(heading_away_deg + 90) % 360,
        altitude=alt, speed=spd,
        start_type=StartType.Warm, frequency=freq, tacanchannel=tacan)
    # pydcs's refuel_flight only attaches a SetFrequency TASK (waypoint 2); the
    # group's own radio stays on its 251.0 default, so the tanker spawns off the
    # briefed frequency — co-channel with the AWACS, which has the same problem
    # — and the Mission Editor shows 251 next to a card that says 253.625.
    # set_frequency() puts the group on it from t=0. FlyingGroup takes MHz.
    tk.set_frequency(freq)
    # FIT THE STORE, if this tanker needs one. Only the A-6E does — every other
    # entry in the table has a built-in refuelling system — and `refuel_flight`
    # does not fit it, so the KA-6D shipped with empty pylons: on a track, on
    # frequency, with a TACAN and a briefing, and physically unable to give
    # anybody fuel. Reported from the cockpit; it is the purest form of the
    # say/do gap this product exists to avoid.
    if aar_key:
        _fit_refuelling_store(tk, ttype, aar_key)
    comms.add("Tanker", "Texaco 1-1", f"{freq:.3f}", tacan,
              f"{ttype.id} {label}")
    if gfx is not None:
        gfx["tanker"] = (pos, (heading_away_deg + 90) % 360, 48000,
                         f"TEXACO {freq:.3f} / {tacan} / {label}")
    return tk


def _fit_refuelling_store(group, ttype, aar_key) -> bool:
    """Hang the buddy pod on a tanker whose refuelling system is a store.

    Returns True if a store was required AND fitted. Never raises: a pydcs
    pylon rename must not fail the build, but it MUST be visible, so the caller
    that cares checks the return rather than assuming.
    """
    from . import aar as _aar
    spec = _aar.TANKERS.get(aar_key, {}).get("store")
    if not spec:
        return False                      # built-in system, nothing to fit
    pylon_attr, weapon_attr = spec
    try:
        pylon = getattr(ttype, pylon_attr)
        weapon = getattr(pylon, weapon_attr)
        for u in group.units:
            u.pylons[weapon[0]] = {"CLSID": weapon[1]["clsid"]}
        return True
    except Exception:
        return False


def add_awacs(m, country, atype, anchor, heading_away_deg, comms, gfx=None):
    if atype is None:
        return None
    freq = comms.freq("awacs")
    pos = _offset(anchor, 90000, heading_away_deg)   # 50nm behind friendly lines
    aw = m.awacs_flight(
        country, "Overlord", atype, airport=None, position=pos,
        race_distance=64000, heading=(heading_away_deg + 90) % 360,
        altitude=AWACS_ALT, speed=750, frequency=freq)
    aw.set_frequency(freq)          # see add_tanker: task-only otherwise
    comms.add("AWACS", "Overlord 1-1", f"{freq:.3f}", "-", f"{atype.id} FL300")
    if gfx is not None:
        gfx["awacs"] = (pos, (heading_away_deg + 90) % 360, 64000,
                        f"OVERLORD {freq:.3f} / FL300")
    return aw
