"""The Mission Kit's buttons must be wired where the Kit is drawn.

THE BUG THIS FILE EXISTS BECAUSE OF
-----------------------------------
Rob: *"The briefing pack pdf doesn't download."*

From a Library card, the drawer's **Briefing pack** button was wired on a
`setTimeout(..., 1600)` — on the assumption that a mission finishes generating
inside 1.6 seconds. A plain starter does. A White Knights ride takes about 3.3,
because it carries the coaching cards, the brief pages and the squadron's
diagrams. So the timer fired before the Kit existed, `getElementById` returned
`null`, and the button sat there looking perfectly enabled and did nothing.

It failed on exactly the missions worth reading a brief for, and it failed
silently: no error, no console warning, a button that simply does not respond.
Verified in a real browser before and after — `{'exists': True, 'wired':
False}` and zero network calls on the shipped build; `wired: True` and a
downloaded pack on the fix.

WHY THESE GUARDS ARE STATIC
---------------------------
The honest test is a browser driving the real flow, and that is how the fix was
confirmed. It is not in this suite because it needs a live server, a browser
and fifteen seconds per case. What IS here is the SHAPE: every branch that
draws the Kit must wire it in the same statement, and no branch may wire it on
a timer. That is the property that was violated, and it is checkable in
milliseconds.
"""
import re
from pathlib import Path

import pytest

UI = (Path(__file__).resolve().parent.parent / "frontend" / "index.html").read_text()


def _fn(name):
    """The source of a top-level `function name(...)`, brace-matched."""
    m = re.search(rf"function {name}\s*\([^)]*\)\s*{{", UI)
    assert m, f"{name} is gone"
    i = m.end() - 1
    depth, j = 0, i
    while j < len(UI):
        if UI[j] == "{":
            depth += 1
        elif UI[j] == "}":
            depth -= 1
            if depth == 0:
                return UI[i:j + 1]
        j += 1
    raise AssertionError(f"unbalanced braces in {name}")


def test_the_kit_has_a_single_wiring_helper():
    """Three call sites wiring two buttons by hand is how one of them ends up
    on a timer and nobody notices."""
    assert UI.count("function wireKitButtons(") == 1
    assert "kit_brief" in _fn("wireKitButtons")
    assert "kit_kb" in _fn("wireKitButtons")


def test_every_branch_that_draws_the_kit_wires_it():
    """THE ACTUAL BUG. The Library branch drew the markup and returned without
    wiring anything, and the wiring lived in a racing timer somewhere else."""
    src = _fn("showKit")
    draws = [ln for ln in src.splitlines() if "kitRows(" in ln]
    assert len(draws) >= 3, draws          # lib, quick, builder
    for target in ("libkit", "qfkit", "kit_box"):
        assert target in src, f"showKit no longer draws into {target}"
    # every `return` inside a branch must be preceded by a wiring call
    branches = src.split("if (KIT_TARGET")
    for b in branches[1:]:
        assert "wireKitButtons()" in b.split("return;")[0], \
            f"a KIT_TARGET branch draws the kit without wiring it:\n{b[:400]}"
    assert src.rstrip().rstrip("}").rstrip().endswith("window.scrollTo(0,0);") \
        or "wireKitButtons()" in branches[-1]


def test_the_kit_buttons_are_never_wired_on_a_timer():
    """A timer cannot know when generation finished. This is the rule the bug
    broke, stated so it cannot be broken again by somebody reaching for the
    same convenience."""
    for name in ("generateFromLib", "showKit"):
        src = _fn(name)
        for m in re.finditer(r"setTimeout\((.{0,400}?)\}\s*,\s*\d+\)", src,
                             re.S):
            body = m.group(1)
            assert "kit_brief" not in body and "kit_kb" not in body, \
                f"{name} wires a Kit button inside a setTimeout:\n{body[:300]}"


def test_the_briefing_pack_row_still_has_the_button_it_wires():
    """A wiring helper that looks up an id nothing renders is wiring nothing.
    Both halves have to name the same button."""
    assert 'id="kit_brief"' in UI
    assert 'id="kit_kb"' in UI


def test_the_download_handler_survives_a_slow_generate():
    """`downloadBrief` briefs the mission that was actually generated, falling
    back to live builder state. The Library drawer has no builder DOM, so the
    fallback is what a Library card would hit — and it must not be the only
    path, or every Library brief describes the wrong mission."""
    src = _fn("downloadBrief")
    assert "LAST_GEN_RECIPE" in src, \
        "the brief no longer follows the mission that was generated"
    assert "|| recipe()" in src, "the builder fallback is gone"
