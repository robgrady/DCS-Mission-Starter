"""The comm table: a default the pilot can overwrite, and nothing downstream
allowed to disagree with it.

Rob, flying the F-14B(U) from the front seat: the card said CH 2 and the
cockpit did not. The fix for the module is the module's; ours is to make the
plan the pilot's — a table with a default column and a "this mission" column
(missiongen/commplan.py) — and to prove that a changed cell reaches EVERY
place a frequency lives: the station's radio, the boat (in hertz), each UHF
set in the player's cockpit, the card and the kneeboard. Each refusal rule is
proven by breaking it.
"""
import sys
import zipfile
from pathlib import Path

import pytest

import dcs.lua as lua
from missiongen import Recipe, generate
from missiongen import commplan as cp
from missiongen.comms import CommsPlan
from missiongen.recipe import RecipeError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
from test_comms_truth import _build, _named, _groups, _mission  # noqa: E402

F14 = cp.unit_type_for("F_14B")
P51 = cp.unit_type_for("P_51D_30_NA")


def _errs(v):
    return {e["key"]: e["msg"] for e in v["errors"]}


# --- the rules, one break each ----------------------------------------------

def test_guard_is_never_editable():
    v = cp.validate({"guard": 250.0}, F14)
    assert not v["ok"] and "regulation" in _errs(v)["guard"]
    # ...and even a caller that bypasses validate cannot move it
    assert CommsPlan({"guard": 250.0}).freq("guard") == 243.0


def test_off_raster_is_refused_and_the_nearest_channel_is_named():
    v = cp.validate({"tanker": 271.51}, F14)
    assert "271.500" in _errs(v)["tanker"] and "25 kHz" in _errs(v)["tanker"]
    assert cp.validate({"tanker": 271.5}, F14)["ok"]


def test_out_of_band_is_refused_unless_the_airframe_can_tune_it():
    assert "outside UHF" in _errs(cp.validate({"flight_common": 124.0}, F14))["flight_common"]
    assert cp.validate({"flight_common": 124.0}, P51)["ok"], \
        "a Mustang's VHF flight frequency is a Mustang's business"
    assert not cp.validate({"tanker": 400.0}, F14)["ok"], "400.000 is past the band"
    assert cp.validate({"tanker": 399.975}, F14)["ok"], "the top channel is in it"
    assert not cp.validate({"tanker": 500.0}, F14)["ok"]
    assert not cp.validate({"tanker": 124.0}, None)["ok"], "no airframe: UHF only"


def test_unknown_row_and_non_numbers_are_refused_by_name():
    v = cp.validate({"texaco": 271.5, "tanker": "abc", "awacs": True, "cap": float("nan")}, F14)
    e = _errs(v)
    assert "texaco" in e and "Rows:" in e["texaco"]
    assert "not a frequency" in e["tanker"]
    assert "not a frequency" in e["awacs"], "True is not 1.0 MHz"
    assert "cap" in e


def test_a_row_moved_onto_guard_is_refused():
    assert "Guard" in _errs(cp.validate({"tactical": 243.0}, F14))["tactical"]


def test_default_values_are_not_overrides():
    v = cp.validate({"tanker": 253.625, "awacs": 251.475}, F14)
    assert v["ok"] and v["clean"] == {}
    assert cp.validate({"tanker": None, "awacs": ""}, F14)["clean"] == {}, \
        "an emptied cell is back-to-default, not an error"


def test_co_channel_is_warned_not_refused():
    v = cp.validate({"tanker": 251.475}, F14)          # AWACS's default
    assert v["ok"] and v["clean"] == {"tanker": 251.475}
    assert v["warnings"] and "AWACS" in v["warnings"][0]["msg"]
    assert not cp.validate({"tanker": 271.5}, F14)["warnings"]


def test_not_a_table_is_refused():
    assert not cp.validate([271.5], F14)["ok"]
    assert cp.validate(None, F14) == {"ok": True, "clean": {}, "errors": [], "warnings": []}


# --- the table itself -------------------------------------------------------

