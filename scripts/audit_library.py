#!/usr/bin/env python3
"""Build content variants and record emitted mission facts for editorial review.

This is evidence collection, not a DCS flight certification. Output records
contain actual group tasks, routes, aircraft, dates, warnings and archive files.
No template flags are disabled to accelerate the audit.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import csv
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor')]


def values(value):
    return list(value.values()) if isinstance(value, dict) else list(value or [])


def inspect_archive(path):
    import dcs.lua as lua
    with zipfile.ZipFile(path) as z:
        mission = lua.loads(z.read('mission').decode())['mission']
        files = z.namelist()
        strings = {name: z.read(name).decode(errors='replace') for name in files
                   if name.endswith('.lua') or name.endswith('/dictionary')}
    groups = []
    for side in ('blue', 'red', 'neutrals'):
        for country in values(mission.get('coalition', {}).get(side, {}).get('country')):
            for kind in ('plane', 'helicopter', 'vehicle', 'ship', 'static'):
                for group in values(country.get(kind, {}).get('group')):
                    points = values(group.get('route', {}).get('points'))
                    groups.append({'side': side, 'country': country.get('name'),
                                   'kind': kind, 'name': group.get('name'),
                                   'task': group.get('task'), 'late': group.get('lateActivation', False),
                                   'units': [{k: u.get(k) for k in ('name', 'type', 'skill', 'x', 'y', 'heading', 'payload')}
                                             for u in values(group.get('units'))],
                                   'route': [{k: p.get(k) for k in ('name', 'x', 'y', 'alt', 'alt_type', 'speed', 'action', 'task', 'airdromeId', 'linkUnit', 'helipadId', 'ETA', 'ETA_locked')}
                                             for p in points]})
    return {'date': mission.get('date'), 'start_time': mission.get('start_time'),
            'theatre': mission.get('theatre'), 'weather': mission.get('weather'), 'groups': groups,
            'zones': values(mission.get('triggers', {}).get('zones')),
            'trigger_rules': values(mission.get('trigrules')), 'trig': mission.get('trig'),
            'files': files, 'embedded_text': strings, 'drawings': mission.get('drawings')}


def build_case(case):
    from missiongen import Recipe, generate
    key, era, map_key, seed, recipe, label, premise = case
    record = {'key': key, 'era': era, 'map': map_key, 'seed': seed,
              'label': label, 'premise': premise, 'input': recipe}
    try:
        with tempfile.TemporaryDirectory(prefix='sortie-content-audit-') as tmp:
            path = str(Path(tmp) / 'mission.miz')
            rc = Recipe.from_dict({**recipe, 'template': key, 'map': map_key, 'era': era, 'seed': seed})
            result = generate(rc, path)
            record.update({'resolved_recipe': vars(rc), 'stats': result['stats'],
                           'warnings': result['warnings'], 'mission': inspect_archive(path)})
    except Exception as exc:
        record['error'] = f'{type(exc).__name__}: {exc}'
    return record


def cases(seeds):
    from missiongen.templates import templates, effective_recipe
    from server.app import options
    catalog = options()['templates']
    source = templates()
    for key, tpl in catalog.items():
        if key not in source and key not in ('backseat_izlid', 'backseat_intercept', 'rio_fleet_defense'):
            continue  # Installed pack bytes require a separate audit of that revision.
        for era in tpl.get('eras', []):
            base = effective_recipe(key, era) if key in source else tpl.get('recipe', {})
            maps = tpl.get('maps') or [base.get('map') or tpl.get('default_map') or 'caucasus']
            for map_key in maps:
                recipe = effective_recipe(key, era, map_key) if key in source else base
                for seed in seeds:
                    yield (key, era, map_key, seed, recipe, tpl['label'],
                           (tpl.get('library') or {}).get('premise', ''))


def write_summary(records, output):
    """Readable facts only: a successful build is never a promise verdict."""
    rows = []
    for r in records:
        m = r.get('mission', {})
        groups = m.get('groups', [])
        player = [g for g in groups if any(u.get('skill') in ('Player', 'Client')
                                         for u in g['units'])]
        enemies = [g for g in groups if g['kind'] == 'plane' and g['side'] == 'red'
                   and not g['name'].startswith('Ambient')]
        moving = [g for g in groups if g['kind'] == 'vehicle' and len(g['route']) > 1]
        rows.append({'key': r['key'], 'era': r['era'], 'map': r['map'], 'seed': r['seed'],
                     'label': r['label'], 'premise': r['premise'],
                     'build': r.get('error', 'ok'), 'year': m.get('date', {}).get('Year'),
                     'player_waypoints': ';'.join(str(len(g['route'])) for g in player),
                     'player_loadout': r.get('stats', {}).get('player_loadout', ''),
                     'dedicated_enemy_flights': ';'.join(g['name'] for g in enemies),
                     'moving_ground_groups': ';'.join(g['name'] for g in moving),
                     'target_packages': ';'.join(r.get('stats', {}).get('targets', [])),
                     'trigger_rules': len(m.get('trigger_rules', [])),
                     'overlays': ';'.join(r.get('stats', {}).get('historical_airspace', [])),
                     'warnings': ';'.join(r.get('warnings', []))})
    with (output / 'case-summary.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['key'])
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--seeds', type=int, nargs='+', default=[7, 19])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    todo = list(cases(args.seeds))
    records = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(build_case, c) for c in todo]
        for i, future in enumerate(as_completed(futures), 1):
            records.append(future.result())
            if i % 25 == 0 or i == len(todo):
                print(f'{i}/{len(todo)} cases, {sum("error" in r for r in records)} build failures', flush=True)
    records.sort(key=lambda r: (r['key'], r['era'], r['map'], r['seed']))
    (args.output / 'mission-evidence.json').write_text(json.dumps(records, ensure_ascii=False, indent=1, default=str)+'\n')
    write_summary(records, args.output)
    print(f'{len(records)} records saved to {args.output}', flush=True)


if __name__ == '__main__':
    main()
