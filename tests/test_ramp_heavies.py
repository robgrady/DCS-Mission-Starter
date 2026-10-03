"""Tankers and AWACS have to be able to park.

Rob's report: "when I generate a new mission for Nellis, it often doesn't have
many AWACs or Tankers on the field." Measured before the fix, "often" was
generous — across eight seeds a default Nevada mission put **zero** parked
tankers or AWACS on any ramp on the map, and 0-1 heavy aircraft of any kind in
total. Cold War Germany managed 0-2 across fifteen airfields. Normandy: zero.

Three independent causes, each of which is pinned below:

  1. A stand counted as heavy-capable if `slot.large or (length >= 60 and
     width >= 55)`. NTTR sets `large` on NOTHING — Nellis has 247 stands and the
     flag is False on every one — so everything rode on the 60x55 fallback,
     which exactly six Nellis stands passed. The threshold was also
     airframe-blind: it refused a C-130 a stand it fits and would have offered a
     B-52 one it does not. Now the real pydcs box is checked against the real
     stand box.
  2. Heavy-capable stands were shared with the fighter pool, which won them
     twice over — pool weights about 11 fighter to 8 heavy, and a fighter block
     is 4-8 deep against 2-3. One F-16 block could swallow the lot.
  3. Nevada dressed Nellis with the generic `usaf` ramp. The `red_flag` theme —
     literally "Nellis surge ramp", the only blue theme carrying an E-3A —
     existed in both eras and the map used neither.

The temptation with a fix like this is to test the knob. The knob is the least
interesting part: what matters is that a Nellis mission has a tanker on it, so
most of this file builds missions and counts what is standing on the ramp.
"""
from ui_source import ui_source, server_source
import collections
import zipfile

import pytest

import dcs.lua as lua
from dcs import planes
from missiongen import Recipe, generate
from missiongen.dressing import RAMP_HEAVIES, STAND_TOLERANCE, stand_fits
from missiongen.resolver import load_json

# Tankers and AWACS specifically — the thing Rob asked about. Kept apart from
# the general heavy set because "some big aircraft parked" is not the same
# answer as "a tanker is on the ramp".
TANKER_AWACS = {"KC-135", "KC135MPRS", "KC-130", "E-3A", "E-2C", "IL-78M", "A-50"}
HEAVY = TANKER_AWACS | {"C-130", "C-17A", "B-1B", "B-52H", "S-3B",
                        "IL-76MD", "An-26B", "C-47", "Ju-88A-4"}

NEVADA_FIELDS = ("Nellis", "Creech", "Groom Lake", "Tonopah Test Range",
                 "Tonopah", "Beatty", "Lincoln County", "Pahute Mesa",
                 "Mesquite", "McCarran")


def _mission(path):
    return lua.loads(zipfile.ZipFile(path).read("mission").decode())["mission"]


