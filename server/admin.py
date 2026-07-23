"""Admin section — sponsor-ad management.

Password-gated (ADMIN_PASSWORD env var) UI + endpoints to manage the sponsor
library that feeds the mission-launch splash. See missiongen/sponsors.py and
the design doc `claude/sponsor-ads-design.md`.

Auth is a signed session cookie (HMAC over ADMIN_PASSWORD); no accounts. If
ADMIN_PASSWORD is unset the whole section is disabled (returns a notice), so a
misconfigured deploy can never expose an open admin.
"""
from __future__ import annotations

import os
import time
import json
import hmac
import base64
import hashlib
import html

from fastapi import APIRouter, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, PlainTextResponse

from missiongen import sponsors

router = APIRouter(tags=["admin"])

_COOKIE = "ss_admin"
_TTL = 7 * 24 * 3600


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def _password() -> str:
    return os.environ.get("ADMIN_PASSWORD", "")


def _configured() -> bool:
    return bool(_password())


def _sign(payload_b: bytes) -> str:
    return hmac.new(_password().encode(), payload_b, hashlib.sha256).hexdigest()


def _make_token() -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"exp": int(time.time()) + _TTL}).encode())
    return payload.decode() + "." + _sign(payload)


def _valid(tok: str) -> bool:
    try:
        payload_s, sig = tok.split(".", 1)
        payload_b = payload_s.encode()
        if not hmac.compare_digest(_sign(payload_b), sig):
            return False
        return json.loads(base64.urlsafe_b64decode(payload_b)).get("exp", 0) > time.time()
    except Exception:
        return False


def _authed(request: Request) -> bool:
    if not _configured():
        return False
    tok = request.cookies.get(_COOKIE)
    return bool(tok and _valid(tok))


def _set_cookie(resp, request: Request):
    resp.set_cookie(_COOKIE, _make_token(), max_age=_TTL, httponly=True,
                    samesite="lax", secure=(request.url.scheme == "https"))
    return resp


def _redirect(path="/admin"):
    return RedirectResponse(path, status_code=303)


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #
_STYLE = """
<style>
:root{--bg:#0d1117;--panel:#161b22;--panel2:#1c2330;--line:#2a3441;--text:#e6edf3;
--dim:#8b98a5;--accent:#ffb020;--green:#3fb8af;--danger:#e5534b}
*{box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--text);
font-family:-apple-system,Segoe UI,Roboto,sans-serif;font-size:14px;line-height:1.5}
.wrap{max-width:860px;margin:0 auto;padding:28px 20px 80px}
h1{font-size:22px;margin:0 0 4px} h1 .am{color:var(--accent)}
.sub{color:var(--dim);margin:0 0 24px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin-bottom:18px}
.card h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--dim);margin:0 0 14px}
label{display:block;font-size:12px;color:var(--dim);margin:10px 0 4px}
input[type=text],input[type=url],input[type=password],input[type=number]{width:100%;padding:9px 11px;
background:var(--panel2);border:1px solid var(--line);border-radius:8px;color:var(--text);font-size:14px}
input[type=file]{color:var(--dim);font-size:13px}
button,.btn{background:var(--accent);color:#0b0e11;font-weight:700;border:none;border-radius:8px;
padding:9px 16px;font-size:13px;cursor:pointer}
.btn.ghost{background:none;border:1px solid var(--line);color:var(--dim);font-weight:500}
.btn.danger{background:none;border:1px solid rgba(229,83,75,.5);color:var(--danger);font-weight:500}
.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.sp{display:flex;gap:14px;align-items:center;padding:12px 0;border-top:1px solid var(--line)}
.sp:first-of-type{border-top:none}
.thumb{width:120px;height:70px;object-fit:contain;background:#11161d;border:1px solid var(--line);border-radius:8px;flex:none}
.sp .meta{flex:1;min-width:0} .sp .meta b{font-size:15px}
.sp .meta small{color:var(--dim);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.badge{display:inline-block;background:rgba(63,184,175,.16);color:var(--green);border-radius:20px;
padding:2px 10px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.imp{color:var(--accent);font-weight:700}
form.inline{display:inline}
.note{color:var(--dim);font-size:12px;margin-top:6px}
.toggle{padding:8px 14px;border-radius:8px;border:1px solid var(--line)}
.toggle.on{border-color:rgba(63,184,175,.5);color:var(--green)}
.flash{background:rgba(255,176,32,.12);border:1px solid rgba(255,176,32,.4);color:var(--accent);
border-radius:8px;padding:10px 14px;margin-bottom:16px;font-size:13px}
hr{border:none;border-top:1px solid var(--line);margin:16px 0}
</style>
"""


