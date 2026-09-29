"""No squadron parks more than six aircraft on one ramp.

Rob's rule: "The max number of statics displayed from a single squadron should
be 6. After that, a new squadron must be picked."

The failure it fixes is a ramp that reads as a copy-paste error — measured
before the cap, one seed put **22 MiG-21s in a single scheme** on Templin, and
440 blocks across 40 missions exceeded six. The block system was already trying
to produce "a squadron lives here" rows; what it lacked was any memory of what
it had already parked, so the same identity could be drawn again for the next
block, and the next.

WHAT COUNTS AS A SQUADRON. A named entry in `squadrons.json` obviously is. A
generic theme block has no name, so the identity is what a pilot actually sees:
airframe plus paint. Two F-16 blocks in different squadron liveries are two
squadrons sharing a field and are allowed; two in the same livery are one
squadron parked twice, which is the thing being stopped.

CONSEQUENCE, MEASURED. Ramp population falls about 15% (22.6 -> 19.2 aircraft
per field across 40 missions). That is the correct price of the rule, and it is
self-limiting: a field can show at most (distinct squadrons x 6) aircraft, so a
theme with three airframes tops out at 18 however many stands the base has.
`test_a_theme_can_populate_a_busy_ramp` makes that ceiling visible per theme
rather than leaving it to surprise somebody.
"""
import collections
import re

import pytest

import dcs.lua as lua
import zipfile

from missiongen import Recipe, generate
from missiongen.dressing import SQUADRON_MAX, _squadron_id
from missiongen.resolver import load_json

# "ST <field> x<slot> <TYPE>[ · <squadron name>]"
NAME_RE = re.compile(r"^ST (.+?) x\d+ (.+)$")

# map, era, and a period-legal player aircraft where the default would not be
CASES = [("nevada", "modern", None), ("syria", "modern", None),
         ("caucasus", "modern", None), ("germany", "coldwar", "F_4E_45MC"),
         ("normandy", "wwii", "P_51D")]


