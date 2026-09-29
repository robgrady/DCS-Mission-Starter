"""The War on Terror era: the one where nothing shoots back from the air.

This era exists because Eagle Dynamics built the DCS Iraq North region for it
and we had no way to express it. Its window (2003-2025) overlaps `modern`
entirely, so the era gate is NOT what separates them. What separates them is
who is shooting: `modern` red flies MiG-29s and rings its bases with SA-10;
`gwot` red flies nothing at all and shoots optically-aimed guns.

That makes the whole era one large negative claim, and negative claims are
exactly what rots. Three ways it could quietly stop being true:

  * something spawns an enemy aircraft anyway — a CAP flight, a BFM adversary,
    or (the one that actually happened in development) *ambient traffic*,
    which would have taxied the derelict MiG-21s out and flown them;
  * the threat dial stops meaning anything, because the area belt is SAM-only
    and this era has no SAMs, so Minimal and Maximum generate the same map;
  * a SAM appears, from an era fallback or a tier table.

Each is asserted against a real generated .miz rather than against the tables,
because the tables are the thing most likely to be edited.
"""
import zipfile

import pytest

import dcs.lua as lua

from missiongen import Recipe, generate
from missiongen import threats
from missiongen.resolver import load_json

ERAS = load_json("eras")
MAPS = load_json("maps")

# Every map that offers the era. Parameterising over the data rather than
# naming Iraq means a third GWOT map inherits all of this for free.
GWOT_MAPS = sorted(mk for mk, cfg in MAPS.items()
                   if not mk.startswith("_") and "gwot" in cfg.get("presets", {}))


def _build(tmp_path, **over):
    rc = dict(map="iraq", era="gwot", aircraft="A_10C_2", coalition="blue",
              slots=1, seed=7)
    rc.update(over)
    path = str(tmp_path / "m.miz")
    generate(Recipe.from_dict(rc), path)
    with zipfile.ZipFile(path) as z:
        return lua.loads(z.read("mission").decode("utf-8"))["mission"]


def _red(mission, kind):
    return [g for c in mission["coalition"]["red"].get("country", {}).values()
            for g in c.get(kind, {}).get("group", {}).values()]


def test_the_era_exists_and_is_offered_somewhere():
    assert "gwot" in ERAS
    assert GWOT_MAPS, "an era no map offers cannot be selected"


@pytest.mark.parametrize("map_key", GWOT_MAPS)
def test_nothing_of_the_enemys_is_in_the_air(map_key, tmp_path):
    """The defining claim, read out of the file.

    Deliberately checks planes AND helicopters, at maximum threat intensity,
    with ambience and the BFM block both switched on — i.e. every route by
    which an enemy aircraft could reach the sky."""
    m = _build(tmp_path, map=map_key, threat_intensity=5,
               bb_ambient=True, bb_bfm=True)
    flying = [g.get("name") for kind in ("plane", "helicopter")
              for g in _red(m, kind)]
    assert not flying, (
        f"{map_key}/gwot put enemy aircraft in the air: {flying}. This enemy "
        f"has no air force; if a building block needs one it must say so, not "
        f"quietly borrow the parked-aircraft list.")


def test_the_derelicts_are_still_parked(tmp_path):
    """The other half of the same claim: the airframes exist as SCENERY. If
    suppressing enemy air also emptied the ramps, a captured airfield would
    read as a bare strip instead of a boneyard."""
    m = _build(tmp_path, bb_dressing=True)
    statics = [g.get("name") for c in
               m["coalition"]["red"].get("country", {}).values()
               for g in c.get("static", {}).get("group", {}).values()]
    assert statics, "the enemy ramp is completely empty"


def test_no_sam_anywhere_on_either_side(tmp_path):
    """An era with no SAM inventory must not acquire one by falling back to
    another era's table. `sam_kits_for` falls back to the era's own list when a
    tier pool is empty — which is the correct behavior everywhere else and
    would be a silent bug here if the era list were not also empty."""
    for tier in ("auto", "light", "heavy", "mixed"):
        for side in ("blue", "red"):
            kits = threats.sam_kits_for("gwot", side, tier,
                                        ERAS["gwot"][side]["sam_kits"])
            assert kits == [], f"gwot/{side}/{tier} offers SAM kits {kits}"
    m = _build(tmp_path, threat_intensity=5)
    named = [g.get("name", "") for side in ("blue", "red")
             for c in m["coalition"][side].get("country", {}).values()
             for g in c.get("vehicle", {}).get("group", {}).values()]
    sams = [n for n in named
            if any(t in n.upper() for t in ("SA-", "PATRIOT", "HAWK", "S-300"))]
    assert not sams, f"a SAM site appeared in an era with no SAMs: {sams}"


