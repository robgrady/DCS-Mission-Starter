"""Google Analytics 4 tag, injected at serve time.

WHY IT IS NOT IN index.html
---------------------------
This app ships as a downloadable zip that people re-host — REPLIT.md is
literally a brief for doing that. A measurement id hard-coded into the page
would mean every self-hosted copy reports into Rob's Google property: his
traffic numbers would become "everyone who has ever run this", and other
people's visitors would be reported into an account they have never heard of.

So the id comes from the environment. Set it where you own the deployment and
nowhere else. No `GA_MEASUREMENT_ID`, no tag, no third-party request — which is
also what makes the test suite and the screenshot capture run clean.

WHY THE ID IS VALIDATED
-----------------------
It is interpolated into a <script> block. The value comes from an operator's
environment rather than from a user, so this is not the front line of anything
— but a typo'd or quoted env var that silently produced broken JavaScript would
take the whole page down, and an id containing a quote would be an injection in
the most literal sense. A strict pattern costs one line and removes both.

WHAT THIS DOES NOT DO
---------------------
It does not gate on Do Not Track or on the site's own analytics off-switch.
That was Rob's explicit call: the tag runs for every visitor, and the footer
says so in as many words rather than the page carrying a promise it has
stopped keeping. `tests/test_ga.py` holds the footer to it.
"""
from __future__ import annotations

import os
import re

ENV_VAR = "GA_MEASUREMENT_ID"

# GA4 measurement ids are "G-" followed by an uppercase alphanumeric token.
# Anchored, so nothing else can ride along inside the script tag.
ID_RE = re.compile(r"^G-[A-Z0-9]{4,20}$")


def measurement_id() -> str:
    """The configured id, or "" when there is none (or it is malformed)."""
    raw = (os.environ.get(ENV_VAR) or "").strip()
    return raw if ID_RE.match(raw) else ""


def snippet(mid: str | None = None) -> str:
    """Google's own gtag.js block, or "" when no id is configured."""
    mid = measurement_id() if mid is None else mid
    if not mid or not ID_RE.match(mid):
        return ""
    return (
        "\n<!-- Google tag (gtag.js) -->\n"
        f'<script async src="https://www.googletagmanager.com/gtag/js?id={mid}"></script>\n'
        "<script>\n"
        "  window.dataLayer = window.dataLayer || [];\n"
        "  function gtag(){dataLayer.push(arguments);}\n"
        "  gtag('js', new Date());\n"
        f"  gtag('config', '{mid}');\n"
        "</script>\n"
    )


def inject(html: str, mid: str | None = None) -> str:
    """Put the tag in the <head>, or at the top when a document has no head.

    IDEMPOTENT. Every HTML response on this site runs through here, and one of
    them (the sources page) is already passed through a second transform; a
    second injection would load gtag.js twice and double every page view.
    """
    tag = snippet(mid)
    if not tag or "googletagmanager.com/gtag/js" in html:
        return html
    lowered = html.lower()
    i = lowered.find("</head>")
    if i != -1:
        return html[:i] + tag + html[i:]
    # Generated doc pages (packformat, roadmap, sources) are fragments in some
    # builds. Prepending still puts the tag before any body content, which is
    # where Google asks for it.
    return tag + html
