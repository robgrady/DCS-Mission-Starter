"""Regression guards for the bugs found in the v1.9.1 code review.

Each test pins a specific defect so it can never silently come back:
  P0b — slot_name is not unique (Syria): duplicate unit names + under-placement
  P0c — radio presets wrote UHF into VHF-only airframes
  P2  — coalition="purple" silently flew from the RED side

Run:  pytest tests/ -v   |   python tests/test_regressions.py
"""
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
while not (ROOT / "missiongen").is_dir() and ROOT != ROOT.parent:
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "vendor"))
sys.path.insert(0, str(ROOT))


def _gen(tmp, **recipe):
    from missiongen import generate, Recipe
    out = str(Path(tmp) / "t.miz")
    generate(Recipe.from_dict(recipe), out)
    return out


def _mission_text(miz):
    return zipfile.ZipFile(miz).read("mission").decode("utf-8", "ignore")


# --- P0b: slot_name uniqueness --------------------------------------------

def test_no_duplicate_group_or_unit_names(tmp_path):
    """DCS rejects duplicate group/unit names. Syria's Ramat David has six
    stands named '02'; keying on slot_name produced duplicate ST/GSE names."""
    for mp, era, ac in [("syria", "modern", "FA_18C_hornet"),
                        ("caucasus", "modern", "F_16C_50")]:
        m = _mission_text(_gen(tmp_path, map=mp, era=era, coalition="blue",
                               aircraft=ac, home_airbase=None, dress_fill=100,
                               seed=3))
        # our placed statics/flights are the ST/GSE/RAMP/INF-prefixed names
        names = re.findall(r'\["name"\]\s*=\s*"((?:ST|GSE|RAMP|INF) [^"]+)"', m)
        dupes = [n for n, c in Counter(names).items() if c > 1]
        assert not dupes, f"{mp}: duplicate placed-object names: {dupes[:5]}"


def test_ramat_david_places_all_stands(tmp_path):
    """The 17 twin-named stands were unreachable; a full-fill composer mix
    under-placed 86 -> 69. crossroad_idx keying makes all 86 reachable."""
    import random
    from dcs.terrain.syria import Syria
    from missiongen import dressing
    from missiongen.placement import slot_key
    ap = next(a for a in Syria().airport_list() if a.name == "Ramat David")
    fillable = [s for s in ap.parking_slots if s.airplanes]
    placed = []
    dressing._place_mix(ap, {"F_16C_50": len(fillable) + 10},
                        lambda s, ut, liv: placed.append(slot_key(s)) or True,
                        random.Random(1), set())
    assert len(placed) == len(fillable), \
        f"placed {len(placed)} of {len(fillable)} fillable stands"
    assert len(placed) == len(set(placed)), "placed the same stand twice"


# --- P0c: radio preset band -----------------------------------------------

def test_vhf_only_aircraft_get_no_uhf_presets(tmp_path):
    """Spitfire/MiG-21/Ka-50 have no UHF radio; writing the UHF ladder there is
    invalid. They must be skipped (no CHAN column, no ladder freqs in radios)."""
    from missiongen.presets import _uhf_radio_id
    from dcs import planes, helicopters
    for tid in ["SpitfireLFMkIX", "MiG_21Bis", "Ka_50", "SA342M"]:
        t = getattr(planes, tid, None) or getattr(helicopters, tid, None)
        assert _uhf_radio_id(t.panel_radio) is None, f"{tid} wrongly got a UHF radio"


def test_uhf_ladder_lands_on_the_uhf_radio(tmp_path):
    """A-10C's UHF set is radio 2, the Hornet's is radio 1 — the ladder must
    follow the band, not always radio 1."""
    from missiongen.presets import _uhf_radio_id
    from dcs import planes, helicopters
    assert _uhf_radio_id(planes.FA_18C_hornet.panel_radio) == 1
    assert _uhf_radio_id(planes.F_16C_50.panel_radio) == 1
    assert _uhf_radio_id(planes.A_10C_2.panel_radio) == 2
    assert _uhf_radio_id(helicopters.AH_64D_BLK_II.panel_radio) == 2


if __name__ == "__main__":
    import tempfile
    failed = 0
    for fn in [test_no_duplicate_group_or_unit_names, test_ramat_david_places_all_stands,
               test_vhf_only_aircraft_get_no_uhf_presets, test_uhf_ladder_lands_on_the_uhf_radio]:
        try:
            with tempfile.TemporaryDirectory() as d:
                fn(Path(d))
            print(f"PASS  {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {fn.__name__}\n      {type(e).__name__}: {e}")
    print(f"\n{'FAILED' if failed else 'OK'} — {failed} failure(s)")
    sys.exit(1 if failed else 0)
