# Library audit — what's compelling, and what doesn't make sense

*Campaign-design review, 15 August 2026. All 41 Library cards **built** and their
contents compared against what their briefs promise. Not read — built.*

---

## First, a fair hit I should own

The previous review's Proposal 2 led with "AFMAN 11-2F-22A" and Rob's response
was the correct one: **we don't have the F-22 in DCS.**

The proposal was never to fly an F-22 — that document is a generic USAF
ops-procedures manual whose floors and airspeed gates apply to any fighter, and
it happens to carry an F-22 title. But leading a proposal with an airframe the
customer cannot fly is a framing failure regardless of what the fine print says.
If the first thing a reader sees is an aircraft that isn't in the sim, the
proposal has already lost. My fault, not his misreading.

---

## Method

Every card was generated at seed 7 and the resulting `.miz` inspected: client
slots, enemy and friendly aircraft, vehicles, statics, moving groups, tanker,
AWACS, trigger zones. Then each brief was searched for the things it *promises* —
"moving target", "9-line", "wingman", "tanker", "range" — and checked against
what the mission actually contains.

**That comparison is the whole audit.** A card whose brief describes a mission
the file does not contain is the same failure as an invented number in a
briefing card: the pilot believes it, flies looking for something that isn't
there, and concludes the tool is broken.

---

## Broken: the brief promises something the mission does not contain

### 1. `bc_cas1` — the worst offender

The brief says, in capitals:

> **THE 9-LINE IS THE SORTIE. Read it back.**

and

> plan at least ONE attack against an actual **moving target**

The mission contains **no JTAC, no 9-line, and nothing that moves.** Two target
packages with AAA, sitting still, and a tanker.

A pilot loads this, reads "read the 9-line back", and finds no one to read it
back to. This card currently teaches that our briefs cannot be trusted.

### 2. Two accusations I got wrong — and the lesson in them

My first pass also flagged `f100_fulda_cas` and `f100_victor_alert`. **Both were
innocent, and reading their actual text is instructive:**

> `f100_fulda_cas`: "No JTAC datalink in this era — talk-on off the F10 picture
> and your own eyes."

> `f100_victor_alert`: "No fixed waypoints: pick your own run-in around the
> threat rings. GCI only — no AWACS."

Those cards **name the gap in order to close it.** My matcher saw the keyword
and missed the negation — the same error as flagging escaped HTML because the
payload's characters are still in the output, which I also made this week.

The lesson runs the other way from what I expected: **the older cards in this
Library were more disciplined about this than the twelve I added in the last two
releases.** Naming what is absent is better writing than silence, and it was
already the house style before I stopped following it.

### 3. Nothing in the entire Library moves

**Zero moving vehicle groups across all 41 cards.** Two cards are *named* for
movement:

- `armed_recon_route` — "armed recon" against parked vehicles
- `af_convoy_overwatch` — a convoy that is not driving anywhere

This is a known engine gap (ROADMAP lists "Moving convoys" under *Later*), but
the cards were written as if it were closed. Either the briefs stop implying
movement, or the gap moves up the roadmap. It is the single biggest gap between
what this product says and what it does.

---

## Thin: a long brief over a nearly empty mission

### 5. `bc_lasdt1` — a low-level card with nothing at low level

Thirty lines of brief: the 500 ft floor, an eight-item awareness block, the 1 %
/ 50 % / 10 % rules, "the threat tier is guns, and that is the point."

The mission contains: the player, one ambient friendly, one ambient enemy, and
airfield dressing. **No guns. No targets. Nothing to fly at, around or under.**

The recipe sets `threat_tier: "guns"` with `threat_intensity: 1` and no targets
— so the tier has nothing to attach to. The pilot gets an empty desert and a
reading assignment. **This is the least compelling card we ship.**

### 6. `bc_tr1` — briefs an empty sky, then puts an enemy in it

> Nothing is trying to kill you and nothing is supposed to.

The mission contains an airborne `Ambient enemy 2`. It will not attack, but it
is a red aircraft in a mission that promised none — and on the *first card of
the track*, which is where trust is built.

### 7. `bc_sa1` — honest, but the range is thin

