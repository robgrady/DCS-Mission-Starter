# The F-16 B-Course track

*Instructional design note, 14 August 2026. Source: AETC Syllabus F16C0B00PL /
F16C0TX0PL / F16C0SOCPL (56 FW), "F-16C/D Initial Qualification", April 2014 —
the Luke AFB Combined Wingman Syllabus. 287 pages, 53 flying sorties in the
B-Course.*

---

## What this is, and what it deliberately is not

The B-Course is how the United States Air Force turns a pilot into an F-16
wingman. It is not a list of missions; it is an **architecture** — four phases,
each of which refuses to start until the previous one has been demonstrated,
and a grading grammar that separates *seeing* a task from *doing* it from
*owning* it.

That architecture is the thing worth taking. Eleven Library cards now follow
it. **They are not a reproduction of the course** — you cannot fly 53 sorties
in DCS with an instructor in the back seat, and pretending otherwise would be
the same lie as a briefing card with an invented number on it.

What they are: the sorties from that syllabus that DCS can deliver honestly,
flown to the real geometry, with the real task list, citing the paragraph.

## The architecture we took

**Four phases, in order** (syllabus para 2-7):

| Phase | Modules | What it settles |
|---|---|---|
| **TR** Transition | TR, INST, NTR | Can you fly the airplane? |
| **AH** Advanced Handling | AHC, BFM | Can you fight it against one jet? |
| **A-A** Air-to-Air | ACM, TI, ACT, NTI | Can you fight it as a flight? |
| **A-S** Air-to-Surface | LASDT, SA, SAT, CAS, SAN | Can you hit something with it? |

**The grading grammar** (para 2-9c), which is what makes it a syllabus rather
than a playlist:

- **Introduce** — the first time you see a task. Performance to standard is not
  expected.
- **Practice** — you have seen it. Standard still not required.
- **Demonstrate Proficiency** — standard required, graded, and it gates the
  phase.
- **Milestone task** — must meet standard *by* a named sortie or you do not
  progress.
- **Asterisked task** — required for the mission to count as complete at all.

A mission is **Effective**, **Effective/Incomplete**, **Effective/Regression**,
or **Non-Effective / Student Non-Progression**. Note the fourth one: failing is
a defined outcome with a defined consequence, not a vibe.

The cards carry the asterisked task lists verbatim in intent, so a pilot can
grade the sortie against the same items an IP would.

## The eleven cards

| Card | Real sortie | Para | Why this one |
|---|---|---|---|
| `bc_tr1` | **TR-1** Single-Ship Operations | 5-4 | The G-awareness profile is a real, exact, flyable number set |
| `bc_ahc` | **AHC** Advanced Handling | 5-8 | Turn-circle entry only — the sortie that makes BFM legible |
| `bc_bfm1` | **BFM-1** Offensive BFM | 5-9 | 9,000 / 6,000 / 3,000 ft perches |
| `bc_bfm4` | **BFM-4** Defensive BFM | 5-9 | Same three ranges, other seat |
| `bc_bfm7` | **BFM-7** High-Aspect BFM | 5-9 | First solo air-combat ride |
| `bc_acm1` | **ACM-1** Defensive ACM | 5-11 | Where one jet becomes a flight |
| `bc_ti1` | **TI-1** Single-Ship Tactical Intercepts | 5-12 | The radar as the weapon |
| `bc_lasdt1` | **LASDT-1** Low Altitude Step Down | 5-17 | The 500 ft AGL floor and the three rules |
| `bc_sa1` | **SA-1** Basic Surface Attack | 5-18 | Deliveries only, direct to the range |
| `bc_sat2` | **SAT-2** Element SAT | 5-19 | Ingress, threat reactions, wounded bird |
| `bc_cas1` | **CAS-1** Close Air Support | 5-20 | The sortie where you stop deciding |

The five existing **formation** cards cover the element-operations content of
TR-3 and TR-4, so they are not duplicated here.

## The single most valuable thing in the document

**The BFM perches were wrong, and now they are not.**

We shipped a three-perch BFM ladder in v1.66.0. The concept was right — geometry
as the difficulty knob, not an AI skill slider — but the ranges were ours:
2,200 m for the offensive and defensive perches, 3,700 m neutral, 9,260 m
high-aspect. Plausible, invented.

The syllabus flies offensive BFM on BFM-1/2/3 and defensive BFM on BFM-4/5/6,
and every one of those sorties runs the same three setups:

```
*6. Offensive BFM — a. 9,000 ft; b. 6,000 ft; c. 3,000 ft
*6. Defensive BFM — a. 9,000 ft; b. 6,000 ft; c. 3,000 ft
```

That is a **range ladder inside each position**, not one range per position —
a structurally better idea than ours, and it comes with numbers. Six new
setups (`off_9k`, `off_6k`, `off_3k`, `def_9k`, `def_6k`, `def_3k`) now sit
alongside the original four, which are frozen because share links minted
against them must keep building the identical mission.

Measured out of a generated `.miz`: 8,999 / 6,001 / 2,999 ft. `tests/test_bcourse.py`
asserts each one in **feet against the document**, not against the metres in our
own table — which the implementation would agree with by construction.

## What the syllabus does NOT contain, and what we therefore did not invent

