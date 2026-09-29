"""An aligned base parks its OWN nation's aircraft, and never the enemy's.

Rob built a Syria mission out of Incirlik — a blue, Turkish, NATO base — and
found it parked with A-50s, Il-76s, Su-24s and MiG-29s alongside its F-16s.

The cause was mine, introduced in v1.47.0 and live from v1.48.0. The per-field
ramp theme added for Nellis worked out which side a field belonged to like this:

    side = r.coalition if theme is own_theme else enemy_side

An identity check against a value the caller had already transformed. For an
internationally-aligned base, `_atheme()` merges that nation's roster over the
side theme and returns a NEW dict, so `theme is own_theme` was False for every
aligned base on every map — Incirlik, Akrotiri, Ramat David — and each one was
re-resolved against the RED theme.

Two lessons are pinned below. The narrow one: aligned bases are national.
The broad one: a field's side must be passed, never inferred from the identity
of an object that other code is entitled to replace.
"""
import collections
import zipfile

import pytest

import dcs.lua as lua
from missiongen import Recipe, generate
from missiongen import alignment
from missiongen.resolver import load_json

MAPS = load_json("maps")

# Airframes no NATO or Western-aligned ramp should ever park. Types, not
# coalitions: the point is that a Turkish base looks Turkish, and "it was on the
# blue coalition" is exactly the check that passed while this bug was live.
RED_ONLY = {"A-50", "IL-76MD", "IL-78M", "Su-24M", "Su-24MR", "Su-25", "Su-27",
            "Su-33", "Su-34", "MiG-29A", "MiG-29S", "MiG-31", "MiG-23MLD",
            "MiG-21Bis", "An-26B", "An-30M", "Tu-22M3", "Tu-95MS", "Tu-142",
            "Mi-24P", "Mi-8MT", "Ka-27", "Yak-40"}


