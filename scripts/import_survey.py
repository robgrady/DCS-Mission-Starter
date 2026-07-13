#!/usr/bin/env python3
"""Import parking-heading SURVEY output into parking_headings.json.

Takes the lines the survey mission logged (PSURVEY_OUT|<airport>|<slot>|<hdg>)
from either a raw dcs.log, the Saved Games/DCS/parking_survey.txt file, or a
pasted snippet, and merges exact per-spot headings into
missiongen/data/parking_headings.json under the given map key.

Each surveyed field is written as:
  "<Airfield>": { "default": <dominant heading>, "slots": { "<slot>": <hdg>, ... } }
so static aircraft face the exact painted line per spot, with the dominant
heading as the fallback for any spot not in the survey.

Usage:
  python3 scripts/import_survey.py <map_key> <path-to-log-or-txt> [--dry-run]
"""
import json
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "missiongen" / "data" / "parking_headings.json"

LINE = re.compile(r"PSURVEY_OUT\|(.+?)\|(.+?)\|([-\d.]+)")


def parse(text):
    """airport -> {slot_name: heading} from any text containing PSURVEY_OUT lines."""
    fields = defaultdict(dict)
    for m in LINE.finditer(text):
        airport, slot, hdg = m.group(1), m.group(2), float(m.group(3))
        fields[airport][slot] = round(hdg % 360, 1)
    return fields


def dominant(headings):
    """Most common heading rounded to the nearest degree (the majority apron)."""
    counts = Counter(round(h) for h in headings)
    return float(counts.most_common(1)[0][0])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    if len(args) < 2:
        raise SystemExit(__doc__)
    map_key, src = args[0], args[1]

    text = Path(src).read_text(errors="ignore")
    fields = parse(text)
    if not fields:
        raise SystemExit("No PSURVEY_OUT lines found. Check the log/txt path.")

    data = json.loads(DATA.read_text())
    data.setdefault(map_key, {})
    for airport, slots in fields.items():
        entry = {"default": dominant(slots.values()),
                 "slots": {k: slots[k] for k in sorted(slots)}}
        data[map_key][airport] = entry
        print(f"  {airport:<28} {len(slots)} spots  default={entry['default']:g}")

    if dry:
        print("\n--dry-run: not written. Preview above.")
        return
    DATA.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"\nmerged {len(fields)} field(s) into {DATA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
