# Fly Now: instant action — spawn where the mission starts

*Discussion doc, 13 Aug 2026. Rob: "Fly Now should probably provide the user
with instant action. Maybe that starts in the air." Measured against v1.64.0.
Nothing built.*

---

## 1. The measurement: half the menu makes you commute

Generated all four Fly Now cards (Caucasus, modern, A-10A, seed 42) and
measured where the player spawns and how far the first interesting thing is.

| Card | Spawn | Alt | Distance to the action | Time before anything happens |
|---|---|---|---|---|
| **BFM Merge** | airborne | 4,500 m | bandit **6.1 km** | **~25 seconds** ✅ |
| **Tanker Time** | airborne | FL200 | tanker basket, by design ~7 km | **~1 minute** ✅ |
| **Kill the Guns** | **ramp, engines warm** | 0 | target **133 km** | taxi + takeoff + cruise ≈ **18 min in an A-10** |
| **Beat the SAM** | **ramp, engines warm** | 0 | ring **104 km** | ≈ **13 min in an A-10** |

The two air-start cards are exactly right — the BFM card puts you 25 seconds
from a merge, which is the whole product in one number. The other two ask for
**a quarter of an hour of taxiing and cruising** in a screen whose promise is
"I have fifteen minutes, put me in the air." At A-10 speeds the commute *is*
the session.

So: Rob's instinct is right, and it's not a nuance — it's half the feature
missing.

## 2. The principle: spawn where the interesting part starts

Not at the ramp (that's a commute), and **not on top of the target** (that
deletes the skill). The right spawn is the last moment before the problem
becomes yours:

| Card | Spawn it here | Why that point |
|---|---|---|
| BFM | 2 nm abeam, co-alt *(already correct)* | the merge is the exercise |
| Tanker | 7 km behind the basket at FL200 *(already correct)* | the join-up is the exercise |
| **Kill the Guns** | **8–12 km out, 8–10k ft, target off the nose** | you still have to find it, set up the wheel and roll in — but the ingress is free |
| **Beat the SAM** | **just outside the WEZ, medium alt, ring hot** | the RWR lights up in seconds; standing off, notching or going under it *is* the syllabus |

The engine already does this. `builder.py` has an air-start branch driven by
`air_start` in the template (`"tanker"` and `"merge"` exist today); adding
`"roll_in"` and `"outside_the_ring"` is a small, well-shaped change.

## 3. Two things to fix while we're in there

**Airframe-correct spawn numbers.** The default air start uses a fixed 4,500 m
and 700–800 km/h. That's a fast-jet number: an A-10 doesn't cruise at 430 kts,
and a warbird certainly doesn't. `formation.cruise_for()` already solves this
— it derives altitude and speed from the airframe's own `max_speed` and exists
precisely because hard-coded numbers turned a feature into "an F-16 tool".
Reuse it.

**Template defaults are applied client-side.** `qfRecipe()` merges the
template's `recipe` block in the browser, so `POST /api/generate` with just
`{"template": "qf_bfm"}` produces a **ramp start** — the air start silently
doesn't happen. Anything that isn't our own frontend (an API caller, a share
link built by hand, a future mobile client) gets the wrong mission. The merge
belongs on the server.

## 4. Make it a testable promise

This project's habit is to turn a design intention into a measured guard, and
this one is unusually easy to measure: **time to first action**.

Proposed test: for every Fly Now card, on several maps and airframes, generate
and assert the player spawns airborne and within **N minutes** of the nearest
threat *at that airframe's own cruise speed*. Ninety seconds is a defensible
ceiling; the BFM card currently does it in 25 seconds.

That converts "instant action" from a marketing sentence into something that
fails the build when it stops being true — and it protects against exactly the
drift that produced today's state, where two cards quietly kept their ramp
starts while the other two got air starts.

## 5. What about people who want the takeoff?

Some pilots genuinely want the full sortie, and the ramp start is the right
thing for the Library and the Builder — where you *are* flying a mission, not
running a rep. Fly Now is the exception, not the rule.

Proposal: **airborne is the default and needs no control.** If we want the
choice, it's one small toggle beside the spice selector ("Start: airborne /
on the ramp"), not a step. It should not cost a click for the common case.

## 6. Suggested scope

| | Change | Size |
|---|---|---|
| 1 | `air_start: "roll_in"` for Kill the Guns, `"outside_the_ring"` for Beat the SAM; both templates `start: air` | small |
| 2 | Air-start geometry uses `cruise_for()` instead of fixed 4,500 m / 800 km/h | small |
| 3 | Server-side template-recipe merge so the API gives the same mission as the UI | small, fixes a real correctness gap |
| 4 | `test_time_to_first_action.py` — every Fly Now card, airborne, ≤90 s from the action | medium |
| 5 | Optional "start on the ramp" toggle | small, only if you want it |

Items 1–4 are one release and would make the Fly Now promise literally true.
This is independent of the three-click work in `docs/ux-review-2026-08-13.md`
— they compose (fewer clicks *and* no commute) but neither blocks the other.

## 7. One open question

**Kill the Guns and Beat the SAM currently include a target package** — an
actual objective with a briefing. If we spawn you 10 km out with the target
already off the nose, do those stay "missions in miniature", or do they become
pure gunnery/RWR drills with no brief at all? My read: keep the brief (it's
one page and it's what makes the rep feel like a sortie), but the kneeboard
should open on the attack geometry rather than the flight plan, since there is
no longer a flight plan worth reading.