This matters more than the list of what we built. Chapter 5 is a set of
*gradesheets*, not a tactics manual. It deliberately pushes the numbers to
AFTTP 3-3.F-16, AFI 11-2F-16V3 and unit phase guides. So it contains:

- **No dive angles, release altitudes, release airspeeds, pull-down points,
  pop parameters or safe-escape numbers** for any air-to-surface delivery.
  Deliveries are named by acronym only — HARB, HADB, LAHD, TMLT, LAS.
- **No count of engagements or passes** per BFM or ACM sortie. Only the setup
  ranges.
- **No pattern altitudes, pattern airspeeds, or approach minima** beyond
  "700-2" for post-TR-5 weather.
- **No BFM floor value.** "Floor awareness" is a graded milestone task, and the
  number itself is not in this chapter. Our `HARD_DECK_FT = 5000` was therefore
  labelled as **ours** — until two other documents turned up stating it for
  exactly this activity: the **48 OG F-15C Flying Training Syllabus** (Feb 2009,
  "Floor: 5,000 ft AWL/AGL") and **AFMAN 11-2F-22A Vol 3** Table 3.2
  ("Air Combat Training / Advanced Handling: 5,000"). Now cited, not invented.
  See `docs/source-library-proposals.md`.
- **No G limits** beyond the 8–9 G G-awareness turn.

The cards therefore name the deliveries and the tasks and stop. Where a number
*is* in the document, it is in the card exactly:

| Number | Value | Where |
|---|---|---|
| BFM setup ranges | 9,000 / 6,000 / 3,000 ft | BFM-1…6 task 6 |
| G-awareness profile | 4 G warm-up → 6–8 G 180° → 8–9 G 180°, ≥2 AGSM cycles per turn | TR-1 Note 2 |
| Low-level floor | 500 ft AGL | 5-16f(1) |
| LOWAT CAT I band | 1,000 → 500 ft AGL | LASDT-2 Note 3 |
| LATF tactical turns from wing | minimum 2 | LASDT-1 Note 5 |
| Minimum maneuvering speed >5,000 ft AGL | the low-speed warning tone — terminate at the tone | 5-7d, 5-10g |
| High-to-low conversion target speed | 250–300 kt | NTI-1 Note 3 |
| Weather minima after TR-5 | CAT 3, 700-2 | 5-1a |
| Student-to-IP ratio | 1:1, except 2:1 on SA-1 – SA-4 | 5-1b |

## The 42 sorties we did not build, and why

Not an oversight list — a scope decision, stated so nobody has to guess.

**Cannot be delivered honestly in DCS today**

- **INST-1/2/3** (instruments, strange field, ACBT). DCS has approaches; it does
  not have an IP who can fail your gyro and watch you not notice.
- **NTR-1/2, NTI-1/2, SAN-1…6** — every night and NVG sortie. These are
  buildable as *missions*; what is not buildable is the NVG qualification the
  syllabus is actually granting. A card that says "night qualified" would be
  claiming something we cannot check.
- **TR-5** (Instrument/Qualification Evaluation) and the other check rides. An
  evaluation without an evaluator is a flight.

**Needs a human in another seat to mean anything**

- **TI-2…TI-5, ACT, SAT-4/5/6** — element and four-ship work. The engine will
  build them; the *training* is the flight-lead coordination, and a card that
  hands you three AI wingmen teaches the opposite lesson.
- **CAS-2** — the syllabus explicitly warns against launching without a
  dedicated FAC(A)/JTAC.

**Repeats of a card we already have**

- **BFM-2/3** (offensive), **BFM-5/6** (defensive), **SA-2/3/4** — the same
  sortie flown again at the next setup or with the next weapon. Re-fly
  `bc_bfm1` at `off_6k` and `off_3k`; that *is* BFM-2 and BFM-3.

**Needs weapons or systems we do not yet drive**

- **SA-5** (live GP), **SA-6/7/8** (LGB, IAM, inert), **SA-9/10** (scored
  range, 5 qual bombs + 5 LOFT). The delivery parameters are not in this
  document, so building these means either sourcing AFTTP 3-3.F-16 or inventing
  numbers. We will do the first or neither.

## Where this goes next

1. **A B-Course tab in the Library**, with the cards in phase order and the
   phase gates visible, so the track reads as a progression rather than eleven
   cards that happen to share a prefix.
2. **The 6K and 3K perches as their own cards**, if the Builder round-trip
   turns out to be friction rather than flexibility. Worth watching in the
   analytics before adding six more cards.
3. **AFTTP 3-3.F-16 for the delivery parameters**, which would unlock SA-5
   through SA-10 and make `bc_sa1` a much sharper card.
4. **A gradesheet kneeboard page** — the asterisked task list with Effective /
   Incomplete / NE-SNP boxes. The syllabus's real contribution is that it makes
   you say afterwards whether it counted, and that is a document we can
   generate.

---

*Source document: AETC Syllabus F16C0B00PL (56 FW), April 2014, HQ AETC/A3ZF.
Cited by paragraph throughout the cards. Distribution on the original is
restricted to DoD and DoD-contractor use for the course; nothing from it is
reproduced here beyond the structural facts and the specific figures listed
above, which is what a citation is for.*
