"""Contact messages — the product's only inbound channel.

The analytics ledger deliberately cannot tell us who anyone is (see
analytics.py). That is the right call for telemetry and the wrong shape for
"the Syria map crashed for me on Tuesday", so this module is the other half:
a small store for messages people CHOSE to send us, kept entirely separate
from the anonymous ledger so the anonymous ledger stays anonymous.

Storage: JSONL, one file per month, under CONTACT_DATA_DIR (point it at the
Fly volume — /data/contact — or it defaults to ./instance/contact, which is
ephemeral in a container; same pattern as analytics and the sponsor store).

APPEND-ONLY, including mutations. Marking a message read appends
{"id": ..., "op": "read"} rather than rewriting the line in place; `load()`
folds the ops over the base records. Rewriting a line inside a JSONL file is
where data loss lives — a truncated write costs you every message in the
month, and this file is the one thing in the product a user cannot regenerate
by pressing the button again.

Privacy posture: this is the ONE store that holds personal data, by the
user's own choice and with the form saying so. Email is optional and exists
only so Rob can reply. No IP address is ever written here — the submit
endpoint's rate limiter uses one transiently and discards it.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import secrets
import threading
from pathlib import Path

DATA_DIR = Path(os.environ.get(
    "CONTACT_DATA_DIR", str(Path(__file__).parent.parent / "instance" / "contact")))

TOPICS = ("bug", "feature", "mission", "other")
TOPIC_LABELS = {"bug": "Bug report", "feature": "Feature request",
                "mission": "Mission / content idea", "other": "Something else"}

# Field bounds. Enforced HERE as well as at the API edge, because a validation
# rule that lives only in the request handler is a rule the next caller skips.
MAX_NAME = 80
MAX_EMAIL = 254          # RFC 5321 practical maximum
MIN_COMMENT = 10
MAX_COMMENT = 4000

_lock = threading.Lock()


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _month_file(ts: _dt.datetime) -> Path:
    return DATA_DIR / f"messages-{ts:%Y%m}.jsonl"


def new_id(ts: _dt.datetime | None = None) -> str:
    """Time-sortable unique id: <utc compact>-<random>. Sorting by id sorts by
    arrival, which is what the inbox wants, and no counter file exists to get
    out of sync with the data."""
    ts = ts or _now()
    return f"{ts:%Y%m%d%H%M%S}-{secrets.token_hex(4)}"


def _clean(s, limit: int) -> str:
    """Trim, cap, and strip control characters. Control bytes in a name are
    either a broken client or someone probing the log format; neither belongs
    in a file the admin renders."""
    s = "" if s is None else str(s)
    s = "".join(ch for ch in s if ch == "\n" or ch == "\t" or ord(ch) >= 0x20)
    return s.strip()[:limit]


def validate(name, email, topic, comment) -> dict:
    """Returns {field: message} — empty dict means valid.

    Shared by the API and the store so both agree on what a message is.
    """
    errors = {}
    name = _clean(name, MAX_NAME + 1)
    comment = _clean(comment, MAX_COMMENT + 1)
    email = _clean(email, MAX_EMAIL + 1)
    if not name:
        errors["name"] = "Please tell us your name."
    elif len(name) > MAX_NAME:
        errors["name"] = f"Please keep your name under {MAX_NAME} characters."
    if topic not in TOPICS:
        errors["topic"] = "Please choose what this is about."
    if len(comment) < MIN_COMMENT:
        errors["comment"] = f"Please write at least {MIN_COMMENT} characters."
    elif len(comment) > MAX_COMMENT:
        errors["comment"] = f"Please keep it under {MAX_COMMENT} characters."
    # Email is OPTIONAL by design (see docs/contact-form-spec.md §2.2):
    # requiring it costs us the anonymous bug reports, which are the most
    # useful messages we get. Validated only when actually supplied.
    if email:
        if len(email) > MAX_EMAIL or email.count("@") != 1:
            errors["email"] = "That email address doesn't look right."
        else:
            local, _, domain = email.partition("@")
            if not local or "." not in domain or domain.startswith(".") \
                    or domain.endswith(".") or " " in email:
                errors["email"] = "That email address doesn't look right."
    return errors


def add(name, email, topic, comment, context=None) -> str | None:
    """Append one message. Returns its id, or None if it could not be stored.

    Unlike analytics.record (best-effort by contract, because telemetry must
    never fail a generate), a failure HERE matters: the user was told their
    message was sent. The caller gets None and tells them the truth.
    """
    errors = validate(name, email, topic, comment)
    if errors:
        return None
    ts = _now()
    mid = new_id(ts)
    rec = {
        "id": mid,
        "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "name": _clean(name, MAX_NAME),
        "email": _clean(email, MAX_EMAIL) or None,
        "topic": topic,
        "comment": _clean(comment, MAX_COMMENT),
        "context": _clean_context(context),
        "read": False,
        "read_at": None,
    }
    with _lock:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(_month_file(ts), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    return mid


def _clean_context(context) -> dict:
    """Auto-captured, disclosed-to-the-user context (spec §2.3). Whitelisted:
    a bug report needs a version, and this must never become a free-form
    channel for whatever a client feels like posting."""
    c = context if isinstance(context, dict) else {}
    out = {}
    for key, limit in (("version", 20), ("view", 20), ("recipe", 400)):
        v = _clean(c.get(key), limit)
        out[key] = v or None
    return out


def _op(mid: str, op: str) -> bool:
    """Append a mutation record. See the module docstring on why this is not
    an in-place rewrite."""
    ts = _now()
    try:
        with _lock:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(_month_file(ts), "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": mid, "op": op,
                                    "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ")}) + "\n")
        return True
    except OSError:
        return False


def mark_read(mid: str, read: bool = True) -> bool:
    return _op(mid, "read" if read else "unread")


def delete(mid: str) -> bool:
    return _op(mid, "delete")


def load(topic: str | None = None, unread_only: bool = False) -> list:
    """All live messages, newest first, with ops folded in.

    A corrupt or truncated line is SKIPPED, not fatal: a half-written line
    (power loss mid-append) must cost one message, not the whole inbox.
    """
    base: dict = {}
    ops: list = []
    try:
        files = sorted(DATA_DIR.glob("messages-*.jsonl"))
    except OSError:
        return []
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue          # truncated/corrupt line — skip it
                    if not isinstance(rec, dict) or not rec.get("id"):
                        continue
                    if rec.get("op"):
                        ops.append(rec)
                    else:
                        base[rec["id"]] = rec
        except OSError:
            continue
    # Ops are applied in file/line order, so the LAST op for a message wins —
    # read then unread leaves it unread, which is what the admin clicked.
    for o in ops:
        rec = base.get(o["id"])
        if not rec:
            continue
        if o["op"] == "delete":
            base.pop(o["id"], None)
        elif o["op"] == "read":
            rec["read"], rec["read_at"] = True, o.get("ts")
        elif o["op"] == "unread":
            rec["read"], rec["read_at"] = False, None
    out = sorted(base.values(), key=lambda r: r["id"], reverse=True)
    if topic in TOPICS:
        out = [r for r in out if r.get("topic") == topic]
    if unread_only:
        out = [r for r in out if not r.get("read")]
    return out


def get(mid: str):
    for r in load():
        if r["id"] == mid:
            return r
    return None


def unread_count() -> int:
    """Drives the admin tab badge — an inbox you must open to discover is
    empty is an inbox nobody opens."""
    return sum(1 for r in load() if not r.get("read"))


def counts() -> dict:
    msgs = load()
    return {"total": len(msgs),
            "unread": sum(1 for r in msgs if not r.get("read")),
            "by_topic": {t: sum(1 for r in msgs if r.get("topic") == t)
                         for t in TOPICS}}


def prune(months: int = 24) -> int:
    """Delete monthly files older than `months`. NOT automatic and not called
    on write: expiring somebody's bug report on a timer is a decision, so it
    stays a command someone runs. Returns files removed."""
    try:
        files = sorted(DATA_DIR.glob("messages-*.jsonl"))
    except OSError:
        return 0
    n = 0
    for f in files[:-months] if months > 0 else files:
        try:
            f.unlink()
            n += 1
        except OSError:
            pass
    return n
