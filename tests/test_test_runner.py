"""Fast checks are explicit; release runs retain every test and shared fixtures."""
from pathlib import Path

import pytest

from scripts import test as runner


def test_full_mode_runs_every_test_without_filters():
    args = runner.pytest_args(full=True, has_xdist=True, cpus=14)
    assert args == ['tests', '-q', '-n', '4', '--dist', 'loadfile']


def test_quick_mode_covers_user_contracts_and_real_archive_generation():
    args = runner.pytest_args()
    assert 'tests/test_recipe_contract.py' in args
    assert 'tests/test_parking_directions.py' in args
    assert 'tests/test_determinism.py' in args
    assert '-n' not in args
    for arg in args:
        if arg.startswith('tests/'):
            assert (runner.ROOT / arg).is_file()


def test_optional_parallelism_and_worker_override():
    assert runner.pytest_args(full=True, has_xdist=False, cpus=14) == ['tests', '-q']
    assert runner.worker_count(True, cpus=2) == 2
    assert runner.worker_count(True, cpus=1) == 1
    assert runner.worker_count(False, 'auto', cpus=14) == 4
    assert '-n' not in runner.pytest_args(full=True, workers='1', has_xdist=True)
    assert runner.pytest_args(full=True, workers='6', has_xdist=True)[3] == '6'


@pytest.mark.parametrize('value', ['0', '-1', 'lots'])
def test_invalid_worker_count_is_clear(value):
    with pytest.raises(ValueError, match='positive integer'):
        runner.worker_count(True, value)


def test_profiling_is_available_without_changing_selection():
    args = runner.pytest_args(full=True, profile=True)
    assert args == ['tests', '-q', '--durations=20']


def test_preflight_keeps_the_same_bounded_parallel_policy():
    source = (runner.ROOT / 'scripts/preflight.sh').read_text()
    assert 'TEST_WORKERS' in source and 'min(4, os.cpu_count() or 1)' in source
    assert '--dist loadfile' in source
