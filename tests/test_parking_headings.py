"""The measured parking headings must still point at real stands.

`missiongen/data/parking_headings.json` holds **9,550 individually measured
per-slot headings** across ten maps — the painted-line facing for a specific
parking spot, keyed by that spot's NAME ('01', '02', '50'…). They exist because
pydcs does not expose the terrain's own parking heading, so a static aircraft
would otherwise face a geometric guess.

They were measured by hand. That makes them the most expensive data in the
repository and the least defended: nothing checked that a slot named in this
file still exists on the terrain it claims to describe.

The failure mode is silent and visual. If a terrain export renumbers or drops a
slot, the measurement for '17' is applied to whatever '17' now means, or to
nothing at all — aircraft face the wrong way on the ramp, and every existing
test still passes, because those tests assert that a heading was APPLIED, never
that it was the RIGHT one for that stand.

Written while evaluating a pydcs fork whose Germany export is three times the
size of ours (docs/pydcs-plan-critique.md §5). Germany alone carries 2,220 of
these measurements. The names turned out to match — but "I checked by hand once"
is not a guarantee, and this file is the guarantee.
"""
import json
import math

import pytest

from missiongen.resolver import load_json, resolve_terrain

HEADINGS = {k: v for k, v in load_json("parking_headings").items()
            if not k.startswith("_")}
MAPS = load_json("maps")


def _terrain_slots(map_key):
    """{airfield name: {slot names}} for a map, from the terrain itself."""
    cfg = MAPS.get(map_key)
    if not cfg:
        return None
    terrain = resolve_terrain(cfg["terrain_class"])()
    out = {}
    for ap in terrain.airport_list():
        out[ap.name] = {str(s.slot_name) for s in ap.parking_slots
                        if s.slot_name is not None}
    return out


@pytest.mark.parametrize("map_key", sorted(HEADINGS))
def test_every_measured_field_exists_on_its_map(map_key):
    """A field named here that the terrain does not have is a measurement
    pointing at nothing — usually a rename we did not notice."""
    slots = _terrain_slots(map_key)
    assert slots is not None, f"parking_headings names map '{map_key}', maps.json does not"
    missing = sorted(f for f in HEADINGS[map_key] if f not in slots)
    assert not missing, (
        f"{map_key}: measured headings for airfields that do not exist on the "
        f"terrain: {missing}")


@pytest.mark.parametrize("map_key", sorted(HEADINGS))
def test_every_measured_slot_still_exists(map_key):
    """The expensive one. Each measurement is keyed by slot name; if that name
    is gone, the measurement is silently dead and the aircraft on that stand
    goes back to a geometric guess without anything saying so."""
    slots = _terrain_slots(map_key)
    dead = []
    for field, val in HEADINGS[map_key].items():
        if not isinstance(val, dict):
            continue                      # a bare number = whole-field default
        have = slots.get(field, set())
        for slot_name in (val.get("slots") or {}):
            if str(slot_name) not in have:
                dead.append(f"{field}/{slot_name}")
    assert not dead, (
        f"{map_key}: {len(dead)} measured slot headings point at stands that no "
        f"longer exist (first 20: {dead[:20]}). A terrain export probably "
        f"renumbered the ramp; the measurements must be re-taken, not deleted.")


@pytest.mark.parametrize("map_key", sorted(HEADINGS))
def test_identified_stand_surveys_still_match_the_export_geometry(map_key):
    terrain = resolve_terrain(MAPS[map_key]["terrain_class"])()
    for field, val in HEADINGS[map_key].items():
        if not isinstance(val, dict):
            continue
        stands = {str(s.crossroad_idx): s for s in terrain.airports[field].parking_slots}
        for sid, measured in (val.get("stands") or {}).items():
            assert sid in stands, f"{map_key}/{field}/{sid}: surveyed stand removed"
            slot = stands[sid]
            assert str(slot.slot_name) == measured["slot_name"]
            assert math.hypot(slot.position.x - measured["x"], slot.position.y - measured["y"]) <= 0.05, (
                f"{map_key}/{field}/{sid}: surveyed stand moved; verify its direction in DCS")
            assert math.isfinite(measured["heading"]) and 0 <= measured["heading"] < 360


def test_the_corpus_is_the_size_we_think_it_is():
    """A canary on the data itself. These measurements are hand-taken and hard
    to reproduce; a big silent DROP (a bad merge, a truncated write) should be
    noticed by the build, not by a pilot seeing a ramp face the wrong way."""
    total = sum(len(v.get("slots") or {})
                for fields in HEADINGS.values()
                for v in fields.values() if isinstance(v, dict))
    assert total >= 9000, (
        f"only {total} measured slot headings remain — the corpus was ~9,550. "
        f"If this was a deliberate removal, update the floor and say why.")


@pytest.mark.parametrize("map_key", sorted(HEADINGS))
def test_measured_headings_are_plausible_compass_bearings(map_key):
    for field, val in HEADINGS[map_key].items():
        vals = ([val] if isinstance(val, (int, float))
                else [val.get("default")] + list((val.get("slots") or {}).values()))
        for h in vals:
            if h is None:
                continue
            assert isinstance(h, (int, float)) and 0.0 <= float(h) <= 360.0, \
                f"{map_key}/{field}: {h!r} is not a compass bearing"
