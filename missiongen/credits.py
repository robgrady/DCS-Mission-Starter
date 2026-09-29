"""Thanks — the people whose work this product leans on.

WHY THIS IS RUNTIME DATA AND NOT A FILE IN THE REPO.

`docs/SOURCES.md` is the product's bibliography: pinned commits, licenses,
historical citations. It lives in the repo because it must be versioned,
reviewed and guarded — `tests/test_sources.py` asserts it byte-for-byte against
its generated page, and `scripts/release.sh` rebuilds it.

Thanks are a different kind of thing. They are a *living list*, curated by the
person who actually knows the community, and they change between releases. Put
them in `SOURCES.md` and two bad things happen: the owner cannot add a name
without a deploy, and anything edited on the server is overwritten by the next
release. So they live here — on the same `/data` volume as sponsors and the
contact inbox, managed from the password-gated `/admin`, and injected into the
served Sources page at request time.

The split is the point: **cited facts are versioned, gratitude is editable.**

Storage is a single small JSON manifest, mirroring `missiongen/sponsors.py`.
No database, because this is a list of names.
"""
from __future__ import annotations

import json
import os
import re
import threading
import uuid
from pathlib import Path

# Override with CREDITS_DATA_DIR (e.g. /data/credits on a Fly volume). The
# default is writable inside the container but ephemeral without a volume —
# same contract as sponsors.py, and the reason the seed below exists.
DATA_DIR = Path(os.environ.get(
    "CREDITS_DATA_DIR", str(Path(__file__).parent.parent / "instance" / "credits")))
_MANIFEST = DATA_DIR / "credits.json"

_lock = threading.RLock()

NAME_MAX = 80
NOTE_MAX = 400
URL_MAX = 300

# Seeded on first run so a fresh deploy is never a blank page. These are
# starting points for the owner to correct, not researched claims — the whole
# reason this is admin-editable is that Rob knows this community and I do not.
SEED = [
    {"name": "Eagle Dynamics",
     "note": "For DCS World itself, and for the terrain teams whose maps this "
             "tool exists to fill. Not affiliated with them.",
     "url": "https://www.digitalcombatsimulator.com/"},
    {"name": "The pydcs authors",
     "note": "pydcs (LGPL-3.0) is the mission-file framework everything here "
             "is built on. Vendored unmodified.",
     "url": "https://github.com/pydcs/dcs"},
    {"name": "The DCS Retribution team",
     "note": "Their pydcs fork is where the Iraq and Afghanistan terrain "
             "packages came from.",
     "url": "https://github.com/dcs-retribution/pydcs"},
    {"name": "Sedlo",
     "note": "Campaign author (Bold Cheetah and others). The bar for what a "
             "hand-built DCS mission should feel like.",
     "url": "https://forum.dcs.world/profile/61874-sedlo/"},
    {"name": "Stewmanji",
     "note": "For the community teaching work that gets people from installed "
             "to actually flying.",
     "url": "https://forum.dcs.world/profile/75641-stewmanji/"},
    {"name": "The MOOSE project",
     "note": "Their airbase enum is the independent list we cross-check our "
             "terrain exports against.",
     "url": "https://github.com/FlightControl-Master/MOOSE"},
]


def _clean(s, limit: int) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\r", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit]


def _clean_url(u: str) -> str:
    """https/http only. A credits entry is rendered as a link on a public page,
    so a `javascript:` or `data:` URL here is stored XSS with a friendly face."""
    u = _clean(u, URL_MAX)
    if not u:
        return ""
    if not re.match(r"^https?://[^\s]+$", u, re.I):
        return ""
    return u


def _read() -> list:
    try:
        with open(_MANIFEST, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write(rows: list) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _MANIFEST.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
    tmp.replace(_MANIFEST)


def load() -> list:
    """Every credit, in display order. Seeds on first read so the page is never
    empty on a fresh deploy."""
    with _lock:
        rows = _read()
        if not rows and not _MANIFEST.exists():
            rows = [dict(id=uuid.uuid4().hex[:12], order=i * 10, **c)
                    for i, c in enumerate(SEED)]
            try:
                _write(rows)
            except Exception:
                pass            # read-only filesystem: serve the seed anyway
        return sorted(rows, key=lambda r: (r.get("order", 0), r.get("name", "")))


def add(name: str, note: str = "", url: str = "") -> str | None:
    name = _clean(name, NAME_MAX)
    if not name:
        return None
    with _lock:
        rows = _read() or load()
        cid = uuid.uuid4().hex[:12]
        rows.append({"id": cid, "name": name, "note": _clean(note, NOTE_MAX),
                     "url": _clean_url(url),
                     "order": max([r.get("order", 0) for r in rows] or [0]) + 10})
        _write(rows)
        return cid


def update(cid: str, name=None, note=None, url=None, order=None) -> bool:
    with _lock:
        rows = _read() or load()
        for r in rows:
            if r.get("id") != cid:
                continue
            if name is not None:
                cleaned = _clean(name, NAME_MAX)
                if not cleaned:
                    return False        # a nameless credit is not a credit
                r["name"] = cleaned
            if note is not None:
                r["note"] = _clean(note, NOTE_MAX)
            if url is not None:
                r["url"] = _clean_url(url)
            if order is not None:
                try:
                    r["order"] = int(order)
                except (TypeError, ValueError):
                    pass
            _write(rows)
            return True
        return False


def delete(cid: str) -> bool:
    with _lock:
        rows = _read() or load()
        keep = [r for r in rows if r.get("id") != cid]
        if len(keep) == len(rows):
            return False
        _write(keep)
        return True


def restore_seed() -> int:
    """Put the shipped list back. The way out of 'I deleted everything'."""
    with _lock:
        rows = [dict(id=uuid.uuid4().hex[:12], order=i * 10, **c)
                for i, c in enumerate(SEED)]
        _write(rows)
        return len(rows)
