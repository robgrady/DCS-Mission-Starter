#!/usr/bin/env python3
"""Bake a scenery keep-out data pack from a scenery-survey dcs.log.

Reads the SCNKEEP lines produced by scripts/build_scenery_survey.py and writes
missiongen/data/scenery_keepout.json:

    { "<map>": { "<airfield>": [[x_north, y_east, radius_m], ...] } }

Only footprints big enough to matter are kept (hangars, big sheds) — small props
(fences, lamps) are dropped so we don't over-constrain placement. Objects whose
box DCS didn't report (radius -1) fall back to a keyword size table, else are
dropped and COUNTED (never silently). The placement keep-out consumes this file.

Usage:
  python3 scripts/import_scenery.py <map_key> <path/to/dcs.log>
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "missiongen" / "data" / "scenery_keepout.json"

# Keep only footprints at/above this half-extent (m) — a truck-sized prop is ~2 m;
# hangars/large sheds are 15 m+. This is the "is it big enough to block on" gate.
MIN_RADIUS_M = 12.0
# Cap absurd boxes (a whole-tile object) so one bad row can't blanket a field.
MAX_RADIUS_M = 120.0
# Fallback sizes when DCS gave no box (radius -1), matched on typeName keywords.
KEYWORD_RADII = [
    ("hangar", 35.0), ("shelter", 22.0), ("hardened", 22.0),
    ("depot", 30.0), ("warehouse", 30.0), ("tower", 12.0),
]
PAD_M = 3.0  # grow each footprint slightly so we clear the wall, not just the mesh


def _fallback_radius(type_name):
    t = type_name.lower()
    for kw, r in KEYWORD_RADII:
        if kw in t:
            return r
    return None


def main(map_key, log_path):
    text = Path(log_path).read_text(encoding="utf-8", errors="ignore")
    rows = re.findall(r"SCNKEEP\|([^|]+)\|([^|]+)\|(-?[\d.]+)\|(-?[\d.]+)\|(-?[\d.]+)",
                      text)
    if not rows:
        raise SystemExit("no SCNKEEP lines found — wrong log, or the survey didn't run.")

    per_field = {}
    kept = dropped_small = dropped_nobox = 0
    for field, tname, x, z, rad in rows:
        x, z, rad = float(x), float(z), float(rad)
        if rad < 0:
            fb = _fallback_radius(tname)
            if fb is None:
                dropped_nobox += 1
                continue
            rad = fb
        if rad < MIN_RADIUS_M:
            dropped_small += 1
            continue
        rad = min(rad, MAX_RADIUS_M) + PAD_M
        per_field.setdefault(field, []).append([round(x, 1), round(z, 1), round(rad, 1)])
        kept += 1

    # de-dup near-identical circles (searchObjects can return an object twice)
    for field, circles in per_field.items():
        uniq = []
        for c in circles:
            if not any(abs(c[0] - u[0]) < 2 and abs(c[1] - u[1]) < 2 for u in uniq):
                uniq.append(c)
        per_field[field] = uniq

    data = {}
    if OUT.exists():
        data = json.loads(OUT.read_text())
    data[map_key] = per_field
    OUT.write_text(json.dumps(data, indent=2))

    total = sum(len(v) for v in per_field.values())
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  {map_key}: {total} keep-out footprints across {len(per_field)} field(s)")
    for f, c in sorted(per_field.items()):
        print(f"    {f:<28} {len(c)}")
    print(f"  kept {kept}, dropped {dropped_small} (too small), "
          f"{dropped_nobox} (no box + unknown type)")
    if dropped_nobox and not total:
        print("  NOTE: DCS returned no bounding boxes — see scenery survey notes; "
              "may need the typeName size table instead.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
