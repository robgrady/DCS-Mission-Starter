"""Era-aware skins are emitted only for the exact compatible aircraft model."""
import random
import zipfile

import dcs.lua as lua
import pytest

from missiongen import Recipe, generate
from missiongen import dressing


@pytest.mark.parametrize("style", ["squadron", "aggressors", "random"])
def test_coldwar_stock_phantom_does_not_leave_skin_to_dcs(style):
    rng = random.Random(7)
    before = rng.getstate()
    assert dressing._pick_livery("F-4E", "USA", rng, style,
                                 era="coldwar") == "af standard"
    assert rng.getstate() == before


@pytest.mark.parametrize("type_id, country, era, style", [
    ("F-4E", "USA", "modern", "squadron"),
    ("F-4E", "Iran", "coldwar", "squadron"),
    ("F-4E", "USA", "coldwar", "clean"),
    ("F-16C_50", "USA", "coldwar", "squadron"),
])
def test_partial_verification_never_enables_unrelated_guessed_skins(type_id, country, era, style):
    assert not dressing.livery_pack_verified()
    assert dressing._pick_livery(type_id, country, random.Random(7), style, era=era) is None


def test_heatblur_texture_is_never_borrowed_by_the_stock_model():
    skin = dressing._pick_livery("F-4E-45MC", "USA", random.Random(7), era="coldwar")
    assert skin == "421st_TFS_SEA_68-336"
    assert skin not in dressing._verified_static_liveries("F-4E", "USA", "coldwar")


def test_installed_pack_can_describe_different_period_skins(monkeypatch):
    pack = {"_verified": True, "types": {"TEST": {
        "USA": ["wrong-period"], "player": {"modern": ["player-only"]},
        "static": {"coldwar": {"USA": ["sea"]}, "modern": {"USA": ["gray"]}}}}}
    monkeypatch.setattr(dressing, "_LIVERY_RAW", pack)
    monkeypatch.setattr(dressing, "_LIVERY_PACK", None)
    rng = random.Random(7)
    assert dressing._pick_livery("TEST", "USA", rng, era="coldwar") == "sea"
    assert dressing._pick_livery("TEST", "USA", rng, "random", era="modern") == "gray"
    assert dressing._pick_livery("TEST", "USA", rng, era="ww2") is None


def test_real_mission_stock_phantom_statics_have_a_compatible_skin(tmp_path):
    path = tmp_path / "phantoms.miz"
    generate(Recipe.from_dict({"map": "nevada", "era": "coldwar", "seed": 7,
        "aircraft": "F_4E_45MC", "dress_mix": {"F_4E": 4}, "bb_ambient": False,
        "bb_kneeboard": False}), str(path))
    with zipfile.ZipFile(path) as z:
        m = lua.loads(z.read("mission").decode())["mission"]
    found = []
    for c in m["coalition"]["blue"]["country"].values():
        if c["name"] != "USA":
            continue
        for g in c.get("static", {}).get("group", {}).values():
            for u in g["units"].values():
                if u["type"] == "F-4E":
                    found.append(u)
                    assert u["livery_id"] == "af standard"
    assert len(found) >= 4
