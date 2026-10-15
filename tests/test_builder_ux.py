"""Structural guards on the Builder.

The Builder is one 3,000-line vanilla-JS file with no build step and no type
checker, and this session alone produced four defects that a compiler would
have caught for free:

  * `sec_kind` — the Mission-type control — was **orphaned since v1.19**. The
    markup existed, the handler existed, and no screen listed it, so for four
    months every mission the Builder made was open tasking whether that was
    what you wanted or not. Nothing errored. It just wasn't reachable.
  * The carrier deck panel appeared on landlocked maps, because folding Carrier
    into Flight dropped its visibility condition.
  * `ALL_STEP_IDS` and `CUR_SCREEN` were deleted and then re-declared during a
    scripted edit, so the page threw on load.
  * The footer grew a second GENERATE .MIZ that competed with the real one.

None of these are testable through the DOM without a browser, and all of them
are visible in the source as broken *relationships* — a screen naming a step
that doesn't exist, a declaration appearing twice, a mission kind the engine has
never heard of. That is what this file checks: the wiring between the frontend's
tables and the markup and the engine, which is exactly where it keeps breaking.
"""
from ui_source import ui_source, server_source
import re
from pathlib import Path

import pytest

from missiongen.recipe import RECIPE_ENUMS

HTML = ui_source()


def _js_array_of_objects(name):
    """Pull `const NAME = [ ... ];` out of the file as raw text."""
    m = re.search(rf"const {name} = \[(.*?)\n\];", HTML, re.S)
    assert m, f"const {name} = [...] is gone from index.html"
    return m.group(1)


def _screens():
    """[(key, num, [step ids])] parsed out of the SCREENS table."""
    body = _js_array_of_objects("SCREENS")
    out = []
    for m in re.finditer(r'\{key:"(\w+)",\s*num:(\d+).*?steps:\[(.*?)\]',
                         body, re.S):
        steps = re.findall(r'"(\w+)"', m.group(3))
        out.append((m.group(1), int(m.group(2)), steps))
    return out


SCREENS = _screens()
STEPS = [(k, s) for k, _n, steps in SCREENS for s in steps]


def _element_ids():
    return re.findall(r'\bid="([\w-]+)"', HTML)


IDS = _element_ids()


# --- the tables and the markup agree ----------------------------------------

def test_the_screen_table_parsed():
    """Guard on the guard: every check below is driven by this parse, and a
    regex that quietly matches nothing turns the file green."""
    assert len(SCREENS) >= 5, f"parsed only {len(SCREENS)} screens"
    assert len(STEPS) >= 9, f"parsed only {len(STEPS)} steps"


@pytest.mark.parametrize("screen,step", STEPS, ids=[f"{s}/{b}" for s, b in STEPS])
def test_every_step_a_screen_lists_exists_in_the_markup(screen, step):
    """A screen naming a step that isn't there is a blank panel with a Next
    button — no error, just nothing."""
    assert step in IDS, f"screen '{screen}' lists step '{step}', which has no element"


def _step_blocks():
    """[(id, is_hidden_at_rest)] for every `<div class="step" id=...>`."""
    out = []
    for m in re.finditer(r'<div class="step" id="([\w-]+)"([^>]*)>', HTML):
        out.append((m.group(1), "display:none" in m.group(2).replace(" ", "")))
    return out


BLOCKS = _step_blocks()


def test_no_visible_block_of_markup_is_unreachable():
    """THE v1.19 DEFECT, inverted. `sec_kind` sat in the markup for four months
    with no screen listing it, and nothing said so.

    The distinction that makes this checkable: a block deliberately outside the
    flow is `display:none` at rest — `sec_template` is a state-holder the
    Library's "open in Builder" path writes into, and `sec_kit` is the
    post-build panel. A block that renders and that no screen lists is not a
    design decision, it is a control the user can never reach.
    """
    listed = {s for _k, s in STEPS}
    orphans = sorted(i for i, hidden in BLOCKS if not hidden and i not in listed)
    assert not orphans, (
        f"unreachable Builder blocks: {orphans} — the markup renders and no "
        f"screen lists it, so the user can never get to it")


