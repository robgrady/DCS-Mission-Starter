"""Product analytics — what missions get made, never who made them.

The privacy contract (claude/analytics-plan.md, PRD v2 §B): each event records
the MISSION's shape — kind, source, template, map, era, aircraft, slots,
threat tier — plus an ANONYMOUS visitor id, and a timestamp. The record schema
below is the entire universe of what can be logged; there is deliberately no
free-form field.

About the visitor id (v1.43.0): a random UUID the browser generates and keeps
in localStorage. It is not derived from anything about the person — no IP, no
user agent, no fingerprint — so it identifies a BROWSER, not a human, and only
so we can answer "how many people, and do they come back?". It is stored
here HASHED (truncated SHA-256 with a server-side salt), so the log cannot be
used to look anyone up even if the raw id were known. Visitors can turn it off
in the app; the client then sends nothing and events log visitor=None. A
browser sending Do Not Track is treated as opted out without being asked.

Storage: JSONL, one file per month, under ANALYTICS_DATA_DIR (point it at the
Fly volume — /data/analytics — or it defaults to ./instance/analytics, which is
ephemeral in a container; same pattern as the sponsor store). Files are tiny
(one short line per generate); `_prune` caps retention at 6 months.
"""
from __future__ import annotations

import os
import json
import hashlib
import secrets
import threading
import datetime as _dt
from pathlib import Path

DATA_DIR = Path(os.environ.get(
    "ANALYTICS_DATA_DIR", str(Path(__file__).parent.parent / "instance" / "analytics")))

KINDS = ("generate", "brief", "dl", "pack")
SOURCES = ("builder", "library", "quick", "share", "api")
RETAIN_MONTHS = 6

_lock = threading.Lock()

# Server-side salt for hashing visitor ids. Persisted next to the events so it
# survives restarts (a rotating salt would fragment every returning visitor
# into a new person). Kept OUT of the log itself: without it the stored hashes
# cannot be reversed or matched against a known id.
_salt_cache: dict = {}


def _salt() -> str:
    """Read (or mint) the salt from the CURRENT data dir. Resolved per call
    rather than at import so the path always follows DATA_DIR."""
    f = DATA_DIR / ".visitor_salt"
    key = str(f)
    if key not in _salt_cache:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            if f.exists():
                _salt_cache[key] = f.read_text().strip()
            else:
                val = secrets.token_hex(16)
                f.write_text(val)
                _salt_cache[key] = val
        except OSError:
            _salt_cache[key] = "ephemeral"
    return _salt_cache[key]


def _hash_visitor(v) -> str | None:
    """Anonymous id -> short salted hash. None stays None (opted out)."""
    if not v:
        return None
    v = str(v)[:64]
    return hashlib.sha256((_salt() + v).encode()).hexdigest()[:16]


def _month_file(ts: _dt.datetime) -> Path:
    return DATA_DIR / f"events-{ts:%Y%m}.jsonl"


def _prune() -> None:
    """Keep at most RETAIN_MONTHS monthly files. Best-effort."""
    try:
        files = sorted(DATA_DIR.glob("events-*.jsonl"))
        for f in files[:-RETAIN_MONTHS]:
            f.unlink()
    except OSError:
        pass


def record(kind: str, source: str, recipe, visitor: str | None = None) -> None:
    """Append one event. Best-effort: analytics must NEVER fail a generate."""
    try:
        if kind not in KINDS:
            return
        if source not in SOURCES:
            source = "api"
        ts = _dt.datetime.now(_dt.timezone.utc)
        line = json.dumps({
            "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "kind": kind,
            "source": source,
            "visitor": _hash_visitor(visitor),
            "template": getattr(recipe, "template", None),
            "map": getattr(recipe, "map", None),
            "era": getattr(recipe, "era", None),
            "aircraft": getattr(recipe, "aircraft", None),
            "slots": getattr(recipe, "slots", 1),
            "threat_tier": getattr(recipe, "threat_tier", None),
        })
        with _lock:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(_month_file(ts), "a", encoding="utf-8") as f:
                f.write(line + "\n")
            _prune()
    except Exception:
        pass  # never let telemetry break the product


