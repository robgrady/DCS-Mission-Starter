# AAR Academy — incorporation review

**Reviewing:** *Air-to-Air Refueling Training Campaign — Research & UX Plan* (2026-08-16, wiki: dcs-maker)
**Against:** DCS Mission Starter v1.73.1 (`missiongen/aar.py`, six AAR Library cards, `formation.py`, `crewops.py`)
**Date:** 2026-08-16

---

## Verdict

The plan and the product converged independently, which is the good news and
the awkward news. Roughly **60% of the plan is already shipped** — the pedagogy,
the tanker speeds, the pre-contact start, the sight-picture card, the
probe/boom lanes. The remaining 40% is not more content. It is **one
architectural decision**: whether a generated `.miz` is allowed to contain
executable Lua.

Everything the plan calls "instrumentation", "graduation evidence",
"competency grades" and "the debrief" collapses into that single question.
Answer it and the rest is a fortnight of writing. Dodge it and we ship ten more
kneeboards.

---

## 1. What the plan asks for that we already have

| Plan element | Status in v1.73.1 |
|---|---|
| Formation-first, not narrative-first | Shipped — six standalone cards, no campaign wrapper |
| Delete the commute; start at the position | Shipped — `air_start: astern_tanker`, 1 nm astern / 1,000 ft below / on speed |
| Tanker at a speed the receiver can fly | Shipped — per-tanker IAS with an IAS→TAS conversion at the track altitude |
| "ME speed presentation ≠ cockpit IAS" (plan's DCS constraint) | Shipped — this was the v1.73.0 bug; 550 km/h ≈ 217 KIAS at FL200 |
| Probe lane (Hornet-first) and boom lane (Viper-first) | Shipped — `aar_3_probe` / `aar_boat` vs `aar_1_join` / `aar_2_contact` / `aar_4_night` |
| Precontact sight picture, tanker features as references | Shipped — "THE FOUR POSITIONS" on the procedure card |
| External focus ("fly the tanker, not the basket") | Shipped — it is the headline of `aar_3_probe` |
| PIO framed as gain, not character | Shipped — "WHY IT OSCILLATES, WHICH IS NOT A CHARACTER FLAW", four gain levers |
| Self-controlled hints via the F10 menu | **Machinery shipped, not wired to AAR** — `crewops.CrewFlow.add_command()` already builds F10 item → flag → action, with progressive disclosure and difficulty-gated hints |
| Bandwidth feedback (silence while in tolerance) | **Machinery shipped, not wired to AAR** — `formation.py` runs a live coaching loop on ME triggers with a hysteresis deadband (out at radius, credited back at 60% of it) so it cannot ping-pong |
| Night lane | Shipped, and **the plan does not have one.** Keep ours. |

Two of those rows matter more than the rest. We already own a **live in-mission
coaching state machine** and an **F10 self-service hint menu**. The plan
assumes both must be built in Lua. They exist, in Python, emitting Mission
Editor triggers, tested, in production.

---

## 2. The actual decision: does a `.miz` get Lua?

The plan's measurement design needs `S_EVENT_REFUELING`,
`S_EVENT_REFUELING_STOP`, `Unit.getFuel()` and 5 Hz relative-position sampling
in the tanker's local frame. **None of that is reachable from Mission Editor
triggers.** ME conditions cannot see a refuelling event and cannot read fuel.

### What triggers *can* honestly measure

| Quantity | Condition | Fidelity |
|---|---|---|
| Distance to the tanker | `UnitInMovingZone(player, R, tanker)` | A **sphere**, not a box — cannot tell astern from abeam |
| On-speed | `UnitSpeedHigher` / `UnitSpeedLower` | Good; the track speed is a constant we set |
| On-altitude | `UnitAltitudeHigher` / `UnitAltitudeLower` | Good; the tanker holds a constant altitude |
| Dwell time in tolerance | `TimeSinceFlag` | Good — this is the plan's "stabilized for N seconds" |
| Excursion count | `IncreaseFlag` on fall-out | Good — this is "≤2 inadvertent disconnects", by proxy |
| **Contact / disconnect** | — | **Impossible** |
| **Fuel taken** | — | **Impossible** |
| **Closure rate** | — | Impossible directly; approximable as speed delta vs the known track speed |

### What shipping Lua costs

Not "some effort". Four specific things:

1. **Inline `DoScript` does not work in our stack.** Recorded in
   `scripts/build_projection_probe.py`: `m.string()` serialises the script as a
   dictionary key that DCS compiles literally →
   `"'=' expected near '<eof>'"`. The proven path is a **resource file +
   `DoScriptFile`**, which means every graded mission carries an extra file
   inside the `.miz`.
2. **Share links.** Our byte-stability discipline exists so an old share link
   regenerates the same mission. A resource file in the zip is new surface area
   for that guarantee.
3. **Testability.** Our whole test culture is "generate the mission, assert on
   the contents". We cannot assert on Lua that only runs inside DCS. A grading
   engine would be the first substantial piece of this product with **no
   automated proof it works** — and given this session's tally of vacuous tests,
   that should worry us more than it worries most teams.
4. **Integrity Check / multiplayer.** Worth confirming before committing;
   the plan does not address it.

### The recommendation

**Split it, and be honest in the brief about which tier the pilot is in.**

- **Tier 1 — trigger-graded (no Lua).** Grade *position, speed, altitude and
  dwell*, with bandwidth feedback and F10 hints, reusing `formation.py` and
  `crewops.py`. Do not claim to grade contacts. This is on-thesis: the plan's
  own central claim is *"AAR is close formation flying with a fuel connection
  attached"* — so grading the formation and staying silent about the plug is
  not a compromise, it is the argument.
- **Tier 2 — Lua-instrumented (later, opt-in).** Contact seconds, fuel delta,
  disconnect cause, the three-item debrief, the qualification certificate. Ship
  it behind a flag once we know the IC answer and have a way to prove it works.

Tier 1 delivers the plan's Missions 0–2 and about **half the qualification
gate** with zero new architecture.

---

## 3. Syllabus mapping — plan's 10 vs our 6

| Plan mission | Our card | Gap |
|---|---|---|
| 0 · Fit Check | — | **New.** Diagnostic: can you hold a wing position at all? Highest-value new card — it stops people starting at mission 3. Tier 1 gradeable. |
| 1 · The Anchor | `aar_1_join` | Close. Ours does join-up *and* observation hold; the plan splits them. Add grading, keep the card. |
| 2 · The Closure | *(inside `aar_2_contact`)* | **Split out.** Ours conflates closure with contact. The plan is right that closure control is its own lesson. Tier 1 gradeable. |
| 3 · First Plug | `aar_2_contact` | Shipped. Grading needs Tier 2. |
| 4 · The Flow (multi-ship rotation) | — | **New.** Needs AI receivers cycling through contact. Cheap to build, no grading needed — it teaches patience and the pattern. |
| 5 · Reset (deliberate bad approach → recover) | *(a paragraph in `aar_2_contact`)* | **New card.** This is the plan's best original idea and it is currently buried in prose. |
| 6 · The Turn | — | **New.** Tanker in a banked turn; the receiver flies the inside/outside geometry. Needs the orbit timed so the player meets him mid-turn — non-trivial waypoint work, and the plan's own note that the Orbit advanced action overrides waypoint speed bites here. |
| 7 · The Rendezvous | — | **New, and it re-adds the commute we deliberately deleted.** Justified *once*, late, as a named skill — never as the default entry point. Flag this to anyone who builds it. |
| 8 · Qualification | `qf_tanker` | Exists as practice, not as a gate. Tier 1 can gate 3 of the 6 criteria (config/stabilised precontact/no unsafe closure); the other 3 (contact seconds, disconnects, fuel) need Tier 2. |
| 9 · Operational Transfer | — | **New — and the highest-value card in the plan.** The generator already produces real missions with tankers; this is the one that makes AAR training pay off in the actual product rather than in a training annex. |
| — | `aar_4_night` | Ours. The plan has no night lane. Keep it. |
| — | `aar_boat` | Ours. Carrier-organic (S-3B / KA-6D). Keep it. |

**Net new cards: 6** (Fit Check, The Closure, The Flow, Reset, The Turn,
Operational Transfer), plus The Rendezvous if we accept the commute argument.

---

## 4. Numbers to reconcile before writing anything

Two places where the plan and the shipped card disagree. Neither is a
catastrophe; both must be resolved rather than silently picked.

**Closure rate.** The card says **1–3 kt closure**. The plan cites **KC-46
≈ 1 ft/sec**. One knot is 1.688 ft/s, so the card is asking for **1.7–5.1
ft/s — two to five times the plan's figure.** They are not measuring the same
phase: 1–3 kt is a reasonable *approach* closure from pre-contact, ~1 ft/s is
the *final few feet*. **Fix:** state both, phase-labelled. The card is
currently wrong by omission.

**Stabilisation time.** The plan gates on **15 s stable at pre-contact**; the
card asks for **zero closure for 60 s**. These are different claims — a gate
versus a proficiency demonstration — and the card presents its 60 s as though
it were the standard. **Fix:** 15 s is the gate, 60 s is what "good" looks
like. Say so.

**Also:** the card's ATP-56 attribution for the 60 s figure should be
re-checked against `docs/SOURCES.md`. If it is not in the library, it goes
under the honest-numbers rule as a tuned setting, like the tanker speeds.

---

## 5. What I would cut or defer from the plan

- **The campaign wrapper.** The plan already says formation-first; agreed, and
  it should stay deferred past the graded cards. The wrapper is the part that
  ages worst.
- **`Unit.getFuel()` as evidence.** The plan flags it itself: it is a fraction
  and may not represent external tanks uniformly. As a *grade input* it is
  unsafe. Fine as a debrief nicety; not a gate criterion.
- **Competency currency ("Current").** Requires persistent state across
  sessions, which this product does not have and should not grow for this.
  Ship Developing / Proficient / Qualified; drop Current.
- **5 Hz sampling.** If we do Tier 2, sample at the rate the coaching needs
  (~2 Hz for feedback, higher only for a closure estimate), not the rate the
  plan happens to name.

---

## 6. Risks the plan names, and one it does not

Named and correct: AI tanker behavior changes with DCS patches; contact events
do not say *why* a disconnect happened; the Orbit advanced waypoint action
overrides waypoint speed.

**Not named:** a graded mission that grades the wrong thing is worse than an
ungraded one. If a Tier 1 sphere-based position check calls a pilot "out of
position" when they are correctly abeam, we have taught them to distrust the
grade — and once they distrust it, every later grade is noise. **Tolerances
must be wide enough that a correct pilot is never wrong**, even at the cost of
letting a sloppy one pass.

---

## 7. Proposed sequence

1. **Reconcile the numbers** (§4) — a card edit, no new architecture.
2. **Wire `formation.py`'s coaching loop to the tanker** — the pre-contact
   station-keeping check. One module, reuses tested machinery.
3. **Ship Mission 0 (Fit Check) and Mission 2 (The Closure)** graded at Tier 1.
   These two prove the grading tier is worth having.
4. **Wire the F10 hint menu** via `CrewFlow` across all AAR cards.
5. **Ship Reset, The Flow, The Turn, Operational Transfer** ungraded.
6. **Decide on Lua** with the IC and testability answers in hand. Only then
   Tier 2 and the qualification certificate.

Steps 1–2 are small. Step 3 is the one that tells us whether the whole Academy
idea works in this product.
