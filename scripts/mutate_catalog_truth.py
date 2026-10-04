"""Prove catalog/schema correction guards; restore every changed source."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
CASES = [
    ('server/recipe_contract.py', "schema['properties'][name].update(minimum=lower, maximum=upper)",
     'pass', 'advertised_numeric_bounds', 'schema hides numeric bounds'),
    ('server/recipe_contract.py', "schema['allOf'] = [", "schema['x-unused-seat-rules'] = [",
     'schema_seat_rules', 'schema accepts an all-AI flight'),
    ('missiongen/recipe.py', 'not (lower <= value <= upper)', 'not (lower <= value)',
     'advertised_numeric_bounds', 'engine ignores numeric upper bounds'),
    ('missiongen/recipe.py', 'bounds["veteran_wingmen"][0] <= self.veteran_wingmen < self.slots',
     'bounds["veteran_wingmen"][0] <= self.veteran_wingmen <= self.slots',
     'schema_seat_rules', 'engine accepts an all-AI flight'),
    ('missiongen/recipe.py', '"pattern_count": (1, MAX_COUNT)', '"pattern_count": (1, 8)',
     'pattern_bounds_follow', 'pattern limit drifts from its owner'),
    ('server/recipe_contract.py', "'maximum': FILL_BOUNDS[1]", "'maximum': FILL_BOUNDS[1] + 1",
     'nested_constraints', 'parking override above 100 percent is advertised as valid'),
    ('server/recipe_contract.py', 'maxItems=TARGET_PACKAGE_BOUNDS[1]', 'maxItems=4',
     'nested_constraints', 'four target packages advertised as valid'),
    ('missiongen/data/eras.json', 'War on Terror (2003-2025)', 'War on Terror (2003-2020)',
     'catalog_label_matches', 'era label disagrees with aircraft filter'),
    ('missiongen/data/tracks.json', 'Eleven rides: the tanker drag', 'Ten rides: the tanker drag',
     'proud_phantom_intro', 'collection prose undercounts rides'),
    ('scripts/add_white_knights.py', 'Eleven rides: the tanker drag', 'Ten rides: the tanker drag',
     'proud_phantom_intro', 'authoring script restores stale collection prose'),
]


def run(selector):
    return subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_catalog_truth.py',
                           '-q', '-x', '-k', selector], cwd=ROOT, capture_output=True, text=True)


def main():
    selector = 'not published_proud and not real_browser'
    baseline = run(selector)
    if baseline.returncode:
        raise SystemExit('Baseline failed:\n' + baseline.stdout + baseline.stderr)
    originals = {path: (ROOT/path).read_text() for path, *_ in CASES}
    try:
        for path, anchor, replacement, guard, label in CASES:
            source = originals[path]
            assert source.count(anchor) == 1, (path, anchor)
            (ROOT/path).write_text(source.replace(anchor, replacement))
            try:
                result = run(guard)
                if result.returncode != 1:
                    raise SystemExit(f'WEAK or invalid run: {label}\n{result.stdout}\n{result.stderr}')
                print('caught:', label, flush=True)
            finally:
                (ROOT/path).write_text(source)
    finally:
        for path, source in originals.items():
            (ROOT/path).write_text(source)
    restored = run(selector)
    if restored.returncode:
        raise SystemExit('Restored baseline failed:\n' + restored.stdout + restored.stderr)
    print(f'{len(CASES)} caught; 0 weak; baseline restored and rechecked.')


if __name__ == '__main__':
    main()