def test_rows_say_which_kind_each_row_is():
    rows = {r["key"]: r for r in cp.rows(F14, {"bb_tanker": True, "bb_awacs": False,
                                               "bb_carrier": False})}
    assert rows["guard"]["kind"] == "engine" and not rows["guard"]["editable"]
    assert rows["flight_common"]["kind"] == "engine" and rows["flight_common"]["editable"]
    assert rows["tanker"]["kind"] == "generated" and rows["tanker"]["channel"] == 4
    assert rows["carrier"]["kind"] == "absent" and not rows["carrier"]["held"]
    assert rows["awacs"]["kind"] == "absent"
    assert rows["aew"]["channel"] == 3, "AEW takes CH 3 when there is no AWACS"
    assert cp.rows(F14, {"bb_awacs": True})[[r["key"] for r in cp.rows()].index("aew")]["channel"] == 8


def test_held_follows_the_airframes_uhf_radios():
    assert [r["id"] for r in cp.radios_for(F14)] == [1, 2]
    assert cp.radios_for(P51) == []
    assert all(not r["held"] for r in cp.rows(P51)), "a Mustang gets a card, not presets"
    assert all(r["held"] for r in cp.rows(F14)), "the Tomcat holds every row on both sets"
    assert cp.radios_for(cp.unit_type_for("F_14B_U")) == cp.radios_for(F14)


# --- Recipe: refuse early, canonicalize ------------------------------------

def test_recipe_refuses_a_bad_table_naming_the_row():
    with pytest.raises(RecipeError, match="Tanker.*271.510"):
        Recipe.from_dict(dict(map="caucasus", era="modern", aircraft="F_14B",
                              comms={"tanker": 271.51}))


def test_recipe_drops_a_table_of_defaults():
    r = Recipe.from_dict(dict(map="caucasus", era="modern", aircraft="F_14B",
                              comms={"tanker": 253.625}))
    assert r.comms is None, "a table of defaults is the same recipe as no table"
    r = Recipe.from_dict(dict(map="caucasus", era="modern", aircraft="F_14B",
                              comms={"tanker": 271.5, "awacs": 251.475}))
    assert r.comms == {"tanker": 271.5}


# --- the world follows the table --------------------------------------------

@pytest.fixture(scope="module")
def custom(tmp_path_factory):
    tp = tmp_path_factory.mktemp("custom")
    m, rows = _build(tp, map="caucasus", era="modern", aircraft="F_14B",
                     bb_tanker=True, bb_awacs=True, seed=4,
                     comms={"tanker": 271.5, "awacs": 299.0, "flight_common": 310.0,
                            "tactical": 277.25})
    return m, rows


def test_every_station_moves_to_the_pilots_number(custom):
    m, rows = custom
    card = {r[0]: r for r in rows}
    assert float(card["Tanker"][2]) == 271.5 and float(card["AWACS"][2]) == 299.0
    assert _named(m, "texaco", "plane")["frequency"] == pytest.approx(271.5)
    assert _named(m, "overlord", "plane")["frequency"] == pytest.approx(299.0)
    player = next(g for g in _groups(m, "plane")
                  if any(u.get("skill") in ("Player", "Client") for u in g["units"].values()))
    assert player["frequency"] == pytest.approx(310.0), "the flight's own radio follows"


def test_every_uhf_set_in_the_cockpit_holds_every_card_channel(custom):
    """The hardened form of test_player_presets_match_the_card: not `any`
    radio — EVERY programmed UHF set, named by channel, with its name."""
    m, rows = custom
    unit = next(u for g in _groups(m, "plane") for u in g["units"].values()
                if u.get("skill") in ("Player", "Client"))
    radios = unit["Radio"]
    assert sorted(radios) == [1, 2]
    for agency, cs_, freq, chan, *_ in rows:
        if not chan.startswith("CH"):
            continue
        ch = int(chan[2:])
        for rid, r in radios.items():
            assert r["channels"][ch] == pytest.approx(float(freq)), \
                f"{agency}: card CH{ch}={freq}, radio {rid} holds {r['channels'][ch]}"
            assert r["channelsNames"][ch] == agency
    for rid, r in radios.items():
        last = max(r["channels"])
        assert r["channels"][last] == 243.0 and r["channelsNames"][last] == "Guard"


def test_the_card_marks_what_was_overwritten(custom):
    m, rows = custom
    notes = {r[0]: r[-1] for r in rows}
    assert "custom" in notes["Tanker"] and "custom" in notes["AWACS"]
    assert "custom" in notes["Flight"] and "custom" in notes["Tactical"]
    assert "custom" not in notes["Guard"]


