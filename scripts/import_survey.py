#!/usr/bin/env python3
"""Merge DCS parking-direction surveys without deleting earlier measurements.

Usage: python3 scripts/import_survey.py <map_key> <dcs.log> [--dry-run]
Legacy PSURVEY_OUT records remain supported. PSURVEY2_OUT records bind a
heading to the stand's unique crossroad id, name and source-export coordinates.
"""
import json
import math
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'missiongen/data/parking_headings.json'


def parse_survey(text):
    fields = {}
    for line in text.splitlines():
        marker = 'PSURVEY2_OUT|' if 'PSURVEY2_OUT|' in line else 'PSURVEY_OUT|'
        if marker not in line:
            continue
        parts = line.split(marker, 1)[1].strip().split('|')
        expected = 6 if marker == 'PSURVEY2_OUT|' else 3
        if len(parts) != expected:
            raise ValueError('Malformed parking survey record')
        airport = parts[0]
        entry = fields.setdefault(airport, {'slots': {}, 'stands': {}})
        if expected == 3:
            slot, heading = parts[1], float(parts[2])
            if not math.isfinite(heading):
                raise ValueError('Survey heading must be finite')
            entry['slots'][slot] = round(heading % 360, 3)
        else:
            sid, name, heading, x, y = parts[1:]
            heading, x, y = float(heading), float(x), float(y)
            if not sid.isdecimal() or not all(math.isfinite(v) for v in (heading, x, y)):
                raise ValueError('Invalid survey stand id or geometry')
            entry['stands'][str(int(sid))] = {
                'slot_name': name, 'heading': round(heading % 360, 3), 'x': x, 'y': y}
    return fields


def parse(text):
    """Compatibility parser for callers consuming legacy name-keyed records."""
    return {name: entry['slots'] for name, entry in parse_survey(text).items()}


def dominant(headings):
    return float(Counter(round(h) for h in headings).most_common(1)[0][0] % 360)


def merge_survey(data, map_key, fields, terrain):
    """Validate against the target export before merging any measurement."""
    result = json.loads(json.dumps(data))
    for airport, measured in fields.items():
        ap = terrain.airports.get(airport)
        if ap is None:
            raise ValueError(f'{airport!r} is not an airfield on {map_key}')
        names = {str(s.slot_name) for s in ap.parking_slots}
        slots = {str(s.crossroad_idx): s for s in ap.parking_slots}
        for name in measured['slots']:
            if name not in names:
                raise ValueError(f'{airport}/{name}: no such parking stand')
        for sid, value in measured['stands'].items():
            slot = slots.get(sid)
            if slot is None or str(slot.slot_name) != value['slot_name']:
                raise ValueError(f'{airport}/{sid}: parking stand identity changed')
            if math.hypot(slot.position.x - value['x'], slot.position.y - value['y']) > 0.05:
                raise ValueError(f'{airport}/{sid}: parking coordinates changed; rebuild the survey')
        old = result.setdefault(map_key, {}).get(airport, {})
        entry = dict(old) if isinstance(old, dict) else {'default': old}
        entry['slots'] = {**entry.get('slots', {}), **measured['slots']}
        entry['stands'] = {**entry.get('stands', {}), **measured['stands']}
        values = list(entry['slots'].values()) + [v['heading'] for v in entry['stands'].values()]
        entry['default'] = dominant(values)
        if not entry['stands']:
            entry.pop('stands')
        result[map_key][airport] = entry
    return result


def atomic_write(path, data):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.parking-survey-', dir=path.parent)
    os.close(fd)
    tmp = Path(temporary)
    try:
        tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        raise SystemExit(__doc__)
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / 'vendor'))
    from missiongen.resolver import load_json, resolve_terrain
    map_key, src = args
    maps = load_json('maps')
    if map_key not in maps or map_key.startswith('_'):
        raise SystemExit(f'Unknown map {map_key!r}')
    try:
        fields = parse_survey(Path(src).read_text(errors='ignore'))
        if not fields:
            raise ValueError('No parking survey records found')
        terrain = resolve_terrain(maps[map_key]['terrain_class'])()
        data = merge_survey(json.loads(DATA.read_text()), map_key, fields, terrain)
    except (ValueError, OSError) as e:
        raise SystemExit(str(e)) from e
    for airport, entry in fields.items():
        print(f"  {airport}: {len(entry['slots'])} legacy / {len(entry['stands'])} identified stands")
    if '--dry-run' in sys.argv:
        print('Validated; --dry-run: data not changed.')
    else:
        atomic_write(DATA, data)
        print(f'Merged {len(fields)} airfields into {DATA.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
