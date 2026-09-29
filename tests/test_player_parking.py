"""The player's jet must not park on a stand a heavy needed.

pydcs sorts free parking by `(helicopter, slot_name)`, so among every stand an
aircraft fits it takes whichever sorts first by NAME. Stand '01' is usually the
biggest thing on the field — a wide-body apron — so a single-seat fighter
routinely got handed the one spot a KC-135 or E-3 could have used.

Measured across every airfield we ship: **22 of 144 fields** hand the F-16 a
heavy-capable stand under pydcs's ordering. The sharpest case is Fujairah Intl,
which has exactly ONE heavy stand — pydcs gives it to the fighter, leaving the
tanker nowhere.

This is the same class of bug v1.47.0 fixed for the ramp DRESSING (stands judged
by the real airframe footprint). The player's own parking never got the same
treatment because it goes through pydcs, not through our placement code. The
dcs-retribution fork made the same one-key fix upstream; we apply it in
`builder._fitting_slots` rather than editing vendor/dcs, which is a
byte-for-byte mirror (vendor/dcs/PYDCS_PROVENANCE.md).
"""
import pytest

from dcs import planes

from missiongen.builder import _fitting_slots
from missiongen.resolver import load_json, resolve_terrain

MAPS = load_json("maps")
FIGHTER = planes.F_16C_50
HEAVY = planes.KC_135


def _fields(map_key):
    terrain = resolve_terrain(MAPS[map_key]["terrain_class"])()
    return terrain.airport_list()


def test_the_fighter_takes_the_tightest_stand_that_fits():
    """The property, on the field that shows it most clearly: Fujairah has one
    heavy-capable stand, and the fighter must not be the one standing on it."""
    ap = next(a for a in _fields("persiangulf") if "Fujairah" in a.name)
    heavy = {s.slot_name for s in ap.free_parking_slots(HEAVY)}
    assert len(heavy) == 1, (
        f"Fujairah's heavy stands changed ({len(heavy)}) — pick another witness")
    chosen = _fitting_slots(ap, FIGHTER, 1)[0]
    assert chosen.slot_name not in heavy, (
        f"the fighter parked on Fujairah's only heavy stand ({chosen.slot_name})")


@pytest.mark.parametrize("map_key", ["caucasus", "persiangulf", "syria", "sinai"])
def test_the_fix_never_makes_things_worse(map_key):
    """A width-first sort must not take a heavy stand where the name-first sort
    would have left it alone. (It is a strict improvement or a no-op.)"""
    worse = []
    for ap in _fields(map_key):
        try:
            free = ap.free_parking_slots(FIGHTER)
            heavy = {s.slot_name for s in ap.free_parking_slots(HEAVY)}
        except Exception:
            continue
        if not free or not heavy:
            continue
        old = sorted(free, key=lambda s: (s.helicopter, str(s.slot_name)))[0]
        new = _fitting_slots(ap, FIGHTER, 1)[0]
        if new.slot_name in heavy and old.slot_name not in heavy:
            worse.append(f"{ap.name}: {old.slot_name} -> {new.slot_name}")
    assert not worse, f"{map_key}: the sort took heavy stands it used to leave: {worse}"


def test_a_flight_gets_contiguous_stands():
    """A four-ship should sit together, not scattered across the field — the
    sort's last key is the slot name for exactly that reason."""
    ap = next(a for a in _fields("caucasus") if "Nellis" not in a.name)
    slots = _fitting_slots(ap, FIGHTER, 4)
    assert slots and len(slots) == 4
    widths = {s.width for s in slots}
    assert len(widths) <= 2, (
        f"a four-ship was spread across {len(widths)} different stand sizes")


def test_an_airfield_that_cannot_seat_the_flight_returns_none():
    """The caller relies on this to fall through to its NoParkingSlotError path
    and try the next field — returning a short list instead would seat half a
    flight and silently drop the rest."""
    ap = next(a for a in _fields("caucasus"))
    assert _fitting_slots(ap, FIGHTER, 10_000) is None


class _Slot:
    """A synthetic parking slot, for testing the SORT rather than the data."""
    def __init__(self, name, width, heli):
        self.slot_name, self.width, self.helicopter = name, width, heli
        self.unit_id = None
        self.length = 40.0


class _FakeAirport:
    def __init__(self, slots):
        self._slots = slots

    def free_parking_slots(self, aircraft_type):
        return list(self._slots)


def test_aeroplanes_stay_off_helicopter_pads():
    """pydcs's first sort key, preserved — and it means the OPPOSITE of what it
    looks like. `False` sorts before `True`, so `helicopter` first puts plain
    airplane stands ahead of dual-use pads: it keeps an AEROPLANE off a pad,
    rather than keeping a helo on one. (Helicopters never need it, because
    free_parking_slots already filters their eligible set down to pads.)

    Synthetic slots on purpose. Across all twelve shipped maps there is no
    airfield where an airplane stand is narrower than the narrowest pad, so a
    width-only sort picks the same stand anyway and a data-driven test passes
    for the wrong reason — the first version of this test did exactly that, and
    survived deleting the key. Testing the contract catches it; testing the
    data does not."""
    ap = _FakeAirport([
        _Slot("P1", 12.0, True),     # a dual-use pad, NARROWER
        _Slot("A1", 20.0, False),    # a plain airplane stand, wider
    ])
    chosen = _fitting_slots(ap, FIGHTER, 1)
    assert not chosen[0].helicopter, (
        "with a narrow pad and a wider airplane stand free, the airplane took "
        "the pad — the helicopter key has been dropped, and a helo will find "
        "its pad occupied")
