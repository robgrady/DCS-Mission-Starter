"""The release zip has to be a complete recovery point.

This test exists because of a specific, expensive failure. The build
environment was reclaimed mid-project and the entire workspace went with it.
Recovery was possible because a release zip existed — but `scripts/package.sh`
shipped `missiongen`, `server`, `frontend`, `docs`, `samples` and `vendor`, and
NOT `tests`. So the code came back and a 188-test suite did not, and every
invariant those tests protected went unguarded until they could be rewritten.

A zip that restores a product nobody can verify is a partial recovery point
dressed as a complete one. The manifest is a one-line file that nothing else
checks, which is exactly the kind of thing that quietly loses an entry, so:
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PACKAGE_SH = (ROOT / "scripts" / "package.sh").read_text()


def _manifest():
    m = re.search(r"MANIFEST=\((.*?)\n\)", PACKAGE_SH, re.S)
    assert m, "MANIFEST=(...) is gone from scripts/package.sh"
    entries = []
    for line in m.group(1).splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            entries.append(line)
    return entries


MANIFEST = _manifest()


def test_the_manifest_parsed():
    assert len(MANIFEST) >= 10, f"parsed only {len(MANIFEST)} manifest entries"


@pytest.mark.parametrize("entry", [
    "missiongen", "server", "frontend", "scripts", "docs", "vendor",
    "tests", "requirements.txt", "Dockerfile", "fly.toml",
    "run_mac.command", "run_windows.bat",
])
def test_the_zip_carries_everything_needed_to_rebuild_and_verify(entry):
    assert entry in MANIFEST, (
        f"'{entry}' is not in scripts/package.sh's MANIFEST. The zip is the "
        f"recovery point; anything missing from it is gone if this machine is.")


@pytest.mark.parametrize("entry", MANIFEST)
def test_every_manifest_entry_exists(entry):
    """`zip` fails on a missing path, so a stale entry breaks the build — but
    it breaks it at release time, which is the worst moment to find out."""
    assert (ROOT / entry).exists(), \
        f"MANIFEST lists '{entry}', which is not in the repository"


def test_the_package_script_verifies_its_own_output():
    """Listing a path is not the same as shipping it. The script re-opens the
    zip and checks — this pins that it checks for the tests too."""
    assert re.search(r"for must in .*tests/conftest\.py", PACKAGE_SH), \
        "package.sh no longer verifies that the tests made it into the zip"


def test_the_version_is_parsed_not_imported():
    """`import missiongen` pulls in vendored pydcs and pyproj, so packaging
    used to fail on any checkout where the vendor path wasn't already on
    sys.path — the same trap preflight.sh was fixed for."""
    assert "sed -n 's/^__version__" in PACKAGE_SH, \
        "package.sh is importing the package to read its version again"
    code = "\n".join(l.split("#", 1)[0] for l in PACKAGE_SH.splitlines())
    assert "import missiongen" not in code, \
        "package.sh imports missiongen to read the version; it must parse it"


def test_the_suite_can_be_run_with_a_bare_pytest():
    """A shipped test suite that needs an undocumented PYTHONHASHSEED-style
    incantation to start is a suite nobody runs. `tests/conftest.py` puts the
    vendored pydcs on the path so `pytest` works from a fresh unzip."""
    conftest = ROOT / "tests" / "conftest.py"
    assert conftest.exists(), "tests/conftest.py is missing"
    body = conftest.read_text()
    assert "vendor" in body and "sys.path" in body, \
        "conftest no longer puts the vendored pydcs on sys.path"


def test_no_test_reaches_outside_the_repository():
    """The suite ships inside the zip, so it has to run from a fresh unzip on
    someone else's machine. An absolute path to this build environment would
    work here forever and fail everywhere else."""
    bad = []
    for f in sorted((ROOT / "tests").glob("test_*.py")):
        for hit in re.findall(r'["\'](/(?:home|Users|root|mnt)/[^"\']*)["\']',
                              f.read_text()):
            bad.append(f"{f.name}: {hit}")
    assert not bad, "tests hard-code machine-specific paths:\n  " + "\n  ".join(bad)


def test_the_preflight_check_runs_the_suite():
    """Shipping the tests is half of it. A release that ships them and never
    runs them is the same partial recovery point with extra files."""
    pre = (ROOT / "scripts" / "preflight.sh").read_text()
    assert "pytest" in pre, \
        "scripts/preflight.sh does not run the test suite before a deploy"