def _page(body: str) -> HTMLResponse:
    return HTMLResponse(f"<!doctype html><meta charset=utf-8><meta name=viewport "
                        f'content="width=device-width,initial-scale=1">'
                        f"<title>SortieStarter Admin</title>{_STYLE}<div class=wrap>{body}</div>")


def _not_configured() -> HTMLResponse:
    return _page(
        "<h1>Admin</h1><div class=card><p>The admin section isn't configured yet.</p>"
        "<p class=note>Set an <code>ADMIN_PASSWORD</code> environment variable on the "
        "server (e.g. <code>fly secrets set ADMIN_PASSWORD=…</code>) and reload.</p></div>")


def _login_page(msg: str = "") -> HTMLResponse:
    flash = f"<div class=flash>{html.escape(msg)}</div>" if msg else ""
    return _page(
        f"<h1>SortieStarter <span class=am>Admin</span></h1>"
        f"<p class=sub>Sign in to manage sponsor ads.</p>{flash}"
        "<div class=card><form method=post action='/admin/login'>"
        "<label>Password</label><input type=password name=password autofocus>"
        "<div style='margin-top:14px'><button type=submit>Sign in</button></div>"
        "</form></div>")


def _dashboard(msg: str = "") -> HTMLResponse:
    m = sponsors.list_sponsors()
    active = m.get("active")
    enabled = m.get("branding_enabled", True)
    flash = f"<div class=flash>{html.escape(msg)}</div>" if msg else ""

    # global branding toggle
    tstate = "on" if enabled else ""
    tlabel = "Sponsor ads: ON" if enabled else "Sponsor ads: OFF"
    toggle = (
        f"<div class=card><h2>Global</h2><div class=row>"
        f"<span class='toggle {tstate}'>{tlabel}</span>"
        f"<form class=inline method=post action='/admin/branding'>"
        f"<input type=hidden name=enabled value='{0 if enabled else 1}'>"
        f"<button class='btn ghost' type=submit>{'Turn off' if enabled else 'Turn on'}</button></form>"
        f"<span class=note>When off, missions ship with no logo splash at all.</span>"
        f"</div></div>")

    # sponsor list
    rows = []
    for sid, sp in m.get("sponsors", {}).items():
        is_active = (sid == active)
        badge = "<span class=badge>Active</span>" if is_active else (
            f"<form class=inline method=post action='/admin/sponsors/{sid}/activate'>"
            f"<button class='btn ghost' type=submit>Set active</button></form>")
        src = html.escape(sp.get("source_url") or "uploaded file")
        refresh = (f"<form class=inline method=post action='/admin/sponsors/{sid}/refresh'>"
                   f"<button class='btn ghost' type=submit>Refresh</button></form>"
                   if sp.get("source_url") else "")
        rows.append(
            f"<div class=sp>"
            f"<img class=thumb src='/admin/sponsors/{sid}/thumb.png?v={sp.get('impressions',0)}'>"
            f"<div class=meta><b>{html.escape(sp.get('name', sid))}</b>"
            f"<small>{src}</small>"
            f"<small>size {sp.get('splash_size',30)}% · <span class=imp>{sp.get('impressions',0)}</span> impressions</small>"
            f"</div>"
            f"<div class=row style='flex:none'>{badge}{refresh}"
            f"<form class=inline method=post action='/admin/sponsors/{sid}/delete' "
            f"onsubmit=\"return confirm('Delete this sponsor?')\">"
            f"<button class='btn danger' type=submit>Delete</button></form></div>"
            f"</div>")
    sp_list = "".join(rows) or "<p class=note>No sponsors yet — add one below.</p>"

    add_form = (
        "<div class=card><h2>Add a sponsor</h2>"
        "<form method=post action='/admin/sponsors' enctype='multipart/form-data'>"
        "<label>Name</label><input type=text name=name placeholder='Pimax' required>"
        "<label>Logo image URL (https)</label>"
        "<input type=url name=url placeholder='https://…/logo.png'>"
        "<label>…or upload a file</label><input type=file name=file accept='image/*'>"
        "<div class=row style='margin-top:12px'>"
        "<div style='flex:1'><label>Splash size (% of screen)</label>"
        "<input type=number name=splash_size value=30 min=5 max=100></div>"
        "<div style='flex:1'><label>Panel opacity (0–255)</label>"
        "<input type=number name=panel_opacity value=90 min=0 max=255></div></div>"
        "<label style='margin-top:12px'><input type=checkbox name=make_active value=1 checked> "
        "Make this the active sponsor</label>"
        "<div style='margin-top:14px'><button type=submit>Add sponsor</button></div>"
        "<p class=note>The logo is pulled/processed server-side (background knocked out, "
        "placed on a translucent panel) and baked into every mission's launch splash.</p>"
        "</form></div>")

    logout = ("<form class=inline method=post action='/admin/logout'>"
              "<button class='btn ghost' type=submit>Sign out</button></form>")

    return _page(
        f"<h1>SortieStarter <span class=am>Sponsor Ads</span></h1>"
        f"<p class=sub>One sponsor is active at a time; it shows on the mission-launch "
        f"splash. {logout}</p>{flash}{toggle}"
        f"<div class=card><h2>Sponsors</h2>{sp_list}</div>{add_form}")


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@router.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request):
    if not _configured():
        return _not_configured()
    if not _authed(request):
        return _login_page()
    return _dashboard()


