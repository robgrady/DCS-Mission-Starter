"""Formation departures — DCS 2.9.30's AI runway line-up — in the pattern.

Two branches, both proven. UNSUPPORTED (the build as shipped until a real
Mission-Editor file gives us the encoding): the recipe refuses the knob with
the reason, the API says so, the page hides the checkbox, and nothing in a
built mission changes. SUPPORTED (a stand-in encoding patched into
lineup.TASK): every departing pattern section is two aircraft, carries the
action on its takeoff waypoint, landings stay singles, the count still means
aircraft, the brief says so, and pydcs can load the file back.
"""
from ui_source import ui_source, server_source
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

import dcs                                                   # noqa: E402
import dcs.lua as lua                                        # noqa: E402
from dcs import task as dtask                                # noqa: E402
from missiongen import generate, lineup, pattern            # noqa: E402
from missiongen.recipe import Recipe, RecipeError           # noqa: E402

# A stand-in with the SHAPE the ME writes for an advanced waypoint action.
# It is not the real encoding and nothing outside this file ever sees it.
STANDIN = {"id": "WrappedAction",
           "params": {"action": {"id": "RunwayLineUpStandIn", "params": {"value": True}}}}


def _rc(**kw):
    return dict(map="caucasus", era="modern", aircraft="F_16C_50", seed=11,
                bb_pattern=True, bb_targets=False, bb_sams=False,
                bb_tanker=False, bb_awacs=False, bb_ambient=False, **kw)


def _build(tmp, **kw):
    out = tmp / "p.miz"
    res = generate(Recipe.from_dict(_rc(**kw)).validate(), str(out), brief_dir=str(tmp))
    raw = lua.loads(zipfile.ZipFile(out).read("mission").decode())["mission"]
    return out, raw, res


def _pattern_groups(raw):
    return [g for co in raw["coalition"].values() for c in co["country"].values()
            for k in ("plane", "helicopter") for g in c.get(k, {}).get("group", {}).values()
            if str(g.get("name", "")).startswith("Pattern ")]


def _is_departure(g):
    return g["route"]["points"][1]["type"] in ("TakeOffParking", "TakeOffParkingHot", "TakeOff")
# (points is a 1-based Lua table, so [1] is the first — the takeoff — waypoint)


def _tasks_at_takeoff(g):
    return list(g["route"]["points"][1]["task"]["params"]["tasks"].values())


@pytest.fixture()
def supported(monkeypatch):
    monkeypatch.setattr(lineup, "TASK", STANDIN)
    lineup.register()
    yield
    dtask.wrappedactions.pop("RunwayLineUpStandIn", None)


# --- unsupported: the shipped state -----------------------------------------

def test_shipped_build_has_no_verified_encoding_yet():
    """When this fails, DCS gave us the encoding — delete the test, keep the rest."""
    assert lineup.TASK is None and not lineup.supported()


def test_the_knob_is_refused_with_the_reason_when_unsupported():
    with pytest.raises(RecipeError, match="not been verified"):
        Recipe.from_dict(_rc(pattern_mode="takeoff", pattern_lineup=True))
    Recipe.from_dict(_rc(pattern_mode="takeoff", pattern_lineup=False))   # default path untouched


def test_apply_writes_nothing_when_unsupported():
    m = dcs.Mission()
    g = m.flight_group_inflight(m.country("USA"), "x", dcs.planes.F_16C_50,
                                dcs.mapping.Point(0, 0, m.terrain), 3000)
    before = [t.dict() for t in g.points[0].tasks]
    assert lineup.apply(g) is False
    assert [t.dict() for t in g.points[0].tasks] == before
    with pytest.raises(RuntimeError, match="not been verified"):
        lineup.task()


def test_departures_stay_singles_when_unsupported(tmp_path):
    out, raw, res = _build(tmp_path, pattern_mode="takeoff", pattern_count=4)
    gs = _pattern_groups(raw)
    assert len(gs) == 4 and all(len(g["units"]) == 1 for g in gs)
    assert "line up" not in Path(res["brief_md"]).read_text().lower()


