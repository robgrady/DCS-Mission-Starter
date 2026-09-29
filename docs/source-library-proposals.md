# What's in the PDF library, and what to build from it

*Instructional-design review, 15 August 2026. 29 documents. Read, not skimmed —
every claim below is traced to a document and a page.*

---

## The headline: one of our invented numbers turns out to be doctrine

`missiongen/bfm.py` carries `HARD_DECK_FT = 5000`. Four days ago I labelled it,
in `docs/f16-bcourse-track.md` and on the Sources page, as **ours** — because
the AETC B-Course syllabus grades "floor awareness" without ever stating the
floor.

**Two documents in this folder state it, independently:**

- **48 OG F-15C Flying Training Syllabus** (493d FS, RAF Lakenheath, Feb 2009,
  signed Col John T. Quintas, 48 OG/CC). SPINS for MQT-2, MQT-3, MQT-4,
  2 FL-1/2/3: **"Floor: 5,000 ft AWL/AGL."**
- **AFMAN 11-2F-22A Vol 3**, *F-22A Operations Procedures*, 20 Sep 2018,
  Table 3.2 Minimum Altitude Summary: **Aerobatics / Air Combat Training /
  Advanced Handling — 5,000 ft AGL.**

Same number, two services' worth of paperwork apart, for the same activity.
Our hard deck stops being a guess and becomes a cited standard. **This is the
cheapest and most valuable change in the entire review.**

And a second corroboration: the 48 OG syllabus flies **"Offensive BFM 3K', 6K',
9K'; Defensive BFM 9K', 6K', 3K'"** — the *same three perches* we took from the
F-16 B-Course in v1.71.0. That ladder is not F-16-specific. It is how the USAF
teaches BFM, and we now have it from two commands and two airframes.

---

## Three corrections you should know about

**1. The two "TO" files are not Technical Orders.** Both
`TO-1F-16CMAM-34-1-1-BMS.pdf` and `TO-1F-15C-34-1-1-BMS.pdf` are **Falcon BMS
community manuals** ("BMS dev team", versions 4.37.4 / 4.37.3, copyright rather
than distribution notices). Excellent documents — but if you were expecting the
real delivery-parameter annexes, they aren't there. The F-16 one even says so:
it describes dive-recovery altitude loss as matching *"the numbers in the
reference table"* and then does not print that table (p.581). The F-15C one is
frank that its air-to-ground sections are **"not implemented yet."**

**2. The "Lockheed Martin F-22A Weapons Delivery Manual" is misnamed** — it is
**AFMAN 11-2F-22A Volume 3**, an Air Force operations-procedures manual with no
releasability restrictions. It contains no weapons data at all. It is also, by
some distance, the **most immediately useful document in the folder** (see
Proposal 2).

**3. The delivery parameters are still missing.** Dive-angle / release-altitude
/ release-airspeed matrices, pull-down points, pop-up geometry, safe-escape
distance tables — not in any of these 29 documents. If you want SA-5 through
SA-10 built properly, the sources are the **AFTTP 3-3 series** or a genuine
**TO 1F-16CM-34-1-1 with its ballistics annexes**. Worth saying plainly so
nobody spends another evening hunting.

---

## The proposals, ranked

### 1. An F-15C training track — 8 to 10 cards · *high value, low risk*

**Source:** 48 OG F-15C Flying Training Syllabus, Feb 2009, 109 pp.

This is a real signed squadron syllabus and it is **richer in hard numbers than
the AETC B-Course**, because its SPINS tables specify the actual fight setups.

The gift is the **Perch / All-Aspect ACM card (MQT-5)**, which gives geometry
precise enough to code directly:

> Blue **16–18,000 ft, 1.5–2.0 nm line abreast, 440 kt ±10**; Red **16–18,000 ft,
> 6–9,000 ft trail**. Blue block 8–16; Red ≤7 or ≥17. Floor 5K. Regen >15 nm
> (>20 desired).

And the rest of the ladder, all stated:

| Card | Setup | Numbers |
|---|---|---|
| MQT-1 Local Area / AHC | — | — |
| MQT-2/3 Offensive & Defensive BFM | 3K / 6K / 9K perches | Floor 5,000 ft; kill = 2 missiles or 3-1 gun track |
| MQT-4 High-Aspect BFM | **Butterfly** | Rule of 12's, <2K of floor; **one missile per merge**; only one AIM-9X counts |
| MQT-5 Perch / All-Aspect ACM | as above | the card to build first |
| MQT-6 Tactical Intercepts | 2 v 4 | Blue block 0–4K, Red 5–9K; floor 1K; **no pre-planned maneuvers >30 nm**; Link-16 off on the first run |
| MQT-7/8 DCA | 2 v 4 | **15–25 min vul window, 5-min TOT window inside it**; Red regen 2 min cold, no closer than 30 nm |
| MQT-10 LOWAT | — | 500 ft AGL; **maneuvering limited below 5,000 ft AGL both sides** |

