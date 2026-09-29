# Skillwork: the reps a DCS pilot actually needs

*Discussion doc, 13 Aug 2026. Written from the pilot's chair, checked against
what the engine can already do.*

---

## 1. The problem worth solving

A DCS pilot buys a module, flies the included training missions, and plateaus.
Not from lack of content — there is more free content than anyone can fly —
but because of three things:

1. **What kills you is never practiced in isolation.** You don't lose a sortie
   because "you're bad at DCS". You lose it because you couldn't plug the
   basket and went home, or you lost sight at the merge, or an SA-6 you never
   heard took you at 18,000 ft.
2. **A mission bundles six skills at once.** When it goes badly you learn "that
   was hard", not *which* part beat you.
3. **Repetition without variation teaches the mission, not the skill.** Fly the
   same tutorial ten times and you've memorised where the bandit is.

What real squadrons do instead is **rides**: one skill, defined setup, defined
standards, flown until the standard is met, then the next rung. That is what
this product is unusually well positioned to generate — because the setup *is*
a recipe, and a recipe can be rerolled.

**The frame I'd argue for: Sortie Starter isn't a mission generator that also
has practice. It's the range complex and the syllabus, that also generates
missions.**

## 2. What makes a rep different from a mission

A rep is not a small mission. It's a different object, and the difference is
worth being strict about:

| | Mission | Rep |
|---|---|---|
| Length | 30–60 min | **5–15 min, five of them in a session** |
| Skills | many, bundled | **exactly one** |
| Start | ramp or air | **airborne, at the problem** (v1.65.0) |
| Success | "did I complete it" | **a number you can self-assess** |
| Variation | new mission | **same setup, rerolled** |
| Progression | none | **rungs** |

Two of those we now have (instant action, reroll). The two missing pieces are
**standards** and **rungs** — and they're the cheap ones.

## 3. The insight: geometry is the difficulty ladder

The thing we built for instant action — precise control of where the player
spawns relative to the problem — is *the same machinery a rep ladder needs*.
Almost every air-combat skill's difficulty is set by geometry, not by an AI
skill slider:

