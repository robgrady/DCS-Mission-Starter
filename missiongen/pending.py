"""Pending-module support: aircraft announced/pre-order but not yet in pydcs.

A pending aircraft inherits flight data from its closest released airframe and uses a
provisional DCS type id. Selecting one works end-to-end, but generation attaches a
warning until the real id is confirmed on release day (edit pending_aircraft.json).

This keeps FR-1 (full roster, including day-one support for new modules) honest with
FR-2 (never silently produce a broken .miz): the risk is explicit, loud, and one JSON
edit away from resolved.
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
    warning = (f"{cfg['label']}: module not released yet - using provisional DCS type id "
               f"'{cfg['provisional_id']}' (inherits {cfg['inherits']} flight data). "
               f"Verify/update pending_aircraft.json when Heatblur ships.")
    return _registry[key], warning