I was wrong in my first pass: the range **is** there — six fuel tanks in a ring
and three strafe targets. But the brief walks three distinct delivery patterns
(HARB, HADB, LAHD) and "grade yourself on flying the same pattern three times"
against nine static objects and no scoring. It works. It is not yet *good*.

---

## Compelling: what's actually working

Worth saying, because most of it is:

- **The BFM cards** (`bc_bfm1/4/7`, `bc_ahc`, `qf_bfm`, `f4_turning_phantom`,
  `f100_sabre_dance_bfm`). One jet, one bandit, exact geometry, a standards card
  on the kneeboard. Nothing promised that isn't delivered. **This is the
  product at its best** and it is not an accident — these are the cards where
  the brief describes geometry we assert in tests.
- **The formation ladder** (`form_*`). Five cards, one job each, a lead who
  behaves identically every time, radio coaching. Correct instructional design.
- **The carrier cards** (`carrier_qual`, `acls_practice`, `f14_case3_night`).
  Clear premise, deck, tanker, no over-claiming.
- **`sead_range`, `gun_belt_strike`, `cv_alpha_strike_escort`** — dense, real
  missions with threats, packages and support that match their briefs.
- **`f4_turning_phantom`** — the tightest card in the Library. A specific
  article, three specific exercises, one bandit, and a conclusion you can quote.

---

## Library-level UX problems

### 8. The NEW badge means nothing

**28 of 41 cards are flagged `new`** — 68 %. A returning pilot cannot see what
actually changed this month. `new` should be a rolling window of the last one
or two releases, not a permanent decoration.

### 9. The Library now reads as a school

**17 of 41 cards are role `training`** — 41 %. Add the five formation cards and
the four Quick Flight reps and more than half of what a first-time visitor sees
is homework. The Library's job is "pick something and fly in under a minute";
right now the front page argues for a syllabus.

**Fix:** the eleven `bc_*` cards should collapse into ONE Library entry — a
B-Course *track* — that expands into its sorties. Same for the formation ladder.
That is one card and one decision instead of eleven cards and eleven decisions.

### 10. Four cards have no role

`qf_tanker`, `qf_bfm`, `qf_guns`, `qf_sam` carry no `library.role`, so the
frontend synthesises one. They are the Quick Flight reps and they should be
tagged `training` explicitly rather than defaulted.

### 11. Three cards tell the user to go configure something

`bc_ahc`, `bc_bfm1` and `bc_bfm4` each say some version of:

> open this in the Builder and change the BFM setup to `off_6k`

That is a card admitting it did not finish its job. The user picked a card
*because* they did not want to configure. Either ship the 6K and 3K perches as
their own cards, or have the track sequence them — but do not hand the pilot a
config task in the middle of a briefing.

---

## What I'd change, in order

| # | Change | Size |
|---|---|---|
| 1 | **Stop the briefs promising what the missions lack** — `bc_cas1` was the only genuine offender; rewritten to name both gaps | ✅ done |
| 2 | **A permanent guard** — `tests/test_library_promises.py`, negation-aware | ✅ done |
| 3 | **Fill `bc_lasdt1`** — a low-level card needs something at low level: a route, gun positions, terrain features to navigate by | medium |
| 4 | **Ambient enemy traffic off** where the brief promises an empty sky (`bc_tr1`, `bc_sa1`) | ✅ done |
| 5 | **Collapse `bc_*` and `form_*` into two track cards** | medium, biggest UX win |
| 6 | **`new` is a rolling window** — 28 of 41 became 12 of 46, guarded at a third | ✅ done |
| 7 | **Moving convoys** — closes the largest say/do gap in the product | large, and now clearly justified |
| 8 | **6K/3K perches shipped as cards** — no card sends the pilot to the Builder mid-brief any more | ✅ done |

**What I would not do:** build more cards until 1, 2 and 4 are done. We have 41
and at least four of them do not do what they say. Adding a twelfth B-Course
sortie while `bc_cas1` promises a 9-line that does not exist is the wrong order
of work.

---

## The rule this suggests

We already have a rule that says a number in a briefing must be measured or
cited. This audit says it needs a sibling:

> **A brief may only promise what the mission contains.** If the engine cannot
> build it, the brief does not mention it — and if the brief mentions it, a test
> proves it is in the file.

That is checkable, it is cheap, and it would have caught all four broken cards
the day they shipped.