def test_the_threat_dial_still_does_something(tmp_path):
    """The bug this era would have shipped with.

    The area belt is SAM sites unless the pilot picks the guns tier. With no
    SAMs to place, Minimal and Maximum generated the *same empty map* — the
    intensity control silently did nothing on the default tier. `builder` now
    falls to the AAA belt whenever the era has no SAMs, whatever tier is set."""
    low = _build(tmp_path, threat_intensity=1)
    high = _build(tmp_path, threat_intensity=5)
    n_low = sum(len(g["units"]) for g in _red(low, "vehicle"))
    n_high = sum(len(g["units"]) for g in _red(high, "vehicle"))
    assert n_high > n_low * 1.5, (
        f"threat intensity 1 gave {n_low} enemy vehicles and intensity 5 gave "
        f"{n_high} — the dial is not connected in this era")


SAMLESS_ERAS = sorted(
    e for e in ERAS
    if not any(threats.sam_kits_for(e, s, t, ERAS[e][s]["sam_kits"])
               for s in ("blue", "red")
               for t in ("auto", "light", "heavy", "mixed")))


@pytest.mark.parametrize("era", SAMLESS_ERAS)
def test_an_era_with_no_sams_still_gets_an_area_threat_belt(era, tmp_path):
    """Building the GWOT era exposed this in WWII, where it had been true
    since the Threat Dial shipped.

    The area belt places SAM sites; the AAA belt only ran on the explicit
    "guns" tier. An era with no SAM inventory therefore generated NO area
    threat at all on the default tier, at any intensity — the flak in a 1944
    mission was entirely airfield SHORAD. Nothing errored, so nothing said so.

    Parameterised over whichever eras have no SAMs rather than naming them, so
    a future gun-only era cannot regress silently."""
    maps = sorted(mk for mk, cfg in MAPS.items()
                  if not mk.startswith("_") and era in cfg.get("presets", {}))
    assert maps, f"era {era} is offered by no map"
    ac = {"wwii": "P_51D", "gwot": "A_10C_2"}.get(era, "F_16C_50")
    rc = dict(map=maps[0], era=era, aircraft=ac, coalition="blue", slots=1,
              seed=7, threat_intensity=5)
    path = str(tmp_path / f"{era}.miz")
    generate(Recipe.from_dict(rc), path)
    with zipfile.ZipFile(path) as z:
        m = lua.loads(z.read("mission").decode("utf-8"))["mission"]
    belt = [g.get("name") for g in _red(m, "vehicle")
            if (g.get("name") or "").upper().startswith("AAA - AREA")]
    assert belt, (
        f"{era} on {maps[0]} at maximum threat intensity placed no area threat "
        f"belt — the dial is decorative in an era with no SAMs")


def test_the_area_belt_guns_are_the_insurgent_variants(tmp_path):
    """pydcs ships dedicated `_Insurgent` gun types. Using them is the whole
    difference between an insurgency and a downgraded regular army.

    Scoped to the AREA belt (`threats.TIER_AAA`) on purpose. The first version
    of this test looked at every red vehicle in the mission and passed even
    after `TIER_AAA["gwot"]` was gutted, because airfield SHORAD comes from a
    DIFFERENT table (`eras.json` -> gwot -> red -> shorad) and still had the
    insurgent types in it. Two tables, one assertion, and the assertion was
    satisfied by the table it was not testing."""
    m = _build(tmp_path, threat_intensity=5)
    belt = [g for g in _red(m, "vehicle")
            if (g.get("name") or "").upper().startswith("AAA - AREA")]
    assert belt, "no area AAA belt was placed at maximum intensity"
    types = {u["type"] for g in belt for u in g["units"].values()}
    assert any("Insurgent" in t for t in types), (
        f"the area gun belt uses regular-army AAA, not the insurgent "
        f"variants: {sorted(types)}")


def test_the_brief_says_there_is_no_enemy_air(tmp_path):
    """Stated, not implied. An absent 'Enemy air' line reads as a hole in the
    brief; the sentence is the intelligence."""
    rc = dict(map="iraq", era="gwot", aircraft="A_10C_2", coalition="blue",
              slots=1, seed=7, bb_briefing=True)
    path = str(tmp_path / "b.miz")
    generate(Recipe.from_dict(rc), path)
    with zipfile.ZipFile(path) as z:
        m = lua.loads(z.read("mission").decode("utf-8"))["mission"]
        text = " ".join(str(v) for v in
                        lua.loads(z.read("l10n/DEFAULT/dictionary").decode(
                            "utf-8"))["dictionary"].values())
    assert "NO ENEMY AIR FORCE" in text.upper(), (
        "the brief does not tell the pilot the one thing that most changes "
        "how this sortie is flown")


@pytest.mark.parametrize("map_key", GWOT_MAPS)
def test_the_era_has_corridors_where_it_has_presets(map_key):
    """The gap that prompted all of this: Iraq shipped a map with an empty
    corridor picker."""
    have = [c for c in load_json("air_corridors").get(map_key, [])
            if "gwot" in c.get("eras", [])]
    assert have, f"{map_key} offers the gwot era with no corridors"
