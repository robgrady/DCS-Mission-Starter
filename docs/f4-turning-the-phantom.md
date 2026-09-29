# Turning the Phantom

*Training note for the `f4_turning_phantom` Library card. Source: **TAC ATTACK,
Vol 7 No 2, February 1967, page 4**, "Turning the Phantom — keep your speed up,
Podner." Published by the Tactical Air Command Chief of Safety, Col Homer C.
Boles. A US Government work.*

---

## The article, and why it is still the best F-4 handling document you can hand a pilot

Most aircraft-handling writing tells you what the airplane does. This one tells
you what it did to eleven crews, and then works backwards.

TAC reviewed 22 F-4 accidents. In **eleven of them the aircrew lost control of
the airplane** — half. Lined up, the eleven rhyme:

| Finding | Count |
|---|---|
| Maneuvering — pulling G — when they got into trouble | **10 of 11** (the 11th "safely a possibility") |
| At **300 knots or below** | **8 of 11** (one between 180 and 200 kt) |
| Carrying **external stores** | **11 of 11** — nine had two 370-gallon tanks; eight had at least one other store |
| **12,000 to 14,000 lb** of fuel aboard | 7 of 11 |
| At **low altitude** — "no time or space for recovery from post stall gyrations" | 8 of 11 |

And the part that should stop you: **these pilots were not inexperienced.**
Seven averaged 175 hours in the Phantom. Two of the four with less F-4 time had
plenty of previous fighter experience.

The article's own summary, which is the sentence to remember:

> in fifty percent of our F-4 accidents, the pilot lost control while he was
> maneuvering … with stores on … at too low a speed!

## The three mechanisms

### 1. You have about 3G, and you are used to five

From Figure 5-9 of the F-4C-1, for a clean airplane: **between 250 and 300
knots CAS you have around 3G (plus or minus one-half) available before stall.**

> For a fighter pilot, accustomed to pulling 4½ or 5G or more with plenty of
> airspeed during recovery from a weapons delivery pass, 2½ or 3G isn't very
> much.

That is the entire trap. Nothing about 3G *feels* like a limit on the way to it.

### 2. The stores took away half your stick

Category II Stability and Control tests on the F-4C found:

- In subsonic windup turns, a **nose-up pitching tendency shortly after entering
  buffet**, with stick forces *decreasing* alongside a sharp increase in the
  angle-of-attack gradient. Most acute in **approach configuration**.
- At **transonic** speeds, stick lightening became more pronounced — and
  **occurred at G loads well below buffet.**
- The pitch-up tendency exists with external stores as well as clean, and
  **external stores decreased stick force gradients an average of 50 percent.**
- External stores also **reduce the roll rate associated with pre-stall wing
  rock** — so the airframe's own warning gets quieter.

And as airspeed decreases, the energy available to generate buffet decreases,
so the stall warning gets fainter exactly where you need it loudest.

Then the Dash One warning about abrupt entry into accelerated stalls: **snatch
the stick back too fast and you can enter a stall with no noticeable buffet and
no wing rock.** All you get is moderate buffet *at* the stall.

### 3. Buffet is not a turn

> Buffet tells you two things … you're nearing critical angles of attack, and
> you've picked up an impressive amount of drag. Neither one does you any good
> when you're turning the airplane. If you pull far enough into the turn, drag
> increase causes airspeed to drop. Now you're just increasing turn by
> sacrificing speed, not because you're pulling tighter.

And past that, in Don Stuck's phrase quoted in the article, you are

> an unmaneuverable sitting duck in free fall trying to regain what you just
> threw away.

## Aft CG — the quiet contributor

The pilot's handbook permits external stores loading until CG runs back to a
maximum of **36 percent MAC**. The article walks a normal range configuration —
370s on stations 1 and 9, an SUU-21 with six Mk 76s on station 5, a LAU-32 with
three practice rockets on a TER at station 8:

| State | CG |
|---|---|
| At takeoff | **34 %** |
| Externals empty, internal wing + fuselage full | 33.6 % |
| Fuel in tanks 1, 2, 3, 4 only | 30.1 % |
| Non-standard sequencing, fuselage full + 2,000 lb in external wings | **35.2 %** — under 1 % from the limit |
| Externals transferred, fuselage full, wings empty | **35.1 %** — *"a very normal configuration which you encounter with standard fuel sequencing"* |

Aft CG is where the light stick and the pitch-up tendency are worst. You can be
inside every limit in the book and still be flying the sensitive airplane.

## How the sortie is built

`f4_turning_phantom` — Cold War era, F-4E, armed, air start, neutral line-abreast
merge. Three blocks, in this order, because the order is the argument:

**Block 1 — the 3G demonstration.** Get to 250–300 KCAS and find the buffet in a
level turn. Note the G. It will be about three. Do it again at 350 and note the
difference. *This is the whole article in two turns.*

**Block 2 — the drag lesson.** From 350, roll into a hard sustained turn and
hold it. Watch the airspeed. Find the moment where pulling harder stops buying
turn rate and starts buying it with speed. That moment is real, it is findable,
and it is not where most people think it is.

**Block 3 — the fight.** Line abreast, both hot, and now try to hold 350 KCAS
while somebody gives you a reason not to. The instinct is to trade speed for
nose position; the article is one long argument against that instinct. The
adversary is not the lesson — the adversary is what makes the lesson expensive.

## What we did NOT put in the mission

The same discipline as everywhere else in this product: the article's numbers
are the article's, and the gaps stay gaps.

- **No stall speeds or AoA values per configuration.** The article's own
  complaint is that the F-4 Dash One contained **no V-G diagram** and that the
  Operating Flight Limits chart plots G against *Mach*, not indicated airspeed —
  "we all know that an airplane stalls on an indicated (or calibrated) airspeed,
  not Mach!" The authors were asking for that data in 1967. We are not going to
  invent it in 2026.
- **No G limit for the mission.** The article gives 3G-ish *available* at
  250–300 kt; it does not set a limit to fly to.
- **DCS's F-4E is not TAC's F-4C.** The accident set is F-4C-era, the Category
  II tests were on the F-4C, and the CG figures come from an F-4C/D handbook.
  The *mechanisms* — light stick with stores, pitch-up after buffet, quiet
  warning at low speed, drag masquerading as turn — are what transfers, and they
  transfer well. Treat any specific number as history rather than as a spec for
  the module you are flying.

## Sources

- **TAC ATTACK**, Vol 7 No 2, February 1967, pp. 4–8: "Turning the Phantom."
  HQ TAC (OSP), Langley AFB, Va. Editor Capt John D. Shacklock; Chief of Safety
  Col Homer C. Boles.
- Quoted within it: the F-4C-1 flight manual (Figure 5-9, and Section VI
  *Flight Characteristics*), the Category II Stability and Control test report,
  and Don Stuck's "Spin, Crash, Burn … but … WHY?" in the McDonnell Field
  Service Digest.
- A US Government work; TAC ATTACK explicitly encouraged republication of its
  material by other Air Force organizations.
