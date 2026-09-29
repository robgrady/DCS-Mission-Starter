"""Flightline Technical — the token system and the rules that make it stick.

Rob adopted the kit with one engineering condition (the plan's §2): ONE token
source, everything derived. These tests are what stops the palette forking
back into per-renderer copies — the drift pattern behind Incirlik and every
stale document this project has shipped.

Also enforced here: the kit's two hard rules that are testable —
WCAG AA contrast (computed, not trusted from the kit's own claim) and the
prohibition on classification-style markings (which v1.55.0 violated and
v1.56.0 unships).
"""
from pathlib import Path

import pytest

from missiongen import brand
from missiongen.resolver import load_json

ROOT = Path(__file__).parent.parent
TOKENS = load_json("brand/flightline")


# ---------------------------------------------------------------- the tokens
def test_the_token_file_is_wellformed():
    for name, hexval in TOKENS["colors"].items():
        assert len(hexval) == 7 and hexval.startswith("#"), f"{name}: {hexval}"
        int(hexval[1:], 16)


def test_colours_resolve_as_rgb():
    # Authentic Style v2.1 (docs/brand/authentic-style-specimen.pdf)
    assert brand.COLORS.paper == (0xFF, 0xFF, 0xFF)
    assert brand.COLORS.navy == (0x00, 0x20, 0x5B)
    with pytest.raises(AttributeError):
        brand.COLORS.chartreuse


