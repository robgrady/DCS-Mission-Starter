"""Pending-module support: aircraft that pydcs has no native class for yet.

Covers both released modules newer than the vendored pydcs (e.g. the F-14B(U),
whose real type id is verified from an in-sim survey) and any not-yet-shipped
module. A pending aircraft inherits flight data from its closest released airframe
and uses the DCS type id from pending_aircraft.json; a `verified` entry generates
cleanly, an unverified one attaches a "not released yet" warning.

This keeps FR-1 (full roster, including day-one support for new modules) honest with
FR-2 (never silently produce a broken .miz): the type id is explicit and one JSON
edit away from corrected.
"""
from .resolver import load_json, resolve

_registry = {}


def pending_aircraft() -> dict:
    return load_json("pending_aircraft")


def get_pending(key: str):
    """Return (PlaneType subclass, warning) for a pending aircraft key, or (None, None)."""
    cfg = pending_aircraft().get(key)
    if not cfg:
        return None, None
    if key not in _registry:
        base = resolve(cfg["inherits"])
        cls = type(key, (base,), {"id": cfg["provisional_id"]})
        _registry[key] = cls
        # register so pydcs can serialize/deserialize the type name
        try:
            import dcs.planes as planes
            planes.plane_map[cfg["provisional_id"]] = cls
        except Exception:
            pass
    if cfg.get("verified"):
        warning = (f"{cfg['label']}: verified DCS type id '{cfg['provisional_id']}' "
                   f"(flight model inherits {cfg['inherits']} until pydcs adds a "
                   f"native class).")
    else:
        warning = (f"{cfg['label']}: module not released yet - using provisional DCS type id "
                   f"'{cfg['provisional_id']}' (inherits {cfg['inherits']} flight data). "
                   f"Verify/update pending_aircraft.json when Heatblur ships.")
    return _registry[key], warning
