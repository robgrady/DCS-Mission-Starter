# ⚠ PROVISIONAL — generated values pending the Part B projection probe.
# central_meridian is a UTM-style guess for the map's longitude span;
# false_easting/northing are 0 until tools/export_map_projection.py computes
# them from an in-sim coordinate dump and validates against real airport
# positions. Mission GEOMETRY (x/y placement, parking, runways) is exact
# regardless — only lat/lon derived output (kneeboard coords, brief, DTC
# points) is approximate until the probe lands.
from dcs.terrain.projections import TransverseMercator

PARAMETERS = TransverseMercator(
    central_meridian=66,
    false_easting=0.0,
    false_northing=0.0,
    scale_factor=0.9996,
)
