"""Determinism patches for vendored pydcs.

A recipe + seed MUST reproduce the mission byte-for-byte ACROSS processes — a
share link is a semver contract ("MAJOR = breaking share links"). pydcs has two
sources of per-process nondeterminism, both independent of our seeded rng:

1. `Country.next_onboard_num` builds a set of tail-number STRINGS and `.pop()`s
   one. Set iteration order for strings depends on PYTHONHASHSEED, which CPython
   randomises per process — so every uvicorn restart / autoscaled machine /
   share-link recipient got different modex numbers. Fixed here by taking
   `min()` (stable, ascending, still skips reserved numbers).

2. `UnitGroup.add_runway_waypoint(..., distance=random.randrange(6000, 8000, 100))`
   evaluates its default ONCE at import, freezing a random value for the process
   that no later `seed()` can touch. Fixed at the ONLY call site
   (`ambient.add_ambient_traffic`) by passing `distance` from the seeded rng —
   no pydcs edit needed. This module documents it; the fix lives there.

Import this module for its import side effect before generating anything.
"""
from dcs.country import Country


def _deterministic_next_onboard_num(self) -> str:
    free = {"{:03}".format(x) for x in range(10, 999)} - self._tail_numbers
    tailnum = min(free)                 # stable order, unlike set.pop()
    self.reserve_onboard_num(tailnum)
    return tailnum


# idempotent: patch once
if getattr(Country.next_onboard_num, "__name__", "") != "_deterministic_next_onboard_num":
    Country.next_onboard_num = _deterministic_next_onboard_num
