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
import re
import logging
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request, Form, File, UploadFile
from fastapi.responses import (HTMLResponse, RedirectResponse, FileResponse,
                               PlainTextResponse, Response)

from missiongen import sponsors

router = APIRouter(tags=["admin"])
log = logging.getLogger("sortiestarter.admin")

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
.repl{display:inline-block;margin:0;padding:8px 14px;border:1px solid var(--line);
border-radius:8px;color:var(--dim);font-size:13px;cursor:pointer}
.repl:hover{border-color:var(--accent);color:var(--accent)}
.repl input[type=file]{display:none}
.toggle{padding:8px 14px;border-radius:8px;border:1px solid var(--line)}
.toggle.on{border-color:rgba(63,184,175,.5);color:var(--green)}
.flash{background:rgba(255,176,32,.12);border:1px solid rgba(255,176,32,.4);color:var(--accent);
border-radius:8px;padding:10px 14px;margin-bottom:16px;font-size:13px}
hr{border:none;border-top:1px solid var(--line);margin:16px 0}
.atabs{display:flex;gap:22px;border-bottom:1px solid var(--line);margin-bottom:22px}
.atabs a{color:var(--dim);text-decoration:none;font-size:13px;font-weight:600;
text-transform:uppercase;letter-spacing:.06em;padding:8px 2px;border-bottom:2px solid transparent}
.atabs a.on{color:var(--text);border-bottom-color:var(--accent)}
.atabs a.backapp{margin-left:auto;color:var(--accent);text-transform:none;
letter-spacing:0;font-weight:500}
.atabs a.backapp:hover{text-decoration:underline}
table.stats{width:100%;border-collapse:collapse;font-size:13px}
table.stats th{text-align:left;color:var(--dim);font-size:11px;text-transform:uppercase;
letter-spacing:.05em;padding:6px 8px;border-bottom:1px solid var(--line)}
table.stats td{padding:6px 8px;border-bottom:1px solid var(--line)}
table.stats td.n{text-align:right;font-variant-numeric:tabular-nums;color:var(--accent);font-weight:700}
.bigrow{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:4px}
.big{flex:1;min-width:130px;background:var(--panel2);border:1px solid var(--line);
border-radius:10px;padding:12px 16px}
.big b{display:block;font-size:24px;color:var(--accent)}
.big small{color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:.05em}
.bar{height:9px;background:var(--accent);border-radius:3px;display:inline-block;vertical-align:middle}
.daybar{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--dim);padding:2px 0}
.daybar span.d{width:78px;flex:none;font-variant-numeric:tabular-nums}
.daybar span.v{width:34px;text-align:right;font-variant-numeric:tabular-nums;color:var(--text)}
.tbadge{display:inline-block;background:var(--accent);color:#0b0e11;border-radius:20px;
padding:0 7px;margin-left:6px;font-size:11px;font-weight:800;vertical-align:middle}
/* Unread is marked by WEIGHT + a left rule + the word "new", not by color
   alone — the same redundancy rule the product side follows. */
.msg{border-top:1px solid var(--line);padding:14px 0 14px 14px;border-left:3px solid transparent}
.msg:first-of-type{border-top:none}
.msg.unread{border-left-color:var(--accent);background:rgba(255,176,32,.04)}
.msg.unread .who{font-weight:800}
.msg .who{font-size:15px}
.msg .when{color:var(--dim);font-size:12px;font-variant-numeric:tabular-nums}
.msg .topic{display:inline-block;border:1px solid var(--line);border-radius:20px;
padding:1px 9px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--dim)}
.msg .new{color:var(--accent);font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.06em}
.msg .body{white-space:pre-wrap;margin:8px 0 10px;line-height:1.55}
.msg .ctx{color:var(--dim);font-size:12px;font-family:ui-monospace,monospace;margin-bottom:10px}
.msg summary{cursor:pointer;color:var(--dim);font-size:13px}
.msg a.mail{color:var(--green);text-decoration:none;font-size:13px}
.msg a.mail:hover{text-decoration:underline}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px}
.filters a{color:var(--dim);text-decoration:none;font-size:12px;border:1px solid var(--line);
border-radius:20px;padding:4px 12px}
.filters a.on{color:var(--text);border-color:var(--accent)}
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
        "server (e.g. <code>fly secrets set ADMIN_PASSWORD=…</code>) and reload.</p></div>"
        "<p><a href='/' style='color:var(--accent)'>↩ Back to Sortie Starter</a></p>")


def _login_page(msg: str = "") -> HTMLResponse:
    flash = f"<div class=flash>{html.escape(msg)}</div>" if msg else ""
    return _page(
        f"<h1>SortieStarter <span class=am>Admin</span></h1>"
        f"<p class=sub>Sign in to manage sponsor ads.</p>{flash}"
        "<div class=card><form method=post action='/admin/login'>"
        "<label>Password</label><input type=password name=password autofocus>"
        "<div style='margin-top:14px'><button type=submit>Sign in</button></div>"
        "</form></div>"
        "<p><a href='/' style='color:var(--accent)'>↩ Back to Sortie Starter</a></p>")


def _tabs(active: str) -> str:
    """Admin tab bar + the way home. The admin was a navigational dead end —
    tabs between its own sections but no route back to the product."""
    def a(href, key, label):
        cls = " class=on" if key == active else ""
        return f"<a href='{href}'{cls}>{label}</a>"
    # The Contact tab carries its unread count: an inbox you have to open to
    # discover is empty is an inbox nobody opens.
    try:
        from missiongen import contact as _contact
        n = _contact.unread_count()
    except Exception:
        n = 0
    badge = f"<span class=tbadge>{n}</span>" if n else ""
    return ("<div class=atabs>" + a("/admin", "sponsors", "Sponsor ads")
            + a("/admin/packs", "packs", "Mission packs")
            + a("/admin/analytics", "analytics", "Analytics")
            + a("/admin/contact", "contact", "Contact" + badge)
            + a("/admin/roadmap", "roadmap", "Roadmap")
            + a("/admin/changelog", "changelog", "Changelog")
            + a("/admin/credits", "credits", "Thanks")
            + "<a href='/' class=backapp>↩ Back to Sortie Starter</a></div>")


