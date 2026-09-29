"""Pending modules (the F-14B(U)) — roster presentation and era availability.

Two defects Rob reported, both in the DATA rather than the engine:

  1. Every native entry in the aircraft roster is a bare type designation
     ("F-14B", "F-16C_50") with the popular name supplied separately, so the
     UI renders "F-14B · Tomcat". The F-14B(U)'s label was
     "F-14B(U) Tomcat (Heatblur)" — the only entry carrying a vendor name, and
     because the string ended in "(Heatblur)" the "strip the trailing popular
     name" rule never fired, so it rendered verbatim and duplicated "Tomcat".
  2. Its service window was [1994, 2006], which does not overlap the Cold War
     era window [1965, 1985], so the jet could not be selected there at all.

The (U) is a community UPRATED Tomcat rather than a historical airframe, so its
service window is a product decision — the real F-14B is 1988 and the
period-correct Cold War Tomcat is the F-14A.
"""
import re
from pathlib import Path

import pytest

from missiongen import Recipe, generate
from missiongen.acnames import display
from missiongen.resolver import load_json

ROOT = Path(__file__).parent.parent
HTML = (ROOT / "frontend" / "index.html").read_text()
KEY = "F_14B_U"


def _pending():
    return load_json("pending_aircraft")[KEY]


# --- presentation -----------------------------------------------------------

def test_no_vendor_name_on_any_aircraft_label():
    """The vendor is credited in the site footer, not on the aircraft."""
    for key, cfg in load_json("pending_aircraft").items():
        for vendor in ("Heatblur", "Eagle Dynamics", "Razbam", "Deka", "Aerges"):
            assert vendor.lower() not in cfg["label"].lower(), \
                f"{key} carries the vendor name in its roster label"


def test_pending_label_is_a_bare_designation():
    """Same shape as every native entry, so the shared display rule works."""
    label = _pending()["label"]
    assert label == "F-14B(U)", f"expected a bare designation, got {label!r}"
    assert " " not in label, "a designation should not contain a popular name"


def test_it_renders_like_its_siblings():
    assert display(KEY, _pending()["label"]) == "F-14B(U) · Tomcat"
    assert display("F_14B", "F-14B") == "F-14B · Tomcat"


def test_both_renderers_know_the_popular_name():
    """aircraft_names.json feeds the documents and AC_NAME feeds the UI — they
    are two renderers over one vocabulary and must not disagree."""
    assert load_json("aircraft_names").get(KEY) == "Tomcat"
    assert re.search(r'F_14B_U\s*:\s*"Tomcat"', HTML), \
        "the frontend AC_NAME table has no popular name for the F-14B(U)"


# --- era availability -------------------------------------------------------

def _eras_for(key):
    svc = load_json("aircraft_service")[key]
    frm, to = svc[0], svc[1] or 9999
    return [e for e, cfg in load_json("eras").items()
            if frm <= cfg["window"][1] and to >= cfg["window"][0]]


def test_available_in_the_cold_war_and_modern():
    eras = _eras_for(KEY)
    assert "coldwar" in eras, "the F-14B(U) is still excluded from the Cold War"
    assert "modern" in eras, "widening the window must not cost it the modern era"


def test_the_real_f14b_is_untouched():
    """Only the community variant gets the product-decision window. The stock
    F-14B stays historically honest, and the F-14A remains the period-correct
    Cold War Tomcat."""
    # Stated as the product decision, not as an exact era list. The list was
    # `== ["modern"]` and broke when a fourth era arrived whose window the
    # F-14B's real service (1990-2006) legitimately overlaps — an assertion
    # that fails on CORRECT data teaches people to edit assertions.
    assert "coldwar" not in _eras_for("F_14B"), \
        "the stock F-14B has drifted into the Cold War; that is the F-14A's job"
    assert "coldwar" in _eras_for("F_14A_135_GR")


@pytest.mark.parametrize("era", ["coldwar", "modern"])
def test_it_builds_in_every_era_it_offers(era, tmp_path):
    out = str(tmp_path / f"{era}.miz")
    generate(Recipe.from_dict(dict(map="caucasus", era=era, aircraft=KEY,
                                   bb_ambient=False, seed=3)), out)
    assert Path(out).stat().st_size > 1000


def test_it_still_flies_off_the_deck_in_the_cold_war(tmp_path):
    out = str(tmp_path / "cv.miz")
    generate(Recipe.from_dict(dict(map="caucasus", era="coldwar", aircraft=KEY,
                                   bb_carrier=True, home_airbase="CARRIER",
                                   bb_ambient=False, seed=3)), out)
    import zipfile
    assert any(n.startswith("DTC/") for n in zipfile.ZipFile(out).namelist()), \
        "the F-14B(U) DTC sidecar stopped shipping"


# --- the noise this surfaced ------------------------------------------------

def test_a_pending_module_warns_once(tmp_path):
    """_resolve_aircraft runs several times per build, so the pending-module
    note used to be stamped four times — 500+ characters of a 900-character
    header budget spent saying one thing."""
    out = str(tmp_path / "w.miz")
    r = generate(Recipe.from_dict(dict(map="caucasus", era="coldwar",
                                       aircraft=KEY, bb_ambient=False, seed=3)), out)
    pend = [w for w in r["warnings"] if "verified DCS type id" in w]
    assert len(pend) == 1, f"the pending-module warning repeats {len(pend)} times"