def _ramp(path):
    """{field: Counter(squadron identity -> statics parked)}."""
    m = lua.loads(zipfile.ZipFile(path).read("mission").decode())["mission"]
    per = collections.defaultdict(collections.Counter)
    for coal in m["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for g in c.get("static", {}).get("group", {}).values():
                mt = NAME_RE.match(g.get("name", ""))
                if not mt:
                    continue
                for u in g["units"].values():
                    if u.get("category") != "Planes":
                        continue
                    # The group name already carries type + squadron tag; the
                    # livery is per unit. Together they are the identity.
                    per[mt.group(1)][f"{mt.group(2)}|{u.get('livery_id') or '-'}"] += 1
    return per


def _build(tmp_path, mp, era, ac, seed, **extra):
    rc = dict(map=mp, era=era, seed=seed, density="busy",
              ramp_heavies="surge", **extra)
    if ac:
        rc["aircraft"] = ac
    out = str(tmp_path / f"{mp}_{era}_{seed}.miz")
    generate(Recipe.from_dict(rc), out)
    return out


@pytest.mark.parametrize("mp,era,ac", CASES,
                         ids=[f"{m}/{e}" for m, e, _a in CASES])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_no_squadron_parks_more_than_six(mp, era, ac, seed, tmp_path):
    out = _build(tmp_path, mp, era, ac, seed)
    ramp = _ramp(out)
    assert ramp, f"{mp}/{era}: nothing was parked, so this proves nothing"
    for field, ctr in ramp.items():
        for sid, n in ctr.items():
            assert n <= SQUADRON_MAX, \
                f"{mp}/{era}/seed{seed} {field}: {sid} parked {n}"


def test_a_full_squadron_is_followed_by_a_different_one(tmp_path):
    """The second half of the rule. Capping alone could leave a field with six
    aircraft and bare stands; what Rob asked for is that the ramp moves on to
    another unit."""
    found = False
    for seed in (1, 2, 3, 4, 5):
        out = _build(tmp_path, "nevada", "modern", None, seed)
        for field, ctr in _ramp(out).items():
            if max(ctr.values(), default=0) < SQUADRON_MAX:
                continue          # nothing hit the cap here; not a witness
            found = True
            total = sum(ctr.values())
            # Counting identities is not enough: heavies are their own
            # identities, so a ramp of six fighters plus two tankers would show
            # three "squadrons" while having given up on fighters entirely. The
            # property is that the ramp kept GOING past the cap.
            assert total > SQUADRON_MAX * 2, (
                f"{field} hit the cap and then parked only {total} aircraft in "
                f"total — it stopped instead of picking another squadron: "
                f"{dict(ctr)}")
    assert found, "no field reached the cap, so the follow-on was never exercised"


def test_the_data_cannot_ask_for_more_than_the_ramp_will_show():
    """`count` in squadrons.json is clamped at build time. If the file were
    allowed to say 12, it would describe a mission that does not exist — so the
    pack validator rejects it rather than quietly rendering 6."""
    for mapk, bases in load_json("squadrons").items():
        if mapk.startswith("_"):
            continue
        for base, entries in bases.items():
            for e in entries:
                assert e.get("count", 1) <= SQUADRON_MAX, \
                    f"{mapk}/{base}: {e.get('name')} asks for {e['count']}"


def test_an_oversized_squadron_entry_is_a_pack_error(monkeypatch):
    """Mutation-proof for the validator: the guard has to actually fire."""
    import missiongen.resolver as R
    real = R.load_json

    def fake(name):
        if name == "squadrons":
            return {"nevada": {"Nellis": [
                {"ref": "planes.F_16C_50", "count": SQUADRON_MAX + 1,
                 "name": "Test Sqn"}]}}
        return real(name)

    monkeypatch.setattr(R, "load_json", fake)
    errs = R.validate_data_packs()
    assert any("exceeds" in e and "Nellis" in e for e in errs), errs


def test_a_named_squadron_and_a_generic_block_are_different_identities():
    """The identity function is the whole rule in one line, so it gets its own
    test rather than only being exercised through a built mission."""
    assert _squadron_id("F-16C_50", "usaf", "64th AGRS") == "64th AGRS"
    assert _squadron_id("F-16C_50", "a", None) != _squadron_id("F-16C_50", "b", None)
    assert _squadron_id("F-16C_50", None, None) == _squadron_id("F-16C_50", None, None)
    assert _squadron_id("F-15C", None, None) != _squadron_id("F-16C_50", None, None)


# Themes whose airframe list is deliberately narrow. Recorded with a reason so
# a thin ramp is a decision on the record rather than a surprise: with the cap
# in force a field can show at most (types x SQUADRON_MAX) aircraft.
THIN_THEMES = {
    ("coldwar", "blue", "navy"): "a carrier air wing ashore is genuinely few types",
    ("modern", "red", "strategic"): "bomber bases park bombers",
    ("wwii", "blue", "raf"): "RAF fighter stations were single-type by design",
    # GWOT. Three of these four are thin because the RAMP is thin, and one is
    # thin because the test counts only fixed-wing.
    ("gwot", "blue", "rotary_heavy"):
        "an aviation brigade's field IS mostly helicopters — it carries four "
        "rotary types, which this check does not count",
    ("gwot", "blue", "air_bridge"):
        "a lift hub parks transports; its variety is in `large`, not `planes`",
    ("gwot", "red", "abandoned"):
        "a boneyard of derelict Iraqi Air Force airframes should look sparse — "
        "a full ramp would imply an air force that is still operating",
    ("gwot", "red", "captured"): "same, one step less abandoned",
}


def test_a_theme_can_populate_a_busy_ramp():
    """With the cap, airframe VARIETY is what sets how full a ramp can get —
    stands stopped being the binding constraint. A theme with two aircraft types
    tops out at twelve statics no matter how big the base is."""
    thin = []
    for era, sides in load_json("ramp_themes").items():
        if era.startswith("_"):
            continue
        for side, themes in sides.items():
            for key, cfg in themes.items():
                if key == "default" or not isinstance(cfg, dict):
                    continue
                types = len(cfg.get("planes") or [])
                ceiling = types * SQUADRON_MAX
                if ceiling < 18 and (era, side, key) not in THIN_THEMES:
                    thin.append(f"{era}/{side}/{key}: {types} types "
                                f"-> at most {ceiling} parked aircraft")
    assert not thin, (
        "these themes cannot fill a busy ramp under the squadron cap; add "
        "airframes or record them in THIN_THEMES with a reason:\n  "
        + "\n  ".join(thin))


# ---------------------------------------------------------------------------
# Explicit fill outranks the variety cap (v1.62.0, Rob: "When I select 100%
# fill for Nellis airfield, it doesn't populate completely").
#
# The cap made (distinct identities × 6) the ramp's hard ceiling, and with the
# livery pack unverified every type is exactly one identity — measured 79 of
# 233 airplane stands at Nellis on an explicit fill=100. dress_airfield now
# escalates squad_cap by waves when an EXPLICIT fill still has budget; the
# auto/density path never escalates, so the variety rule still governs there
# (that path is what every other test in this file exercises).
# ---------------------------------------------------------------------------

def _dress_nellis(fill, seed=1):
    import random
    from dcs.mission import Mission
    from dcs.terrain import Nevada
    from missiongen import dressing
    m = Mission(Nevada())
    ap = next(a for a in m.terrain.airport_list() if "Nellis" in a.name)
    era_cfg = load_json("eras")["modern"]["blue"]
    preset = load_json("maps")["nevada"]["presets"]["modern"]
    _k, theme = dressing.resolve_theme("modern", "blue", preset, None,
                                       airport_name=ap.name)
    free = sum(1 for s in ap.parking_slots if s.unit_id is None)
    placed = dressing.dress_airfield(
        m, ap, m.country("USA"), era_cfg, "busy", random.Random(seed),
        theme=theme, fill=fill, aircraft_mode="static", map_key="nevada",
        ramp_heavies="surge")
    return placed, free


def test_an_explicit_100_percent_fill_fills_the_ramp():
    """100% must mean the stands, not the squadron ceiling. A couple of stands
    may legitimately fail the collision gate or a heavy-fit check, so the floor
    is 95%, not equality."""
    placed, free = _dress_nellis(fill=100)
    assert placed >= free * 0.95, (
        f"asked for 100% of {free} stands, got {placed} "
        f"({placed / free * 100:.0f}%) — the squadron cap is still the ceiling")


def test_an_explicit_half_fill_lands_on_half():
    placed, free = _dress_nellis(fill=50)
    target = round(free * 0.5)
    assert abs(placed - target) <= max(3, target * 0.05), \
        f"asked for 50% ({target}), got {placed}"


def test_the_auto_path_still_stops_at_the_variety_cap(tmp_path):
    """The escalation must be reachable ONLY through an explicit fill. The
    auto/density path keeps the six-per-squadron rule absolute — that is the
    whole existing contract of this file, restated here right next to the
    feature that could have broken it."""
    out = _build(tmp_path, "nevada", "modern", None, 1)
    for field, ctr in _ramp(out).items():
        for sid, n in ctr.items():
            assert n <= SQUADRON_MAX, \
                f"auto path: {field}: {sid} parked {n} — escalation leaked"


def test_the_cap_did_not_empty_the_ramps(tmp_path):
    """The rule costs population — measured at ~15%. This is the floor that
    says it cost that and not everything, so a future tightening that guts the
    ramp fails here rather than in somebody's mission."""
    total = fields = 0
    for mp, era, ac in CASES:
        for seed in (1, 2):
            for field, ctr in _ramp(_build(tmp_path, mp, era, ac, seed)).items():
                total += sum(ctr.values())
                fields += 1
    assert fields, "no fields dressed at all"
    per_field = total / fields
    assert per_field >= 12, \
        f"only {per_field:.1f} aircraft per field — the cap is starving ramps"
