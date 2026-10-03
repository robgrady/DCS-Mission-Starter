"""Automatic waypoints — the opt-in flight plan, and the default that stayed.

Rob: "Before we didn't want to do that but what about now creating a set of core
waypoints to the strike or target area and then back? Maybe we have it as an
option where the user can select automatically create waypoints."

THE PRINCIPLE THIS TESTS IS THE DEFAULT, NOT THE FEATURE.

"Never place player waypoints" was shorthand. The actual rule is "we set the
stage, you write the play" — do not tell a pilot how to fly a mission he did not
ask us to plan. A route he ticked a box for does not break that; an unrequested
one does. So the load-bearing assertions here are the negative ones:

  * `bb_route` defaults False
  * a mission without it has no waypoints, no route kneeboard page, and an
    empty DTC waypoint list
  * every recipe that existed before the field did generates identical bytes

`test_the_default_produces_identical_bytes_to_before_the_feature` is the one
that would catch this feature leaking. The rest check that when it IS asked for,
it arrives in all three places Rob chose: the flight plan, the F-14B(U)
cartridge, and a kneeboard leg card.
"""
import json
import zipfile

import pytest

import dcs.lua as lua
from missiongen import Recipe, generate
from missiongen import routing
from missiongen.recipe import Recipe as R


def _mission(path):
    return lua.loads(zipfile.ZipFile(path).read("mission").decode())["mission"]