def _packs_page(msg: str = "") -> HTMLResponse:
    from missiongen import packs as _packs
    flash = f"<div class=flash>{html.escape(msg)}</div>" if msg else ""
    rows = []
    for man in _packs.list_packs():
        ev = man.get("events", [])
        img = (f"<img class=thumb src='/api/pack/{man['id']}/{man['image']}'>"
               if man.get("image") else "<div class=thumb></div>")
        derived = ("<small style='color:var(--accent)'>manifest auto-detected "
                   "from the files</small>" if man.get("derived") else
                   "<small>pack.json supplied</small>")
        rows.append(
            f"<div class=sp>{img}<div class=meta>"
            f"<b>{html.escape(man.get('label') or man['id'])}</b>"
            f"<small>id <code>{man['id']}</code> · {len(ev)} mission"
            f"{'s' if len(ev) != 1 else ''} · {man.get('size_mb', '?')} MB · "
            f"Library tab: {html.escape(man.get('role', 'training'))}</small>"
            f"{derived}</div>"
            f"<div class=row style='flex:none'>"
            f"<a class='btn ghost' style='text-decoration:none' "
            f"href='/api/pack/{man['id']}/all.zip'>Download</a>"
            f"<form class=inline method=post action='/admin/packs/{man['id']}/delete' "
            f"onsubmit=\"return confirm('Remove this pack? Missions stay on your "
            f"computer; this only removes it from the site.')\">"
            f"<button class='btn danger' type=submit>Remove</button></form>"
            f"</div></div>")
    lst = "".join(rows) or ("<p class=note>No packs installed. Drop one below — "
                            "it appears in the Library immediately, and survives "
                            "deploys.</p>")
    return _page(
        f"<h1>SortieStarter <span class=am>Admin</span></h1>"
        f"<p class=sub>Curated mission collections. Uploaded here, stored on the "
        f"server's volume — never in the code, so adding content needs no deploy.</p>"
        + _tabs("packs") + flash +
        f"<div class=card><h2>Installed packs</h2>{lst}</div>"
        "<div class=card><h2>Add a pack</h2>"
        "<form id=pack-upload method=post action='/admin/packs' enctype='multipart/form-data'>"
        "<label>Pack file</label>"
        # .sspack FIRST, and it must be here at all. `packs.install` has
        # accepted it since format 2, but this attribute did not — so the file
        # picker grayed out the one extension `scripts/build_pack.py` produces
        # and the only way in was to rename the product's own output.
        "<input type=file name=file accept='.sspack,.zip,.miz' required>"
        "<p class=note>A <b>.sspack</b> built by <code>scripts/build_pack.py</code> "
        "— manifest, missions, briefs and guide, already checked. Also accepted: "
        "a <b>.zip</b> of missions (any folder layout — documents "
        "and card art welcome), or a single <b>.miz</b>. If the zip contains a "
        "<code>pack.json</code> it is used as-is; otherwise one is built by "
        "reading the missions — pairing each with its brief by number, detecting "
        "the theater, and using any image found as the card art.</p>"
        "<div class=row style='margin-top:10px'>"
        "<div style='flex:1'><label>Pack id (optional)</label>"
        "<input type=text name=pack_id placeholder='from the file name'></div>"
        "<div style='flex:2'><label>Card title (optional)</label>"
        "<input type=text name=label placeholder='from pack.json or the id'></div>"
        "</div>"
        "<div style='margin-top:14px'><button type=submit>Upload pack</button></div>"
        "<p class=note>Re-uploading the same id replaces it.</p>"
        "</form></div>" + _pack_upload_script())


def _pack_upload_script():
    # fly-replay buffers at most 1 MB. Pin the upload before sending its body.
    # https://docs.fly.io/networking/dynamic-request-routing#requirements-and-limitations
    owner = os.environ.get('PACKS_OWNER_MACHINE')
    if not owner:
        return ''
    return """<script>
const uploadForm = document.getElementById('pack-upload');
uploadForm.addEventListener('submit', async event => {
  event.preventDefault();
  const button = uploadForm.querySelector('button');
  button.disabled = true; button.textContent = 'Uploading…';
  try {
    const response = await fetch(uploadForm.action, {method:'POST',
      body:new FormData(uploadForm), headers:{'Fly-Force-Instance-Id':OWNER}});
    if (response.redirected) { location.assign(response.url); return; }
    const page = await response.text();
    document.open(); document.write(page); document.close();
  } catch (error) {
    button.disabled = false; button.textContent = 'Retry upload';
    const message = document.createElement('p');
    message.textContent = 'Upload failed. Please try again.';
    uploadForm.appendChild(message);
  }
});
</script>""".replace('OWNER', json.dumps(owner))


