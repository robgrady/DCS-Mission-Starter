"""BB-11..12: AI support flights — tanker and AWACS with correct orbits, TACAN, freqs."""
from dcs import mapping, planes
from dcs.mission import StartType

from .dressing import _offset

AWACS_TYPES = {
    "wwii": {"blue": None, "red": None},          # no AWACS in 1944
    "coldwar": {"blue": planes.E_3A, "red": planes.A_50},
    "modern": {"blue": planes.E_3A, "red": planes.A_50},
}
# Receivers that take the flying BOOM (need a boom tanker, e.g. KC-135); everything
# else refuels probe-and-drogue. Giving an F-16 a drogue tanker (the old bug) left
# it unable to refuel at all.
BOOM_RECEIVERS = {
    "F-16C_50", "F-16A", "F-16A MLU", "F-15C", "F-15E", "F-15ESE",
    "A-10C", "A-10C_2", "A-10A", "F-4E-45MC", "B-1B", "B-52H", "F-117A",
}


def tanker_type(era, side, player_id):
    """Match the tanker to the PLAYER's receiver: boom -> KC-135, probe -> drogue."""
    if era == "wwii" or side != "blue":
        return None                               # no blue-only asset for this case
    if player_id in BOOM_RECEIVERS:
        return planes.KC_135                       # flying boom (USAF)
    return planes.KC135MPRS if era == "modern" else planes.KC130  # probe-and-drogue


def awacs_type(era, side):
    return AWACS_TYPES[era][side]


# knots/feet converted: pydcs wants m and km/h-ish speeds; keep its sane defaults where possible
TANKER_ALT = 6096   # 20,000 ft
AWACS_ALT = 9144    # 30,000 ft


def add_tanker(m, country, ttype, anchor, heading_away_deg, comms, gfx=None):
    if ttype is None:
        return None
    tk_cfg = comms.cfg("tanker")
    freq = tk_cfg["freq"]
    tacan = tk_cfg["tacan"]
    pos = _offset(anchor, 55000, heading_away_deg)   # 30nm behind friendly lines
    tk = m.refuel_flight(
        country, "Texaco", ttype, airport=None, position=pos,
        race_distance=48000, heading=(heading_away_deg + 90) % 360,
        altitude=TANKER_ALT, speed=550,
        start_type=StartType.Warm, frequency=freq, tacanchannel=tacan)
    comms.add("Tanker", "Texaco 1-1", f"{freq:.3f}", tacan,
              f"{ttype.id} FL200")
    if gfx is not None:
        gfx["tanker"] = (pos, (heading_away_deg + 90) % 360, 48000,
                         f"TEXACO {freq:.3f} / {tacan} / FL200")
    return tk


def add_awacs(m, country, atype, anchor, heading_away_deg, comms, gfx=None):
    if atype is None:
        return None
    freq = comms.freq("awacs")
    pos = _offset(anchor, 90000, heading_away_deg)   # 50nm behind friendly lines
    aw = m.awacs_flight(
        country, "Overlord", atype, airport=None, position=pos,
        race_distance=64000, heading=(heading_away_deg + 90) % 360,
        altitude=AWACS_ALT, speed=750, frequency=freq)
    comms.add("AWACS", "Overlord 1-1", f"{freq:.3f}", "-", f"{atype.id} FL300")
    if gfx is not None:
        gfx["awacs"] = (pos, (heading_away_deg + 90) % 360, 64000,
                        f"OVERLORD {freq:.3f} / FL300")
    return aw
