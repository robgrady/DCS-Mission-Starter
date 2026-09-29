"""The F-16 B-Course track, and the numbers that make it one.

These cards claim to follow a real document — AETC Syllabus F16C0B00PL (56 FW,
Luke AFB, April 2014), the F-16C/D Combined Wingman Syllabus. That claim is the
whole product: a card that says "BFM-1, 9,000 ft" and spawns you at 7,200 ft is
worse than a card that says nothing, because a pilot will believe it.

The syllabus flies offensive BFM on BFM-1/2/3 and defensive BFM on BFM-4/5/6,
and every one of those sorties runs the same three setups:

    *6. Offensive BFM — a. 9,000 ft; b. 6,000 ft; c. 3,000 ft
    *6. Defensive BFM — a. 9,000 ft; b. 6,000 ft; c. 3,000 ft

So the perch ranges are asserted in FEET, against a distance measured out of a
generated .miz — not against the meters in the table, which is the number the
implementation would agree with by construction.
"""
import math
import tempfile
import zipfile

import pytest

import dcs.lua as lua

from missiongen import Recipe, generate
from missiongen.bfm import SETUPS
from missiongen.resolver import load_json
from missiongen.templates import effective_recipe

TEMPLATES = load_json("mission_templates")
BC = sorted(k for k in TEMPLATES if k.startswith("bc_"))

# Straight from the syllabus, in the unit the syllabus uses. Anything derived
# from `SETUPS` would be circular.
SYLLABUS_PERCH_FT = {
    "off_9k": 9000, "off_6k": 6000, "off_3k": 3000,
    "def_9k": 9000, "def_6k": 6000, "def_3k": 3000,
}
FT_PER_M = 3.280839895


def _build(rc, tmp_path, name="m.miz"):
    path = str(tmp_path / name)
    generate(Recipe.from_dict(rc), path)
    with zipfile.ZipFile(path) as z:
        return lua.loads(z.read("mission").decode("utf-8"))["mission"]


def _planes(mission):
    for side in ("blue", "red"):
        for c in mission["coalition"][side].get("country", {}).values():
            for g in c.get("plane", {}).get("group", {}).values():
                yield side, g


@pytest.mark.parametrize("setup,want_ft", sorted(SYLLABUS_PERCH_FT.items()))
def test_the_perch_is_at_the_range_the_syllabus_says(setup, want_ft, tmp_path):
    """Measured in the built mission, in feet, against the document.

    Tolerance is 30 ft on setups of 3,000 to 9,000 ft — that is 1% at the
    tightest perch, and it is there for floating-point and projection rounding,
    not for 'about right'."""
    m = _build(dict(map="nevada", era="modern", aircraft="F_16C_50",
                    coalition="blue", slots=1, seed=7, start="air",
                    bb_bfm=True, bfm_setup=setup), tmp_path, f"{setup}.miz")
    player = bandit = None
    for _side, g in _planes(m):
        units = list(g["units"].values())
        if any(u.get("skill") in ("Player", "Client") for u in units):
            player = units[0]
        if "Bandit" in (g.get("name") or ""):
            bandit = units[0]
    assert player and bandit, f"{setup}: no player/bandit pair was built"
    got_ft = math.hypot(player["x"] - bandit["x"],
                        player["y"] - bandit["y"]) * FT_PER_M
    assert abs(got_ft - want_ft) <= 30, (
        f"{setup} is briefed as {want_ft} ft and measures {got_ft:.0f} ft in "
        f"the generated mission")


def test_the_offensive_and_defensive_ladders_are_the_same_ranges():
    """The syllabus runs the SAME three ranges in both positions. If one ladder
    drifts, the pair stops being comparable and the whole point of flying both
    — same geometry, opposite seat — is gone."""
    off = [SETUPS[k]["range_m"] for k in ("off_9k", "off_6k", "off_3k")]
    dfn = [SETUPS[k]["range_m"] for k in ("def_9k", "def_6k", "def_3k")]
    assert off == dfn, f"offensive ladder {off} != defensive ladder {dfn}"
    assert off == sorted(off, reverse=True), "the ladder is not descending"


def test_the_original_four_perches_are_untouched():
    """Share links are byte-stable. A recipe minted against `offensive` before
    the syllabus landed must keep building the identical mission, so the six
    new setups are ADDITIVE and the original four are frozen."""
    assert SETUPS["neutral"]["range_m"] == 3700
    assert SETUPS["offensive"]["range_m"] == 2200
    assert SETUPS["defensive"]["range_m"] == 2200
    assert SETUPS["high_aspect"]["range_m"] == 9260


def test_every_new_setup_is_selectable_in_a_recipe():
    """A setup the recipe validator rejects is a setup nobody can fly."""
    from missiongen.recipe import RECIPE_ENUMS
    allowed = set(RECIPE_ENUMS["bfm_setup"])
    missing = sorted(set(SYLLABUS_PERCH_FT) - allowed)
    assert not missing, f"bfm_setup rejects {missing}"


def test_the_track_covers_all_four_phases():
    """TR, AH, A-A, A-S. A 'B-Course' that is really just a BFM pack should not
    be called a B-Course."""
    labels = " ".join(TEMPLATES[k]["label"] for k in BC)
    for sortie in ("TR-1", "AHC", "BFM-1", "BFM-4", "BFM-7",
                   "ACM-1", "TI-1", "LASDT-1", "SA-1", "SAT-2", "CAS-1"):
        assert sortie in labels, f"no card for {sortie}"