def test_a_hidden_state_holder_says_why_it_is_hidden():
    """The other half. `display:none` is also what a broken block looks like,
    so the ones we keep have to be documented at the point they are declared —
    otherwise the test above becomes a license to hide anything."""
    for i, hidden in BLOCKS:
        if not hidden:
            continue
        before = HTML[:HTML.index(f'id="{i}"')]
        comment = before.rsplit("<div", 1)[0][-1200:]
        assert "<!--" in comment, \
            f"'{i}' is display:none with no comment explaining why it exists"


def test_the_mission_type_control_is_reachable():
    """Named explicitly rather than left to the sweep above, because this is
    the one that actually shipped broken and it is worth failing by name."""
    assert "sec_kind" in {s for _k, s in STEPS}, \
        "the Mission type control is orphaned again (it was, from v1.19 to v1.45)"
    assert "sec_kind" in IDS


def test_screens_are_numbered_in_order_from_one():
    nums = [n for _k, n, _s in SCREENS]
    assert nums == list(range(1, len(nums) + 1)), \
        f"screen numbering is {nums} — the rail prints these"


def test_the_step_number_badges_are_hidden_or_honest():
    """Each block header carries a `<span class="n">` badge left over from the
    original eight-step wizard, and they never got renumbered — `sec_kind`
    still says 3 while it sits on screen 1, Review still says 9 of 6, and two
    different blocks both say 2. They are invisible today (`.step h2 .n
    { display: none }`), so this is dormant rather than broken; the test exists
    so that turning them back on cannot silently ship contradictory numbers."""
    if re.search(r"\.step h2 \.n \{[^}]*display:\s*none", HTML):
        return
    want = {s: n for _k, n, steps in SCREENS for s in steps}
    for m in re.finditer(r'<div class="step" id="([\w-]+)"[^>]*>'
                         r'<h2[^>]*>(?:<span[^>]*>)*<span class="n">([^<]*)</span>',
                         HTML):
        sid, badge = m.group(1), m.group(2).strip()
        if sid in want:
            assert badge == str(want[sid]), \
                f"'{sid}' shows badge {badge!r} but lives on screen {want[sid]}"


def test_no_step_appears_on_two_screens():
    seen = [s for _k, s in STEPS]
    dupes = {s for s in seen if seen.count(s) > 1}
    assert not dupes, f"{dupes} would be shown and hidden by two screens"


# --- the outline rail can only name blocks that exist -----------------------

def _block_info_keys():
    m = re.search(r"const BLOCK_INFO = \{(.*?)\n\};", HTML, re.S)
    assert m, "BLOCK_INFO is gone"
    return re.findall(r"^\s{2}(\w+):\s*\{", m.group(1), re.M)


def test_the_outline_rail_describes_every_step_and_no_others():
    """The rail lists each block with its current setting. A step with no
    BLOCK_INFO entry is a blank rail line; a BLOCK_INFO entry with no step is
    a rail line that jumps nowhere."""
    info = set(_block_info_keys())
    steps = {s for _k, s in STEPS}
    assert not (steps - info), f"steps with no rail entry: {sorted(steps - info)}"
    assert not (info - steps), f"rail entries for no step: {sorted(info - steps)}"


# --- nothing is hidden ------------------------------------------------------

# Disclosure widgets that are ALLOWED to start closed, by class, with the
# reason. The rule below is about the WIZARD — configuration you must click to
# discover. Secondary explanatory text elsewhere is progressive disclosure and
# is supposed to be closed; listing it here keeps that an explicit decision
# rather than a hole in the guard.
COLLAPSIBLE_BY_DESIGN = {
    "libraryfilters": "Secondary Library filters collapse to keep missions near search; this is outside the Builder.",
    "libhistory": "Library evidence and adaptation notes, below the always-visible date and classification; not Builder controls",
    "cctx": "contact form: 'what we'll include with your message' — disclosure "
            "of auto-captured context, secondary to the act of writing",
}


