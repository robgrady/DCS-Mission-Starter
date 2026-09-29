"""Every card in the Library must build in every era it offers.

v1.46.1 found nine advertised combinations that could not produce a mission.
The shape of the bug was always the same: a card names the eras it supports in
`eras` but pins an aircraft in `recipe`, and nobody checked the two against each
other. **Carrier Qualification** offered the Cold War while pinned to the
FA-18C, which did not exist until 1987 — clicking it in the Cold War returned an
error instead of a mission. CAP/Alert-5, SEAD Range and four Fly Now cards were
pinned to the F-16C with the same result, and two Fly Now cards offered WWII on
a map with no WWII content.

None of it was visible from the code: the card *looked* fine, the era *looked*
supported, and the failure only happened on the click. So the test is the
brute-force one — build the thing, in every era it advertises, and see.
"""
import pytest

from missiongen import Recipe, generate
from missiongen.templates import (advertised_combinations, effective_recipe,
                                  templates)
from missiongen.resolver import load_json

ERAS = load_json("eras")
MAPS = load_json("maps")
SERVICE = load_json("aircraft_service")

COMBOS = list(advertised_combinations())


def test_the_library_is_not_empty():
    """A guard on the guard. Every check below parametrizes over COMBOS, so an
    empty list would turn the whole file green while testing nothing."""
    assert len(COMBOS) >= 30, f"only {len(COMBOS)} advertised combinations"
    assert len(templates()) >= 20


# --- the cheap checks, one card at a time -----------------------------------

@pytest.mark.parametrize("key,era", COMBOS, ids=[f"{k}/{e}" for k, e in COMBOS])
def test_the_pinned_aircraft_existed_in_the_era_the_card_offers(key, era):
    """The exact v1.46.1 defect, checked without building anything: an F/A-18C
    on a Cold War card, an F-16C on a 1975 mission."""
    rc = effective_recipe(key, era)
    ac = rc.get("aircraft")
    if not ac:
        return                              # card lets the user choose
    win = SERVICE.get(ac)
    assert win, f"{key}/{era}: '{ac}' has no service window in aircraft_service"
    e_lo, e_hi = ERAS[era]["window"]
    a_lo, a_hi = (win[0] or 0), (win[1] or 9999)
    assert not (a_lo > e_hi or a_hi < e_lo), (
        f"{key} offers {era} ({e_lo}-{e_hi}) but is pinned to {ac}, "
        f"in service {a_lo}-{a_hi}")


@pytest.mark.parametrize("key,era", COMBOS, ids=[f"{k}/{e}" for k, e in COMBOS])
def test_the_map_the_card_lands_on_supports_the_era(key, era):
    """Two Fly Now cards offered WWII on a map with no WWII content.

    A map declares the eras it can stage by carrying a `presets` block per era
    — countries, airbase splits, front line. No preset, no mission: this is the
    check `Recipe.validate()` cannot make, because the recipe is fine in
    isolation and only the pairing is wrong.
    """
    rc = effective_recipe(key, era)
    m = MAPS.get(rc["map"])
    assert m, f"{key}/{era}: unknown map '{rc['map']}'"
    have = sorted(m.get("presets") or {})
    assert era in have, \
        f"{key} offers {era} on {rc['map']}, which only stages {have}"


@pytest.mark.parametrize("key,era", COMBOS, ids=[f"{k}/{e}" for k, e in COMBOS])
def test_the_recipe_a_card_produces_is_valid(key, era):
    """`Recipe.validate()` is the same gate the API applies. A card that can't
    get through it is a 400 with the user's click already spent."""
    Recipe.from_dict(effective_recipe(key, era)).validate()


def test_a_carrier_card_asks_for_a_carrier():
    """`needs_carrier` drives which maps the card is offered on. A card that
    claims it and doesn't set `bb_carrier` would be offered on sea maps only
    and then build a land mission."""
    for key, tpl in templates().items():
        if not tpl.get("needs_carrier"):
            continue
        for era in tpl.get("eras", []):
            rc = effective_recipe(key, era)
            assert rc.get("bb_carrier"), \
                f"{key}/{era} is flagged needs_carrier but bb_carrier is off"


def test_by_era_overrides_actually_override():
    """The fix for the nine broken combinations was a `by_era` block per card.
    If `effective_recipe` ever stopped merging it, every one of them would
    silently revert — and the era-pinning tests above would be the only thing
    standing between that and a shipped regression, so pin the mechanism too."""
    overriding = [(k, e) for k, t in templates().items()
                  for e in (t.get("by_era") or {})
                  if e in t.get("eras", [])]
    assert overriding, "no card overrides anything per era any more"
    for key, era in overriding:
        tpl = templates()[key]
        for field, want in tpl["by_era"][era].items():
            assert effective_recipe(key, era)[field] == want, \
                f"{key}/{era}: by_era sets {field}={want!r} and it did not stick"


# --- and the one that actually proves it ------------------------------------

@pytest.mark.parametrize("key,era", COMBOS, ids=[f"{k}/{e}" for k, e in COMBOS])
def test_every_advertised_combination_builds_a_mission(key, era, tmp_path):
    """Brute force, because that is what the bug required. Everything above is
    a proxy for this."""
    rc = effective_recipe(key, era)
    rc.setdefault("seed", 7)
    rc["bb_ambient"] = False            # the slow part, and not what's on trial
    out = str(tmp_path / f"{key}_{era}.miz")
    res = generate(Recipe.from_dict(rc), out)
    assert res["path"], f"{key}/{era} built nothing"

    import zipfile
    z = zipfile.ZipFile(out)
    assert "mission" in z.namelist(), f"{key}/{era}: .miz has no mission table"
    assert z.read("mission").startswith(b"mission="), \
        f"{key}/{era}: mission table has the wrong preamble — DCS won't open it"