def _iter_events(days: int | None):
    cutoff = None
    if days is not None:
        cutoff = (_dt.datetime.now(_dt.timezone.utc)
                  - _dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        files = sorted(DATA_DIR.glob("events-*.jsonl"))
    except OSError:
        return
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                for line in f:
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if cutoff and e.get("ts", "") < cutoff:
                        continue
                    yield e
        except OSError:
            continue


def people(days: int = 30) -> dict:
    """Who-scale metrics from the anonymous visitor id: how many distinct
    browsers, how many came back, how much each builds. Counts only — the id
    is a salted hash of a random UUID, so 'who' remains unanswerable."""
    first_seen: dict = {}
    last_seen: dict = {}
    per_visitor: dict = {}
    days_active: dict = {}
    anon = 0
    total = 0
    for e in _iter_events(days):
        if e.get("kind") != "generate":
            continue
        total += 1
        v = e.get("visitor")
        if not v:
            anon += 1
            continue
        ts = e.get("ts", "")
        first_seen[v] = min(first_seen.get(v, ts), ts)
        last_seen[v] = max(last_seen.get(v, ts), ts)
        per_visitor[v] = per_visitor.get(v, 0) + 1
        days_active.setdefault(v, set()).add(ts[:10])

    n = len(per_visitor)
    returning = sum(1 for v in days_active if len(days_active[v]) > 1)
    # "new this period" = first ever event inside the window. Approximated on
    # the window itself, so a long window is the honest one to read.
    window_start = (_dt.datetime.now(_dt.timezone.utc)
                    - _dt.timedelta(days=days)).strftime("%Y-%m-%d")
    new = sum(1 for v in first_seen if first_seen[v][:10] >= window_start)
    counts = sorted(per_visitor.values(), reverse=True)
    return {
        "days": days,
        "visitors": n,
        "returning": returning,
        "returning_pct": round(100 * returning / n) if n else 0,
        "new": new,
        "avg_missions": round(sum(counts) / n, 1) if n else 0,
        "median_missions": counts[len(counts) // 2] if counts else 0,
        "top_builder_missions": counts[0] if counts else 0,
        "one_and_done_pct": round(100 * sum(1 for c in counts if c == 1) / n) if n else 0,
        "opted_out_events": anon,
        "opted_out_pct": round(100 * anon / total) if total else 0,
        # distribution buckets for a tiny histogram
        "buckets": [
            ("1 mission", sum(1 for c in counts if c == 1)),
            ("2-4", sum(1 for c in counts if 2 <= c <= 4)),
            ("5-9", sum(1 for c in counts if 5 <= c <= 9)),
            ("10+", sum(1 for c in counts if c >= 10)),
        ],
    }


def stats(days: int = 30) -> dict:
    """Aggregate view for the admin Analytics tab. Counts only."""
    per_day: dict = {}
    top = {"template": {}, "aircraft": {}, "map": {}, "era": {}}
    sources: dict = {}
    kinds: dict = {}
    mp = 0
    total = 0
    for e in _iter_events(days):
        kinds[e.get("kind", "?")] = kinds.get(e.get("kind", "?"), 0) + 1
        if e.get("kind") != "generate":
            continue
        total += 1
        day = e.get("ts", "")[:10]
        per_day[day] = per_day.get(day, 0) + 1
        sources[e.get("source", "?")] = sources.get(e.get("source", "?"), 0) + 1
        if (e.get("slots") or 1) > 1:
            mp += 1
        for dim in top:
            v = e.get(dim)
            key = v if v else ("(custom)" if dim == "template" else "?")
            top[dim][key] = top[dim].get(key, 0) + 1

    def _top(d, n=10):
        return sorted(d.items(), key=lambda kv: -kv[1])[:n]

    briefs = kinds.get("brief", 0)
    return {
        "days": days,
        "generates": total,
        "briefs": briefs,
        "share_dls": kinds.get("dl", 0),
        "brief_attach_pct": round(100 * briefs / total) if total else 0,
        "multiplayer_pct": round(100 * mp / total) if total else 0,
        "per_day": sorted(per_day.items()),
        "sources": sorted(sources.items(), key=lambda kv: -kv[1]),
        "top_templates": _top(top["template"]),
        "top_aircraft": _top(top["aircraft"]),
        "top_maps": _top(top["map"]),
        "top_eras": _top(top["era"]),
    }