**Why this one first:** it is a near 1:1 fit for what our engine already does,
it needs no new building blocks, and it gives the F-15C the same treatment the
F-16 just got. The "one missile per merge" and "Rule of 12's" scoring rules also
give us something we have never had — **a stated way to score a fight.**

---

### 2. A training-rules layer under every card · *high value, small*

**Source:** AFMAN 11-2F-22A Vol 3, 20 Sep 2018 (the misnamed file).

Every training card we ship invents its own limits. This document is a generic
USAF fighter ops-procedures template with the limits already set:

- **Floors:** ACM/AHC 5,000 ft · KIO 1,000 ft · low-altitude Cat I 500 ft ·
  formation low approach 100 ft
- **Airspeed gates:** **300 KCAS minimum for low-level navigation**;
  **350 KCAS minimum for low-altitude tactical maneuvering below 5,000 ft AGL**
- **Deconfliction:** 1,000 ft altitude separation, **500 ft below 5,000 ft AGL**
- **G-awareness:** flight members hold **6,000 ft separation** during the exercise
- **Weather gates:** VFR rejoin day 1,500/3 · night 3,000/5 · low-level nav
  1,500/3 · low-altitude intercepts 3,000/5
- **Ops checks** at 10,000 ft or level-off, before each engagement, after AR;
  *"same" call permitted within 500 lb of lead's fuel*
- **Eight briefing-guide skeletons** we could generate against

Note the 350 KCAS number: it is the *same* figure TAC ATTACK gave in 1967 as the
F-4's basic maneuvering speed. Fifty-one years apart, same answer.

**Build:** a shared "training rules" block on the kneeboard for every `bc_*`,
`form_*` and BFM card, plus the floors becoming real, tested values rather than
per-card prose.

---

### 3. Operation Bolo — 2 January 1967 · *the marquee historical mission*

**Sources:** Scutts, *Wolfpack: Hunting MiGs Over Vietnam* (full planning and
execution, callsigns, launch times, loadouts); Futrell et al., *Aces and Aerial
Victories* (USAF official).

Robin Olds' 8th TFW flew F-4Cs on **F-105 routes, at F-105 speeds and altitudes,
with F-105 callsigns and ECM pods**, so North Vietnamese GCI would launch
MiG-21s against what it believed were bombers. Seven MiG-21s destroyed for no
losses.

**Why it is the best historical proposal we have:** the mission is a *ruse*, and
a ruse is terrain-independent. Everything that makes Bolo Bolo — the false
signature, the staggered five-minute TOTs, the overcast the MiGs had to climb
through — can be built anywhere.

**Terrain:** no Vietnam map. **Caucasus** is the honest analogue — ridge and
river valley, clustered ex-Soviet airfields at roughly the right 15-mile
spacing, native S-125, and MiG-21bis and F-4E both exist.

*Sources disagree* on two points, and we would say so on the card: Scutts
credits the concept to **Capt John B. Stone** (22 Sept 1966); *Aces* puts Olds
at 7AF on **22 December** and credits the 7AF commander. And *Aces* says both
"12 minutes" and "15 minutes" of combat, in different chapters of the same book.

---

### 4. Eagle Flight, 2 September 1972 — hunter-killer · *most immediately buildable*

**Source:** *Smoke Trails* 5/4 ("One Day, One MiG"), the F-105 Thunderchief
historical society journal.

A four-ship Wild Weasel hunter-killer over Phuc Yen that ends with a MiG kill —
self-contained, one package, coordinated SAM-and-MiG defense, and **every
component has a DCS equivalent today**. Where Bolo is the marquee mission, this
is the one we could build this week.

**Terrain:** Syria or Caucasus. **Build:** an Iron Hand card with a real
hunter-killer split — the Weasel trolls, the killer shoots — which is a mission
type we do not currently teach at all.

---

### 5. "Twenty Thousand Pounds of Fighter Performance" · *TAC ATTACK, Aug 1975*

Ranked first out of ~40 feature articles across ten TAC ATTACK issues. The
mission: **one lightweight fighter against two F-4Es above 30,000 ft** — engage
the first to his bingo, separate, engage the second to his bingo, and land above
your own bingo. Exactly as the Joint Test Force pilots demonstrated it.

That is a complete, scoreable sortie with a pass criterion that is not "did you
win" but **"did you still have fuel."** We have nothing like it.

---

### 6. Eldorado Canyon — the terminal 25 minutes · *ambitious, honest about scope*

**Sources:** van Waarde (2006) — a per-airframe callsign / target / outcome
table and a minute-by-minute Zulu timeline; Endicott (USAF official) — ROE and
command rationale.

**The full mission cannot be built and we should not pretend otherwise:** 6,400
miles, 13–14 hours, four air refuellings, and no F-111F, EF-111A, A-6E or A-7E
in DCS. What *is* buildable is the last 25 minutes — night, coast-crossing,
low-level, urban and airfield targets, SA-2/SA-3, feet-wet egress.

