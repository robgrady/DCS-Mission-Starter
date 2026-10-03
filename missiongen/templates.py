"""Effective recipe for a curated template in a given era.

A template's `recipe` pins one aircraft. Several templates declare more than one
era, so that pin is a DEFAULT rather than a requirement — and a default that
spans eras has to vary by era. Without this the Library advertised combinations
the engine then refused: "Carrier Qualification, Cold War" handed the builder an
F/A-18C and got an EraViolation, which is how the card appeared broken.

One implementation, used by the tests and by /api/options, so the frontend and
the engine cannot drift on what a card actually builds.
"""
from .resolver import load_json


def templates() -> dict:
    return {k: v for k, v in load_json("mission_templates").items()
            if not k.startswith("_")}


def effective_recipe(key: str, era: str, map_key: str = "") -> dict:
    """The recipe a card really builds: base + per-era override + per-MAP override.

    Also carries `map` when the era override supplies one — a WWII card cannot
    use a default map that has no WWII preset.

    `by_map` IS THE TWIN OF `by_era`, and it exists for the same reason. A card
    that means one thing in one theatre and another thing next door has two
    honest implementations: two hand-authored cards that drift, or one card and
    a per-theatre override. This engine has been bitten enough times by the
    first to have earned the second.

    The order matters. ERA FIRST, THEN MAP: a map override is about the ground
    you are standing on, and the ground does not care which decade it is. If
    both set the same field, the map wins, because the map is the more specific
    fact.
    """
    tpl = templates().get(key) or {}
    rc = dict(tpl.get("recipe") or {})
    rc.update(dict((tpl.get("by_era") or {}).get(era) or {}))
    rc["era"] = era
    rc.setdefault("map", tpl.get("default_map") or "caucasus")
    if map_key:
        rc["map"] = map_key
    rc.update(dict((tpl.get("by_map") or {}).get(rc["map"]) or {}))
    # A by_map block must not move the mission to a different map. Silently
    # honoring `{"by_map": {"sinai": {"map": "germany"}}}` would make the
    # override a teleport, and the caller who asked for Sinai would get
    # Germany with no error.
    rc["map"] = map_key or rc.get("map") or (tpl.get("default_map") or "caucasus")
    if rc.get("bb_carrier") and not rc.get("home_airbase"):
        rc["home_airbase"] = "CARRIER"
    return rc


def maps_for(key: str) -> list:
    """Every map this card may be built on, most-preferred first.

    A card with no `maps` whitelist travels anywhere and advertises only its
    default; a card with one advertises exactly what it lists. An empty list is
    a card nobody can build, so it is treated as unrestricted rather than
    silently disappearing from the Library.
    """
    tpl = templates().get(key) or {}
    listed = list(tpl.get("maps") or [])
    default = tpl.get("default_map") or "caucasus"
    if not listed:
        return [default]
    return ([default] + [m for m in listed if m != default]) \
        if default in listed else listed


def advertised_combinations():
    """(key, era) for every combination a card offers the user. The set a test
    must prove actually builds."""
    for k, v in templates().items():
        for era in (v.get("eras") or []):
            yield k, era
