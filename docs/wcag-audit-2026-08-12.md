# WCAG 2.2 AA audit — DCS Sortie Starter (v1.62.0)

Audited 12 Aug 2026: axe-core 4.x automated scan across seven view/mode
combinations (entry, quick, library, detail modal, builder × paper/night)
plus a manual code review against the WCAG 2.2 AA checklist. Target level:
**AA** — the standard referenced by the ADA (US), the European Accessibility
Act, and every mainstream procurement checklist. (AAA is aspirational and not
expected of a hobby/product site.)

## Where we already stand (stronger than most sites)

- **Palette contrast is computed, not claimed** — 30 token pairs tested at
  build time, including the role taxonomy shipped in v1.61.0 specifically in
  Apple's *accessible* variants.
- **Color is never the only signal** — the kit's redundancy rule (●◆▲
  shapes + text labels on every state) is WCAG 1.4.1 compliance by design.
- `lang="en"`, a real `<title>`, alt text on the one content image, 45
  `<label>` elements, real `<button>` elements for most actions, Lucide SVG
  icons inheriting text color.

## Gaps, ranked by user impact

### P1 — blocks real users, fast to fix

1. **Unlabelled selects** (axe: critical; WCAG 4.1.2 / 1.3.1). The six
   Library filter selects (`#lfAc #lfMap #lfType #lfEra #lfDiff #lfSort`)
   have visible `<label>` text that is NOT programmatically bound (no
   `for`/`id`). A screen reader announces "combo box" with no name. Fix:
   bind every label in the file; audit all 25 selects + 23 inputs.
2. **Accent-blue small text fails contrast** (axe: serious; WCAG 1.4.3).
   systemBlue #007AFF is 4.02:1 on white — legal for large/bold text only,
   but used at 10–13px: `.eyebrow`, `.qlabel`, `.lmodtag`/`.lnew` chips
   (white-on-blue at 10px), `.epath .go`, builder rail labels, topbar
   version span (~60 nodes per light-mode page). Our own PAIRS test allowed
   white-on-sys_blue at the 3.0 large-text floor — the deviation was scoped
   too broadly. Fix: add Apple's accessible blue (`#0040DD` light /
   `#409CFF` dark) as an `--accent-text-small`-class token, move small-type
   accent usages onto it, re-scope the PAIRS floors so 3.0 applies ONLY to
   the ≥15px-bold button faces.
3. **Status updates are silent** (WCAG 4.1.3). `#status`/`#status2`
   ("Generating…", "Mission ready") update via textContent with no
   `aria-live` — a screen-reader user never hears the product's main
   feedback loop. Fix: `role="status"` + `aria-live="polite"` on both.
4. **Modals aren't modals** (WCAG 2.1.2 / 4.1.2). The Library detail card
   and My-Content overlay have no `role="dialog"`, no `aria-modal`, no focus
   trap, no focus restore; Escape only closes the per-base overlay. Fix:
   dialog semantics + focus trap + Esc on both (or migrate to native
   `<dialog>`).

### P2 — the big one: keyboard access

5. **Click-only cards** (WCAG 2.1.1 — keyboard). ~15 static `onclick` divs
   plus every JS-rendered card: `.libcard`, `.lmodcard`, `.corrcard`,
   `.qcard`, `.revrow`, `.epath`, era chips, `.ochk` rows. None are
   focusable; none respond to Enter/Space. A keyboard user cannot open a
   mission, pick a Quick Flight option, or filter by module. This is the
   largest single work item: convert to `<button>` (preferred) or
   `role="button" tabindex="0"` + key handler, with a shared helper.
6. **Focus visibility** (WCAG 2.4.7 / 2.4.13-adjacent). Two `outline:none`
   on search inputs (border-color change partially compensates); no
   `:focus-visible` ring anywhere else — once cards become focusable they
   need a visible ring. Fix: one global
   `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px }`.
7. **Half-implemented tab pattern** (WCAG 4.1.2). The view bar uses
   `role="tablist"/"tab"` with one static `aria-selected` and no arrow-key
   support or state updates. Either complete the ARIA tabs pattern or drop
   the roles and let them be plain buttons (honest and compliant).

### P3 — verify-and-polish

8. **Target size** (WCAG 2.5.8, new in 2.2): measure the small controls
   (`.dclose`, `.oclr`, chip buttons, threat pips) against the 24×24px
   minimum; pad where short.
9. **Reflow at 320px** (WCAG 1.4.10): the 900px breakpoint exists; verify
   no two-axis scrolling at 320×256 and fix overflow.
10. **Reduced motion** (2.3.3 is AAA, but cheap): wrap the hover
    translate/transition effects in `@media (prefers-reduced-motion: no-preference)`.
11. **Heading order / landmark audit** and one manual VoiceOver pass
    (Safari, the Mac this project is developed on) through the three core
    flows: Quick Flight, Library→generate, Builder.

## Enforcement (so it never regresses)

- Add an **axe gate to the release pipeline**: the screenshot pass already
  drives Playwright; run axe on the same pages and fail preflight on any
  serious/critical violation. Mutation-prove it by re-unbinding one label.
- Extend the PAIRS contrast list with the corrected small-text floors.
- Add a scan test: no `onclick` on non-focusable elements (regex over the
  frontend, allowlist for decorated `<button>`s).

## Effort

- **Phase 1 (P1 items + axe gate):** one release. Highest impact per hour.
- **Phase 2 (keyboard pass):** one to two releases, touches every card
  renderer; the shared focus ring and key-handler helper keep it mechanical.
- **Phase 3 (P3 + VoiceOver pass):** one release.

After Phase 2 the site is defensibly AA for the flows that matter; Phase 3
closes the long tail and the manual-verification obligation that no
automated tool can discharge (axe catches roughly a third of WCAG).