def _statics_by_field(path, fields):
    m = lua.loads(zipfile.ZipFile(path).read("mission").decode())["mission"]
    out = collections.defaultdict(collections.Counter)
    for coal in m["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for g in c.get("static", {}).get("group", {}).values():
                name = g.get("name", "")
                field = next((f for f in fields if f in name), None)
                if field is None:
                    continue
                for u in g.get("units", {}).values():
                    t = u.get("type") or ""
                    if u.get("category") == "Planes" or "-" in t:
                        out[field][t] += 1
    return out


def _aligned_blue(map_key, era):
    """Blue preset fields on this map that alignment gives a real nation."""
    preset = MAPS[map_key]["presets"][era]
    bases = alignment.bases(map_key, era)
    return [b for b in preset["blue_airbases"] if bases.get(b)]


CASES = [("syria", "modern", "FA_18C_hornet"),
         ("syria", "coldwar", "F_4E_45MC"),
         ("persiangulf", "modern", "FA_18C_hornet")]


@pytest.mark.parametrize("map_key,era,ac", CASES,
                         ids=[f"{m}/{e}" for m, e, _a in CASES])
def test_an_aligned_base_never_parks_the_enemys_aircraft(map_key, era, ac, tmp_path):
    """The report, generalised. This is checked on the aircraft TYPES rather
    than the coalition, because the coalition was right the whole time — the
    aircraft on the ramp were not."""
    fields = _aligned_blue(map_key, era)
    if not fields:
        pytest.skip(f"{map_key}/{era} has no internationally-aligned blue base")

    seen = collections.Counter()
    for seed in (3, 4, 5):
        out = str(tmp_path / f"{seed}.miz")
        generate(Recipe.from_dict(dict(
            map=map_key, era=era, aircraft=ac, home_airbase=fields[0],
            bb_ambient=False, bb_alignment=True, seed=seed)), out)
        per = _statics_by_field(out, fields)
        for field, counts in per.items():
            seen.update(counts)
            wrong = sorted(set(counts) & RED_ONLY)
            assert not wrong, (
                f"{map_key}/{era} seed {seed}: {field} is a blue, "
                f"{alignment.bases(map_key, era)[field]} base and it is parked "
                f"with {wrong}. Full ramp: {dict(counts)}")
    assert seen, "no aligned base was dressed at all — this test proved nothing"


def test_incirlik_specifically(tmp_path):
    """Named on its own because it is the case Rob actually hit, and a named
    failure is diagnosable where a parametrized one is a puzzle."""
    out = str(tmp_path / "i.miz")
    generate(Recipe.from_dict(dict(
        map="syria", era="modern", aircraft="F_14B_U", home_airbase="Incirlik",
        bb_ambient=False, seed=3)), out)
    ramp = _statics_by_field(out, ["Incirlik"])["Incirlik"]
    assert ramp, "Incirlik was not dressed"
    assert not (set(ramp) & RED_ONLY), \
        f"Russian aircraft at Incirlik again: {dict(ramp)}"
    assert "F-16C_50" in ramp, \
        f"Incirlik has no Turkish Vipers on it: {dict(ramp)}"


def test_an_explicit_theme_choice_does_not_erase_national_rosters(tmp_path):
    """The second instance of the same bug, caught while fixing the first: the
    replacement re-resolved the theme whenever the user had picked one in the
    Builder, which would have put the map's default ramp on Akrotiri."""
    fields = _aligned_blue("syria", "modern")
    out = str(tmp_path / "t.miz")
    generate(Recipe.from_dict(dict(
        map="syria", era="modern", aircraft="FA_18C_hornet",
        home_airbase="Incirlik", dress_theme="expeditionary",
        bb_ambient=False, seed=3)), out)
    for field, counts in _statics_by_field(out, fields).items():
        assert not (set(counts) & RED_ONLY), \
            f"{field} with an explicit theme: {dict(counts)}"


def test_the_side_is_passed_not_inferred():
    """The general lesson, pinned in the source. Inferring a field's side from
    the identity of a theme object is unsafe the moment anything is entitled to
    wrap or merge that object — which `_atheme()` is, by design."""
    from pathlib import Path
    src = (Path(__file__).parent.parent / "missiongen" / "builder.py").read_text()
    assert "def _dress(ap, country, cfg, theme, side" in src, \
        "_dress no longer takes an explicit side"
    code = "\n".join(l.split("#", 1)[0] for l in src.splitlines())
    assert "theme is own_theme" not in code, \
        "the identity check that caused the Incirlik bug is back"


def test_red_fields_still_look_red(tmp_path):
    """The other direction. A fix that made everything blue would pass every
    assertion above and quietly disarm the opposition's ramps."""
    out = str(tmp_path / "r.miz")
    generate(Recipe.from_dict(dict(
        map="syria", era="modern", aircraft="FA_18C_hornet",
        home_airbase="Incirlik", bb_ambient=False, seed=3)), out)
    red_fields = MAPS["syria"]["presets"]["modern"]["red_airbases"]
    per = _statics_by_field(out, red_fields)
    assert per, "no red field was dressed"
    assert any(set(c) & RED_ONLY for c in per.values()), \
        f"not one red field parks a Russian airframe: " \
        f"{ {f: dict(c) for f, c in per.items()} }"


def test_the_per_field_theme_still_works(tmp_path):
    """Nellis is what the per-field theme was added for in v1.47.0, and the fix
    must not throw the feature out with the bug. The E-3A exists only in the
    `red_flag` pool, so finding one proves the override still applies."""
    out = str(tmp_path / "n.miz")
    generate(Recipe.from_dict(dict(
        map="nevada", era="modern", aircraft="FA_18C_hornet",
        home_airbase="Nellis", ramp_heavies="surge",
        bb_ambient=False, seed=13)), out)
    ramp = _statics_by_field(out, ["Nellis"])["Nellis"]
    assert ramp.get("E-3A"), \
        f"Nellis lost its Red Flag ramp: {dict(ramp)}"
