"""Afghanistan came from a hand-built export until v1.68.0. This is what the
swap to the official one had to preserve.

`test_parking_headings.py` already proves the general case — every one of the
9,550 measured slot headings still names a slot that exists, 460 of them on
this map. That test is what made the swap a twenty-minute job. What it does
NOT pin is the two things specific to replacing a whole terrain package: that
the projection still puts airfields where they are on Earth, and that stands
did not get NARROWER underneath the width-first parking sort added in the same
release.

Both are stated as absolutes here rather than as before/after comparisons. A
differential assertion is how three vacuous tests got shipped this year: if
both sides move together, the test passes and says nothing.
"""
import math

import pytest
from dcs import planes

from missiongen.terrains.afghanistan import Afghanistan

# Surveyed positions, from public aeronautical sources. A terrain export that
# lands these on the wrong side of the country is the failure mode a byte diff
# of 4,600 lines will never show you.
REAL = {
    "Bagram":       (34.9461, 69.2650),
    "Kandahar":     (31.5058, 65.8478),
    "Kabul":        (34.5658, 69.2125),
    "Herat":        (34.2100, 62.2283),
    "Shindand":     (33.3913, 62.2610),
    "Jalalabad":    (34.3995, 70.4983),
    "Zaranj":       (30.9722, 61.8658),
}

# Camp Bastion is deliberately absent: its airport reference point sits ~1.5 km
# from the published ARP because the base is enormous and the export anchors on
# the ramp. Listing it with a loose tolerance would weaken the whole table.
TOLERANCE_KM = 0.5


@pytest.fixture(scope="module")
def terrain():
    return Afghanistan()


@pytest.mark.parametrize("name,latlon", sorted(REAL.items()))
def test_the_projection_puts_the_field_where_it_is_on_earth(terrain, name, latlon):
    rlat, rlon = latlon
    ll = terrain.airports[name].position.latlng()
    km = math.hypot((ll.lat - rlat) * 111.0,
                    (ll.lng - rlon) * 111.0 * math.cos(math.radians(rlat)))
    assert km <= TOLERANCE_KM, (
        f"{name} is {km:.2f} km from its surveyed position "
        f"({ll.lat:.4f},{ll.lng:.4f} vs {rlat},{rlon}) — the projection is wrong")


def test_zaranj_is_present(terrain):
    """The 26th airfield, in the south-west on the Iranian border. Our
    hand-built export missed it entirely; it is the one thing the swap ADDS,
    and it is why the same seed now produces a different Afghanistan mission
    (the airport list feeds the seeded draws)."""
    assert "Zaranj" in terrain.airports
    assert len(terrain.airports) == 26, (
        f"Afghanistan has {len(terrain.airports)} airfields, expected 26")


# Widest stand on each field, MEASURED off the hand-built export this replaced
# (v1.31.0 - v1.67.0). Not an aspiration and not a round number: this is the
# ramp we already shipped, so an export that comes in under any of it has taken
# capability away.
PRE_SWAP_WIDEST = {
    "Bagram": 60.0, "Bamyan": 41.0, "Bost": 36.0, "Camp Bastion": 60.0,
    "Camp Bastion Heliport": 23.0, "Chaghcharan": 18.0, "Dwyer": 52.0,
    "FOB Salerno": 23.0, "Farah": 40.0, "Gardez": 41.0,
    "Ghazni Heliport": 18.0, "Herat": 40.0, "Jalalabad": 41.0, "Kabul": 61.0,
    "Kandahar": 60.0, "Kandahar Heliport": 34.0, "Khost": 22.0,
    "Maymana Zahiraddin Faryabi": 18.0, "Nimroz": 24.0, "Qala i Naw": 18.0,
    "Sharana": 23.0, "Shindand": 24.0, "Shindand Heliport": 23.0,
    "Tarinkot": 52.0, "Urgoon Heliport": 23.0,
}

# KC-135-capable stands per field, same source. Zero is the honest number on
# most of these — Shindand's widest stand is 41 m even after the swap widened
# it from 24 m, and a Stratotanker does not fit. Recording the zeros is the
# point: a future export that quietly drops Kandahar from 26 to 0 fails here.
PRE_SWAP_HEAVY_STANDS = {
    "Bagram": 8, "Camp Bastion": 12, "Dwyer": 2, "Kabul": 16,
    "Kandahar": 26, "Tarinkot": 2,
}


@pytest.mark.parametrize("name,was", sorted(PRE_SWAP_WIDEST.items()))
def test_no_stand_got_narrower_in_the_swap(terrain, name, was):
    """Every airframe we place — the player via `builder._fitting_slots`, the
    heavies via the v1.47.0 footprint rule — is seated by comparing its width
    to a stand's. If an export narrows stands, aircraft stop fitting and the
    failure is a silent fallback to another field, not an error."""
    widest = max((s.width or 0) for s in terrain.airports[name].parking_slots)
    assert widest >= was, (
        f"{name}'s widest stand went {was} m -> {widest} m; the export took "
        f"ramp capability away")


@pytest.mark.parametrize("name,was", sorted(PRE_SWAP_HEAVY_STANDS.items()))
def test_the_heavies_can_still_park(terrain, name, was):
    """The product promise from v1.47.0, restated against the new data."""
    now = len(terrain.airports[name].free_parking_slots(planes.KC_135))
    assert now >= was, (
        f"{name} went from {was} KC-135-capable stands to {now}")


def test_the_utc_offset_survived_the_swap(terrain):
    """The one adaptation. The fork's `Terrain` has no `utc_offset`; ours
    requires it. Lose it in a future re-vendor and the terrain will not even
    construct — but a silently WRONG offset would just make every mission's
    sun angle wrong, which is why the value is pinned and not merely present."""
    assert terrain.utc_offset.utcoffset(None).total_seconds() == 4.5 * 3600
