"""The flight flies under a callsign DCS can say.

WHY
---
DCS's radio speaks a fixed table. For every western air force in the sim
the fighter pool is eight names — Enfield, Springfield, Uzi, Colt, Dodge,
Ford, Chevy, Pontiac — and ATC, AWACS and your AI wingmen will use one of
those whatever the paperwork says. Every commercial campaign on the shelf
lives with this: Reflected's "ROCKET 11" is voiced in 300 clips and flies as
Dodge in the file; 75 of 97 missions in the corpus scan carry a stock name
under a voiced one. Our v1.91.0 self-check flagged the same gap in our own
briefs and Rob's call was: always map. The paperwork uses the name you will
hear.

WHAT SURVIVES
-------------
The authentic callsign (VF-32 "Gypsy", the Jolly Rogers' "Victory", Misty
for the Hun — callsigns.json) is not thrown away. It becomes the squadron's
heritage line in the brief: "the squadron's own callsign is Gypsy; DCS
speaks eight, so you fly as Colt". Same for a name the user types. A name
that is already one of the eight is used as typed.

THE MAPPING IS STABLE. "Gypsy" always becomes the same DCS name, in every
mission, on every map, so a pilot who flies VF-32 learns one radio name.
It is a hash of the authentic name, not the seed.

THE INDEX MATTERS. DCS reads callsign[1] (the position in its table), not
the "name" string, which the Editor merely derives. pydcs writes the name
and leaves [1] at 1 — so a mission that says "Springfield11" in its name
field is announced as ENFIELD in the sim. `apply()` sets both.
"""
from __future__ import annotations

import zlib


def pool() -> list[str]:
    """DCS's western fighter callsign table, read from pydcs (one source)."""
    try:
        from dcs.countries import USA
        names = list(USA.callsign.get("Air") or [])
    except Exception:                                     # pragma: no cover
        names = []
    return names or ["Enfield", "Springfield", "Uzi", "Colt",
                     "Dodge", "Ford", "Chevy", "Pontiac"]


def is_bort(name: str | None) -> bool:
    """Soviet/WP practice: the callsign IS the side number."""
    return bool(name) and str(name).strip().isdigit()


def dcs_name(wanted: str | None) -> str:
    """The DCS-speakable name for a wanted callsign. Stable per input."""
    names = pool()
    w = (wanted or "").strip()
    if not w:
        return names[0]
    for n in names:
        if n.lower() == w.lower():
            return n
    return names[zlib.crc32(w.lower().encode("utf-8")) % len(names)]


def heritage_line(wanted: str | None, used: str, squadron: str | None = None) -> str | None:
    """The one brief sentence that keeps the real name. None when identical."""
    w = (wanted or "").strip()
    if not w or w.lower() == used.lower():
        return None
    who = f"{squadron}'s own callsign" if squadron else "The squadron's own callsign"
    return (f"{who} is {w}. DCS's radio speaks only its eight names, so you "
            f"fly as {used.upper()} — that is what ATC, AWACS and your wingmen "
            f"will say.")


def apply(group, name: str) -> None:
    """Put `name` on every unit of the group so the sim announces it.

    Western: callsign[1] = index in the pool (what DCS actually reads),
    [2] = flight 1, [3] = position, "name" = the derived string.
    Bort number: the integer itself, lead first, +1 per wingman.
    Never raises — a mis-set callsign is a cosmetic defect, a failed build is not.
    """
    try:
        units = list(getattr(group, "units", []) or [])
        if is_bort(name):
            base = int(str(name).strip())
            for i, u in enumerate(units):
                u.callsign = base + i
                u.callsign_dict = {1: 1, 2: 1, 3: i + 1, "name": ""}
            return
        names = pool()
        used = dcs_name(name)
        idx = names.index(used) + 1
        for i, u in enumerate(units, start=1):
            u.callsign = None
            u.callsign_dict = {1: idx, 2: 1, 3: i, "name": f"{used}1{i}"}
    except Exception:
        return
