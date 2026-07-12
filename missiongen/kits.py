"""Functional-group kit definitions: complete SAM sites with doctrinally sensible layouts.

Each kit is a list of (unit_ref, offset_x, offset_y, heading_offset) placed relative to
the site center. Layouts follow real deployment geometry (launcher rings around the
track radar, search radar offset) so sites actually engage in DCS.
"""
import math

# (ref, radius_m, bearing_deg, face_out)
def _ring(ref, count, radius, start_bearing=0.0):
    step = 360.0 / count
    return [(ref, radius, start_bearing + i * step, True) for i in range(count)]


SAM_KITS = {
    "sa2": {
        "label": "SA-2 Guideline site", "wez_m": 40000,
        "units": (
            [("vehicles.AirDefence.SNR_75V", 0, 0, False)]                 # Fan Song TR center
            + _ring("vehicles.AirDefence.S_75M_Volhov", 6, 140)            # 6 launchers, star
            + [("vehicles.AirDefence.P_19_s_125_sr", 220, 30, False)]      # Flat Face SR
        ),
    },
    "sa3": {
        "label": "SA-3 Goa site", "wez_m": 22000,
        "units": (
            [("vehicles.AirDefence.Snr_s_125_tr", 0, 0, False)]            # Low Blow TR
            + _ring("vehicles.AirDefence.X_5p73_s_125_ln", 4, 110, 45)
            + [("vehicles.AirDefence.P_19_s_125_sr", 200, 300, False)]
        ),
    },
    "sa6": {
        "label": "SA-6 Gainful battery", "wez_m": 24000,
        "units": (
            [("vehicles.AirDefence.Kub_1S91_str", 0, 0, False)]            # Straight Flush
            + _ring("vehicles.AirDefence.Kub_2P25_ln", 4, 130, 20)
        ),
    },
    "sa11": {
        "label": "SA-11 Gadfly battery", "wez_m": 35000,
        "units": (
            [("vehicles.AirDefence.SA_11_Buk_SR_9S18M1", 0, 0, False),
             ("vehicles.AirDefence.SA_11_Buk_CC_9S470M1", 60, 180, False)]
            + _ring("vehicles.AirDefence.SA_11_Buk_LN_9A310M1", 4, 150, 10)
        ),
    },
    "hawk": {
        "label": "MIM-23 Hawk battery", "wez_m": 40000,
        "units": (
            [("vehicles.AirDefence.Hawk_sr", 0, 0, False),
             ("vehicles.AirDefence.Hawk_tr", 70, 90, False),
             ("vehicles.AirDefence.Hawk_pcp", 60, 200, False),
             ("vehicles.AirDefence.Hawk_cwar", 90, 320, False)]
            + _ring("vehicles.AirDefence.Hawk_ln", 6, 160)
        ),
    },
    "patriot": {
        "label": "MIM-104 Patriot battery", "wez_m": 90000,
        "units": (
            [("vehicles.AirDefence.Patriot_str", 0, 0, False),
             ("vehicles.AirDefence.Patriot_ECS", 50, 150, False),
             ("vehicles.AirDefence.Patriot_AMG", 70, 210, False),
             ("vehicles.AirDefence.Patriot_EPP", 60, 270, False),
             ("vehicles.AirDefence.Patriot_cp", 80, 330, False)]
            + _ring("vehicles.AirDefence.Patriot_ln", 4, 140, 45)
        ),
    },
}


def kit_positions(kit_key: str, center, base_heading: float = 0.0):
    """Yield (unit_ref, dcs.mapping.Point, heading_deg) for each unit in a kit."""
    from dcs import mapping
    kit = SAM_KITS[kit_key]
    for ref, radius, bearing, face_out in kit["units"]:
        b = math.radians(bearing + base_heading)
        pos = mapping.Point(center.x + radius * math.cos(b),
                            center.y + radius * math.sin(b), center._terrain)
        heading = (bearing + base_heading) % 360 if face_out else base_heading
        yield ref, pos, heading