def _credits_page(msg: str = "") -> HTMLResponse:
    """The Thanks list, editable here rather than in the repo.

    `docs/SOURCES.md` carries the CITATIONS — commits, licenses, historical
    sources — and is a guarded build artifact. Gratitude is a living list that
    the owner curates without a deploy, so it lives on the volume and is
    injected into /api/sources when that page is served."""
    from missiongen import credits as _cr
    flash = f"<div class=flash>{html.escape(msg)}</div>" if msg else ""
    rows = []
    for c in _cr.load():
        cid = html.escape(c.get("id", ""))
        rows.append(
            f"<div class=sp><div class=meta style='flex:1'>"
            f"<form class=inline method=post action='/admin/credits/{cid}' "
            f"style='display:block'>"
            f"<div class=row>"
            f"<div style='flex:2'><label>Name</label>"
            f"<input type=text name=name value=\"{html.escape(c.get('name',''))}\" "
            f"maxlength=80 required></div>"
            f"<div style='flex:1'><label>Order</label>"
            f"<input type=text name=order value=\"{int(c.get('order',0))}\"></div>"
            f"</div>"
            f"<label>What you are thanking them for</label>"
            f"<input type=text name=note maxlength=400 "
            f"value=\"{html.escape(c.get('note',''))}\">"
            f"<label>Link (optional, https only)</label>"
            f"<input type=text name=url maxlength=300 "
            f"value=\"{html.escape(c.get('url',''))}\">"
            f"<div style='margin-top:10px'><button type=submit>Save</button></div>"
            f"</form></div>"
            f"<div class=row style='flex:none;align-items:flex-start'>"
            f"<form class=inline method=post action='/admin/credits/{cid}/delete' "
            f"onsubmit=\"return confirm('Remove this credit?')\">"
            f"<button class='btn danger' type=submit>Remove</button></form>"
            f"</div></div>")
    lst = "".join(rows) or "<p class=note>Nobody thanked yet.</p>"
    return _page(
        "<h1>SortieStarter <span class=am>Admin</span></h1>"
        "<p class=sub>Who gets thanked on the public Sources page. Lives on the "
        "server's volume, so adding a name needs no deploy — and a release will "
        "not overwrite it.</p>"
        + _tabs("credits") + flash +
        f"<div class=card><h2>Thanks</h2>"
        "<p class=note>Lowest <b>order</b> shows first. The citations themselves "
        "&mdash; pinned commits, licenses, historical sources &mdash; are in the "
        "repository at <code>docs/SOURCES.md</code> and are not editable here, "
        "on purpose: those need to be versioned and reviewed.</p>"
        f"{lst}</div>"
        "<div class=card><h2>Add someone</h2>"
        "<form method=post action='/admin/credits'>"
        "<label>Name</label><input type=text name=name maxlength=80 required>"
        "<label>What you are thanking them for</label>"
        "<input type=text name=note maxlength=400 "
        "placeholder='Be specific &mdash; a vague thank-you reads as filler'>"
        "<label>Link (optional, https only)</label>"
        "<input type=text name=url maxlength=300 placeholder='https://...'>"
        "<div style='margin-top:14px'><button type=submit>Add</button></div>"
        "</form></div>"
        "<div class=card><h2>Start over</h2>"
        "<form method=post action='/admin/credits/restore' "
        "onsubmit=\"return confirm('Replace the whole list with the shipped one?')\">"
        "<p class=note>Puts the shipped list back. The way out of deleting "
        "everything.</p>"
        "<button class='btn ghost' type=submit>Restore the shipped list</button>"
        "</form></div>")


def _analytics_page(days: int = 30) -> HTMLResponse:
    from missiongen import analytics
    s = analytics.stats(days)

    def table(title, rows, label):
        body = "".join(f"<tr><td>{html.escape(str(k))}</td><td class=n>{v}</td></tr>"
                       for k, v in rows) or "<tr><td colspan=2>—</td></tr>"
        return (f"<div class=card><h2>{title}</h2><table class=stats>"
                f"<tr><th>{label}</th><th style='text-align:right'>generates</th></tr>"
                f"{body}</table></div>")

    # `default=` only fires on an EMPTY sequence — a non-empty list of zeros
    # still yields 0, which is what took the whole page down with a 500 (the
    # buckets list is always four entries, all zero before anyone has built a
    # mission with a visitor id). Trailing `or 1` is the guard that matters.
    peak = max((v for _, v in s["per_day"]), default=1) or 1
    days_html = "".join(
        f"<div class=daybar><span class=d>{d}</span>"
        f"<span class=bar style='width:{max(3, round(240 * v / peak))}px'></span>"
        f"<span class=v>{v}</span></div>"
        for d, v in s["per_day"][-21:]) or "<p class=note>No generates recorded yet.</p>"

    ranges = " · ".join(
        f"<b>{days}d</b>" if d == days else f"<a href='/admin/analytics?days={d}' "
        f"style='color:var(--dim)'>{d}d</a>" for d in (7, 30, 90, 180))

    pe = analytics.people(days)
    peak_b = max((v for _, v in pe["buckets"]), default=1) or 1
    if pe["visitors"]:
        dist = "".join(
            f"<div class=daybar><span class=d>{lab}</span>"
            f"<span class=bar style='width:{max(3, round(200 * v / peak_b))}px'></span>"
            f"<span class=v>{v}</span></div>" for lab, v in pe["buckets"])
    else:
        # Four zero-length bars is not a chart, it's clutter that reads like a
        # broken page. Say why it's empty instead — the usual reason is that
        # the events pre-date v1.43.0, when the anonymous id didn't exist yet.
        dist = ("<p class=note>No missions in this window can be attributed to "
                "a browser yet. Events recorded before v1.43.0 carry no "
                "anonymous id, and browsers that opted out or send Do Not "
                "Track never send one — the totals below still count them.</p>")
    # With nobody to attribute, "0% built exactly one mission" and "busiest
    # browser: 0" are just zeros pretending to be findings. The opted-out count
    # is the one number that still says something, so keep only that.
    if pe["visitors"]:
        notes = (
            f"<p class=note>{pe['one_and_done_pct']}% built exactly one mission and "
            f"haven't returned. Busiest single browser: {pe['top_builder_missions']} "
            f"missions. {pe['opted_out_events']} generate(s) came from browsers that "
            f"opted out or send Do Not Track ({pe['opted_out_pct']}%) — those are "
            f"counted in the totals above but can't be attributed to a person.</p>"
            f"<p class=note>A \"person\" here is a browser that kept its random id: "
            f"clearing site data looks like someone new, and one human on two "
            f"machines looks like two. Read these as a floor, not a headcount.</p>")
    else:
        notes = (f"<p class=note>{pe['opted_out_events']} generate(s) in this "
                 f"window came from browsers that opted out or send Do Not Track "
                 f"({pe['opted_out_pct']}%). They are counted in the totals below.</p>")
    people_card = (
        f"<div class=card><h2>People (anonymous)</h2>"
        f"<div class=bigrow>"
        f"<div class=big><b>{pe['visitors']}</b><small>distinct browsers</small></div>"
        f"<div class=big><b>{pe['returning']}</b><small>came back another day "
        f"({pe['returning_pct']}%)</small></div>"
        f"<div class=big><b>{pe['new']}</b><small>first seen this window</small></div>"
        f"<div class=big><b>{pe['avg_missions']}</b><small>missions per person "
        f"(median {pe['median_missions']})</small></div>"
        f"</div>"
        f"<h2 style='margin-top:16px'>Missions per person</h2>{dist}{notes}"
        f"</div>")

    return _page(
        f"<h1>SortieStarter <span class=am>Admin</span></h1>"
        f"<p class=sub>What gets made, and how many people make it. Missions' shapes "
        f"plus a random per-browser id — no IPs, no accounts, no names "
        f"(see missiongen/analytics.py for the whole schema).</p>"
        + _tabs("analytics") + people_card +
        f"<div class=card><h2>Last {s['days']} days &nbsp; <small>({ranges})</small></h2>"
        f"<div class=bigrow>"
        f"<div class=big><b>{s['generates']}</b><small>missions generated</small></div>"
        f"<div class=big><b>{s['briefs']}</b><small>briefing packs ({s['brief_attach_pct']}% attach)</small></div>"
        f"<div class=big><b>{s['share_dls']}</b><small>share-link downloads</small></div>"
        f"<div class=big><b>{s['multiplayer_pct']}%</b><small>multiplayer (2+ seats)</small></div>"
        f"</div></div>"
        f"<div class=card><h2>Generates per day</h2>{days_html}</div>"
        f"<div class=card><h2>By door</h2><table class=stats>"
        f"<tr><th>source</th><th style='text-align:right'>generates</th></tr>"
        + ("".join(f"<tr><td>{html.escape(k)}</td><td class=n>{v}</td></tr>"
                   for k, v in s["sources"]) or "<tr><td colspan=2>—</td></tr>")
        + "</table></div>"
        + table("Top templates", s["top_templates"], "template")
        + table("Top aircraft", s["top_aircraft"], "aircraft")
        + table("Top maps", s["top_maps"], "map")
        + table("Eras", s["top_eras"], "era"))


