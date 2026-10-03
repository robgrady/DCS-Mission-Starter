"""DCS Sortie Starter — API server.

Run:  uvicorn server.app:app --reload
Then open http://127.0.0.1:8000
"""
import hashlib
import logging
import os
import secrets
import time as _time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from missiongen import __version__
from missiongen import contact as contact_store

log = logging.getLogger("missionstarter")


router = APIRouter()

_CONTACT_SECRET = os.environ.get("CONTACT_SECRET") or secrets.token_hex(16)


_CONTACT_MIN_SECONDS = 3


_CONTACT_TOKEN_TTL = 60 * 60 * 4          # a form left open over lunch still works


_CONTACT_HOURLY, _CONTACT_DAILY = 5, 20


_contact_hits: dict = {}


def _contact_sign(issued: int) -> str:
    import hmac as _hmac
    return _hmac.new(_CONTACT_SECRET.encode(), str(issued).encode(),
                     hashlib.sha256).hexdigest()[:32]


def _contact_rate_ok(ip: str) -> bool:
    """Token bucket keyed by IP. The IP lives in this dict and nowhere else —
    it is never persisted, which is what keeps the no-PII stance true even
    though this endpoint accepts personal data by design."""
    now = _time.time()
    hits = [t for t in _contact_hits.get(ip, []) if now - t < 86400]
    if len(hits) >= _CONTACT_DAILY:
        return False
    if len([t for t in hits if now - t < 3600]) >= _CONTACT_HOURLY:
        return False
    hits.append(now)
    _contact_hits[ip] = hits
    if len(_contact_hits) > 4096:         # bound the dict; oldest keys go
        for k in list(_contact_hits)[:1024]:
            _contact_hits.pop(k, None)
    return True


class ContactRequest(BaseModel):
    name: str = ""
    email: str = ""
    topic: str = ""
    comment: str = ""
    context: dict | None = None
    issued: int = 0
    sig: str = ""
    website: str = ""          # honeypot: labelled plausibly, hidden in CSS


@router.get("/api/contact/token")
def api_contact_token():
    """Issued when the form opens; proves on submit that a human spent time
    in it. Signed so the client cannot backdate itself."""
    issued = int(_time.time())
    return {"issued": issued, "sig": _contact_sign(issued),
            "topics": [{"value": t, "label": contact_store.TOPIC_LABELS[t]}
                       for t in contact_store.TOPICS],
            "max_comment": contact_store.MAX_COMMENT}


@router.post("/api/contact")
def api_contact(req: ContactRequest, request: Request):
    accepted = {"ok": True}               # the shape every rejection mimics
    # 1. honeypot
    if req.website.strip():
        log.info("contact: honeypot")
        return accepted
    # 2. signed issue-time
    import hmac as _hmac
    if not _hmac.compare_digest(req.sig or "", _contact_sign(req.issued)):
        log.info("contact: bad token")
        return accepted
    age = _time.time() - req.issued
    if age < _CONTACT_MIN_SECONDS or age > _CONTACT_TOKEN_TTL:
        log.info("contact: token age %.1fs", age)
        return accepted
    # 3. rate limit — the one rejection the user is told about, because a real
    # person hitting it needs to know their message did not go through
    ip = (request.client.host if request.client else "?") or "?"
    if not _contact_rate_ok(ip):
        raise HTTPException(status_code=429,
                            detail="That's a lot of messages in a short time. "
                                   "Please try again later.")
    errors = contact_store.validate(req.name, req.email, req.topic, req.comment)
    if errors:
        return JSONResponse(status_code=422, content={"ok": False, "errors": errors})
    ctx = dict(req.context or {})
    ctx["version"] = __version__          # server-stamped: a client-supplied
                                          # version in a bug report is worthless
    mid = contact_store.add(req.name, req.email, req.topic, req.comment, ctx)
    if not mid:
        raise HTTPException(status_code=500,
                            detail="We couldn't save that message. Please try again.")
    log.info("contact: stored %s (%s)", mid, req.topic)
    return {"ok": True}