# -------------------------------------------------------------- WCAG contrast
def _lum(rgb):
    def chan(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# Every (text, surface) pair a document or the site actually renders. The kit
# CLAIMS AA compliance; this computes it, because a claim in a README is not a
# guard and the pairs we use are not exactly the pairs they tested.
PAIRS = [
    ("ink", "paper", 4.5),          # body text
    ("white", "navy", 4.5),         # title bands, note blocks
    ("slate", "paper", 4.5),        # secondary text, rail
    # Authentic v2.1: warn (#B45309) and danger (#9F1239) are TEXT and pill
    # colors on paper, never fills that carry text.
    ("caution", "paper", 4.5),      # CAUTION pill text / warn text
    ("warning", "paper", 4.5),      # FAIL pill text / danger text
    ("white", "warning", 4.5),      # warning block text
    ("accent", "paper", 4.5),       # accent text (links, INFO pill)
    ("ok", "paper", 4.5),           # PASS pill text
    ("slate", "panel", 4.5),        # dim text on a panel
    ("night_text", "night", 4.5),   # night mode body
    ("phosphor", "night", 4.5),     # night status
    ("instrument", "night", 4.5),   # night selection
    ("night_caution", "night", 4.5),
    ("night_warning", "night", 4.5),
    # --- the SITE's Apple HIG palette (iteration 4) ---
    ("sys_dim", "white", 4.5),          # secondary text on cards
    ("sys_dim", "sys_bg", 4.5),         # secondary text on the grouped bg
    # sys_blue no longer carries TEXT anywhere — the v1.61 "3.0 large-text
    # floor" deviation was scoped too broadly (10px chips wore it) and is
    # retired. #007AFF now serves only borders, rings and icons, where the
    # 1.4.11 non-text floor (3:1 against the surface) is the rule that applies:
    ("sys_blue", "white", 3.0),          # non-text: focus ring / border on white
    ("sys_blue", "sys_bg", 3.0),
    # Small accent text + solid accent surfaces use the HIG accessible blues
    # (WCAG pass, v1.63.0) — full 4.5, no size exception needed anywhere:
    ("sys_blue_access", "white", 4.5),        # small accent text, light
    ("sys_blue_access", "sys_fill", 4.5),
    ("white", "sys_blue_access", 4.5),        # chip/button text on solid, light
    ("sys_blue_access_dark", "sys_dark_fill", 4.5),   # small accent text, night
    ("sys_blue_access_dark", "sys_dark_panel", 4.5),
    ("white", "sys_blue_solid_dark", 4.5),    # chip/button text on solid, night
    ("sys_green_access", "white", 4.5),       # FREE tags, kit checkmarks
    ("sys_green_access", "sys_fill", 4.5),
    ("sys_green_dark", "sys_dark_fill", 4.5),
    ("sys_dim", "sys_fill", 4.5),        # dim text reaches panel2 surfaces too
    ("sys_dark_dim", "sys_dark_fill", 4.5),
    ("sys_dark_dim", "sys_dark_panel", 4.5),
    ("white", "sys_dark_panel", 4.5),
]

# The Library's role taxonomy renders as 11px text labels — small text, so
# the strict 4.5 floor, no large-text exception. This is WHY the tokens are
# Apple's ACCESSIBLE variants rather than the default system colors (default
# systemOrange on white is 2.2:1). Light values must hold on sys_fill (the
# darkest light surface a role label can sit on — white and sys_bg follow);
# dark values must hold on sys_dark_fill.
for _n in ("a2a", "strike", "sead", "cas", "carrier", "training", "historic"):
    PAIRS.append((f"role_{_n}", "sys_fill", 4.5))
    PAIRS.append((f"role_{_n}_dark", "sys_dark_fill", 4.5))


@pytest.mark.parametrize("fg,bg,floor", PAIRS, ids=[f"{a}-on-{b}" for a, b, _ in PAIRS])
def test_contrast_meets_wcag_aa(fg, bg, floor):
    a = brand.COLORS.__getattr__(fg)
    b = brand.COLORS.__getattr__(bg)
    c = contrast(a, b)
    assert c >= floor, f"{fg} on {bg}: {c:.2f}:1 — fails AA ({floor}:1)"


# ------------------------------------------------------------------ the fonts
@pytest.mark.parametrize("role", list(TOKENS["fonts"]))
def test_every_font_role_loads_its_vendored_face(role):
    """The vendored file must actually load — a typo'd filename would silently
    hand every page to the DejaVu fallback and nobody would file a bug, the
    documents would just quietly stop looking like the kit."""
    f = brand.font(role, 20)
    name = " ".join(x for x in (f.getname() or ()) if x)
    assert "DejaVu" not in name, f"{role} fell back to {name}"


def test_a_missing_font_degrades_instead_of_failing(monkeypatch):
    """The fallback contract: fidelity may be lost, a mission may not."""
    brand.font.cache_clear()
    toks = {k: (dict(v) if isinstance(v, dict) else v)
            for k, v in brand.tokens().items()}
    toks["fonts"] = dict(toks["fonts"])
    toks["fonts"]["display"] = {"file": "DoesNotExist.ttf",
                                "fallback": "DejaVuSans-Bold.ttf"}
    monkeypatch.setattr(brand, "tokens", lambda: toks)
    f = brand.font("display", 20)
    assert f is not None
    brand.font.cache_clear()


def test_the_licences_ship_with_the_fonts():
    """OFL requires the license text to accompany the fonts. This is the
    difference between vendoring and pirating."""
    d = ROOT / "missiongen" / "data" / "brand" / "fonts"
    licences = {p.name.lower() for p in d.glob("OFL-*.txt")}
    for fam in ("barlowcondensed", "bangers", "sourcesans3",
                "sourceserif4", "ibmplexmono"):
        assert f"ofl-{fam}.txt" in licences, f"no license text for {fam}"


# ------------------------------------------------- one source, no forked copy
def test_the_renderers_use_the_tokens_not_local_copies():
    """kneeboard.py and brief.py must derive their palettes from brand. If
    someone re-hardcodes a color that later drifts from the token file, this
    is the test that names it."""
    from missiongen import kneeboard as kb
    from missiongen import brief as br
    assert kb.BG == brand.COLORS.paper
    assert kb.NAVY == brand.COLORS.navy
    assert kb.RED == brand.COLORS.warning
    assert br.PAPER == brand.COLORS.paper
    assert br.NAVY == brand.COLORS.navy
    assert br.INK == brand.COLORS.ink


def test_red_is_never_an_accent():
    """The kit's costliest rule: red means danger, full stop. The kneeboard's
    ACCENT (section identity) and the brief's band color must not be the
    warning red."""
    from missiongen import kneeboard as kb
    assert kb.ACCENT != brand.COLORS.warning
    assert kb.NAVY != brand.COLORS.warning


# ------------------------------------- no classification-style markings left
def test_no_classification_markings_anywhere():
    """The kit is explicit (DESIGN.md don'ts, research §5D): do not imitate
    classification banners. v1.55.0 shipped 'UNCLASSIFIED //' on every page;
    v1.56.0 unships it. This scans the renderers so it cannot creep back in a
    footer nobody reviews."""
    for rel in ("missiongen/kneeboard.py", "missiongen/brief.py",
                "missiongen/dtc.py", "server/app.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert "UNCLASSIFIED" not in src, f"classification marking in {rel}"


def test_the_identity_rail_answers_the_four_questions():
    """What publication, what product, what subject, what revision."""
    from missiongen import __version__
    rail = brand.rail_text("Caucasus · Modern", "page 2 of 4")
    assert "DSS 1-1" in rail
    assert "DCS SORTIE STARTER" in rail
    assert "CAUCASUS" in rail
    assert f"REV {__version__}" in rail
    assert "PAGE 2 OF 4" in rail
    assert "UNCLASSIFIED" not in rail


# ----------------------------------------------------------- the site (Ph. 2)
FRONTEND = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")


def test_the_site_defaults_to_paper_mode():
    """Rob's call from the plan: paper default, night on the toggle.

    Matches the BODY TAG, not the substring — 'data-mode="paper"' also appears
    in the CSS mode selector, so the loose check passed with the default
    flipped to night. Found by mutation, kept as a comment so nobody loosens
    it back."""
    assert '<body data-mode="paper">' in FRONTEND, \
        "the body tag does not default to paper"


def test_both_mode_token_blocks_exist_and_are_generated():
    assert 'body[data-mode="paper"]' in FRONTEND
    assert 'body[data-mode="night"]' in FRONTEND
    assert "FLIGHTLINE:TOKENS:BEGIN" in FRONTEND
    # the generator agrees with what is committed (the artifact registry runs
    # this too; asserting here keeps the failure close to the cause)
    import subprocess, sys as _sys
    r = subprocess.run([_sys.executable, "scripts/gen_theme.py", "--check"],
                       cwd=str(ROOT), capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_mode_toggle_is_wired():
    assert 'id="modebtn"' in FRONTEND
    assert "function flipMode()" in FRONTEND
    assert "localStorage.setItem('fl_mode'" in FRONTEND


def test_no_third_party_font_request():
    """Self-hosted fonts were half the point: opening the page must not ship
    the visitor's IP to Google for typography. The analytics stance ('no PII
    leaves') now covers fonts."""
    assert "fonts.googleapis.com" not in FRONTEND
    assert "fonts.gstatic.com" not in FRONTEND
    assert "/fonts/SourceSans3-VF.ttf" in FRONTEND


def test_the_font_route_serves_and_does_not_traverse():
    from fastapi.testclient import TestClient
    from server.app import app
    c = TestClient(app)
    ok = c.get("/fonts/IBMPlexMono-Regular.ttf")
    assert ok.status_code == 200
    assert ok.content[:4] == b"\x00\x01\x00\x00", "not a TTF"
    for bad in ("../flightline.json", "..%2F..%2Fapp.py", "nope.ttf"):
        assert c.get(f"/fonts/{bad}").status_code == 404, bad


def test_amber_is_no_longer_the_default_status_voice():
    """Semantic color on the site: the status lines that narrate normal
    progress ('Generating…') must not render in the caution color. Amber
    speaks only when something IS a caution."""
    import re
    for m in re.finditer(r"#status2? \{[^}]*\}", FRONTEND):
        assert "var(--amber)" not in m.group(0), m.group(0)


def test_the_topbar_is_the_identity_band():
    assert "background: var(--band)" in FRONTEND
    # BETA is a quiet label now, not an amber warning
    beta = FRONTEND[FRONTEND.index(".topbar .beta"):FRONTEND.index(".topbar .beta") + 400]
    assert "--amber" not in beta, "BETA still borrows the caution color"


def test_the_role_palette_lives_only_in_the_generated_block():
    """v1.60.0 and earlier carried a second :root with seven hand-picked role
    colors — a palette fork the anti-fork machinery couldn't see because it
    sat outside the markers. The role vars are generated now (Apple HIG
    accessible variants, per mode); this pins them to exactly the two mode
    blocks so the fork cannot quietly reopen."""
    begin = FRONTEND.index("FLIGHTLINE:TOKENS:BEGIN")
    end = FRONTEND.index("FLIGHTLINE:TOKENS:END")
    for var in ("--a2a:", "--strike:", "--sead:", "--cas:",
                "--carrier:", "--training:", "--historic:"):
        hits = [i for i in range(len(FRONTEND))
                if FRONTEND.startswith(var, i)]
        assert len(hits) == 2, f"{var} defined {len(hits)} times, want 2 (paper+night)"
        assert all(begin < i < end for i in hits), \
            f"{var} defined outside the generated block — the fork is back"


def test_the_library_accent_is_the_accent_not_carrier_teal():
    """Pre-HIG, the Library used the carrier ROLE color as its de-facto
    accent (search focus, checkmarks, NEW badges, hover borders). Under the
    HIG there is one accent — systemBlue — and role_carrier speaks only for
    the carrier role. The old hardcoded chip-text/teal values must stay gone."""
    for relic in ("#04211d", "#0B0E11", "rgba(63,184,175",
                  "rgba(45,212,191", "rgba(88,166,255"):
        assert relic.lower() not in FRONTEND.lower(), f"relic hardcode: {relic}"
    # var(--carrier) may appear exactly once: the ROLES dict entry for the
    # carrier role itself.
    assert FRONTEND.count("var(--carrier)") == 1, \
        "var(--carrier) used beyond the carrier ROLE entry"


# ------------------------------------------------------------- the icon system
def test_the_icon_sprite_is_present_and_used():
    """Lucide stroke icons (ISC) are the site's icon language — the open
    equivalent of SF Symbols, which is license-restricted to Apple platforms.
    Color emoji clash with the HIG register and were retired (Rob: 'the icons
    look a bit odd for this design')."""
    assert '<symbol id="i-zap"' in FRONTEND
    assert FRONTEND.count('<use href="#i-') >= 20, "the sprite exists but nothing uses it"
    lic = ROOT / "missiongen" / "data" / "brand" / "LICENSE-lucide.txt"
    assert lic.exists(), "Lucide license text must ship with the embedded icons"


def test_no_colour_emoji_in_the_ui_chrome():
    """The design-carrying pictographs are SVG now. This scans for the emoji
    ranges that used to serve as icons; the handful of legitimate text glyphs
    (check marks, the semantic ●◆▲ shapes, the anchor inside a <select> option
    where SVG cannot render) are allowed by name."""
    allowed = set("✓✗✕×⚓⚠▸▾●◆▲↳⌀°—·↑")
    bad = []
    for ch in FRONTEND:
        cp = ord(ch)
        if (0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF) and ch not in allowed:
            bad.append(f"U+{cp:05X} {ch!r}")
    assert not bad, f"emoji-as-icon crept back: {sorted(set(bad))}"
