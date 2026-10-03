#!/usr/bin/env python3
"""Fast development checks by default; --full keeps the entire release suite.

Usage: python3 scripts/test.py [--full] [--workers 4] [--profile] [pytest options]
pytest-xdist is optional. Whole test files stay on one worker so expensive
module fixtures are built once. Test storage is always temporary.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
QUICK_TESTS = (
    'test_recipe_contract.py', 'test_quick_flight_contract.py',
    'test_mission_kit_wiring.py', 'test_architecture_contracts.py',
    'test_generation_capacity.py', 'test_pack_publication.py',
    'test_parking_directions.py', 'test_parking_headings.py',
    'test_player_parking.py', 'test_determinism.py', 'test_test_runner.py',
)


def worker_count(full, requested=None, cpus=None):
    cpus = cpus or os.cpu_count() or 1
    if requested in (None, 'auto'):
        return min(4, cpus) if full or requested == 'auto' else 1
    try:
        count = int(requested)
    except (TypeError, ValueError) as e:
        raise ValueError('workers must be auto or a positive integer') from e
    if count < 1:
        raise ValueError('workers must be auto or a positive integer')
    return count


def pytest_args(full=False, workers=None, has_xdist=False, cpus=None, profile=False):
    count = worker_count(full, workers, cpus)
    args = ['tests'] if full else [f'tests/{name}' for name in QUICK_TESTS]
    args += ['-q']
    if count > 1 and has_xdist:
        args += ['-n', str(count), '--dist', 'loadfile']
    if profile:
        args += ['--durations=20']
    return args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full', action='store_true')
    parser.add_argument('--workers', default=os.environ.get('TEST_WORKERS'))
    parser.add_argument('--profile', action='store_true')
    options, extra = parser.parse_known_args()
    has_xdist = importlib.util.find_spec('xdist') is not None
    try:
        count = worker_count(options.full, options.workers)
        args = pytest_args(options.full, options.workers, has_xdist, profile=options.profile)
    except ValueError as e:
        parser.error(str(e))
    mode = 'Full release suite' if options.full else 'Quick development checks'
    actual_workers = count if has_xdist else 1
    print(f'{mode}: {actual_workers} worker(s)', flush=True)
    if count > 1 and not has_xdist:
        print('pytest-xdist unavailable; running serially. Install it to enable parallel tests.', flush=True)
    with tempfile.TemporaryDirectory(prefix='sortie-tests-') as temporary:
        env = dict(os.environ)
        for name in ('PACKS', 'SPONSOR', 'ANALYTICS', 'CONTACT', 'CREDITS'):
            env[f'{name}_DATA_DIR'] = str(Path(temporary) / name.lower())
        result = subprocess.call([sys.executable, '-m', 'pytest', *args, *extra], cwd=ROOT, env=env)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