**Terrain:** Syria (Akrotiri is on-map and was historically used) or Sinai.

*Sources disagree* on Karma 52's fate — shot down after release (van Waarde) or
crashed before reaching the target (Endicott) — which materially changes a
script. And on the Aziziyah results, 2 of 9 vs 3 dropped. We would use Endicott
where they conflict; she is the official history.

---

### 7. A back-seater task syllabus · *for the F-14 and any two-seat module*

**Source:** NAMRL-1170, *A Function Level Commonality Analysis of the F-4/F-14
NFO Positions*, US Navy, Nov 1972. Unclassified, public release.

Six roles, 24 duties, a full task taxonomy with per-task ratings for time,
importance and complexity. It tells you *what the back-seater does* with more
rigour than anything else in the folder — and its finding is the design
principle: **Sensor Manager is 26% of tasks but 46% of what's new**, and the
real difficulty is not any single duty but **integrating across roles.**

**Build:** sorties that isolate one duty at a time — radar management, degraded
and jammed radar with forced mode reversion, data link, INS — then a deliberate
role-integration capstone. Our crew-ops templates already exist; this gives them
a progression.

---

### 8. TAC ATTACK handling cards · *cheap, and they compound*

Ten more issues, ~40 feature articles. After "Turning the Phantom", the ones
worth building, in order:

| Card | Source | The sortie |
|---|---|---|
| **Task saturation at 500 ft** | Oct 83, "Got a Minute? — Maybe" | A-10 low-level with scripted radio/IFF/weapons tasks forced on you at random; you may not exceed the article's worst case — **500 ft lost in 11 seconds, wings level** |
| **Spatial misorientation** | Aug 85 | F-16 night IMC radar-trail departure with a caution light; **never 45 seconds without an attitude reference** |
| **Hydroplaning** | Jul 75 | F-4E wet-runway recovery. **Dynamic hydroplaning onset ~110 kt nose / ~140 kt main**; formula **8.6 × √(tire pressure)**; reverted-rubber skid sustains **down to ~10 kt** |
| **The Saga of Blue Flight** | Mar 78 | F-4E four-ship overhead with a **15-kt left quartering tailwind**; 60° break, 200 kt final turn; anyone braking above 100 kt blows tires |
| **Red Flag Mistakes** | Mar 78 | F-4E four-ship interdiction vs F-5E aggressors — comm-out, terrain masking, **never show a white belly**, split to force a commit |

---

## What I would do, in order

1. **Re-label the hard deck as cited, not invented** (30 minutes, and it makes an
   existing claim more honest rather than less).
2. **The F-15C MQT track** — 8 to 10 cards, the richest ready-made syllabus here.
3. **The training-rules layer** from AFMAN 11-2F-22A, under everything.
4. **Eagle Flight 2 Sep 72** as the first historical card, because it is
   genuinely buildable now.
5. **Operation Bolo** as the marquee, with the source disagreement on the card.
6. TAC ATTACK cards as filler between larger pieces — each is an afternoon.

**What I would not do:** promise Eldorado Canyon end-to-end, or build any
air-to-surface delivery card that needs parameters none of these documents
contain.

---

## Sources

All documents read in full or sampled to their tables of contents and then
deeply where relevant. Per-claim page citations are in the working reports.

- AETC Syllabus F16C0B00PL (56 FW), Apr 2014 — *already shipped, v1.71.0*
- 48 OG / 493 FS F-15C Flying Training Syllabus, Feb 2009
- AFMAN 11-2F-22A Vol 3, *F-22A Operations Procedures*, 20 Sep 2018
- TAC ATTACK: Feb 1967 *(shipped)*, Jul 1975, Aug 1975, Mar 1978, Dec 1979,
  Oct 1983, Jun 1985, Aug 1985, May 1986, Jan 1987, Sep 1987
- Scutts, *Wolfpack: Hunting MiGs Over Vietnam*
- Futrell et al., *Aces and Aerial Victories: The USAF in Southeast Asia
  1965–1973* (USAF official)
- van Waarde, *The bombing of Libya: Operation Eldorado Canyon* (2006)
- Endicott, *Raid on Libya: Operation ELDORADO CANYON* (USAF official)
- *Smoke Trails* 5/4 (F-105 Thunderchief historical society)
- Boyne, *Route Pack 6*
- NAMRL-1170, *F-4/F-14 NFO Function Level Commonality Analysis*, USN, Nov 1972
- Pavlović & Pavlović, *Fighter Performance in Practice: Phantom vs MiG-21*
  (2009) — **19-page excerpt only; printed pages 69–79 are missing**, which is
  exactly the instantaneous-vs-sustained turn chapter
- Falcon BMS community manuals for the F-16C and F-15C (labelled as TOs)
