"""The double-click launchers are how most people start this tool, so they are
part of the product, not scaffolding.

The bug these pin: both launchers used to `pip install` a hand-typed package
list instead of requirements.txt. The list drifted — it never gained
python-multipart, which the admin login form needs — so a clean install died at
import with `RuntimeError: Form data requires "python-multipart"`. Nothing in
CI caught it because the dev container already had the package.

Run:  pytest tests/test_launchers.py -v
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
while not (ROOT / "missiongen").is_dir() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))

LAUNCHERS = ("run_mac.command", "run_windows.bat")


@pytest.mark.parametrize("name", LAUNCHERS)
def test_launcher_ships(name):
    assert (ROOT / name).is_file(), f"{name} is missing from the repo"


@pytest.mark.parametrize("name", LAUNCHERS)
def test_launcher_installs_from_requirements(name):
    """requirements.txt is the single source of truth for runtime deps."""
    text = (ROOT / name).read_text(encoding="utf-8", errors="ignore")
    installs = re.findall(r"pip install[^\n]*", text)
    dep_installs = [ln for ln in installs if "--upgrade pip" not in ln]
    assert dep_installs, f"{name} never installs dependencies"
    for line in dep_installs:
        assert "-r requirements.txt" in line, (
            f"{name} installs a hand-maintained package list instead of "
            f"requirements.txt, which is how python-multipart went missing: "
            f"{line.strip()!r}")


@pytest.mark.parametrize("name", LAUNCHERS)
def test_launcher_preflights_every_requirement(name):
    """The `import ...` guard decides whether to install at all. If it does not
    name a package, a machine missing only that package skips the install and
    then crashes at boot — exactly the python-multipart failure."""
    text = (ROOT / name).read_text(encoding="utf-8", errors="ignore")
    guard = re.search(r'python -c "import ([^"]+)"', text)
    assert guard, f"{name} has no dependency preflight check"
    checked = {m.strip() for m in guard.group(1).split(",")}
    # distribution name on PyPI -> module name you actually import
    import_name = {"pillow": "PIL", "python-multipart": "multipart",
                   "uvicorn[standard]": "uvicorn"}
    for dist in _requirements():
        mod = import_name.get(dist, dist)
        assert mod in checked, (
            f"{name} does not preflight {dist!r} (import {mod!r}); a machine "
            f"missing only that package would skip the install and crash")


def _requirements():
    """Distribution names from requirements.txt, comments and pins stripped."""
    out = []
    for raw in (ROOT / "requirements.txt").read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            out.append(re.split(r"[=<>!~]", line, 1)[0].strip())
    return out


def test_requirements_covers_what_the_app_imports():
    """python-multipart is not imported by our code — FastAPI reaches for it at
    route-definition time — so it can only be caught by actually importing the
    app. This is the end-to-end guard."""
    import importlib
    for dist in _requirements():
        mod = {"pillow": "PIL", "python-multipart": "multipart",
               "uvicorn[standard]": "uvicorn"}.get(dist, dist)
        importlib.import_module(mod)
    importlib.import_module("server.app")   # raises if a dep is missing


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
