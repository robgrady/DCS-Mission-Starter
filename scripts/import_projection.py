#!/usr/bin/env python3
"""Compute an extension terrain's TransverseMercator parameters from a
PROJPROBE dcs.log (see build_projection_probe.py).

Method (same as pydcs tools/export_map_projection.py): the __ZERO__ line gives
the lat/lon of DCS (0,0); for each candidate central meridian (there are only
60), derive false easting/northing from that point, then score the candidate by
reprojection error across every airport. Prints the winning parameters and the
worst-airport error; paste the values into the terrain's projection.py.

Usage:  python scripts/import_projection.py afghanistan dcs.log
"""
import re
import sys
from pathlib import Path

try:
    from pyproj import Transformer
except ImportError:
    sys.exit("pyproj required (pip install pyproj)")


def main():
    key, log = sys.argv[1], sys.argv[2]
    rows = []
    for line in Path(log).read_text(errors="ignore").splitlines():
        mt = re.search(r"PROJPROBE\|([^|]+)\|([-\d.]+)\|([-\d.]+)\|([-\d.]+)\|([-\d.]+)", line)
        if mt:
            rows.append((mt.group(1), float(mt.group(2)), float(mt.group(3)),
                         float(mt.group(4)), float(mt.group(5))))
    zero = next((r for r in rows if r[0] == "__ZERO__"), None)
    airports = [r for r in rows if r[0] != "__ZERO__"]
    if not zero or not airports:
        sys.exit(f"log has {len(airports)} airports, zero-point={'yes' if zero else 'NO'} "
                 "— did the probe run? (filter dcs.log for PROJPROBE)")
    best = None
    for cm in range(-180, 181, 3):
        tr = Transformer.from_crs("EPSG:4326",
              f"+proj=tmerc +lat_0=0 +lon_0={cm} +k_0=0.9996 +x_0=0 +y_0=0 "
              "+ellps=WGS84 +units=m +no_defs", always_xy=True)
        e0, n0 = tr.transform(zero[2], zero[1])
        fe, fn = -e0, -n0     # DCS z = E + fe, DCS x = N + fn at the zero point
        worst = 0.0
        for name, lat, lon, x, z in airports:
            e, n = tr.transform(lon, lat)
            worst = max(worst, abs((e + fe) - z), abs((n + fn) - x))
        if best is None or worst < best[0]:
            best = (worst, cm, fe, fn)
    worst, cm, fe, fn = best
    print(f"map={key}  airports={len(airports)}")
    print(f"central_meridian={cm}")
    print(f"false_easting={fe!r}")
    print(f"false_northing={fn!r}")
    print(f"scale_factor=0.9996")
    print(f"worst airport reprojection error: {worst:.2f} m "
          f"({'OK — paste into projection.py' if worst < 50 else 'HIGH — send me the log'})")


if __name__ == "__main__":
    main()

