# DCS drawing tools — military-chart authenticity evaluation

*Design reference · July 2026 · lens: visual design + military aviation cartography*

Goal: make our F10 overlays read like a real tactical mission-planning chart, not game "zones." Verdict up front: **DCS's drawing engine is capable of it — the authenticity lever we're leaving on the table is line *style* (and weight, and restraint), not color or fill.** Every setting below was inspected in the pydcs drawing module and verified to serialize into the `.miz`.

---

## 1. The lever inventory (what DCS actually gives us)

**Primitives:** Line (segment / multi-segment / freeform; closeable; thickness; style), Polygon (Circle, Oval, Rectangle, FreeForm, Arrow — each with fill, thickness, style), our `add_oblong` stadium helper, **Icon** (built-in tactical symbols), TextBox.

**Line styles — 17, all verified serializing:** `solid, solid2, dot, dot2, dash, dotdash, cross, square, triangle, wirefence, strongpoint, boundry1, boundry2, boundry3, boundry4, boundry5`. The `boundry*` set renders as directional border symbology (ticks/hatching perpendicular to the line) — exactly how published charts draw restricted/special-use boundaries and how tactical charts draw the FLOT/FEBA. `strongpoint`/`wirefence` are tactical field styles. **This is the single most under-used capability.**

**Color:** RGBA hex, with **fill alpha independent of line color** — so we can have a fully saturated boundary over a near-invisible fill, which is precisely what a chart is.

**Typography:** `fontSize`, `font` (overridable; default is already a condensed sans — `DejaVuLGCSansCondensed`, aviation-appropriate), **`angle`** (rotate a label to a corridor/route axis), border thickness, fill (halo).

**Tactical icons (`StandardIcon`):** Mechanized, MechInfantry, Recce, Logistics, (Rocket)Artillery, **AirDefense, SearchRadar** — an APP-6-flavored set. A red ring with an AirDefense glyph at its center reads as a SAM threat instantly; a plain circle does not.

**Layers:** shared `Common` + per-coalition `Blue/Red/Neutral`, visibility per layer — lets us separate the published/shared picture from coalition-private intel.

---

## 2. Where our overlays currently miss

- **Everything is `LineStyle.Solid`** — no type encoding at all. A corridor, a threat ring, and a FARP all draw with the same edge.
- **Flat translucent flood fill (alpha ~18–22)** — reads as colored glass. Real charts are line-work on terrain; large areas are outlined, not flooded.
- **One line weight** — no hierarchy, so nothing tells the eye what's a hard boundary vs an advisory.
- **Single violet for all airspace** — no semantic color system.
- **Labels are horizontal and generic** — no altitude blocks, no axis alignment, no chart grammar.

The net effect is "MOBA minimap," not "mission chart." Fixable entirely with settings we already have.

---

## 3. The design system (real chart conventions → DCS settings)

Published aero charts (VFR sectionals) and tactical planning tools (FalconView / JMPS drawing layers, TPC/ONC/JOG) encode meaning through **boundary style + line weight + restraint**, with color as a secondary semantic. Six principles:

1. **Boundary style carries airspace *type*.** Assign `line_style` by class:
   - Prohibited / no-fly → `boundry3` or `boundry4` (heavy directional hatching), heaviest weight, zero fill.
   - Restricted / MOA / special-use → `boundry1` or `dash`.
   - Corridor / airway → `solid` thin boundary **plus a `dotdash` centerline** (airways are drawn with a centerline).
   - FLOT / FEBA / FSCL → `strongpoint` / `wirefence`.
   - ADIZ → `dot` / `dot2`.

2. **Weight hierarchy** (`line_thickness`): hard boundaries 5–6, corridors 3, centerlines 1–2, annotations hairline. Weight alone creates the read order a chart needs.

3. **Fill restraint.** Alpha **0–12**, not 20+. Zero fill + a styled boundary for anything large; a whisper of tint (≤10) only for small emphasis. Saturated line, near-invisible fill.

4. **Disciplined color semantics** (one palette, everywhere):
   - Threat / hostile / no-fly → **red**
   - Friendly / controlled / corridors → **cyan-blue**
   - Special-use / advisory → **magenta/violet** (authentic — sectionals use magenta for special-use airspace)
   - Neutral reference (bullseye, nav) → **desaturated white / gold**

5. **Typography like a chart.** ALL CAPS, condensed font (keep the DCS default), **altitude-block notation** ("`100/GND`" = 10,000 ft ceiling to ground; "`FL240/8000`"), corridor labels **rotated to the axis** via `angle`, consistent anchor offset, black halo for legibility. Small and tight beats big and soft.

6. **Tactical symbology for points.** Use `StandardIcon.AirDefense` / `SearchRadar` at SAM sites (with the WEZ ring), ground-unit glyphs for laydowns. This is the fastest single upgrade in perceived authenticity.

---

## 4. Recommended settings spec (our elements)

| Element | Color (line) | Fill α | Weight | Line style | Label |
|---|---|---|---|---|---|
| Corridor swath | cyan | 0 | 3 | `solid` | axis-rotated `» NORTH  100/GND` |
| Corridor centerline | cyan | — | 1 | `dotdash` | — |
| Control zone (CTZ) | cyan | 8 | 4 | `solid` | `BERLIN CTZ · 20SM · ≤100` |
| No-fly zone (Iraq OSW/ONW) | red | 0 | 6 | `boundry3` | `OSW NO-FLY — S OF N32°` |
| Restricted / MOA | magenta | 0 | 3 | `boundry1` | `R-xxx  SFC–100` |
| Threat WEZ ring | red | 0 | 3 | `solid` + `AirDefense` icon | `SA-6 · 25KM` |
| FLOT / FSCL | side color | — | 4 | `strongpoint` | `FSCL 1200Z` |
| Deconfliction line (Syria) | amber | — | 3 | `dash` | `DECONFLICTION` |
| Bullseye | white | 5 | 2 | `solid` (dual ring) | `◎ BULLSEYE` |

---

## 5. Honest limits of the DCS tool (design *around* them)

- **No true polygon hatching / fill patterns** — texture lives only in the *line* style. So authenticity = boundary styling, never fill flooding.
- **Curves are circles/ovals only** — no arcs or sectors; a SAM MEZ arc must be approximated by a full ring.
- **Text is a rotatable box, not path-following** — `angle` suits straight corridors, not curved airways; place labels manually at a midpoint.
- **Fixed icon set** — not full APP-6, but AirDefense / SearchRadar / armor cover the common threat and ground cases.
- **Uniform alpha per object** — no gradients.

Net: DCS's layer is a **tactical planning overlay (FalconView register), not a published sectional** — which is exactly the register we want. It gets convincingly authentic through disciplined *line style + weight + restraint + tactical icons*, all of which are available and confirmed working.

---

## 6. Recommendation

Adopt a small shared **chart-style module**: one semantic palette + a category→(color, fill, weight, style) table, consumed by `graphics.py`, `airspace.py`, the threat overlay, and `navpoints.py`. Single change point, consistent chart grammar everywhere; future no-fly zones and threat laydowns inherit it for free.

Rollout order by visual payoff:
1. **Threat rings + SAM icons** (biggest perceived-authenticity jump — styled rings replace flat red discs, `AirDefense` glyphs mark the shooters).
2. **Berlin corridors** retrofit as the airspace reference implementation (centerline, altitude blocks, axis labels, restrained fill).
3. Bullseye / nav points align to the palette; **Iraq no-fly zones** then ship already-authentic via `boundry3`.