def test_api_and_page_hide_the_knob_when_unsupported():
    from fastapi.testclient import TestClient
    import server.app as app_mod
    assert TestClient(app_mod.app).get("/api/options").json()["lineup_supported"] is False
    src = ui_source()
    assert 'id="pattern_lineup"' in src and "OPT.lineup_supported" in src, \
        "the knob must exist and be gated on the server's word"
    assert 'id="pattern_lineup_wrap" style="display:none"' in src, "hidden until the server says yes"
    assert "pattern_lineup:false" in src, "RECIPE_DEFAULTS must know the field or share links drop it"
    assert "r.pattern_lineup = !!(OPT && OPT.lineup_supported)" in src, "recipe() must send what the box says, gated"
    assert "getElementById('pattern_lineup')?.checked" in src
    assert "plu.checked = !!r.pattern_lineup" in src, "a share link must restore it"


# --- supported: proven through the stand-in ---------------------------------

def test_sections_pair_departures_and_count_aircraft():
    legs = ["takeoff"] * 4
    assert pattern._sections(legs, True) == [("takeoff", 2), ("takeoff", 2)]
    assert pattern._sections(["takeoff"] * 3, True) == [("takeoff", 2), ("takeoff", 1)]
    both = ["landing", "takeoff", "landing", "takeoff"]
    assert pattern._sections(both, True) == [("landing", 1), ("takeoff", 2), ("landing", 1)]
    assert pattern._sections(both, False) == [(l, 1) for l in both]
    assert sum(n for _, n in pattern._sections(both, True)) == 4, "count still means aircraft"


def test_every_departing_section_carries_the_action(supported, tmp_path):
    out, raw, res = _build(tmp_path, pattern_mode="both", pattern_count=4, pattern_lineup=True)
    gs = _pattern_groups(raw)
    deps = [g for g in gs if _is_departure(g)]
    lands = [g for g in gs if not _is_departure(g)]
    assert len(deps) == 1 and len(lands) == 2, [(g["name"], len(g["units"])) for g in gs]
    assert all(len(g["units"]) == 2 for g in deps), "a section is two aircraft"
    assert all(len(g["units"]) == 1 for g in lands), "landings stay singles"
    for g in deps:
        hits = [t for t in _tasks_at_takeoff(g)
                if t["id"] == "WrappedAction" and t["params"]["action"]["id"] == "RunwayLineUpStandIn"]
        assert len(hits) == 1, f"{g['name']}: {_tasks_at_takeoff(g)}"
        assert hits[0]["params"]["action"]["params"] == {"value": True}
    for g in lands:
        assert not any(t["id"] == "WrappedAction" and
                       t["params"]["action"]["id"] == "RunwayLineUpStandIn"
                       for t in _tasks_at_takeoff(g)), "a landing aircraft has no runway to line up on"
    assert sum(len(g["units"]) for g in gs) == 4
    brief = Path(res["brief_md"]).read_text()
    assert "4x" in brief and "line up on the runway" in brief
    assert res["stats"]["pattern"]["lineup"] is True and res["stats"]["pattern"]["aircraft"] == 4


def test_the_player_flight_is_never_touched(supported, tmp_path):
    out, raw, res = _build(tmp_path, pattern_mode="takeoff", pattern_count=2,
                           pattern_lineup=True, slots=2)
    player = next(g for co in raw["coalition"].values() for c in co["country"].values()
                  for g in c.get("plane", {}).get("group", {}).values()
                  if any(u.get("skill") in ("Player", "Client") for u in g["units"].values()))
    assert not any(t["id"] == "WrappedAction" and
                   t["params"]["action"]["id"] == "RunwayLineUpStandIn"
                   for p in player["route"]["points"].values()
                   for t in p["task"]["params"]["tasks"].values())


def test_pydcs_loads_the_file_back(supported, tmp_path):
    """pydcs KeyErrors on an id it has no class for — register() is what
    keeps our own round-trip and every pydcs-based reader working."""
    out, raw, res = _build(tmp_path, pattern_mode="takeoff", pattern_count=2, pattern_lineup=True)
    m = dcs.Mission()
    m.load_file(str(out))
    gs = [g for co in m.coalition.values() for c in co.countries.values()
          for g in c.plane_group if g.name.startswith("Pattern ")]
    assert gs and all(lineup.carries(g) for g in gs)


def test_off_by_default_even_when_supported(supported, tmp_path):
    out, raw, res = _build(tmp_path, pattern_mode="takeoff", pattern_count=2)
    assert all(len(g["units"]) == 1 for g in _pattern_groups(raw))
    assert Recipe.from_dict(_rc()).pattern_lineup is False