@router.post("/admin/login")
def admin_login(request: Request, password: str = Form("")):
    if not _configured():
        return _not_configured()
    if hmac.compare_digest(password, _password()):
        return _set_cookie(_redirect("/admin"), request)
    return _login_page("Incorrect password.")


@router.post("/admin/logout")
def admin_logout():
    resp = _redirect("/admin")
    resp.delete_cookie(_COOKIE)
    return resp


@router.post("/admin/sponsors")
def admin_add(request: Request, name: str = Form(...), url: str = Form(""),
              splash_size: int = Form(30), panel_opacity: int = Form(90),
              make_active: str = Form(""), file: UploadFile = File(None)):
    if not _authed(request):
        return _redirect("/admin")
    image_bytes = None
    if file is not None and file.filename:
        image_bytes = file.file.read()
    url = (url or "").strip() or None
    try:
        sponsors.add_sponsor(name, url=url, image_bytes=image_bytes,
                             splash_size=int(splash_size), panel_opacity=int(panel_opacity),
                             make_active=bool(make_active))
        msg = f"Added “{name}”."
    except ValueError as e:
        msg = f"Couldn't add sponsor: {e}"
    return _flash_redirect(msg)


@router.post("/admin/sponsors/{sid}/activate")
def admin_activate(request: Request, sid: str):
    if not _authed(request):
        return _redirect("/admin")
    try:
        sponsors.set_active(sid)
        msg = "Active sponsor updated."
    except ValueError as e:
        msg = str(e)
    return _flash_redirect(msg)


@router.post("/admin/sponsors/{sid}/refresh")
def admin_refresh(request: Request, sid: str):
    if not _authed(request):
        return _redirect("/admin")
    try:
        sponsors.refresh_sponsor(sid)
        msg = "Logo refreshed from source URL."
    except ValueError as e:
        msg = f"Refresh failed: {e}"
    return _flash_redirect(msg)


@router.post("/admin/sponsors/{sid}/delete")
def admin_delete(request: Request, sid: str):
    if not _authed(request):
        return _redirect("/admin")
    sponsors.delete_sponsor(sid)
    return _flash_redirect("Sponsor deleted.")


@router.post("/admin/branding")
def admin_branding(request: Request, enabled: int = Form(1)):
    if not _authed(request):
        return _redirect("/admin")
    sponsors.set_branding_enabled(bool(int(enabled)))
    return _flash_redirect("Branding " + ("enabled." if int(enabled) else "disabled."))


@router.get("/admin/sponsors/{sid}/thumb.png")
def admin_thumb(request: Request, sid: str):
    if not _authed(request):
        return PlainTextResponse("Unauthorized", status_code=401)
    path = sponsors.cache_path(sid)
    if not path.exists():
        return PlainTextResponse("Not found", status_code=404)
    return FileResponse(str(path), media_type="image/png")


# Flash messages via a short-lived query param would need session state; keep it
# simple — re-render the dashboard directly with the message.
def _flash_redirect(msg: str):
    # Render dashboard inline (303 to /admin would drop the message). Requires a
    # valid session which the caller already checked.
    return _dashboard(msg)