@pytest.mark.parametrize("key", BC)
def test_a_card_cites_the_syllabus_paragraph_it_claims(key):
    """Every card names the document and the paragraph. This is the same
    discipline as docs/SOURCES.md: a claim a pilot cannot trace is a claim they
    should not trust."""
    brief = "\n".join(TEMPLATES[key].get("brief") or [])
    assert "F16C0B00PL" in brief, f"{key} does not name the syllabus"
    assert "56 FW" in brief, f"{key} does not name the wing"
    assert "para 5-" in brief or "Chapter 5" in brief, \
        f"{key} does not cite a paragraph"


@pytest.mark.parametrize("key", BC)
def test_every_card_builds(key, tmp_path):
    for era in TEMPLATES[key]["eras"]:
        rc = effective_recipe(key, era)
        rc.setdefault("map", TEMPLATES[key].get("default_map", "nevada"))
        rc.update(era=era, template=key, seed=7)
        m = _build(rc, tmp_path, f"{key}-{era}.miz")
        assert m["coalition"]["blue"], f"{key}/{era} built an empty mission"


def test_the_g_awareness_profile_is_stated_exactly(tmp_path):
    """The one number on TR-1 a pilot might actually copy. The syllabus is
    specific — warm-up to 4 G, a 180 at 6-8 G, a 180 at 8-9 G, two AGSM cycles
    per turn — and a paraphrase ('pull some Gs to warm up') is not training."""
    brief = "\n".join(TEMPLATES["bc_tr1"]["brief"])
    for token in ("4 G", "6 to 8 G", "8 to 9 G", "TWO complete AGSM"):
        assert token in brief, f"TR-1 has lost the '{token}' element"


def test_the_low_altitude_floor_is_stated_and_is_500_feet(tmp_path):
    """LASDT's whole subject. The syllabus floor is 500 ft AGL and the CAT I
    band is 1,000 to 500 — a card that says 'stay low' has taught nothing."""
    brief = "\n".join(TEMPLATES["bc_lasdt1"]["brief"])
    assert "500 FEET AGL" in brief.upper()
    assert "1,000 down to" in brief or "1,000 to 500" in brief
    for rule in ("1 PERCENT", "50 PERCENT", "10 DEGREE"):
        assert rule in brief.upper(), f"the {rule} rule is not briefed"


# ---------------------------------------------------------------------------
# "Turning the Phantom" — TAC ATTACK, February 1967.
#
# A card built from a single magazine article, and the article's whole point is
# a set of specific counts. "Most accidents involved low speed" is a vibe;
# "eight of eleven were at 300 knots or below" is a finding. If the numbers
# drift out of the brief the card stops being the article and becomes an
# opinion about Phantoms.
# ---------------------------------------------------------------------------
PHANTOM = "f4_turning_phantom"


def test_the_phantom_card_exists_and_is_a_phantom():
    t = TEMPLATES[PHANTOM]
    assert t["eras"] == ["coldwar"], "the article is February 1967"
    assert t["recipe"]["aircraft"].startswith("F_4E"), \
        "Turning the Phantom is not a Turning the Anything Else"


@pytest.mark.parametrize("finding", [
    "22 F-4 accidents",      # the population
    "ELEVEN",                # lost control
    "TEN were maneuvering",
    "EIGHT were at 300 knots or below",
    "ALL ELEVEN were carrying external stores",
    "175 hours",             # they were not beginners
    "FIFTY PERCENT",         # what stores did to the stick force gradient
    "350 KCAS",              # the basic maneuvering speed
])
def test_the_article_findings_survive_in_the_brief(finding):
    """Each of these is a counted fact from the February 1967 review, not a
    characterisation of it. They are what make the card worth flying."""
    brief = "\n".join(TEMPLATES[PHANTOM]["brief"])
    assert finding in brief, f"the '{finding}' finding has gone"


def test_the_three_g_figure_is_stated_with_its_airspeed_band():
    """3G alone is meaningless — it is 3G *between 250 and 300 knots CAS*, and
    the contrast with the 4.5-5G a pilot pulls off a weapons pass is the point.
    A brief that keeps the number and drops the band has kept the wrong half."""
    brief = "\n".join(TEMPLATES[PHANTOM]["brief"])
    assert "250 and 300 knots" in brief
    assert "3G" in brief
    assert "4.5 or 5G" in brief, "the comparison that makes 3G alarming is gone"


def test_it_cites_the_magazine_and_the_issue():
    brief = "\n".join(TEMPLATES[PHANTOM]["brief"])
    assert "TAC ATTACK" in brief
    assert "February 1967" in brief
    assert "Podner" in brief, "the article's own conclusion is the mnemonic"


def test_the_phantom_card_builds(tmp_path):
    rc = effective_recipe(PHANTOM, "coldwar")
    rc.setdefault("map", TEMPLATES[PHANTOM].get("default_map", "nevada"))
    rc.update(era="coldwar", template=PHANTOM, seed=7)
    m = _build(rc, tmp_path, "phantom.miz")
    types = {u["type"] for _s, g in _planes(m) for u in g["units"].values()}
    assert any("F-4" in t for t in types), f"no Phantom was built: {sorted(types)}"