def test_the_boat_follows_in_hertz(tmp_path):
    m, rows = _build(tmp_path, map="caucasus", era="coldwar", aircraft="F_14A_135_GR",
                     bb_carrier=True, home_airbase="CARRIER", seed=6,
                     comms={"carrier": 277.0, "angel": 281.5})
    assert next(float(r[2]) for r in rows if r[0] == "Carrier") == 277.0
    ships = [u for g in _groups(m, "ship") for u in g["units"].values()]
    assert ships and all(round(u["frequency"] / 1e6, 3) == pytest.approx(277.0) for u in ships)
    assert _named(m, "angel", "plane", "helicopter")["frequency"] == pytest.approx(281.5)


def test_the_standard_ladder_is_untouched_without_a_table(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    a = _build(tmp_path / "a", map="caucasus", era="modern", aircraft="F_14B",
               bb_tanker=True, bb_awacs=True, seed=4)[1]
    b = _build(tmp_path / "b", map="caucasus", era="modern", aircraft="F_14B",
               bb_tanker=True, bb_awacs=True, seed=4, comms={"tanker": 253.625})[1]
    assert a == b and not any("custom" in r[-1] for r in a)
    plan = CommsPlan()
    assert "standard ladder" in plan.card() and "custom" not in plan.card()
    assert "custom ladder" in CommsPlan({"tanker": 271.5}).card()


def test_stats_name_the_overrides(tmp_path):
    out = str(tmp_path / "s.miz")
    res = generate(Recipe.from_dict(dict(map="caucasus", era="modern", aircraft="F_14B",
                                         bb_ambient=False, seed=4,
                                         comms={"tanker": 271.5})), out,
                   brief_dir=str(tmp_path))
    assert res["stats"]["comms_custom"] == ["Tanker 271.500 (default 253.625)"]


# --- the API and the page ---------------------------------------------------

@pytest.fixture()
def client():
    from fastapi.testclient import TestClient
    import server.app as app_mod
    return TestClient(app_mod.app)


def test_api_describes_the_table_for_the_airframe(client):
    d = client.get("/api/commplan", params={"aircraft": "F_14B_U", "bb_awacs": "false"}).json()
    assert [r["id"] for r in d["radios"]] == [1, 2] and d["aircraft_known"]
    rows = {r["key"]: r for r in d["rows"]}
    assert rows["awacs"]["kind"] == "absent" and rows["aew"]["channel"] == 3
    assert rows["tanker"]["held"] and not rows["guard"]["editable"]
    d = client.get("/api/commplan", params={"aircraft": "P_51D_30_NA"}).json()
    assert d["radios"] == [] and not any(r["held"] for r in d["rows"])


def test_api_validate_matches_recipe_validate(client):
    d = client.post("/api/commplan/validate",
                    json={"comms": {"tanker": 271.51, "guard": 250}, "aircraft": "F_14B"}).json()
    assert not d["ok"] and {e["key"] for e in d["errors"]} == {"tanker", "guard"}
    # the airframe widens the band exactly as Recipe.validate does
    ok = client.post("/api/commplan/validate",
                     json={"comms": {"flight_common": 124.0}, "aircraft": "P_51D_30_NA"}).json()
    assert ok["ok"] and ok["clean"] == {"flight_common": 124.0}
    assert not client.post("/api/commplan/validate",
                           json={"comms": {"flight_common": 124.0}}).json()["ok"]
    r = client.post("/api/generate", json={"recipe": dict(
        map="caucasus", era="modern", aircraft="F_14B", comms={"tanker": 271.51})})
    assert r.status_code == 400 and "Tanker" in r.json()["detail"] and "271.500" in r.json()["detail"]


def test_the_page_carries_the_table():
    src = (ROOT / "frontend" / "index.html").read_text()
    assert 'id="sec_comms"' in src and 'id="commrows"' in src
    assert 'comms:null}' in src, "RECIPE_DEFAULTS must know the field or share links drop it"
    assert "r.comms = commOverrides();" in src, "recipe() must carry the table"
    assert "setCommOverrides(r.comms, true);" in src, "a share link must restore and unfold it"
    assert "/api/commplan/validate" in src and "'/api/commplan?'" in src
    assert "ms_commprofiles" in src, "profiles live in this browser"
    screens = src.split("const SCREENS = [")[1].split("\n];")[0]
    assert '"sec_comms"' in screens, "not on any screen"