def test_no_wizard_block_starts_collapsed():
    """v1.46.0's whole point. Four sections behind fold-out headers meant four
    clicks to see what was even there, and only one could be open at a time.
    Air corridors starting folded shut was the specific complaint.

    Scoped to the wizard by exception-list rather than by loosening: an
    unlisted closed <details> anywhere still fails."""
    details = re.findall(r"<details[^>]*>", HTML)
    bad = []
    for d in details:
        if "open" in d:
            continue
        cls = re.search(r'class="([^"]*)"', d)
        names = set((cls.group(1) if cls else "").split())
        if names & set(COLLAPSIBLE_BY_DESIGN):
            continue
        bad.append(d)
    assert not bad, f"collapsed-by-default disclosure widgets are back: {bad}"


def test_the_carrier_deck_panel_has_a_visibility_condition():
    """My own v1.45.0 regression: folding Carrier into Flight dropped the
    condition, so Cold War Germany offered carrier deck configuration on a map
    with no sea."""
    m = re.search(r"const STEP_COND = \{(.*?)\n\};", HTML, re.S)
    assert m, "STEP_COND is gone — every step is now unconditionally visible"
    assert re.search(r"^\s{2}carrierstep:", m.group(1), re.M), \
        "carrierstep has no condition; it will show on landlocked maps"
    body = m.group(1)
    assert "bb_carrier" in body and "CARRIER" in body, \
        "the carrier condition no longer checks both the toggle and the base list"


# --- one button builds a mission --------------------------------------------

def test_there_is_exactly_one_generate_button():
    """v1.45.1. The orange footer bar had its own GENERATE .MIZ competing with
    the one on Review, and on the first screen with Next as well — three things
    asking to be pressed and no way to tell which was the right one."""
    labels = re.findall(r"<button[^>]*>\s*GENERATE[^<]*</button>", HTML, re.I)
    assert len(labels) == 1, f"{len(labels)} GENERATE buttons in the markup: {labels}"


def test_the_last_screen_is_review_and_it_ends_the_flow():
    key, num, _steps = SCREENS[-1]
    assert key == "review", f"the flow ends on '{key}'"
    assert "Review is the end" in HTML or "vs.length-1" in HTML, \
        "the Next button is no longer suppressed on the final screen"


# --- declarations are declared once -----------------------------------------

@pytest.mark.parametrize("decl", [
    r"const SCREENS = ", r"const BLOCK_INFO = ", r"const STEP_COND = ",
    r"const MISSION_KINDS = ", r"const ALL_STEP_IDS = ", r"let CUR_SCREEN = ",
])
def test_each_top_level_declaration_appears_exactly_once(decl):
    """A duplicate `const` is a SyntaxError that takes the whole page down on
    load — a blank screen, not a degraded one. This happened twice during
    scripted edits to this file."""
    n = len(re.findall(decl, HTML))
    assert n == 1, f"'{decl.strip()}' appears {n} times"


def test_the_step_list_is_derived_from_the_screen_table():
    """Not hand-maintained. A hand-written ALL_STEP_IDS drifts from SCREENS the
    first time a step moves, and the symptom is a panel that never hides."""
    assert "SCREENS.flatMap" in HTML, \
        "ALL_STEP_IDS is no longer derived from SCREENS"


# --- the frontend and the engine agree on the vocabulary --------------------

def _mission_kinds():
    body = _js_array_of_objects("MISSION_KINDS")
    return re.findall(r'\{k:"(\w+)",\s*label:"([^"]+)"', body)


KINDS = _mission_kinds()


def test_every_mission_kind_the_ui_offers_is_one_the_engine_accepts():
    """A kind the enum doesn't know is a 400 on click. The two lists live in
    different languages in different files, so nothing but a test connects
    them."""
    ui = [k for k, _l in KINDS]
    engine = list(RECIPE_ENUMS["mission_kind"])
    assert ui == engine, f"UI offers {ui}, the engine accepts {engine}"


