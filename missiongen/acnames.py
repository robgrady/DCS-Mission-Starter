"""Aircraft display names for the DOCUMENT pipeline (brief PDF/MD, kneeboard).

The UI fixed raw type ids ("FA_18C_hornet") back in UX Tier 1; this brings the
same fix to everything printed. aircraft_names.json is extracted from the
frontend's AC_NAME table — one vocabulary, two renderers. clean_id() is a port
of the frontend's acCleanId(): strip the redundant popular-name tail, turn
underscores into the hyphen sub-variant separator DCS itself uses.
"""
import re
from functools import lru_cache

from .resolver import load_json


@lru_cache(maxsize=1)
def _names() -> dict:
    try:
        return load_json("aircraft_names")
    except Exception:
        return {}


def clean_id(type_id: str, popular: str | None = None) -> str:
    s = str(type_id or "")
    if popular:
        # "FA-18C_hornet" + "Hornet" -> "FA-18C". First word only, so
        # "Warthog II" does not try to eat the "II" off "A-10C_2".
        tail = re.escape(popular.split(" ")[0])
        s = re.sub(rf"[_ ]{tail}$", "", s, flags=re.I)
    s = s.replace("_", "-")
    s = re.sub(r"-{2,}", "-", s).rstrip("-")
    return s or str(type_id or "")


def display(key: str, type_id: str | None = None) -> str:
    """'FA_18C_hornet' -> 'FA-18C · Hornet'. Falls back to a cleaned id."""
    name = _names().get(key)
    tid = type_id or key
    return f"{clean_id(tid, name)} · {name}" if name else clean_id(tid, None)


def designation(key: str, type_id: str | None = None) -> str:
    """Short form: cleaned designation only ('FA-18C')."""
    return clean_id(type_id or key, _names().get(key))
