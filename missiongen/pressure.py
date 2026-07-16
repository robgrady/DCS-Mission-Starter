"""BB-20: realistic altimeter setting (QNH) for the mission.

DCS defaults `weather.qnh` to 760 mmHg — which IS exactly 29.92 inHg / 1013 hPa,
the ISA standard datum — and we never changed it, so every mission briefed the
standard altimeter. Real sea-level QNH swings with the weather: a fair-weather
high sits near 1020+ hPa, a storm system drops toward 990. We roll a realistic,
SEEDED value correlated to the chosen weather preset, bake it into the mission,
and print it in every unit a cockpit might use.

Units matter because modules differ: US jets read inHg (Kollsman 29.xx),
European/metric jets set hPa/mb on the QNH subscale, Russian jets and DCS's own
storage use mmHg. The briefing gives all three so no pilot has to convert.
"""

# hPa realistic bands by weather preset (sea-level QNH). (low, high) inclusive.
QNH_BANDS_HPA = {
    "clear":     (1018, 1028),   # fair-weather high
    "scattered": (1010, 1018),   # near standard
    "overcast":  (1000, 1010),   # a front moving through
    "storm":     (992, 1002),    # deep low
}
_DEFAULT_BAND = (1009, 1019)     # unknown preset -> straddle standard

HPA_PER_MMHG = 1.3332239
MMHG_PER_HPA = 0.7500617
INHG_PER_HPA = 0.02952998


def roll_qnh_hpa(weather_preset, rng):
    """Seeded QNH in whole hPa for this mission's weather."""
    lo, hi = QNH_BANDS_HPA.get(weather_preset, _DEFAULT_BAND)
    return rng.randint(lo, hi)


def qnh_mmhg(hpa):
    """DCS-native units (mm Hg) for `m.weather.qnh`."""
    return round(hpa * MMHG_PER_HPA, 2)


def format_qnh(hpa):
    """Briefing string in all three altimeter units.
    e.g. '29.78 inHg / 1008 hPa / 756 mmHg'."""
    inhg = hpa * INHG_PER_HPA
    mmhg = hpa * MMHG_PER_HPA
    return f"{inhg:.2f} inHg / {hpa:d} hPa / {mmhg:.0f} mmHg"
