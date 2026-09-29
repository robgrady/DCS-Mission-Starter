"""A share link is a promise: the same code builds the same mission.

That promise is stronger than "same seed, same rng draws", and the difference
is where the bugs live. pydcs has two sources of per-process nondeterminism that
no amount of seeding touches:

  1. `Country.next_onboard_num()` builds a set of tail-number STRINGS and
     `.pop()`s one. Set iteration order for strings depends on PYTHONHASHSEED,
     which CPython randomises per process — so every uvicorn restart, every
     autoscaled machine and every share-link recipient got different modex
     numbers off an identical recipe.
  2. `add_runway_waypoint(..., distance=random.randrange(6000, 8000, 100))`
     evaluates its default ONCE at import, freezing a value for the life of the
     process that no later `seed()` can reach.

Neither is visible in a single-process test run, which is why the checks below
that matter are the ones that shell out to a **fresh interpreter** with a
different `PYTHONHASHSEED`. A same-process comparison would have passed
throughout the entire period the bug existed.
"""
import hashlib
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from missiongen import Recipe, generate
from missiongen.share import SHARE_SCHEMA, decode_recipe, encode_recipe

ROOT = Path(__file__).resolve().parent.parent

RECIPES = {
    "modern": dict(map="caucasus", era="modern", aircraft="FA_18C_hornet",
                   threat_intensity=3, bb_sams=True, seed=21),
    "coldwar": dict(map="caucasus", era="coldwar", aircraft="F_5E_3",
                    bb_tanker=True, bb_awacs=True, seed=22),
    "carrier": dict(map="persiangulf", era="modern", aircraft="FA_18C_hornet",
                    bb_carrier=True, home_airbase="CARRIER", seed=23),
}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --- same process -----------------------------------------------------------

@pytest.mark.parametrize("label", sorted(RECIPES))
def test_the_same_recipe_builds_the_same_bytes(label, tmp_path):
    rc = {**RECIPES[label], "bb_ambient": False}
    a, b = str(tmp_path / "a.miz"), str(tmp_path / "b.miz")
    generate(Recipe.from_dict(rc), a)
    generate(Recipe.from_dict(rc), b)
    assert _sha(a) == _sha(b), f"{label}: two builds of one recipe differ"


def test_a_different_seed_builds_a_different_mission(tmp_path):
    """The other direction. A determinism fix that pinned everything to a
    constant would pass every test above and make the seed control useless."""
    rc = {**RECIPES["modern"], "bb_ambient": False}
    a, b = str(tmp_path / "a.miz"), str(tmp_path / "b.miz")
    generate(Recipe.from_dict({**rc, "seed": 1}), a)
    generate(Recipe.from_dict({**rc, "seed": 2}), b)
    assert _sha(a) != _sha(b), "the seed no longer changes anything"


def test_zip_timestamps_are_pinned(tmp_path):
    """Byte-determinism is impossible if the archive records build time. Every
    entry is pinned to the zip epoch (1980-01-01)."""
    out = str(tmp_path / "t.miz")
    generate(Recipe.from_dict({**RECIPES["modern"], "bb_ambient": False}), out)
    for info in zipfile.ZipFile(out).infolist():
        assert info.date_time == (1980, 1, 1, 0, 0, 0), \
            f"{info.filename} carries a wall-clock timestamp {info.date_time}"


# --- fresh process, different hash seed: the check that would have caught it -

_CHILD = r"""
import hashlib, sys
sys.path.insert(0, {root!r}); sys.path.insert(0, {vendor!r})
from missiongen import Recipe, generate
generate(Recipe.from_dict({rc!r}), sys.argv[1])
print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())
"""


def _build_in_subprocess(rc, out, hashseed):
    env = {**os.environ, "PYTHONHASHSEED": str(hashseed)}
    src = _CHILD.format(root=str(ROOT), vendor=str(ROOT / "vendor"), rc=rc)
    r = subprocess.run([sys.executable, "-c", src, out], env=env,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    return r.stdout.strip().splitlines()[-1]


@pytest.mark.parametrize("label", sorted(RECIPES))
def test_the_mission_survives_a_different_python_hash_seed(label, tmp_path):
    """The real contract: your friend opens your share link on their machine,
    in their process, and gets your mission — not one with different tail
    numbers. PYTHONHASHSEED is randomised per process by default, so this is
    what a share-link recipient actually experiences."""
    rc = {**RECIPES[label], "bb_ambient": False}
    one = _build_in_subprocess(rc, str(tmp_path / "1.miz"), 1)
    two = _build_in_subprocess(rc, str(tmp_path / "2.miz"), 99991)
    assert one == two, (
        f"{label}: the same recipe built different bytes under a different "
        f"PYTHONHASHSEED — something is iterating a set of strings")


def test_tail_numbers_are_assigned_in_a_stable_order(tmp_path):
    """The specific mechanism, pinned so the symptom is diagnosable rather than
    just 'the hashes differ'."""
    from dcs.country import Country
    assert Country.next_onboard_num.__name__ == "_deterministic_next_onboard_num", \
        "the pydcs tail-number patch is not installed"
    c = Country(1, "Test", "TST")
    got = [c.next_onboard_num() for _ in range(5)]
    assert got == sorted(got), f"tail numbers came out unordered: {got}"


# --- share links ------------------------------------------------------------

@pytest.mark.parametrize("label", sorted(RECIPES))
def test_a_share_link_round_trips(label):
    rc = Recipe.from_dict(RECIPES[label])
    back = decode_recipe(encode_recipe(rc))
    assert back.to_dict() == rc.to_dict(), f"{label}: the link lost something"


@pytest.mark.parametrize("label", sorted(RECIPES))
def test_a_share_link_rebuilds_the_same_mission(label, tmp_path):
    """Round-tripping the dataclass is not the promise. Building the same
    mission is."""
    rc = Recipe.from_dict({**RECIPES[label], "bb_ambient": False})
    a, b = str(tmp_path / "a.miz"), str(tmp_path / "b.miz")
    generate(rc, a)
    generate(decode_recipe(encode_recipe(rc)), b)
    assert _sha(a) == _sha(b), f"{label}: the shared link built a different mission"


def test_a_link_carries_only_what_was_changed():
    """Codes stay short because the payload is a diff against the defaults. If
    that ever became a full dump, every existing link would still decode — but
    every new one would be four times as long."""
    import base64
    import json
    rc = Recipe.from_dict({"era": "modern", "seed": 4})
    code = encode_recipe(rc)
    raw = json.loads(base64.urlsafe_b64decode(code + "=" * (-len(code) % 4)))
    assert raw["v"] == SHARE_SCHEMA
    assert set(raw["r"]) <= {"era", "seed", "map", "aircraft"}, \
        f"the link is carrying defaults: {sorted(raw['r'])}"


def test_an_older_link_still_opens():
    """Additive fields with defaults must not need a schema bump — that is the
    whole reason the envelope is versioned. A link saved before `mission_kind`
    existed has to keep working."""
    import base64
    import json
    payload = {"v": 1, "r": {"map": "caucasus", "era": "coldwar",
                             "aircraft": "F_5E_3", "seed": 9}}
    code = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    rc = decode_recipe(code)
    assert rc.era == "coldwar" and rc.seed == 9
    assert rc.mission_kind == Recipe().mission_kind, \
        "a field added after the link was saved did not take its default"


def test_a_corrupt_link_is_refused_not_guessed():
    from missiongen.share import RecipeError
    for bad in ("", "!!!!", "bm90anNvbg"):
        with pytest.raises((RecipeError, ValueError, Exception)):
            decode_recipe(bad)
