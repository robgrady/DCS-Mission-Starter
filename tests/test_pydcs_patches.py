"""A local patch to vendored pydcs must not outlive its reason.

`missiongen/pydcs_patches.py` adds fields the DCS Mission Editor writes and
pydcs does not. Patches like that are a liability the moment upstream grows the
field itself: the vendored tree gets re-pulled for a new aircraft, the field
arrives, and our patch quietly keeps overwriting it with our own idea of the
value. So each patch gets a redundancy check that FAILS when it is no longer
needed, with the instruction to delete it rather than keep it.
"""
import pytest

import missiongen  # noqa: F401  — importing applies the patches
from missiongen import pydcs_patches
from dcs.task import Modulation
from dcs.unit import Ship


def test_the_patch_is_applied_by_importing_missiongen():
    assert getattr(Ship.dict, "_sortie_starter_patch", False), (
        "Ship.dict is unpatched — missiongen/__init__ no longer imports "
        "pydcs_patches, and every carrier ships without a modulation field")


def test_applying_twice_does_not_stack():
    """A patch that wraps itself once per call would nest without bound."""
    before = Ship.dict
    pydcs_patches.apply()
    pydcs_patches.apply()
    assert Ship.dict is before, "apply() is not idempotent"


def test_upstream_pydcs_still_lacks_the_field_we_are_adding():
    """THE DELETE-ME ALARM.

    If this fails, pydcs has grown ship modulation on its own. That is good
    news: delete the modulation entry from missiongen/pydcs_patches.py and this
    test with it, rather than leaving our value fighting upstream's.
    """
    unpatched = pydcs_patches._SHIP_DICT
    assert not getattr(unpatched, "_sortie_starter_patch", False), \
        "the saved original is itself a patch — apply() ran twice unguarded"
    src = unpatched.__code__.co_consts
    assert "modulation" not in [c for c in src if isinstance(c, str)], (
        "vendored pydcs now writes ship modulation itself. Delete the patch "
        "and this test.")


def test_the_default_is_am():
    """AM, because the F-14 pilot's ARC-159 is AM-only across 225-400 MHz and
    carrier ATC is the thing this exists for."""
    assert Modulation.AM.value == 0
    from missiongen.terrains import install  # noqa: F401
    import dcs
    m = dcs.Mission()
    grp = m.ship_group(m.country("USA"), "probe", dcs.ships.Stennis,
                       dcs.mapping.Point(0, 0, m.terrain))
    d = grp.units[0].dict()
    assert d["modulation"] == Modulation.AM.value, \
        f"a ship defaults to modulation {d['modulation']}, not AM"


def test_a_ship_can_still_override_the_modulation():
    """The patch reads an instance attribute when one is set, so a future FM
    agency (a scripted LSO on FM, say) is expressible without editing it."""
    import dcs
    m = dcs.Mission()
    grp = m.ship_group(m.country("USA"), "probe", dcs.ships.Stennis,
                       dcs.mapping.Point(0, 0, m.terrain))
    grp.units[0].modulation = Modulation.FM.value
    assert grp.units[0].dict()["modulation"] == Modulation.FM.value
