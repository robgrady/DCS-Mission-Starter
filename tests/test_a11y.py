"""WCAG guards — the automatable share of the audit (docs/wcag-audit-2026-08-12.md).

Two layers:
  * static scans of the frontend source (fast, always run) — the patterns that
    caused the v1.62-era failures cannot come back silently;
  * the axe-core browser gate (scripts/axe_check.js) — runs when Chromium and
    node are present (dev boxes and the release preflight), skips otherwise so
    a minimal CI without a browser still passes the rest of the suite.
"""
from ui_source import ui_source, server_source
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FRONTEND = ui_source()


# ------------------------------------------------------------- static scans
def test_every_click_handler_is_keyboard_operable():
    """WCAG 2.1.1. Any non-native element carrying onclick must also carry a
    role and a tabindex — otherwise it is mouse-only. Native controls
    (button/a/input/select/label/option) are operable by themselves."""
    native = ("button", "a", "input", "select", "label", "option", "textarea")
    bad = []
    for m in re.finditer(r"<(\w+)([^>]*?)onclick=\"([^\"]*)\"", FRONTEND):
        tag, attrs, handler = m.group(1).lower(), m.group(2), m.group(3)
        if tag in native:
            continue
        # Backdrop dismiss handlers (click outside the card to close) are
        # exempt: they duplicate Escape and the close button, and making a
        # full-screen scrim focusable would add a keyboard stop that does
        # nothing useful.
        if "event.target===this" in handler:
            continue
        if "role=" not in attrs or "tabindex=" not in attrs:
            bad.append(m.group(0)[:90])
    assert not bad, "mouse-only controls:\n  " + "\n  ".join(bad)


def test_every_select_and_search_input_has_an_accessible_name():
    """WCAG 4.1.2 — the axe finding that started this: six Library filters
    announced as nameless combo boxes."""
    for sid in re.findall(r'<select id="([^"]+)"', FRONTEND):
        assert (f'for="{sid}"' in FRONTEND) or re.search(
            rf'<label[^>]*>[^<]*<select id="{sid}"', FRONTEND), \
            f"select #{sid} has no bound label"
    for m in re.finditer(r'<input[^>]*type="search"[^>]*>', FRONTEND):
        assert "aria-label=" in m.group(0), f"unnamed search input: {m.group(0)[:80]}"


def test_status_lines_are_live_regions():
    """WCAG 4.1.3 — 'Generating…'/'Mission ready' must reach screen readers."""
    for sid in ("status", "status2"):
        m = re.search(rf'<div id="{sid}"[^>]*>', FRONTEND)
        assert m and 'aria-live="polite"' in m.group(0), \
            f"#{sid} is not a live region"


def test_the_dialogs_are_dialogs():
    """WCAG 2.1.2 / 4.1.2 — role, aria-modal, and the shared focus trap."""
    assert FRONTEND.count('role="dialog"') >= 3
    assert FRONTEND.count('aria-modal="true"') >= 3
    assert "function modalOpen(" in FRONTEND
    assert "e.key==='Escape'" in FRONTEND


def test_no_alpha_dimmed_text_in_the_rail():
    """1.4.3 via the back door: opacity multiplies into effective contrast, so
    dimming text with alpha un-does the computed token guarantees. Dim by
    COLOUR (var(--dim)), never by opacity, in the rail's value/off states."""
    for pat in (r"\.rsub\.off[^}]*opacity:\s*\.\d", r"#railreset[^}]*opacity:\s*\.\d"):
        assert not re.search(pat, FRONTEND), f"alpha-dimmed text: /{pat}/"


def test_reduced_motion_is_honoured():
    assert "prefers-reduced-motion" in FRONTEND


def test_the_global_focus_ring_exists():
    """WCAG 2.4.7. Matches the UNQUALIFIED rule — the one that covers every
    operable element. A substring check passed with the global rule deleted,
    because `.topbar h1 a:focus-visible {...}` contains the same text; found
    by mutation, and this comment is why the regex is anchored."""
    assert re.search(r"(?m)^\s*:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--accent\)",
                     FRONTEND), "no GLOBAL :focus-visible ring"


def test_small_accent_text_uses_the_accessible_blue():
    """The tokens exist so the site can be wrong with them. These selectors are
    the ones axe caught at 4.02:1 — pin them to the accessible variant."""
    for sel_pat in (r"\.eyebrow\{[^}]*color:var\(--accent-small\)",
                    r"\.topbar h1 span \{ color: var\(--accent-small\)",
                    r"\.lmodtag\{[^}]*background:var\(--accent-solid\)",
                    r"\.lnew\{[^}]*background:var\(--accent-solid\)"):
        assert re.search(sel_pat, FRONTEND), f"missing: /{sel_pat}/"


# --------------------------------------------------------- the axe browser gate
def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


@pytest.mark.skipif(
    shutil.which("node") is None or not Path("/opt/pw-browsers/chromium").exists(),
    reason="axe gate needs node + chromium (runs on dev boxes and in release preflight)")
def test_axe_reports_zero_serious_or_critical():
    port = _free_port()
    srv = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server.app:app", "--port", str(port)],
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        deadline = time.time() + 20
        import urllib.request
        while time.time() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        r = subprocess.run(
            ["node", str(ROOT / "scripts" / "axe_check.js"), f"http://127.0.0.1:{port}"],
            capture_output=True, text=True, timeout=180)
        assert r.returncode == 0, r.stdout + r.stderr
    finally:
        srv.terminate()
        srv.wait(timeout=10)
