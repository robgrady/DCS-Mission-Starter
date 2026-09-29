# Flightline Technical — adoption plan for DCS Sortie Starter

*Design review and implementation plan · 12 Aug 2026 · covers the site
(`frontend/index.html`), the generated documents (kneeboard, briefing PDF, DTC
card, user guide), and the published pages (what's new, roadmap).*

---

## 1. Review: what this guide gets right, and where it collides with the product

### 1.1 The core judgment is correct

The guide's central claim — *"the strongest military-aviation visual language is
not stencil lettering or camouflage, it is disciplined information
architecture"* — is exactly the right read, and it happens to describe what this
product already does structurally. We already have persistent identity (version
in the topbar, `/api/health`, share codes), rigid revision control
(`release.sh`, the artifact registry, CHANGELOG discipline), and deterministic
regeneration. Flightline gives that machinery a matching skin. This is the rare
case where a style guide and the engineering culture agree.

### 1.2 Four genuine improvements over what we have

**Semantic color, enforced.** Today amber is simultaneously our brand accent,
our primary CTA, our status-text color and our warning color. The guide's rule
— red only for danger, amber only for caution, navy for identity and information
— removes a real ambiguity. When the era guard rejects an aircraft today, the
message renders in the same amber as the Generate button. Under Flightline those
become different things, which they are.

**A five-role type ramp with a place for everything.** Display (Barlow
Condensed), UI/labels (Source Sans 3), long-form print body (Source Serif 4),
technical data (IBM Plex Mono), and the heritage banner voice (Bangers). Our
current stack (Archivo/Barlow/Plex Mono) has no print-body voice at all, which
is why the briefing PDF reads like a website. All five are OFL-licensed, so they
can be vendored for the server-side PIL renderers and self-hosted for the site.

**Dual modes that resolve our standing dispute.** Rob is tired of the dark
theme; simmers fly at night. The kit legitimises both: paper mode as the
canonical identity, night mode as a deliberate second register with its own
tokens (phosphor/instrument cyan) rather than an inverted afterthought. Our
existing instrument-panel palette is, conveniently, about 80% of the kit's night
mode already.

**The identity rail.** "A thin strip on every page answering: what is this, what
does it cover, what revision, where am I." We print version in the topbar and
nowhere else. The rail generalises it: `DSS · CAUCASUS · MODERN · REV 1.56.0 ·
SEED 4821` is *useful* on every screen and every document — it is the share
link's contents made visible.

### 1.3 Three collisions to resolve

**The classification banner we just shipped (v1.55.0) violates the guide.**
Section 5D and the DESIGN.md don'ts both say: avoid classification banners and
marks that could imply government endorsement. Our documents now carry
"UNCLASSIFIED // FOR SIMULATION USE ONLY" top and bottom. The guide's
replacement — the identity strip with publication ID, revision and date — is
both safer and more informative. Recommendation: **swap banner → identity rail**
across the kneeboard and brief. (Decision for Rob; see §5.)

**Amber cannot stay the primary CTA.** Under the guide's color rules the
Generate button becomes navy (`#17324D`); amber is reserved for genuine caution
states (era-guard rejections, degraded warnings from the engine); red is
reserved for destructive/danger only (we barely use it today — correct).

**Paper (`#F4F0E6`) vs the pure white we shipped yesterday.** The kit is warm
paper with a navy title band; v1.55.0's kneeboards are white with black
double-rules. The kit's version is friendlier to sustained reading and better
matched to the F-4E source material. Recommendation: adopt the kit tokens
exactly — one source of truth beats two interpretations of "military."

### 1.4 What to use sparingly

The Bangers/slanted-parallelogram heritage banner is a strong single note —
1-to-4-word figure banners only, per the guide. Concretely: the landing-page
hero gets one, chart figure titles may get one, and it appears nowhere else.
Not on buttons, not on warnings, not in the Library cards. The guide is
explicit and it is right — this is the element that tips into cosplay if
repeated.

---

## 2. Architecture: one token source, everything derived

The one engineering decision that matters. This project's recurring failure
mode is two copies of a truth drifting apart (Incirlik, the roadmap, the
whatsnew page). Color tokens now exist in **four places**: the site CSS, the
kneeboard PIL constants, the brief PIL constants, and the chartstyle module.
Flightline must not become a fifth thing to hand-sync.

```
missiongen/data/brand/flightline.json     ← THE source (adapted from tokens.json)
        │
        ├─ scripts/gen_theme.py ──► frontend CSS :root block   (rebuild rule)
        ├─ missiongen/brand.py   ──► PIL constants for kneeboard.py / brief.py
        ├─ (chartstyle.py reads brand.py)
        └─ scripts/build_guide_pdf.py / build_whatsnew_html.py / report css
```

* `scripts/gen_theme.py` regenerates the `:root { … }` block inside
  `frontend/index.html` between marker comments, and is registered in
  `scripts/artifacts.py` with a **rebuild** rule — preflight blocks if the CSS
  and the token file disagree.
* `missiongen/brand.py` exposes `PAPER`, `INK`, `NAVY`, `WARN`, `CAUTION`,
  `SLATE`, the night set, and font paths. `kneeboard.py`, `brief.py` and
  `chartstyle.py` import it; their local palettes are deleted.
* Fonts are vendored under `missiongen/data/brand/fonts/` (OFL texts included)
  and self-hosted for the site at `/fonts/…` — which also removes the Google
  Fonts request, consistent with the project's no-third-party-calls analytics
  stance. DejaVu remains the fallback stack so a missing font degrades, never
  crashes a build.

**Tests that make it stick**

* `test_theme_tokens.py`: WCAG AA contrast computed programmatically for every
  (text, surface) pair the tokens declare — ink/paper, white/navy, ink/caution,
  night-text/night, phosphor/night. Mutation: lighten slate until it fails.
* Token-drift guard: the frontend `:root` block matches `gen_theme.py` output
  byte-for-byte (same pattern as `test_docs_fresh`).
* Semantic-color guard: no `--red`/`--warn` token referenced by any CSS class
  that is not a warning/destructive component (greppable, testable).
* Every existing kneeboard/brief/export test keeps passing untouched — the
  restyle changes pixels, not structure, so the structural suite is the safety
  net.

---

## 3. Phased implementation

### Phase 1 — Tokens, fonts, and the documents (one release)

Smallest blast radius first; the documents were restyled 24 h ago, so they move
to the final register before anyone gets used to the interim one.

1. Land `flightline.json`, `brand.py`, `gen_theme.py`, vendored fonts,
   contrast tests, artifact-registry entries.
2. Kneeboard: paper ground, ink text, **navy title band** replacing the black
   masthead, slate rules, black **data plates** for STATION/STORE headers,
   warning-red reserved for threat rings, caution-amber for degraded notes.
   Banner → identity rail (pending Rob's call, §5).
3. Brief PDF: Source Serif 4 body, Barlow Condensed headings, navy section
   bands, the four-part warning/caution/note blocks from the kit for the
   threat/safety content, identity rail header/footer.
4. DTC card (markdown), user guide PDF, whatsnew/roadmap HTML: same tokens via
   the generators.

### Phase 2 — The site, paper mode (one release)

The big one: ~3,000 lines of CSS-in-HTML re-skinned. Structure is untouched —
this is a token swap plus component re-skin, not a rebuild, and the v1.27→v1.31
redesign already concentrated color into `:root` vars, which caps the risk.

1. **Mode architecture**: `<body data-mode="paper|night">`, two token blocks,
   toggle in the topbar, choice persisted in the recipe-style URL param (no
   localStorage in artifacts; the site can use it — it already stores the
   ownership profile).
2. **Paper mode** (default, pending §5): paper ground, panels white with slate
   1-px borders (flat — shadows removed per the guide), navy topbar as the
   identity band, navy CTAs, ink text.
3. **Identity rail**: topbar becomes the rail — `DCS SORTIE STARTER · vX.Y.Z ·
   BETA` left, live `MAP · ERA · AIRCRAFT · SEED` (the share-link contents)
   right, in Plex Mono label style.
4. **Safety semantics**: engine warnings (`X-Warnings`) render as the kit's
   caution block (amber head, dark text, four-part structure where the message
   supports it); era-guard 400s as warning blocks; the BETA chip becomes a
   quiet slate label, not amber.
5. **Night mode**: existing dark palette re-stepped onto the kit's night tokens
   (bg → `#0A1118`, status greens → phosphor, cyan accents → instrument cyan,
   CTA stays navy-on-dark with white text). Every color-coded state gets a
   shape/symbol partner (●◆▲ per the specimen) — the guide's redundancy rule,
   and cheap to add where statuses already render.
6. **Wizard steps as procedures**: the numbered-square step counters from the
   specimen's procedure list replace the current step badges — which finally
   retires the hidden stale `<span class="n">` badges (a known dormant issue).

### Phase 3 — Heritage layer + polish (small release or ride-along)

Landing hero with the slanted banner; chart figure banners; guide PDF cover in
the kit's cover language (large aircraft figure, publication-style ID block);
grayscale-print check on the theater chart (hatching for WEZ rings so the chart
survives a monochrome printer — guide rule 4.4).

### Explicitly out of scope

S1000D/Level-3 tooling (the guide itself says don't), any React port (standing
decision), renaming publications to real TO numbers (endorsement risk — our
form IDs stay obviously fictional: `DSS 1-1` style).

---

## 4. Token mapping (site)

| Current | Becomes (paper) | Becomes (night) |
|---|---|---|
| `--bg #0B0E11` | `#F4F0E6` paper | `#0A1118` night |
| `--panel/#panel2` | `#FFFFFF` / `#F4F0E6`, 1-px slate border, no shadow | `#101820` stepped panels |
| `--line #33404D` | slate `#4E5963` at 40% | `#4E5963` |
| `--text/--dim` | ink `#171A1C` / slate `#4E5963` | `#E8EFEA` / slate-light |
| `--accent #FFB020` (CTA) | **navy `#17324D`** | navy-on-dark / instrument cyan focus |
| `--amber` (status) | caution `#F4B41A` — caution only | `#FFC857` + ◆ symbol |
| `--green #8FD14F` | olive `#4B5320` (taxonomy) | phosphor `#9BE28F` + ● symbol |
| *(none)* | warning `#B42318` — danger only | `#FF6B5F` + ▲ symbol |
| Archivo | Barlow Condensed (display) + Source Sans 3 (UI) | same |
| Barlow (body) | Source Sans 3 | same |
| IBM Plex Mono | unchanged — role formalised as data/identity | same |

## 5. Decisions needed from Rob

1. **Documents: identity rail instead of the classification banner?** The guide
   says drop the banner; we shipped it yesterday. (Recommend: rail.)
2. **Site default mode: paper or night?** (Recommend: paper default, night
   toggle in the topbar — it matches "tired of dark," keeps the night option
   for actual night flying.)
3. **Sequencing: Phase 1 alone first, or Phases 1+2 in one release?**
   (Recommend: separate releases — the site re-skin deserves its own review
   pass on screenshots before it ships.)

## 6. Risks

* **Scale of Phase 2**: mitigated by the var-concentrated CSS, the JS being
  untouched, `node --check`, the builder-UX test suite, and the screenshot
  artifacts (which release.sh regenerates and Rob reviews).
* **Contrast regressions**: the caution-amber-on-paper and slate-on-paper pairs
  are the two that historically fail AA; the token test computes them rather
  than trusting the kit's claim.
* **Font vendoring size**: five families ≈ 1.5 MB in the zip; subset to
  latin + the weights the tokens name.
* **Byte churn**: every document-rendering test that pins bytes re-baselines
  once, in Phase 1, and never again if tokens stay in one file.