def _dashboard(msg: str = "") -> HTMLResponse:
    m = sponsors.list_sponsors()
    active = m.get("active")
    enabled = m.get("branding_enabled", True)
    house = m.get("house_brand", False)
    hstate = "on" if house else ""
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
        f"</div>"
        # The house wordmark used to appear whenever no sponsor was active,
        # which meant a fresh deploy branded every mission with our own logo
        # without anyone choosing it. Opt-in now, and stated plainly.
        f"<div class=row style='margin-top:10px'>"
        f"<span class='toggle {hstate}'>"
        f"{'House logo: ON' if house else 'House logo: OFF'}</span>"
        f"<form class=inline method=post action='/admin/housebrand'>"
        f"<input type=hidden name=enabled value='{0 if house else 1}'>"
        f"<button class='btn ghost' type=submit>"
        f"{'Turn off' if house else 'Turn on'}</button></form>"
        f"<span class=note>Shows the Authentic Media wordmark when no sponsor "
        f"is active. Off by default \u2014 a mission only carries a logo you "
        f"chose to put there.</span>"
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
        # Replace the logo IN PLACE. Deleting and re-adding under the same name
        # re-derives the same slug, so the thumb URL never changed and the
        # browser showed the old image — the "image doesn't change" bug.
        replace = (
            f"<form class=inline method=post action='/admin/sponsors/{sid}/replace' "
            f"enctype='multipart/form-data'>"
            f"<label class=repl>Replace image"
            f"<input type=file name=file accept='image/*' onchange='this.form.submit()'>"
            f"</label></form>")
        rows.append(
            f"<div class=sp>"
            # Bust on the splash file's mtime, not the impression count: the
            # count only moves when a mission is generated, so re-rendering a
            # logo left this URL identical and the browser served the stale PNG.
            f"<img class=thumb src='/admin/sponsors/{sid}/thumb.png"
            f"?v={sponsors.cache_version(sid)}'>"
            f"<div class=meta><b>{html.escape(sp.get('name', sid))}</b>"
            f"<small>{src}</small>"
            f"<small>size {sp.get('splash_size',30)}% · <span class=imp>{sp.get('impressions',0)}</span> impressions</small>"
            f"</div>"
            f"<div class=row style='flex:none'>{badge}{replace}{refresh}"
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
        f"<h1>SortieStarter <span class=am>Admin</span></h1>"
        f"<p class=sub>One sponsor is active at a time; it shows on the mission-launch "
        f"splash. {logout}</p>" + _tabs("sponsors") +
        f"{flash}{toggle}"
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


@router.get("/admin/packs", response_class=HTMLResponse)
def admin_packs(request: Request):
    if not _configured():
        return _not_configured()
    if not _authed(request):
        return _login_page()
    return _packs_page()


@router.post("/admin/packs")
def admin_pack_add(request: Request, pack_id: str = Form(""), label: str = Form(""),
                   file: UploadFile = File(None)):
    if not _authed(request):
        return _redirect("/admin/packs")
    if file is None or not file.filename:
        return _packs_page("Choose a .zip or .miz to upload.")
    from missiongen import packs as _packs
    try:
        man = _packs.install(file.file.read(), file.filename,
                             pack_id=(pack_id or "").strip() or None,
                             label=(label or "").strip() or None)
    except ValueError as e:
        # `PackError` is a ValueError whose message was written for the person
        # holding the file. Anything else gets the generic line, because an
        # internal repr is not an instruction.
        return _packs_page(f"Couldn't install that pack: {e}")
    except Exception:
        return _packs_page("Couldn't install that pack: unreadable upload.")
    # STRAIGHT TO REVIEW. The derived manifest is a good guess and a guess is
    # not authorship: the labels are filenames and the premise is a
    # placeholder. Landing the author on the edit screen is the difference
    # between "it installed" and "it is published".
    return _redirect(f"/admin/packs/{man['id']}/edit")


def _pack_edit_page(pid: str, msg: str = "") -> HTMLResponse:
    """Review and correct what derivation guessed.

    Everything on this form is something a machine cannot know: what the pack
    is called, why somebody should fly it, which war it is, what a pilot must
    own, and what each mission is actually about. Derivation gets the SHAPE
    right — the missions, their pairing with briefs, the terrain read out of
    the file — and stops exactly where authorship begins.
    """
    from missiongen import packs as _packs
    man = _packs.get_manifest(pid)
    if not man:
        return _packs_page("That pack is not installed on this server.")
    lib = man.get("library") or {}
    req = man.get("requires") or {}
    flash = f"<div class=flash>{html.escape(msg)}</div>" if msg else ""

    # NO SHADOWING, BECAUSE THERE IS NOTHING TO SHADOW.
    #
    # This page used to warn that an uploaded pack shared its id with one that
    # ships inside the release, and resolve the two by content version. v1.80.0
    # deleted bundled packs — THE IMAGE CARRIES NO CONTENT, every pack arrives
    # through this form — but the warning stayed, calling `_packs._bundled()`,
    # which went with them. So this page raised AttributeError on the FIRST
    # request after every successful upload: the pack installed, the redirect
    # landed here, and the author was shown an internal error for a pack that
    # was already on the volume. Nothing failed except the report of it.
    #
    # There is no replacement warning. An id collides with another UPLOAD, and
    # that is an overwrite the author is doing on purpose from a list he is
    # looking at.

    def esc(v):
        return html.escape(str(v if v is not None else ""))

    roles = "".join(
        f"<option value='{r}'{' selected' if lib.get('role') == r else ''}>{r}"
        f"</option>" for r in _packs.ROLES)
    rides = []
    for i, e in enumerate(man.get("syllabus") or []):
        f = e.get("files") or {}
        rides.append(
            f"<div class=sp><div class=meta>"
            f"<small><code>{esc(f.get('mission'))}</code>"
            + (f" · brief <code>{esc(f.get('brief'))}</code>"
               if f.get("brief") else " · no brief")
            + "</small>"
            f"<div class=row>"
            f"<input name='n_{i}' value='{esc(e.get('n'))}' style='width:4em' "
            f"aria-label='order'>"
            f"<input name='label_{i}' value='{esc(e.get('label'))}' "
            f"placeholder='Mission title' style='flex:1'>"
            f"</div>"
            f"<input name='premise_{i}' value='{esc(e.get('premise'))}' "
            f"placeholder='One line: what this mission is, and why it matters'>"
            f"</div></div>")

    return _page(
        f"<h1>SortieStarter <span class=am>Admin</span></h1>"
        + _tabs("packs") + flash +
        f"<h2>{esc(man.get('label'))}</h2>"
        f"<p class=note>Derivation read the files and guessed. Everything "
        f"below is something it could not know. When you save, this pack is "
        f"live in the Library exactly as you describe it here — and you can "
        f"<a href='/admin/packs/{pid}/manifest.json'>download the manifest</a> "
        f"to drop back into your folder, so the next upload carries your words "
        f"instead of another guess.</p>"
        f"<form method=post action='/admin/packs/{pid}/edit'>"
        f"<label>Title<input name=label value='{esc(man.get('label'))}'></label>"
        f"<label>Content version <small>— yours, not the app's. Bump it when "
        f"you change the missions.</small>"
        f"<input name=version value='{esc(man.get('version'))}'></label>"
        f"<label>Author<input name=author value='{esc(man.get('author'))}'>"
        f"</label>"
        f"<label>Premise <small>— the card copy. One or two sentences.</small>"
        f"<textarea name=premise rows=3>{esc(lib.get('premise'))}</textarea>"
        f"</label>"
        f"<div class=row>"
        f"<label style='flex:1'>Library tab<select name=role>{roles}</select>"
        f"</label>"
        f"<label style='flex:1'>Threat 1-5"
        f"<input name=threat value='{esc(lib.get('threat'))}'></label>"
        f"<label style='flex:1'>Players"
        f"<input name=players value='{esc(lib.get('players'))}'></label>"
        f"</div>"
        f"<div class=row>"
        f"<label style='flex:1'>Era <small>— coldwar, modern, wot…</small>"
        f"<input name=eras value='{esc(', '.join(lib.get('eras') or []))}'>"
        f"</label>"
        f"<label style='flex:1'>Maps"
        f"<input name=maps value='{esc(', '.join(lib.get('maps') or []))}'>"
        f"</label></div>"
        f"<label>Modules a pilot must own <small>— shown BEFORE the download, "
        f"so nobody buys eleven missions for a terrain they do not have."
        f"</small>"
        f"<input name=modules value='{esc(', '.join(req.get('modules') or []))}'>"
        f"</label>"
        f"<h3>The missions</h3>"
        f"<p class=note>Order and titles. The filenames are shown so you can "
        f"tell which is which; they are never what a pilot sees.</p>"
        + "".join(rides) +
        f"<div class=row><button class='btn prime' type=submit>"
        f"Save and publish</button>"
        f"<a class='btn ghost' style='text-decoration:none' href='/admin/packs'>"
        f"Back</a></div>"
        f"</form>")


@router.get("/admin/packs/{pid}/edit", response_class=HTMLResponse)
def admin_pack_edit(request: Request, pid: str):
    if not _authed(request):
        return _login_page()
    return _pack_edit_page(pid)


@router.get("/admin/packs/{pid}/manifest.json")
def admin_pack_manifest(request: Request, pid: str):
    if not _authed(request):
        return _redirect("/admin/packs")
    from missiongen import packs as _packs
    body = _packs.manifest_bytes(pid)
    if not body:
        return _redirect("/admin/packs")
    return Response(
        content=body, media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="pack.json"'})


@router.post("/admin/packs/{pid}/edit")
async def admin_pack_edit_save(request: Request, pid: str):
    if not _authed(request):
        return _redirect("/admin/packs")
    from missiongen import packs as _packs
    form = await request.form()

    def g(k, default=""):
        return (form.get(k) or default).strip()

    def csv(k):
        return [x.strip() for x in g(k).split(",") if x.strip()]

    man = _packs.get_manifest(pid) or {}
    syl = []
    for i, e in enumerate(man.get("syllabus") or []):
        e = dict(e)
        try:
            e["n"] = int(g(f"n_{i}") or e.get("n") or i + 1)
        except ValueError:
            pass
        e["label"] = g(f"label_{i}") or e.get("label")
        e["premise"] = g(f"premise_{i}")
        syl.append(e)
    syl.sort(key=lambda x: (x.get("n") is None, x.get("n")))

    try:
        threat = max(1, min(5, int(g("threat") or 3)))
    except ValueError:
        threat = 3

    patch = {
        "label": g("label") or man.get("label"),
        "version": g("version") or man.get("version"),
        "author": g("author"),
        "syllabus": syl,
        "library": {"role": g("role"), "threat": threat,
                    "players": g("players") or "SP",
                    "premise": g("premise"),
                    "eras": csv("eras") or None,
                    "maps": csv("maps") or None},
        "requires": {"modules": csv("modules") or None,
                     "terrains": csv("maps") or None},
    }
    try:
        _packs.update_manifest(pid, patch)
    except ValueError as e:
        return _pack_edit_page(pid, f"Could not save: {e}")
    return _packs_page("Saved. It is live in the Library now.")


@router.post("/admin/packs/{pid}/delete")
def admin_pack_delete(request: Request, pid: str):
    if not _authed(request):
        return _redirect("/admin/packs")
    from missiongen import packs as _packs
    _packs.delete(pid)
    return _packs_page("Pack removed.")


@router.get("/admin/credits", response_class=HTMLResponse)
def admin_credits(request: Request):
    if not _configured():
        return _not_configured()
    if not _authed(request):
        return _login_page()
    return _credits_page()


@router.post("/admin/credits")
def admin_credit_add(request: Request, name: str = Form(""), note: str = Form(""),
                     url: str = Form("")):
    if not _authed(request):
        return _redirect("/admin/credits")
    from missiongen import credits as _cr
    if _cr.add(name, note, url):
        return _credits_page(f"Added {name.strip()[:80]}.")
    return _credits_page("A credit needs a name.")


@router.post("/admin/credits/{cid}")
def admin_credit_update(request: Request, cid: str, name: str = Form(""),
                        note: str = Form(""), url: str = Form(""),
                        order: str = Form("")):
    if not _authed(request):
        return _redirect("/admin/credits")
    from missiongen import credits as _cr
    ok = _cr.update(cid, name=name, note=note, url=url, order=order or None)
    return _credits_page("Saved." if ok else
                         "Could not save that — a credit needs a name.")


@router.post("/admin/credits/{cid}/delete")
def admin_credit_delete(request: Request, cid: str):
    if not _authed(request):
        return _redirect("/admin/credits")
    from missiongen import credits as _cr
    _cr.delete(cid)
    return _credits_page("Removed.")


@router.post("/admin/credits/restore")
def admin_credit_restore(request: Request):
    if not _authed(request):
        return _redirect("/admin/credits")
    from missiongen import credits as _cr
    n = _cr.restore_seed()
    return _credits_page(f"Restored the shipped list ({n} entries).")


@router.get("/admin/analytics", response_class=HTMLResponse)
def admin_analytics(request: Request, days: int = 30):
    if not _configured():
        return _not_configured()
    if not _authed(request):
        return _login_page()
    try:
        return _analytics_page(max(1, min(180, days)))
    except Exception as e:
        # A reporting page must never be able to lock the operator out of the
        # admin. A bare 500 says nothing and takes the Sponsor and Packs tabs
        # down with it (they're reached through this page's own tab bar), so
        # render the shell with the reason instead.
        log.exception("admin analytics page failed")
        return _page(
            "<h1>SortieStarter <span class=am>Admin</span></h1>"
            + _tabs("analytics")
            + "<div class=card><h2>Analytics unavailable</h2>"
            "<p class=note>The Analytics view failed to render. Everything else "
            "in the admin still works, and no data was lost — the event ledger "
            "is append-only and untouched by this page.</p>"
            f"<p class=note><code>{html.escape(type(e).__name__)}: "
            f"{html.escape(str(e)[:300])}</code></p></div>")


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


@router.post("/admin/sponsors/{sid}/replace")
def admin_replace(request: Request, sid: str, url: str = Form(""),
                  file: UploadFile = File(None)):
    if not _authed(request):
        return _redirect("/admin")
    image_bytes = None
    if file is not None and file.filename:
        image_bytes = file.file.read()
    try:
        sponsors.replace_image(sid, url=(url or "").strip() or None,
                               image_bytes=image_bytes)
        msg = "Logo replaced — the new image is live on the next mission you build."
    except ValueError as e:
        msg = f"Couldn't replace the image: {e}"
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


@router.post("/admin/housebrand")
def admin_housebrand(request: Request, enabled: int = Form(0)):
    if not _authed(request):
        return _redirect("/admin")
    sponsors.set_house_brand(bool(int(enabled)))
    return _flash_redirect(
        "House logo " + ("enabled." if int(enabled) else "disabled."))


@router.get("/admin/sponsors/{sid}/thumb.png")
def admin_thumb(request: Request, sid: str):
    if not _authed(request):
        return PlainTextResponse("Unauthorized", status_code=401)
    path = sponsors.cache_path(sid)
    if not path.exists():
        return PlainTextResponse("Not found", status_code=404)
    # FileResponse sends an ETag but NO Cache-Control, so a browser is free to
    # reuse the cached PNG without revalidating (RFC 9111 heuristic freshness).
    # That is how a replaced logo kept rendering as the old one. no-cache still
    # allows a 304 against the ETag — it just forbids using it blind.
    return FileResponse(str(path), media_type="image/png",
                        headers={"Cache-Control": "no-cache"})


# Flash messages via a short-lived query param would need session state; keep it
# simple — re-render the dashboard directly with the message.
def _flash_redirect(msg: str):
    # Render dashboard inline (303 to /admin would drop the message). Requires a
    # valid session which the caller already checked.
    return _dashboard(msg)


# --------------------------------------------------------------------------- #
# Contact inbox — the product's only inbound channel (docs/contact-form-spec.md)
# --------------------------------------------------------------------------- #
def _contact_page(topic: str = "", unread: bool = False, msg: str = "") -> HTMLResponse:
    from missiongen import contact as _contact
    flash = f"<div class=flash>{html.escape(msg)}</div>" if msg else ""
    counts = _contact.counts()
    rows = _contact.load(topic=topic or None, unread_only=unread)

    def f(href, on, label):
        return f"<a href='{href}'{' class=on' if on else ''}>{html.escape(label)}</a>"
    filters = ("<div class=filters>"
               + f("/admin/contact", not topic and not unread, f"All ({counts['total']})")
               + f("/admin/contact?unread=1", unread, f"Unread ({counts['unread']})")
               + "".join(f(f"/admin/contact?topic={t}", topic == t,
                           f"{_contact.TOPIC_LABELS[t]} ({counts['by_topic'][t]})")
                         for t in _contact.TOPICS)
               + "</div>")

    out = []
    for r in rows:
        # EVERY user-controlled string is escaped here. This page renders text
        # typed by strangers into an authenticated admin session — it is the
        # one place in the product where an XSS would actually be worth
        # something to an attacker.
        name = html.escape(r.get("name") or "")
        email = html.escape(r.get("email") or "")
        body = html.escape(r.get("comment") or "")
        topic_lbl = html.escape(_contact.TOPIC_LABELS.get(r.get("topic"), r.get("topic") or ""))
        when = html.escape((r.get("ts") or "").replace("T", " ").replace("Z", " UTC"))
        ctx = r.get("context") or {}
        ctx_bits = " · ".join(f"{k}: {html.escape(str(v))}"
                              for k, v in ctx.items() if v)
        mid = html.escape(r["id"])
        unread_cls = "" if r.get("read") else " unread"
        newtag = "" if r.get("read") else " <span class=new>new</span>"
        if email:
            subj = quote(f"Re: your message to DCS Sortie Starter ({topic_lbl})")
            reply = (f"<a class=mail href='mailto:{email}?subject={subj}'>"
                     f"✉ Reply to {email}</a>")
        else:
            reply = "<span class=note>No email — nothing to reply to.</span>"
        # Toggling read is a POST (it changes state); the label says which way
        # it goes so the button is never ambiguous.
        toggle_label = "Mark unread" if r.get("read") else "Mark read"
        toggle_val = "0" if r.get("read") else "1"
        out.append(
            f"<div class='msg{unread_cls}'>"
            f"<div class=row><span class=who>{name}</span>"
            f"<span class=topic>{topic_lbl}</span>{newtag}"
            f"<span class=when style='margin-left:auto'>{when}</span></div>"
            f"<div class=body>{body}</div>"
            + (f"<div class=ctx>{ctx_bits}</div>" if ctx_bits else "")
            + f"<div class=row>{reply}"
            f"<form method=post action='/admin/contact/{mid}/read' class=inline "
            f"style='margin-left:auto'>"
            f"<input type=hidden name=read value={toggle_val}>"
            f"<button class='btn ghost'>{toggle_label}</button></form>"
            f"<form method=post action='/admin/contact/{mid}/delete' class=inline "
            f"onsubmit=\"return confirm('Delete this message permanently?')\">"
            f"<button class='btn danger'>Delete</button></form>"
            "</div></div>")

    empty = ("<p class=note>Nothing here yet. Messages sent through the "
             "Contact form on the site land in this list.</p>")
    return _page(
        "<h1>SortieStarter <span class=am>Admin</span></h1>"
        "<p class=sub>What people have written in.</p>"
        + _tabs("contact") + flash
        + "<div class=card><h2>Contact messages</h2>"
        + filters
        + ("".join(out) if out else empty)
        + "</div>")


@router.get("/admin/contact", response_class=HTMLResponse)
def admin_contact(request: Request, topic: str = "", unread: int = 0):
    if not _configured():
        return _not_configured()
    if not _authed(request):
        return _login_page()
    try:
        return _contact_page(topic=topic, unread=bool(unread))
    except Exception as e:
        # Same rule as the analytics page: a rendering failure here must not
        # take the rest of the admin down with it (the other tabs are reached
        # through this page's own tab bar).
        log.exception("admin contact page failed")
        return _page(
            "<h1>SortieStarter <span class=am>Admin</span></h1>" + _tabs("contact")
            + "<div class=card><h2>Contact unavailable</h2>"
            "<p class=note>The inbox failed to render. No messages were lost — "
            "the store is append-only and untouched by this page.</p>"
            f"<p class=note><code>{html.escape(type(e).__name__)}: "
            f"{html.escape(str(e)[:300])}</code></p></div>")


@router.post("/admin/contact/{mid}/read")
def admin_contact_read(request: Request, mid: str, read: str = Form("1")):
    if not _configured():
        return _not_configured()
    if not _authed(request):
        return _login_page()
    from missiongen import contact as _contact
    _contact.mark_read(mid, read == "1")
    return _redirect("/admin/contact")


@router.post("/admin/contact/{mid}/delete")
def admin_contact_delete(request: Request, mid: str):
    if not _configured():
        return _not_configured()
    if not _authed(request):
        return _login_page()
    from missiongen import contact as _contact
    _contact.delete(mid)
    return _contact_page(msg="Message deleted.")


# --------------------------------------------------------------------------- #
# Roadmap and changelog — the plan and the engineering log, for the owner.
# --------------------------------------------------------------------------- #
# Both used to be public pages. Rob: "not for people to read AI implementation
# thoughts." The roadmap and CHANGELOG.md live here, behind the password, and
# nothing on the public site links to them. The public counterpart used to be
# What's new; since v1.105.0 it is the pack format page (/api/packformat) —
# written for authors rather than for readers of our planning.
_DOCS = Path(__file__).parent.parent / "docs"
ROADMAP_HTML = _DOCS / "roadmap.html"
ROADMAP_MD = _DOCS / "ROADMAP.md"
CHANGELOG_MD = Path(__file__).parent.parent / "CHANGELOG.md"


def _md_inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![*\w])\*(?!\*)([^*]+?)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    s = re.sub(r"\[(.+?)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def _md_to_html(md: str) -> str:
    """A small Markdown renderer: headings, bullets, paragraphs, inline
    bold/code. Enough for the two files it serves; no third-party parser."""
    out, para, in_list = [], [], False

    def flush():
        nonlocal in_list
        if para:
            out.append(f"<p>{_md_inline(' '.join(para))}</p>")
            para.clear()

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw in md.splitlines():
        line = raw.rstrip()
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            flush(); close_list()
            lvl = min(len(m.group(1)) + 1, 4)
            out.append(f"<h{lvl}>{_md_inline(m.group(2))}</h{lvl}>")
        elif re.match(r"^\s*[-*]\s+", line):
            flush()
            if not in_list:
                out.append("<ul>"); in_list = True
            item = re.sub(r"^\s*[-*]\s+", "", line)
            out.append(f"<li>{_md_inline(item)}</li>")
        elif line.strip() == "---":
            flush(); close_list(); out.append("<hr>")
        elif not line.strip():
            flush()
            if in_list:
                close_list()
        elif in_list and line.startswith("  "):
            out[-1] = out[-1][:-5] + " " + _md_inline(line.strip()) + "</li>"
        else:
            para.append(line.strip())
    flush(); close_list()
    return "".join(out)


_DOC_STYLE = ("<style>.doc h2{margin-top:28px}.doc h3{margin-top:18px}"
              ".doc p,.doc li{font-size:14px;line-height:1.55}.doc ul{padding-left:20px}"
              ".doc code{font-size:12.5px}.doc hr{border:0;border-top:1px solid var(--line);margin:22px 0}"
              ".doc iframe{width:100%;height:80vh;border:1px solid var(--line);border-radius:8px;background:#fff}</style>")


def _roadmap_page() -> HTMLResponse:
    if ROADMAP_HTML.exists():
        inner = ROADMAP_HTML.read_text()
        # The built page is a full document; show it inside a frame so its own
        # styling survives and the admin tabs stay above it.
        body = (f"<h1>Road<span class=am>map</span></h1>{_tabs('roadmap')}"
                f"<div class=doc><iframe src='/admin/roadmap/page' title='Roadmap'></iframe></div>")
    else:
        body = (f"<h1>Road<span class=am>map</span></h1>{_tabs('roadmap')}"
                f"<div class='card doc'>{_md_to_html(ROADMAP_MD.read_text())}</div>")
    return _page(_DOC_STYLE + body)


def _changelog_page() -> HTMLResponse:
    md = CHANGELOG_MD.read_text() if CHANGELOG_MD.exists() else "# Changelog\n\n(missing)"
    return _page(_DOC_STYLE + f"<h1>Change<span class=am>log</span></h1>{_tabs('changelog')}"
                 f"<div class='card doc'>{_md_to_html(md)}</div>")


@router.get("/admin/roadmap", response_class=HTMLResponse)
def admin_roadmap(request: Request):
    if not _configured():
        return _not_configured()
    if not _authed(request):
        return _login_page()
    return _roadmap_page()


@router.get("/admin/roadmap/page", response_class=HTMLResponse)
def admin_roadmap_page(request: Request):
    """The built roadmap document itself, for the frame above. Same gate."""
    if not _configured() or not _authed(request):
        return _login_page()
    if ROADMAP_HTML.exists():
        return HTMLResponse(ROADMAP_HTML.read_text())
    return HTMLResponse(_md_to_html(ROADMAP_MD.read_text()))


@router.get("/admin/changelog", response_class=HTMLResponse)
def admin_changelog(request: Request):
    if not _configured():
        return _not_configured()
    if not _authed(request):
        return _login_page()
    return _changelog_page()