def test_every_mission_kind_says_what_it_changed():
    """'A line underneath tells you exactly what your choice changed' is the
    feature. A kind with no `what` shows an empty line, which reads as broken."""
    body = _js_array_of_objects("MISSION_KINDS")
    for k, label in KINDS:
        entry = re.search(rf'\{{k:"{k}",.*?(?=\n  \{{k:"|\Z)', body, re.S)
        assert entry, f"could not isolate mission kind '{k}'"
        assert re.search(r'what:"[^"]{20,}', entry.group(0)), \
            f"mission kind '{label}' has no (or a stub) explanation line"
        assert re.search(r"patch:\{", entry.group(0)), \
            f"mission kind '{label}' changes nothing about the theater"


def test_mission_kind_patches_only_set_fields_the_recipe_has():
    """A typo'd field in a patch is silent — the UI cheerfully sets
    `bb_target` and the mission builds with targets off."""
    import dataclasses
    from missiongen import Recipe
    fields = {f.name for f in dataclasses.fields(Recipe)}
    body = _js_array_of_objects("MISSION_KINDS")
    used = set(re.findall(r"[\{,\s]([a-z_][a-z0-9_]*):[^\{]",
                          " ".join(re.findall(r"patch:\{([^}]*)\}", body))))
    unknown = sorted(used - fields)
    assert not unknown, f"mission-kind patches set unknown recipe fields: {unknown}"


# --- and the enums the controls offer ---------------------------------------

@pytest.mark.parametrize("field", sorted(RECIPE_ENUMS))
def test_select_controls_only_offer_values_the_engine_accepts(field):
    """Every `<select id="threat_tier">` option value has to be in the enum, or
    picking it is a 400 the user cannot diagnose."""
    m = re.search(rf'<select[^>]*id="{field}"[^>]*>(.*?)</select>', HTML, re.S)
    if not m:
        pytest.skip(f"no <select id={field}> in the markup")
    offered = set(re.findall(r'value="([^"]*)"', m.group(1)))
    allowed = set(RECIPE_ENUMS[field])
    assert offered <= allowed, \
        f"{field}: UI offers {sorted(offered - allowed)}, engine accepts {sorted(allowed)}"


# --- a setting a card can set must be a setting the Builder can show ---------

def test_every_value_a_shipped_card_sets_is_offerable_in_the_builder():
    """Rob opened Formation 1 in the Builder to change the aircraft and found
    the Start dropdown empty.

    The card sets `start: "air"`. The engine accepts it. The API's `enums.start`
    listed only cold/warm/runway, because air starts used to be template-only —
    so the frontend did `select.value = "air"` on a <select> with no such
    option, which silently does nothing. The setting was then lost the moment
    anything else on the screen changed.

    A value the engine accepts, a card sets, and the UI cannot show is the worst
    of the three states, so this checks the whole shipped Library against the
    enums the API publishes rather than just the one field that broke.
    """
    from server.app import app
    from fastapi.testclient import TestClient
    from missiongen.templates import advertised_combinations, effective_recipe

    enums = TestClient(app).get("/api/options").json()["enums"]
    missing = set()
    for key, era in advertised_combinations():
        rc = effective_recipe(key, era)
        for field, offered in enums.items():
            val = rc.get(field)
            if val is not None and val not in offered:
                missing.add(f"{key}/{era}: {field}={val!r} "
                            f"(UI offers {offered})")
    assert not missing, (
        "Library cards set values the Builder cannot display:\n  "
        + "\n  ".join(sorted(missing)))


@pytest.mark.parametrize("field", sorted(RECIPE_ENUMS))
def test_the_api_never_offers_a_value_the_engine_would_reject(field):
    """The other direction, which was already true and must stay true: the UI
    must not offer something `Recipe.validate()` throws on."""
    from server.app import app
    from fastapi.testclient import TestClient
    enums = TestClient(app).get("/api/options").json()["enums"]
    if field not in enums:
        pytest.skip(f"{field} is not published as a UI enum")
    extra = set(enums[field]) - set(RECIPE_ENUMS[field])
    assert not extra, f"{field}: UI offers {sorted(extra)}, engine rejects them"