- **BFM** — the classic syllabus is three setups and they are pure geometry:
  *offensive perch* (you at his 6, ~1.2 nm, 30° angle off), *defensive perch*
  (he's at yours), *high-aspect merge* (line abreast, both hot). Same bandit,
  same skill setting; completely different rides.
- **Intercept/BVR** — the ladder is range and aspect: 40 nm hot, 25 nm beam,
  20 nm with a bandit that notches when you lock.
- **SAM defeat** — one ring, then overlapping rings, then a pop-up SHORAD.
- **Carrier** — day/calm, day/pitching deck, night Case III.

Turning the AI skill up to Excellent is the lazy version of difficulty and it
teaches the wrong lesson: DCS AI at Excellent flies physics that a human can't
match, so the pilot learns "I lose", not "I flew that badly". **Geometry is the
honest knob.** We already know this — `add_bfm_adversary` deliberately drops
the bandit one notch below the intensity's skill for exactly this reason.

## 4. The syllabus

Marked ✅ shipped, ◐ partial, ○ missing.

### A. Airmanship — the skills that decide whether the sortie happens at all
| Rep | State | Notes |
|---|---|---|
| Formation (5 rungs) | ✅ | route → close → energy → rejoin → takeoff. **This is the model** — a real ladder, already built. |
| Air refuelling | ◐ | Tanker Time exists as one rung. Ladder: calm/high → turbulence & turning basket → **low fuel, one chance** → night. |
| Pattern work & landing | ○ | Overhead break, straight-in, crosswind, single-engine, **fuel emergency**. `unit.fuel` is settable — a "you have 900 lb, field is 20 nm away" rep costs almost nothing. |
| Emergencies | ○ | pydcs exposes `SetFailure` triggers. Engine failure after rotation, hydraulic loss, battle damage RTB. Almost nobody practices this and it's the most memorable ride in any syllabus. |

### B. Air-to-air
| Rep | State | Notes |
|---|---|---|
| BFM | ◐ | One neutral merge. **The three-perch ladder is the single highest-value thing on this page** — offensive/defensive/high-aspect, plus guns-only. Pure geometry; the machinery exists. |
| ACM (2v1, 2v2) | ○ | Section employment, sorting, "who's shooting". Needs a friendly AI wingman with sane BFM behavior. |
| **BVR / intercept** | ○ | **The biggest gap in the product for modern jets.** Radar mechanics, the sort, the timeline, crank/notch/pump. Ladder by range and aspect, with a bandit scripted to notch. Medium build, very high value. |
| Gun jinking / defensive | ○ | Being shot at, from a known start. |

### C. Air-to-ground
| Rep | State | Notes |
|---|---|---|
| Guns/rockets on a target | ✅ | Kill the Guns (now airborne on the run-in). |
| Dive/CCIP/CCRP delivery | ◐ | `bb_range` builds a bombing circle + strafe pit; it isn't a rep yet. Add pass-type rungs and standards. |
| Laser / buddy-lase | ◐ | The F-14 IZLID crew-op exists; not a repeatable rep. |
| SEAD / Iron Hand | ◐ | Two Library missions; no rep. Ladder: known site → search-and-shoot → shoot-and-scoot. |
| **CAS with a JTAC** | ○ | Hugely compelling — 9-line, talk-on, "cleared hot". Also the **most expensive** item here: needs a controller unit, a scripted talk-on and briefing plumbing. |

### D. Survival
| Rep | State | Notes |
|---|---|---|
| SAM defeat | ✅ | Beat the SAM (v1.65.0), one ring. Rungs: overlapping rings, pop-up SHORAD, MANPADS in the target area. |
| RWR interpretation | ○ | "Name what's looking at you" — could be a pure-observation rep with no weapons at all. |

### E. Naval
| Rep | State | Notes |
|---|---|---|
| Case I recovery | ◐ | CQ exists as a mission. Ladder: calm → pitching deck & wind → **night Case III** (the f14_case3_night template is the top rung already). |
| Launch & departure | ○ | Cheap, and the other half of boat work. |

## 5. The two force multipliers

Both are cheap, and they change the product's character more than any single
new rep.

### Standards cards — "what good looks like", on the kneeboard
A rep without a standard is just flying around. Real syllabi publish numbers,
and the kneeboard renderer already exists:

> **CASE I RECOVERY — STANDARDS**
> Break at 800 ft, 350 kt · Abeam 600 ft, gear/flaps, on speed
> 180° position: 600 ft, 1.2 nm · Groove 15–18 s · **Boarding rate ≥ 60%**

That single card converts "I flew the pattern" into "I was 200 ft high abeam
and long in the groove". **No scoring code required** — the pilot grades
themselves, which is what actually happens in debrief anyway. This is the
highest value-per-hour item in this document.

### Currency — the loop that brings people back
Real aviators must stay current: so many traps in 30 days, so many approaches.
It's a genuinely motivating structure and it costs a localStorage counter:

> "Current: BFM ✓ (3 days) · Tanker ✓ (9 days) · **Traps: 21 days — not
> current**"

No accounts, no server, nothing personal stored. It turns a generator into a
habit, and it's the natural home for the "remembered pilot" store the UX
review already wants.

## 6. What I'd build, in order

| | Item | Why here | Cost |
|---|---|---|---|
| 1 | **BFM three-perch ladder** (offensive / defensive / high-aspect, + guns-only) | Highest-demand skill in DCS; the geometry machinery already exists; turns one card into a syllabus | small |
| 2 | **Standards cards** on every rep | Makes every existing rep self-assessable; renderer exists | small |
| 3 | **Pattern & landing ladder** incl. a fuel-emergency rung | Everybody lands, nobody practices the bad landing; `unit.fuel` is one line | small |
| 4 | **Carrier ladder** (calm → pitching → Case III) | The most-practiced skill in DCS; we have the deck machinery and the top rung | small–medium |
| 5 | **Currency tracker** | Converts reps into a habit | small |
| 6 | **BVR / intercept ladder** | The biggest genuine capability gap; needs a bandit with scripted behavior (hot/cold/notch) | medium |
| 7 | **SAM ladder rungs 2–3** | Extends what we just shipped | medium |
| 8 | **A/G delivery ladder** on the practice range | Needs the range upgraded from fuel tanks and tents to something scoreable | medium |
| 9 | **Emergencies** | Distinctive, memorable, nobody else does it; `SetFailure` exists but needs care | medium |
| 10 | **CAS with JTAC** | The most compelling single ride on the list, and the most expensive | large |

Items 1–3 are one release and would triple the practice content without a new
subsystem. My honest recommendation: **do 1, 2 and 3 together, then re-read the
analytics** — the reps people actually reroll will tell us whether to spend the
next release on the boat or on BVR.

## 7. Three questions I'd want your call on

1. **Where do reps live?** They're outgrowing the four-card Fly Now screen. A
   ladder needs somewhere to show rungs and progress — a "Training" tab (already
   on the roadmap) with the formation stages moved into it, or does Fly Now
   grow a "more reps" affordance?
2. **Standards: published numbers or self-set?** Publishing "boarding rate ≥
   60%" invites "says who?". I'd publish, cite the type where it matters, and
   let the pilot ignore it — the number's value is that it's *specific*, and a
   wrong-but-specific number gets corrected by a user, which is exactly what
   the Contact form is now for.
3. **How honest should the AI be about being AI?** For BFM I'd rather brief
   "this bandit flies at High, not Excellent — that's deliberate, Excellent
   flies physics you can't match" than let a pilot conclude they're bad. Does
   that belong in the brief, or is it too much inside-baseball?