def _statics_by_field(m, fields=NEVADA_FIELDS):
    """{field name: Counter(type)} for parked aircraft statics.

    Group names carry the airfield, which is the only handle on "what is at
    Nellis" — coordinates would work too and would break the first time a
    terrain shifts.
    """
    out = collections.defaultdict(collections.Counter)
    for coal in m["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for ctry in coal.get("country", {}).values():
            for g in ctry.get("static", {}).get("group", {}).values():
                name = g.get("name", "")
                field = next((f for f in fields if f in name), None)
                if field is None:
                    continue
                for u in g.get("units", {}).values():
                    out[field][u.get("type")] += 1
    return out


def _build(tmp_path, seed, **rc):
    out = str(tmp_path / f"n{seed}.miz")
    base = dict(map="nevada", era="modern", aircraft="FA_18C_hornet",
                home_airbase="Nellis", bb_ambient=False, seed=seed)
    base.update(rc)
    generate(Recipe.from_dict(base), out)
    return _statics_by_field(_mission(out))


SEEDS = range(6)


# --- cause 1: the stand test ------------------------------------------------

def test_nttr_flags_no_stand_as_large():
    """The terrain fact the whole bug rests on. If a future DCS update starts
    flagging Nellis stands, the fallback stops mattering and this test says so
    rather than leaving a stale comment in the engine."""
    import dcs.terrain.nevada as nevada
    slots = nevada.Nevada().airports["Nellis"].parking_slots
    assert slots, "Nellis has no parking slots at all"
    assert not any(s.large for s in slots), (
        "NTTR now flags large stands — the geometry fallback in dressing.py is "
        "no longer the only thing standing between a tanker and the ramp")


@pytest.mark.parametrize("type_name,length,span", [
    ("KC_135", 46.61, 40.0),
    ("E_3A", 46.61, 44.4),
    ("C_130", 29.79, 40.4),
    ("C_17A", 53.04, 51.76),
    ("B_52H", 49.05, 56.4),
    ("F_16C_50", 14.52, 9.45),
])
def test_pydcs_still_reports_the_dimensions_we_reason_from(type_name, length, span):
    """Every threshold in this feature is derived from these numbers. If pydcs
    revises one, the fit test silently changes behavior."""
    t = getattr(planes, type_name)
    assert t.length == pytest.approx(length, abs=0.5)
    assert t.width == pytest.approx(span, abs=0.5), "pydcs `width` IS wingspan"


class _Slot:
    def __init__(self, length, width, large=False):
        self.length, self.width, self.large = length, width, large


def test_a_stand_is_judged_by_the_aircraft_not_a_magic_number():
    """The old test was one hardcoded 60x55 rectangle for every airframe."""
    nellis_big = _Slot(78.72, 67.10)        # the six real heavy stands
    nellis_med = _Slot(39.86, 40.0)         # the 31-stand medium row
    fighter = _Slot(22.92, 14.5)            # the 126-stand fighter row

    for t in (planes.KC_135, planes.E_3A, planes.C_17A, planes.B_52H):
        assert stand_fits(t, nellis_big), f"{t.id} rejected from a 78x67 stand"

    # A fighter stand takes a fighter and nothing else, at any tolerance.
    assert stand_fits(planes.F_16C_50, fighter)
    for t in (planes.KC_135, planes.C_130, planes.B_52H):
        assert not stand_fits(t, fighter, STAND_TOLERANCE["static"]), \
            f"{t.id} would be parked on a 23x14.5 m fighter spot"

    # The medium row is where airframe-awareness earns its keep: it takes the
    # 707-class jets with the inert-scenery tolerance and never takes a C-17 or
    # a B-52, which the old single threshold could not distinguish.
    tol = STAND_TOLERANCE["static"]
    assert stand_fits(planes.C_130, nellis_med, tol)
    assert stand_fits(planes.KC_135, nellis_med, tol)
    for t in (planes.C_17A, planes.B_52H):
        assert not stand_fits(t, nellis_med, tol), \
            f"{t.id} does not fit a 40x40 stand at any honest tolerance"


def test_live_aircraft_must_actually_fit():
    """`parked_ai` mode spawns uncontrolled flights DCS may taxi, so it gets no
    overhang allowance. `static` mode is inert scenery on an apron that
    continues past the painted box, which is how a real KC-135 sits on a 40 m
    spot with its tail over the taxi lane."""
    assert STAND_TOLERANCE["parked_ai"] == 1.0
    assert STAND_TOLERANCE["static"] > 1.0
    med = _Slot(39.86, 40.0)
    assert not stand_fits(planes.KC_135, med, STAND_TOLERANCE["parked_ai"])
    assert stand_fits(planes.KC_135, med, STAND_TOLERANCE["static"])


def test_a_terrain_authors_large_flag_is_always_honoured():
    """We can measure a box; we cannot measure what the author knew."""
    assert stand_fits(planes.B_52H, _Slot(10, 10, large=True))


# --- cause 3: the ramp identity ---------------------------------------------

def test_nellis_uses_the_red_flag_ramp():
    maps = load_json("maps")
    for era, preset in maps["nevada"]["presets"].items():
        assert (preset.get("blue_field_themes") or {}).get("Nellis") == "red_flag", \
            f"Nevada/{era}: Nellis is not on the Red Flag ramp"


def test_the_red_flag_ramp_is_a_tanker_line():
    """Tankers deploy in for the exercise and sit for two weeks; the bombers
    and the Sentry are guests. A pool where the B-1B outdraws the KC-135 gives
    you a bomber display, which is not what Red Flag looks like."""
    themes = load_json("ramp_themes")
    for era in ("coldwar", "modern"):
        large = dict((r, w) for r, w, *_ in themes[era]["blue"]["red_flag"]["large"])
        assert large.get("planes.KC_135", 0) >= 2 * max(
            w for r, w in large.items() if r != "planes.KC_135"), \
            f"{era} red_flag: the tanker does not lead the heavy pool: {large}"
        assert "planes.E_3A" in large, f"{era} red_flag has no AWACS"


def test_the_test_sites_do_not_inherit_the_exercise_ramp():
    """Setting the map-wide theme to red_flag put B-1Bs and a Sentry on the
    Groom Lake apron. Groom Lake and Tonopah Test Range are black-project test
    sites that happen to share a map with Nellis."""
    maps = load_json("maps")
    for era, preset in maps["nevada"]["presets"].items():
        assert preset.get("blue_theme") != "red_flag", (
            f"Nevada/{era} applies the Red Flag ramp map-wide — every test site "
            f"on the map gets a surge exercise ramp")


def test_groom_lake_gets_no_awacs(tmp_path):
    """The end-to-end version: the E-3A exists only in the red_flag pool, so
    finding one at Groom Lake proves the per-field theme stopped working."""
    for seed in SEEDS:
        fields = _build(tmp_path, seed, ramp_heavies="surge")
        # Not vacuous: the field must actually be dressed, or "no Sentry here"
        # is true of an empty ramp and this test guards nothing.
        assert sum(fields["Groom Lake"].values()) >= 5, \
            f"seed {seed}: Groom Lake is undressed, so this proves nothing"
        assert not fields["Groom Lake"]["E-3A"], \
            f"seed {seed}: a Sentry is parked at Groom Lake"
        assert fields["Nellis"]["E-3A"] or fields["Nellis"]["KC-135"], \
            f"seed {seed}: Nellis has neither a Sentry nor a tanker"


# --- the thing Rob actually reported ----------------------------------------

def test_nellis_reliably_has_tankers_or_awacs_on_the_ramp(tmp_path):
    """The headline. Before the fix this was zero on every seed."""
    counts = []
    for seed in SEEDS:
        nellis = _build(tmp_path, seed)["Nellis"]
        counts.append(sum(v for k, v in nellis.items() if k in TANKER_AWACS))
    assert all(c >= 1 for c in counts), \
        f"Nellis had no tanker or AWACS on some seeds: {counts}"
    assert sum(counts) / len(counts) >= 1.5, \
        f"Nellis averages {sum(counts)/len(counts):.1f} tanker/AWACS — thin for " \
        f"the base Red Flag is named after"


def test_a_surge_ramp_is_visibly_bigger_than_a_normal_one(tmp_path):
    """The control has to do something a pilot would notice, in the direction
    the label promises."""
    def heavies(mode):
        return sum(sum(v for k, v in _build(tmp_path, s, ramp_heavies=mode)["Nellis"].items()
                       if k in HEAVY) for s in SEEDS)
    none_, light, auto, surge = (heavies(m) for m in ("none", "light", "auto", "surge"))
    assert none_ == 0, f"'none' still parked {none_} heavies"
    assert light < auto < surge, \
        f"the control is not monotonic: light={light} auto={auto} surge={surge}"


def test_turning_heavies_off_leaves_the_fighters_alone(tmp_path):
    """A reservation that changes the total population is a fill control in
    disguise. It should change WHO parks, not HOW MANY."""
    for seed in SEEDS:
        on = _build(tmp_path, seed, ramp_heavies="surge")["Nellis"]
        off = _build(tmp_path, seed, ramp_heavies="none")["Nellis"]
        assert abs(sum(on.values()) - sum(off.values())) <= 2, (
            f"seed {seed}: Nellis holds {sum(on.values())} aircraft on surge and "
            f"{sum(off.values())} with heavies off — the reservation is adding "
            f"aircraft rather than substituting them")


def test_the_ramp_never_becomes_all_heavies(tmp_path):
    """A share with no ceiling reserved every heavy-capable stand at 60% fill
    and parked thirty of them, ten being B-1Bs. A heavy line is a feature of a
    ramp, not the ramp."""
    for seed in SEEDS:
        nellis = _build(tmp_path, seed, ramp_heavies="surge", dress_fill=60)["Nellis"]
        heavy = sum(v for k, v in nellis.items() if k in HEAVY)
        total = sum(nellis.values())
        assert total, f"seed {seed}: Nellis is empty"
        assert heavy <= RAMP_HEAVIES["surge"][2] * 3, \
            f"seed {seed}: {heavy} heavies at Nellis, ceiling is " \
            f"{RAMP_HEAVIES['surge'][2]} stands"
        assert heavy / total < 0.5, \
            f"seed {seed}: {heavy} of {total} aircraft at Nellis are heavies"


def test_no_single_heavy_type_takes_the_whole_ramp(tmp_path):
    """The reservation is small and a heavy block is 2-3 deep, so an unguarded
    weighted draw hands the entire heavy line to one type — measured at 1.8
    B-1Bs against 0.6 KC-135s from a pool where both carried weight 2."""
    seen = collections.Counter()
    for seed in SEEDS:
        nellis = _build(tmp_path, seed, ramp_heavies="surge")["Nellis"]
        heavies = {k: v for k, v in nellis.items() if k in HEAVY}
        if sum(heavies.values()) >= 4:
            assert len(heavies) >= 2, \
                f"seed {seed}: every heavy at Nellis is a {list(heavies)[0]}"
        seen.update(heavies)
    assert len(seen) >= 3, f"only {len(seen)} heavy types ever appear: {dict(seen)}"


def test_small_fields_get_a_smaller_heavy_line_than_nellis(tmp_path):
    """The floor is what makes a big base work, and it has to scale or a
    48-stand test site reserves the same heavy line as Nellis's 247."""
    big, small = 0, 0
    for seed in SEEDS:
        f = _build(tmp_path, seed)
        big += sum(v for k, v in f["Nellis"].items() if k in HEAVY)
        small += sum(v for k, v in f["Groom Lake"].items() if k in HEAVY)
    assert big > small, \
        f"Nellis parks {big} heavies and Groom Lake {small} — the floor is flat"


# --- the rest of the world --------------------------------------------------

@pytest.mark.parametrize("map_key,era,ac", [
    ("caucasus", "modern", "FA_18C_hornet"),
    ("germany", "coldwar", "F_4E_45MC"),
    ("normandy", "wwii", "P_51D"),
    ("marianas", "modern", "FA_18C_hornet"),
])
def test_other_maps_gain_heavies_without_gaining_aircraft(map_key, era, ac, tmp_path):
    """This was never a Nevada bug — the 60x55 threshold was failing nearly
    everywhere, and Cold War Germany managed 0-2 heavies across fifteen
    airfields. Fixing it must not inflate the mission: heavies substitute for
    fighters on stands the fighters were taking, so the static count holds and
    nobody's frame rate changes."""
    out = str(tmp_path / "w.miz")
    generate(Recipe.from_dict(dict(map=map_key, era=era, aircraft=ac,
                                   bb_ambient=False, seed=3)), out)
    m = _mission(out)
    heavy = statics = 0
    for coal in m["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for ctry in coal.get("country", {}).values():
            for g in ctry.get("static", {}).get("group", {}).values():
                for u in g.get("units", {}).values():
                    statics += 1
                    if u.get("type") in HEAVY:
                        heavy += 1
    assert heavy, f"{map_key}/{era}: not one transport or tanker on any ramp"
    assert heavy / statics < 0.25, \
        f"{map_key}/{era}: {heavy} of {statics} statics are heavies"


# --- the control's contract -------------------------------------------------

def test_the_setting_survives_a_share_link():
    from missiongen.share import decode_recipe, encode_recipe
    rc = Recipe.from_dict(dict(map="nevada", era="modern",
                               aircraft="FA_18C_hornet", ramp_heavies="surge"))
    assert decode_recipe(encode_recipe(rc)).ramp_heavies == "surge"


def test_an_older_link_defaults_to_the_normal_ramp():
    """`ramp_heavies` is additive, so a link saved before it existed must take
    the default rather than fail to decode."""
    import base64
    import json
    from missiongen.share import decode_recipe
    payload = {"v": 1, "r": {"map": "nevada", "era": "modern",
                             "aircraft": "FA_18C_hornet"}}
    code = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    assert decode_recipe(code).ramp_heavies == "auto"


def test_every_level_is_offered_in_the_builder():
    from pathlib import Path
    html = ui_source()
    import re
    m = re.search(r'<select[^>]*id="ramp_heavies"[^>]*>(.*?)</select>', html, re.S)
    assert m, "the ramp-heavies control is not in the Builder"
    offered = set(re.findall(r'value="([^"]+)"', m.group(1)))
    assert offered == set(RAMP_HEAVIES), \
        f"UI offers {sorted(offered)}, engine has {sorted(RAMP_HEAVIES)}"
