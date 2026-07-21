# Concept: Theater Identity

*Concept doc · July 2026 · Owner: Rob Grady*

**One line:** give each map a real geopolitical and historical identity so the theater carries authenticity the user never has to configure. The map-scale sibling of carrier identity (real name, callsign, TACAN per hull).

**Why now:** we already generate liveries, SAMs, support air, dressing, and F10 graphics. Today they're driven generically ("blue"). Theater Identity is the *spine* that makes all of them era- and nation-correct from a single definition. It converts features we already ship from "plausible" to "authored."

**North-star fit:** everything here is information and environment the theater carries for you — not a routed flight plan. **No player waypoints.** Corridors and no-fly zones are drawn/briefed, never flown-for-you.

---

## The pillars

### Pillar 1 — International Alignment (the spine; build first)

An era-aware faction definition per map: who owns which airbase, who is hostile, who is neutral. Selecting Syria + modern + blue no longer means "blue" — it means flying as part of a realistic coalition (US/IDF/RAF at their real bases) against a Syrian/Russian layout.

The power is that one definition **cascades** into work we already do:
- **Liveries** snap to the airfield's real owning nation (drives the v1.8.7 nation packs by owner, not by a global picker).
- **SAM laydowns** become nation/era-correct and have a *reason* for their location (real strategic sites), not just "not in the ocean."
- **Support air** gets real theater callsigns (Magic/Overlord AWACS; Texaco/Shell/Arco tankers) and realistic orbits.
- **Dressing** gets base-specific static rosters (what actually parks at Incirlik vs Nellis vs Al Dhafra).

Data shape: a per-map/per-era `theater_identity.json` — country→coalition assignment, per-airfield owner, per-nation SAM/livery/callsign preferences. The recipe reads it; the builder cascades it.

### Pillar 2 — Theater IADS

A realistic red integrated air-defense laydown per map/era: EWR plus SAM belts positioned at real strategic sites, tiered by era (SA-2/3/6 for a period Syria red, modern doubles for a current one). "The map defends itself correctly." This is what finally makes the SEAD template *mean* something, and it consumes Pillar 1's nation/era data directly.

### Pillar 3 — Historical Airspace (corridors, no-fly zones, deconfliction)

The theater carries its real airspace structure for the selected era, rendered onto the **F10 map draw layer** (same mechanism as the carrier arrow) plus a kneeboard page. Because it's drawn/briefed information, it stays fully inside the north star.

Concrete, real anchors:
- **Germany, Cold War (1980s):** the three **Berlin air corridors** — North (Hamburg–Berlin), Center (Hannover–Berlin), South (Frankfurt–Berlin) — each ~20 statute miles wide, up to 10,000 ft, transiting East German airspace, plus the Berlin Control Zone. Managed by the Berlin Air Safety Center. Straying out risked Soviet interception. A signature, instantly-recognizable Cold-War feature from one terrain file.
- **Iraq (1991–2003):** **Operation Northern Watch** (no-fly north of the 36th parallel) and **Operation Southern Watch** (no-fly south of the 32nd/33rd parallel). A perfect authored-airspace feature for the Iraq map we're about to add.
- **Syria (modern):** the coalition/Russia **deconfliction line** (roughly the Euphrates) and safe-passage corridors from the flight-safety memorandum — "these are the lanes you may operate in."

Rendered as: F10 map polygons/lines for each corridor or zone, a kneeboard page describing the airspace and the rule ("remain within / do not cross"), and — optional, later — trigger zones so a future scripting layer could score corridor discipline.

### Supporting levers (lighter, hang off the pillars)

- **Named geography** — bullseye and reference points named after real features; target sets that are real installations (ports, bridges, POL, airfields). Briefings read like a real ATO.
- **Navaid/comms realism** — real TACAN/VOR/ILS and correct tower frequencies per field (we already harvest `atc_radio`); surface into kneeboards.
- **Theater weather** — theater-appropriate patterns on top of the per-map temperature/QNH tables we already carry (dust/haze for desert maps, seasonal presets).
- **Era layers** — same terrain, different decade → different roster, SAMs, jets, skins (Cold War aggressor Nevada vs modern from one terrain file).

---

## Sequencing

1. **International Alignment** first — it is the data spine; liveries, SAMs, callsigns, and dressing all key off "who owns this and who's the enemy."
2. **Theater IADS** second — consumes the alignment data; turns SEAD/strike into real content.
3. **Historical Airspace** third — high immersion, self-contained, rides the existing F10 draw layer; Iraq's no-fly zones and Germany's Berlin corridors are the showcase anchors.
4. Supporting levers folded in opportunistically as each pillar lands.

## North-star guardrail

Corridors, no-fly zones, and deconfliction lines are **drawn and briefed, never routed**. They enrich the airspace the player operates in; they do not fly the mission for them. This keeps Theater Identity firmly on the "Select, don't search" side of the line.
