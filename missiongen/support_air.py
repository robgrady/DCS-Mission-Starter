"""BB-11..12: AI support flights — tanker and AWACS with correct orbits, TACAN, freqs."""
from dcs import mapping, planes
from dcs.mission import StartType

from .dressing import _offset

TANKERS = {
    "wwii": {"blue": None, "red": None},          # no AAR in 1944
    "coldwar": {"blue": planes.KC_135, "red": None},
    "modern": {"blue": planes.KC135MPRS, "red": None},
}
AWACS_TYPES = {
    "wwii": {"blue": None, "red": None},          # no AWACS in 1944
    "coldwar": {"blue": planes.E_3A, "red": planes.A_50},
    "modern": {"blue": planes.E_3A, "red": planes.A_50},
}
# knots/feet converted: pydcs wants m and km/h-ish speeds; keep its sane defaults where possible
TANKER_ALT = 6096   # 20,000 ft
AWACS_ALT = 9144    # 30,000 ft


def add_tanker(m, country, era, side, anchor, heading_away_deg, comms):
    ttype = TANKERS[era][side]
    if ttype is None:
        return None
    freq = comms.next_uhf()
    tacan = comms.next_tacan()
    pos = _offset(anchor, 55000, heading_away_deg)   # 30nm behind friendly lines
    tk = m.refuel_flight(
        country, "Texaco", ttype, airport=None, position=pos,
        race_distance=48000, heading=(heading_away_deg + 90) % 360,
        altitude=TANKER_ALT, speed=550,
        start_type=StartType.Warm, frequency=freq, tacanchannel=tacan)
    comms.add("Tanker", "Texaco 1-1", f"{freq:.2f}", tacan,
              f"{ttype.id} FL200")
    return tk


def add_awacs(m, country, era, side, anchor, heading_away_deg, comms):
    atype = AWACS_TYPES[era][side]
    if atype is None:
        return None
    freq = comms.next_uhf()
    pos = _offset(anchor, 90000, heading_away_deg)   # 50nm behind friendly lines
    aw = m.awacs_flight(
        country, "Overlord", atype, airport=None, position=pos,
        race_distance=64000, heading=(heading_away_deg + 90) % 360,
        altitude=AWACS_ALT, speed=750, frequency=freq)
    comms.add("AWACS", "Overlord 1-1", f"{freq:.2f}", "-", f"{atype.id} FL300")
    return aw