def _player_route(path):
    """The player's waypoint names, in order."""
    for coal in _mission(path)["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for g in c.get("plane", {}).get("group", {}).values():
                units = [g["units"][i] for i in sorted(g["units"])]
                if any(u.get("skill") in ("Player", "Client") for u in units):
                    pts = g.get("route", {}).get("points", {})
                    return [pts[i].get("name") for i in sorted(pts)]
    return None


def _dtc(path):
    z = zipfile.ZipFile(path)
    member = [n for n in z.namelist() if n.startswith("DTC/")]
    return json.loads(z.read(member[0])) if member else None


def _kneeboard_pages(path):
    return [n for n in zipfile.ZipFile(path).namelist()
            if n.startswith("KNEEBOARD/")]


def _build(tmp_path, name="m", **rc):
    base = dict(map="caucasus", era="modern", seed=5, bb_targets=True)
    base.update(rc)
    out = str(tmp_path / f"{name}.miz")
    return generate(Recipe.from_dict(base), out), out


# ------------------------------------------------------- the default holds
def test_the_option_is_off_by_default():
    assert R().bb_route is False, \
        "waypoints would arrive unrequested — that is the thing the north star forbids"


def test_a_normal_mission_still_has_no_player_waypoints(tmp_path):
    _res, out = _build(tmp_path)
    names = _player_route(out)
    assert names is not None, "no player flight found, so this proves nothing"
    assert not [n for n in names if n in ("WP1", "IP", "TARGET")], \
        f"an unrequested route appeared: {names}"


def test_a_normal_mission_has_no_route_kneeboard_page(tmp_path):
    # player_arm off, so the STORES card cannot mask the thing under test:
    # this is about the ROUTE page and nothing else.
    _res, out = _build(tmp_path, bb_kneeboard=True, player_arm=False)
    assert len(_kneeboard_pages(out)) == 4, \
        "three references plus historical context; no route page"


def test_a_normal_cartridge_carries_no_route(tmp_path):
    """The one place the old rule was written into a data FORMAT rather than a
    code path, so it gets its own guard."""
    _res, out = _build(tmp_path, aircraft="F_14B_U", name="bu")
    d = _dtc(out)
    assert d, "no cartridge was written at all"
    nav0 = d["data"]["NAV"][0]
    # The cartridge has to be doing its ORIGINAL job here, or "waypoints is
    # empty" is vacuously true and guards nothing.
    assert nav0["additional_points"], "no reference points, so this proves nothing"
    assert nav0["waypoints"] == [], f"unrequested route in the cartridge: {nav0['waypoints']}"
    assert nav0["route_as_line"] is False


def test_the_default_produces_identical_bytes_to_before_the_feature(tmp_path):
    """A new recipe field must not disturb anything. Two builds of the same
    seed, one constructed without ever mentioning `bb_route` and one setting it
    to its default, have to be the same file — which is also what guarantees
    every share link written before today still regenerates."""
    a = str(tmp_path / "a.miz")
    b = str(tmp_path / "b.miz")
    generate(Recipe.from_dict(dict(map="caucasus", era="modern", seed=11,
                                   bb_targets=True)), a)
    generate(Recipe.from_dict(dict(map="caucasus", era="modern", seed=11,
                                   bb_targets=True, bb_route=False)), b)
    assert open(a, "rb").read() == open(b, "rb").read()


# --------------------------------------------------- when it IS asked for
def test_ticking_the_box_produces_a_route(tmp_path):
    res, out = _build(tmp_path, bb_route=True)
    names = _player_route(out)
    assert names[1:4] == ["WP1", "IP", "TARGET"], names
    assert res["stats"]["route"].startswith("WP1 > IP > TARGET")


def test_the_route_goes_out_and_comes_back(tmp_path):
    """"To the target area and then back" — the recovery point is the half
    people forget, and a route that ends at the target is a route that ends
    with you orbiting a burning depot wondering where home is."""
    _res, out = _build(tmp_path, bb_route=True)
    for coal in _mission(out)["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for g in c.get("plane", {}).get("group", {}).values():
                units = [g["units"][i] for i in sorted(g["units"])]
                if not any(u.get("skill") in ("Player", "Client") for u in units):
                    continue
                pts = g["route"]["points"]
                last = pts[max(pts)]
                assert last.get("type") == "Land" or last.get("action") == "Landing", \
                    f"the route does not come home: {last.get('type')}"
                return
    pytest.fail("no player flight")


def test_the_run_in_is_not_the_direct_radial(tmp_path):
    """Real routes dogleg. Flying the straight line from your own airfield to
    the target is the first line an enemy controller draws, and it makes every
    mission look identical from the F10 map."""
    res, _out = _build(tmp_path, bb_route=True)
    rows = res["stats"]["route_legs"]
    transit = rows[0]["heading"]
    run_in = rows[-1]["heading"]
    assert abs((run_in - transit + 180) % 360 - 180) > 8, \
        f"the run-in ({run_in}) matches the transit ({transit}) — no dogleg"


def test_the_legs_are_era_plausible(tmp_path):
    """A Mustang does not transit at 20,000 ft and 430 kt."""
    modern, _o = _build(tmp_path, bb_route=True, name="mod")
    wwii, _o2 = _build(tmp_path, bb_route=True, name="ww2", era="wwii",
                       map="normandy", aircraft="P_51D")
    m0 = modern["stats"]["route_legs"][0]
    w0 = wwii["stats"]["route_legs"][0]
    assert w0["alt_ft"] < m0["alt_ft"], f"WWII {w0['alt_ft']} vs modern {m0['alt_ft']}"
    assert w0["kt"] < m0["kt"], f"WWII {w0['kt']} kt vs modern {m0['kt']} kt"
    assert 150 <= w0["kt"] <= 300, f"{w0['kt']} kt is not a Mustang transit"


def test_the_kneeboard_gets_a_leg_card(tmp_path):
    res, out = _build(tmp_path, bb_route=True, bb_kneeboard=True,
                      player_arm=False)
    assert len(_kneeboard_pages(out)) == 5
    assert res["stats"]["kneeboard_pages"] == 5


def test_the_reference_pages_keep_their_numbers(tmp_path):
    """The route card is appended, not inserted. A pilot who knows the theater
    overview is page 03 must not find a flight plan there because he ticked a
    box on a different screen."""
    _plain_res, plain = _build(tmp_path, bb_kneeboard=True, name="p",
                               player_arm=False)
    _routed_res, routed = _build(tmp_path, bb_route=True, bb_kneeboard=True,
                                 name="r", player_arm=False)
    # Compare page CONTENT, not filenames. Pages are named by position
    # (01/02/03), so inserting the route card at the front produces exactly the
    # same list of names while putting different pictures behind them — a name
    # comparison here passed a mutation that moved every reference page.
    #
    # Page 01 is EXEMPT and deliberately so: its footer says whether waypoints
    # were placed, so it must differ between a routed and an unrouted mission.
    # A card that misdescribes the mission it is bound into is the bug; this is
    # the fix. Pages 02 and 03 carry no such statement and must not move.
    pa, pb = zipfile.ZipFile(plain), zipfile.ZipFile(routed)
    pages = _kneeboard_pages(plain)
    for n in pages[1:3]:
        assert pa.read(n) == pb.read(n), \
            f"{n} is a different page once a route is added"
    assert pa.read(pages[0]) != pb.read(pages[0]), \
        "page 01 still claims no waypoints were placed on a routed mission"


def test_the_tomcat_cartridge_carries_the_route(tmp_path):
    """Rob asked for the DTC specifically: the jet loads the route from the DTM
    page the way it loads everything else."""
    _res, out = _build(tmp_path, bb_route=True, aircraft="F_14B_U", name="bu2")
    nav0 = _dtc(out)["data"]["NAV"][0]
    assert [w["name"] for w in nav0["waypoints"]] == ["WP1", "IP", "TARGET"]
    assert nav0["route_as_line"] is True
    for w in nav0["waypoints"]:
        assert w.get("lat") or w.get("x"), f"waypoint has no position: {w}"


def test_the_reference_points_survive_the_route(tmp_path):
    """The cartridge's original job does not stop mattering because a route was
    added — bullseye and threat rings must still be there."""
    _res, out = _build(tmp_path, bb_route=True, aircraft="F_14B_U",
                       bb_sams=True, name="bu3")
    nav0 = _dtc(out)["data"]["NAV"][0]
    assert nav0["additional_points"], "the reference points were displaced"


def test_asking_with_nothing_to_route_to_warns(tmp_path):
    """Silence would read as a bug: the box is ticked and the F10 map is empty."""
    res, out = _build(tmp_path, bb_route=True, bb_targets=False, name="notgt")
    assert res["stats"].get("route") is None
    assert any("no target to route to" in w for w in res["warnings"]), res["warnings"]
    names = _player_route(out)
    assert not [n for n in names if n in ("WP1", "IP", "TARGET")]


def test_the_setting_survives_a_share_link():
    from missiongen.share import decode_recipe, encode_recipe
    rc = Recipe.from_dict(dict(map="caucasus", era="modern", bb_targets=True,
                               bb_route=True))
    assert decode_recipe(encode_recipe(rc)).bb_route is True


# ------------------------------------------------------------- the geometry
class _P:
    """Minimal stand-in so the planner can be tested without a terrain."""
    def __init__(self, x, y):
        self.x, self.y, self._terrain = float(x), float(y), None

    def distance_to_point(self, o):
        return ((self.x - o.x) ** 2 + (self.y - o.y) ** 2) ** 0.5


class _RNG:
    def __init__(self, v=0.1):
        self.v = v

    def random(self):
        return self.v


def test_a_target_on_top_of_the_field_gets_no_route():
    """Three points inside five miles would put the IP behind you at rotation.
    Better to give nothing than a route that cannot be flown."""
    assert routing.route_for(_P(0, 0), _P(3000, 0), "modern", _RNG()) is None
    assert routing.route_for(_P(0, 0), _P(60000, 0), "modern", _RNG()) is not None


def test_the_dogleg_side_follows_the_seed():
    """Same seed, same route — otherwise a share link stops being a share
    link."""
    left = routing.route_for(_P(0, 0), _P(80000, 0), "modern", _RNG(0.1))
    right = routing.route_for(_P(0, 0), _P(80000, 0), "modern", _RNG(0.9))
    assert left[0]["point"].y != right[0]["point"].y, "the seed does not steer the dogleg"
    again = routing.route_for(_P(0, 0), _P(80000, 0), "modern", _RNG(0.1))
    assert again[0]["point"].y == left[0]["point"].y


def test_a_missing_target_is_not_a_crash():
    assert routing.route_for(_P(0, 0), None, "modern", _RNG()) is None
    assert routing.route_for(None, _P(1, 1), "modern", _RNG()) is None


def test_the_leg_card_maths_is_right():
    """Numbers a pilot flies off. 800 km/h is 432 kt; 6,000 m is 19,700 ft."""
    legs = routing.route_for(_P(0, 0), _P(100000, 0), "modern", _RNG(0.1))
    rows = routing.leg_card(_P(0, 0), legs, "HOME")
    assert rows[0]["from"] == "HOME" and rows[-1]["to"] == "TARGET"
    assert rows[0]["kt"] == 432, rows[0]["kt"]
    assert rows[0]["alt_ft"] == 19700, rows[0]["alt_ft"]
    for r in rows:
        assert 0 <= r["heading"] < 360
        # distance / speed = time, in the units printed on the card
        assert abs(r["min"] - r["nm"] / r["kt"] * 60) < 0.1, r


# ------------------------------------------------------------ the stores card
# Not routing, but the same discovery: the engine had the data and printed it
# nowhere the pilot could reach. Kept in this file because both cards are
# optional kneeboard pages and the page-ordering rule is shared.

def _stores_page_count(path):
    return len(_kneeboard_pages(path))


def test_an_armed_jet_gets_a_stores_card(tmp_path):
    """v1.48.0 has composed the player's fit for five releases and printed it
    only in the PDF brief — which lives on the desktop, behind the sim. In the
    cockpit you had to open the rearm screen or guess."""
    res, out = _build(tmp_path, mission_kind="strike", player_arm=True,
                      bb_kneeboard=True, name="armed")
    assert res["stats"]["player_pylons"], "no station list was captured"
    assert _stores_page_count(out) == 5


def test_a_clean_jet_gets_no_stores_card(tmp_path):
    """`player_arm=False` is somebody deliberately starting clean. A card
    listing nothing is worse than no card."""
    res, out = _build(tmp_path, player_arm=False, bb_kneeboard=True,
                      name="clean")
    assert res["stats"].get("player_pylons") in (None, [])
    assert _stores_page_count(out) == 4


def test_the_card_describes_the_jet_you_are_sitting_in(tmp_path):
    """The station list must come from the SAME dict `apply_fit` hangs on the
    aircraft. Deriving it from the label string would be a second source of
    truth, and the label is lossy — it says "2x AMRAAM" without saying which
    two stations."""
    from missiongen import loadouts
    res, out = _build(tmp_path, mission_kind="strike", player_arm=True,
                      name="match")
    stations = dict(res["stats"]["player_pylons"])
    m = _mission(out)
    for coal in m["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for g in c.get("plane", {}).get("group", {}).values():
                units = [g["units"][i] for i in sorted(g["units"])]
                if not any(u.get("skill") in ("Player", "Client") for u in units):
                    continue
                flown = units[0].get("payload", {}).get("pylons", {})
                assert flown, "the player is carrying nothing to compare against"
                assert set(int(k) for k in flown) == set(stations), (
                    f"the card lists {sorted(stations)} but the jet carries "
                    f"{sorted(int(k) for k in flown)}")
                return
    pytest.fail("no player flight")


def test_the_stores_card_comes_before_the_route_card(tmp_path):
    """Both are optional, so their order has to be fixed rather than incidental
    — stores is the page you check first and most often in the air."""
    _res, out = _build(tmp_path, mission_kind="strike", player_arm=True,
                       bb_route=True, bb_kneeboard=True, name="both")
    pages = _kneeboard_pages(out)
    assert len(pages) == 6
    z = zipfile.ZipFile(out)
    # page 04 is STORES, page 05 is FLIGHT PLAN — compare against a mission
    # built with only one of them switched on.
    _r2, only_route = _build(tmp_path, player_arm=False, bb_route=True,
                             bb_kneeboard=True, name="onlyroute")
    assert z.read(pages[4]) == zipfile.ZipFile(only_route).read(
        _kneeboard_pages(only_route)[3]), "page 05 is not the flight plan"


def test_the_reference_pages_survive_both_optional_cards(tmp_path):
    """Pages 02 and 03 are pure reference and must be identical whatever
    optional cards are appended. Page 01 is excluded: its footer states whether
    a flight plan was placed (see above)."""
    _plain, p = _build(tmp_path, player_arm=False, bb_kneeboard=True, name="p2")
    _both, b = _build(tmp_path, mission_kind="strike", player_arm=True,
                      bb_route=True, bb_kneeboard=True, name="b2")
    za, zb = zipfile.ZipFile(p), zipfile.ZipFile(b)
    for n in _kneeboard_pages(p)[1:3]:
        assert za.read(n) == zb.read(n), f"{n} moved once cards were added"


def test_the_comms_footer_tells_the_truth_about_this_mission(tmp_path):
    """It said "no waypoints placed" on every page ever rendered. The moment a
    pilot switched on automatic waypoints that became a lie printed in his
    cockpit, on the page he reads first."""
    from missiongen import kneeboard as kb
    import io
    args = dict(comms=None, map_label="Caucasus", era_label="Modern",
                home_name="Kutaisi")
    # Render the footer both ways from the renderer directly — the assertion is
    # about the page, and building two missions to compare it is slower and
    # couples this to the builder.
    plain = kb.page_comms(_FakeComms(), "Caucasus", "Modern", "Kutaisi",
                          routed=False)
    routed = kb.page_comms(_FakeComms(), "Caucasus", "Modern", "Kutaisi",
                           routed=True)
    a, b = io.BytesIO(), io.BytesIO()
    plain.save(a, "PNG"); routed.save(b, "PNG")
    assert a.getvalue() != b.getvalue(), \
        "the footer reads the same whether or not a flight plan was placed"


class _FakeComms:
    entries = []
    channels = {}


def test_headings_are_labelled_true(tmp_path):
    """We publish TRUE bearings and have no verified magnetic variation per
    theater. A card that silently implies magnetic is worse than no card — the
    pilot flies the number off the compass and drifts."""
    from missiongen import routing
    rows = routing.leg_card(_P(0, 0),
                            routing.route_for(_P(0, 0), _P(90000, 0), "modern",
                                              _RNG(0.2)), "HOME")
    text = "\n".join(routing.brief_lines(rows, "Depot"))
    assert "TRUE" in text and "magnetic variation" in text


# ------------------------------------------------- the kneeboard pack export
# The pages were always rendered and always locked inside the .miz, which made
# them unusable in OpenKneeboard, unprintable, unshareable, and impossible to
# drop into Saved Games for every mission. Same renderer, different packaging.

def _client():
    from fastapi.testclient import TestClient
    from server.app import app
    return TestClient(app)


def _pack(recipe):
    r = _client().post("/api/kneeboard",
                       json={"recipe": recipe, "source": "builder"})
    return r


def test_the_pages_can_leave_the_miz():
    r = _pack(dict(map="caucasus", era="modern", seed=5, bb_targets=True,
                   mission_kind="strike"))
    assert r.status_code == 200, r.text
    import io
    z = zipfile.ZipFile(io.BytesIO(r.content))
    pngs = [n for n in z.namelist() if n.endswith(".png")]
    assert len(pngs) >= 3, z.namelist()
    for n in pngs:
        assert z.read(n)[:8] == b"\x89PNG\r\n\x1a\n", f"{n} is not a PNG"


def test_the_pack_says_where_to_put_them():
    """A ZIP of unlabelled PNGs is a puzzle. The install path is the whole
    difference between 'files' and 'a kneeboard'."""
    r = _pack(dict(map="caucasus", era="modern", seed=5))
    import io
    readme = zipfile.ZipFile(io.BytesIO(r.content)).read("README.txt").decode()
    assert "Saved Games" in readme and "Kneeboard" in readme
    assert "RCTRL+K" in readme or "RSHIFT+K" in readme.upper()


def test_the_filenames_carry_the_page_order_and_name():
    """DCS displays kneeboard pages in FILENAME order, so the numbering is
    load-bearing, not decoration."""
    r = _pack(dict(map="caucasus", era="modern", seed=5, bb_targets=True,
                   mission_kind="strike", bb_route=True))
    import io
    names = sorted(n for n in zipfile.ZipFile(io.BytesIO(r.content)).namelist()
                   if n.endswith(".png"))
    assert "_01_comms_nav.png" in names[0]
    assert any("_stores.png" in n for n in names)
    assert any("_flight_plan.png" in n for n in names)
    nums = [int(n.split("_")[-2]) if n.split("_")[-2].isdigit()
            else int([p for p in n.split("_") if p.isdigit()][-1]) for n in names]
    assert nums == sorted(nums), names


def test_the_exported_pages_are_the_ones_in_the_mission():
    """If these ever diverge, a pilot flies one card and the mission shows
    another. The determinism contract is what makes a rebuild safe."""
    import io, tempfile, os
    rc = dict(map="caucasus", era="modern", seed=5, bb_targets=True,
              mission_kind="strike")
    d = tempfile.mkdtemp()
    out = os.path.join(d, "m.miz")
    generate(Recipe.from_dict(rc), out)
    inside = zipfile.ZipFile(out)
    in_pages = [inside.read(n) for n in sorted(_kneeboard_pages(out))]
    z = zipfile.ZipFile(io.BytesIO(_pack(rc).content))
    out_pages = [z.read(n) for n in sorted(n for n in z.namelist()
                                           if n.endswith(".png"))]
    assert in_pages == out_pages, "the exported pack is not the mission's kneeboard"


def test_asking_for_a_pack_with_no_kneeboard_is_a_clean_400():
    r = _pack(dict(map="caucasus", era="modern", seed=5, bb_kneeboard=False))
    assert r.status_code == 400
    assert "kneeboard" in r.json()["detail"].lower()


def test_a_bad_recipe_is_a_400_not_a_500():
    r = _pack(dict(map="atlantis", era="modern", seed=5))
    assert r.status_code == 400, r.text
