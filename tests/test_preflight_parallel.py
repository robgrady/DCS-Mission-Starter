"""The release gate runs the suite in parallel — correctly, and optionally.

Two ways to get this wrong, and both are silent:

1. Parallelise with the DEFAULT distribution. Several modules share a
   module-scoped fixture that generates an entire mission (`built`,
   `built_green`, `built_drag`, `built_full_ramp`). pytest-xdist's default
   `--dist load` hands out individual tests, so a module split across N
   workers builds its mission N times. That is not just slower than
   `--dist loadfile`; on a two-core box it can be slower than running
   serially, while looking exactly like a speed-up in the command line.

2. Make pytest-xdist REQUIRED. preflight.sh has to work on a fresh unzip of
   the release, on Rob's machine, before the launcher has built its venv —
   that is the entire reason the pytest step is written as "skip if pytest
   isn't importable" rather than "fail". A hard `-n auto` turns the release's
   own recovery check into an install error.

These are text guards on the script, which is a weaker instrument than
reading a number back out of an artifact. They are here because the failure
they describe leaves no artifact to read: the wrong distribution produces a
correct, green, slow test run.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "scripts" / "preflight.sh"


@pytest.fixture(scope="module")
def src():
    return PREFLIGHT.read_text()


def _pytest_invocation(src):
    """The line that actually runs the suite (not the advice in the note)."""
    lines = [l for l in src.splitlines()
             if "python3 -m pytest tests" in l and ">" in l]
    assert len(lines) == 1, (
        f"expected exactly one line in preflight.sh that RUNS the suite, "
        f"found {len(lines)}: {lines}")
    return lines[0]


def test_preflight_runs_the_suite_at_all(src):
    _pytest_invocation(src)


def test_the_parallel_flag_is_built_from_a_variable_not_hardcoded(src):
    """A hardcoded -n makes xdist mandatory; the flags must come from the probe."""
    line = _pytest_invocation(src)
    assert "$PAR" in line, (
        "preflight's pytest line must take its parallel flags from $PAR, which "
        f"is empty when xdist is missing. Line was: {line.strip()}")
    assert not re.search(r"-n\s+(auto|\d)", line), (
        "preflight hardcodes -n on the pytest line, so a fresh unzip without "
        f"pytest-xdist fails instead of running serially: {line.strip()}")


def test_parallel_is_only_switched_on_if_xdist_imports(src):
    """The probe, and the assignment it guards."""
    assert "import xdist" in src, (
        "preflight must probe for xdist before using it — otherwise it either "
        "hardcodes -n or never parallelises")
    m = re.search(r"if python3 -c 'import xdist'.*?\n(.*?)\n\s*fi", src, re.S)
    assert m, "the xdist probe is not an `if` block guarding the assignment"
    assert "PAR=" in m.group(1), (
        "the xdist probe does not set PAR inside its own if-block, so the "
        "parallel flags are applied whether or not xdist is installed")


def test_the_distribution_is_by_file(src):
    """--dist loadfile, because module-scoped fixtures build whole missions."""
    m = re.search(r'PAR="([^"]*-n[^"]*)"', src)
    assert m, "could not find the PAR assignment that carries the -n flag"
    par = m.group(1)
    assert "--dist" in par, (
        f"preflight parallelises without choosing a distribution ({par!r}); the "
        "default splits modules across workers and rebuilds their .miz fixtures "
        "once per worker")
    assert "--dist loadfile" in par, (
        f"preflight uses a distribution other than loadfile ({par!r}). Only "
        "loadfile keeps a module's tests on one worker, which is what makes the "
        "module-scoped mission fixtures build once each.")


def test_the_module_scoped_mission_fixtures_this_protects_still_exist():
    """If these ever go away, the loadfile requirement is worth re-deciding.

    The guard above asserts a performance property, which rots quietly. This
    one fails loudly if its whole premise has moved on — a module-scoped
    fixture that builds a mission is the thing --dist loadfile exists for.
    """
    found = []
    for p in sorted((ROOT / "tests").glob("test_*.py")):
        text = p.read_text()
        for m in re.finditer(
                r'@pytest\.fixture\(scope="module"\)\s*\ndef (\w+)\(', text):
            name = m.group(1)
            body = text[m.end(): m.end() + 900]
            if "build(" in body or "build_mission" in body or ".miz" in body:
                found.append(f"{p.name}::{name}")
    assert len(found) >= 3, (
        "expected several module-scoped fixtures that build a mission — they "
        f"are why --dist loadfile is required. Found: {found}")


def test_requirements_documents_xdist_as_optional_and_test_only(src):
    """The zip's own dependency file is where someone looks to reproduce a run."""
    req = (ROOT / "requirements.txt").read_text()
    i = req.find("pytest-xdist")
    assert i != -1, "requirements.txt never mentions pytest-xdist"
    # The COMMAND, specifically — not the prose around it. A first cut of this
    # guard searched the whole block for the string "--dist loadfile" and passed
    # happily when the command line lost the flag but the sentence explaining
    # why it matters kept it. A reader copies the command, not the sentence.
    cmd = [l for l in req.splitlines() if "python3 -m pytest" in l]
    assert len(cmd) == 1, (
        f"expected exactly one copyable pytest command in requirements.txt, "
        f"found {len(cmd)}: {cmd}")
    assert "--dist loadfile" in cmd[0], (
        "the command requirements.txt tells the reader to run omits "
        f"--dist loadfile, the one flag that makes xdist faster here: {cmd[0]}")
    assert re.search(r"-n\s+auto", cmd[0]), (
        f"the documented command never actually parallelises: {cmd[0]}")
    assert "module-scoped" in req[i: i + 1200], (
        "requirements.txt gives the flag without the reason, so the next person "
        "to tune the command has nothing to weigh")
    # Pinned lines are the installed runtime deps. A pin here would put xdist
    # into the container, which is not what any of this is for.
    assert not re.search(r"^pytest-xdist[=<>]", req, re.M), (
        "pytest-xdist is pinned as a runtime dependency; it is test-only and "
        "must stay out of the deployed image")
