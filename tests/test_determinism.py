"""Guard tests for the DCS Sortie Starter's core promise:

    "recipe + seed = the same starter, always regenerable; a share link IS the mission"

The important test here is `test_same_recipe_is_byte_identical_across_processes`.
It MUST run generation in subprocesses. An in-process check passes even when the
product is broken, because both bugs this guards against are per-process:

  * pydcs `unitgroup.py:405` evaluates `distance=random.randrange(...)` at import,
    freezing one random value for the life of the process.
  * pydcs `country.py:185` allocates tail numbers with `set.pop()` on a set of
    strings, so modexes follow PYTHONHASHSEED.

Both are stable within a process and vary across processes. That is exactly how
this shipped broken through v1.9.1 unnoticed.

Run:  pytest test_determinism.py -v
      python test_determinism.py          # standalone, no pytest needed
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
while not (ROOT / "missiongen").is_dir() and ROOT != ROOT.parent:
    ROOT = ROOT.parent

# Recipes worth locking down: one per era, plus carrier, composed ramp and template.
RECIPES = {
    "modern_viper": {"map": "caucasus", "era": "modern", "aircraft": "F_16C_50", "seed": 42},
    "coldwar_phantom": {"map": "germany", "era": "coldwar", "aircraft": "F_4E_45MC", "seed": 7},
    "wwii_spitfire": {"map": "thechannel", "era": "wwii", "aircraft": "SpitfireLFMkIX", "seed": 3},
    "carrier_hornet": {"map": "syria", "era": "modern", "aircraft": "FA_18C_hornet",
                       "seed": 11, "bb_carrier": True, "home_airbase": "CARRIER"},
    "composed_ramp": {"map": "nevada", "era": "modern", "aircraft": "F_16C_50", "seed": 5,
                      "dress_mix": {"F_16C_50": 6, "A_10C_2": 4}},
    "template_sead": {"map": "caucasus", "era": "modern", "aircraft": "F_16C_50",
                      "template": "sead_range", "seed": 13},
}

# Child process: build one .miz and print the hash of its inner `mission` entry.
# Hashing the zip itself would be wrong -- zip mtimes legitimately differ.
_CHILD = r'''
import hashlib, json, os, sys, tempfile, zipfile, warnings, io, contextlib
warnings.filterwarnings("ignore")
root = sys.argv[1]; recipe = json.loads(sys.argv[2])
sys.path.insert(0, os.path.join(root, "vendor")); sys.path.insert(0, root)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    from missiongen import Recipe, generate
    out = os.path.join(tempfile.mkdtemp(), "t.miz")
    generate(Recipe.from_dict(recipe), out)
with zipfile.ZipFile(out) as z:
    parts = {n: hashlib.sha256(z.read(n)).hexdigest() for n in sorted(z.namelist())}
print(json.dumps(parts))
'''


def _build_in_subprocess(recipe: dict, hashseed: str | None = None) -> dict:
    """Generate a .miz in a FRESH interpreter; return {zip entry: sha256}."""
    env = dict(os.environ)
    if hashseed is not None:
        env["PYTHONHASHSEED"] = hashseed          # simulate another machine
    env.pop("PYTHONWARNINGS", None)
    r = subprocess.run([sys.executable, "-c", _CHILD, str(ROOT), json.dumps(recipe)],
                       capture_output=True, text=True, env=env, timeout=300)
    if r.returncode != 0:
        raise AssertionError(f"generation failed:\n{r.stderr[-2000:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def _check_identical(name, recipe):
    """Same recipe+seed, three fresh processes under different hash seeds."""
    runs = [_build_in_subprocess(recipe, hashseed=hs) for hs in ("0", "1", "12345")]
    first = runs[0]
    for i, other in enumerate(runs[1:], start=2):
        for entry in sorted(set(first) | set(other)):
            assert first.get(entry) == other.get(entry), (
                f"{name}: '{entry}' differs between run 1 and run {i} for an identical "
                f"recipe+seed.\n  A share link does not reproduce this mission.\n"
                f"  {first.get(entry)} != {other.get(entry)}")
    return first


# --- the tests -------------------------------------------------------------

def test_same_recipe_is_byte_identical_across_processes():
    for name, recipe in RECIPES.items():
        _check_identical(name, recipe)


def test_different_seed_produces_a_different_mission():
    """Determinism must not be achieved by flattening variation."""
    a = _build_in_subprocess({**RECIPES["modern_viper"], "seed": 1})
    b = _build_in_subprocess({**RECIPES["modern_viper"], "seed": 2})
    assert a["mission"] != b["mission"], "seed 1 and seed 2 produced the same mission"


def test_recipe_share_code_round_trips():
    sys.path.insert(0, str(ROOT / "vendor")); sys.path.insert(0, str(ROOT))
    from missiongen.recipe import Recipe
    from missiongen.share import decode_recipe, encode_recipe
    for recipe in RECIPES.values():
        r = Recipe.from_dict(recipe)
        assert decode_recipe(encode_recipe(r)).to_dict() == r.to_dict()


def test_data_packs_are_valid():
    """validate_data_packs() already exists -- this just runs it every push."""
    sys.path.insert(0, str(ROOT / "vendor")); sys.path.insert(0, str(ROOT))
    from missiongen.resolver import validate_data_packs
    errors = validate_data_packs()
    assert not errors, "data pack errors:\n  " + "\n  ".join(errors)


if __name__ == "__main__":
    failed = 0
    for fn in (test_data_packs_are_valid, test_recipe_share_code_round_trips,
               test_same_recipe_is_byte_identical_across_processes,
               test_different_seed_produces_a_different_mission):
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}\n      {e}")
    print(f"\n{'FAILED' if failed else 'OK'} — {failed} failure(s)")
    sys.exit(1 if failed else 0)
