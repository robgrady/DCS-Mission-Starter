# What Eagle Dynamics has actually shipped for DCS: Iraq

*Product research, 14 August 2026. Every claim below has a source; where I could
not verify something I say so rather than filling the gap.*

---

## The finding that changes our plan

We shipped seven Iraq air corridors in v1.68.0 aimed at the Iran–Iraq war and at
Desert Storm / Iraqi Freedom. **Eagle Dynamics has not built the terrain for
either of those yet, and has built it for a third war we had no era for.**

Their own framing of the region that ships today:

> *"The focus of this initial, Northern region, is provided to support missions
> and campaigns mainly pertaining to the Global War on Terror and ISIS."*
> — [ED, 13 December 2024](https://www.digitalcombatsimulator.com/en/news/2024-12-13/)

And, in the same post, that **Desert Storm and Iraqi Freedom are the *southern*
region** — which has not shipped.

## Release state

| | |
|---|---|
| Developer | Eagle Dynamics (first-party) |
| Status | **Early Access**, still, in August 2026 |
| EA release | 11–13 December 2024 |
| Total terrain | 1,820,000 km² |
| **North region (detailed)** | **321,750 km², the only region released** |
| South region (detailed) | 491,550 km² — announced, **never shipped**; its Q2 2025 target was missed by over a year and no new date exists |
| SKUs | Iraq North $39.99 · full Iraq $69.99 · Iraq South announced, unreleased |

**Watch the store page.** It advertises "28 highly detailed airfields." Twenty
are in the sim. The number is forward-looking (17 North + 14 South planned) or
stale; either way it is not a shipped count.

## Airfields — our 20 are complete and current

Cross-checked against the MOOSE `AIRBASE.Iraq` enum (independent, code-derived)
and the ED changelogs. Our vendored list from the dcs-retribution pydcs fork is
the full shipped set as of today.

- **Launch, Dec 2024 (13):** Al-Asad, Al-Sahra, Al-Taquddum, Al-Taji, Baghdad
  International, Balad, Erbil International, Bashur, K1 Base, Al-Salam, Kirkuk
  International, Qayyarah West, Sulaimaniyah International.
- **Added Aug 2025 (6):** H-2, H-3 Main, H-3 Northwest, H-3 Southwest, Al-Kut
  (ED calls it "Al-Jarrah (Al-Kut)"), Mosul.
- **Added 22 July 2026 (1):** Kharg.

## Kharg Island — new, and better than we assumed

Not in the initial release. Added **22 July 2026**, build 2.9.28.26283. The
changelog, verbatim: *"Added Kharg Island with an airfield and unique objects
(terminal, atc, oil flares, and pipelines)."*

It is an **Iraq South asset delivered early** — ED's May 2026 dev report
described adding *"the strategically important Kharg Island with its airfield
and refinery complexes."*

Two consequences for us. The Kharg corridor's far end is now a modelled oil
complex rather than a bare strip, which is a real upgrade for the tanker-war
lane. And the 800-odd km of Gulf between our western basing and the island runs
over the undetailed band.

**A correction to my own earlier assumption:** I had thought this was a re-use
of an older free ED "Kharg Island" area. There is no evidence for that — the ED
terrain catalog has never listed such a product, and searches for it return
*Battlefield 3*'s map of the same name. This is new work.

## What else shipped on 22 July 2026 — and is worth aiming at

**Nine named dams, each with a unique 3D model:** Dukan, Alwand, Fallujah,
Haditha, Hemrin, Kut, Ramadi, Samarra, Diyala. Plus road signs, curbs,
dirt-road detailing, expanded vehicle routes and trains.

Earlier landmarks: Baghdad and Babylon palaces, Tomb of the Unknown Soldier,
Grand Festival Square, Kirkuk and Al-Shaab stadiums, Mar Mattai Monastery,
Erbil Martyrs Monument, Qayyarah control tower, Al-Rahman Mosque.

**This is why v1.69.0 has `infrastructure` and `oil_terminal` target packages.**
Aiming a strike at a structure someone modelled is categorically better than
aiming it at four fuel tanks in a field, and the Haditha and Mosul dams are
real operational objectives with real histories.

## Not confirmed — do not build on these without checking in-sim

- **Tuwaitha / Osirak reactor.** No mention in any ED source. It sits ~17 km
  south-east of Baghdad, inside the detailed North region, so it may be modelled
  generically — but there is no citation. This is the biggest single gap for
  historical mission design.
- **Lake Razazah** — ED mentions "additional lakes" generically, never this one.
  It is one of the two features that *define* the Karbala Gap.
- **Karbala Gap, Hawizeh marshes, Halabja** — no mention; central/southern band.
- **Baghdad "Green Zone" / Republican Palace** — "palaces" plural is confirmed;
  which ones is not.
- **Named Kirkuk / Rumaila oil infrastructure** — "oil plants" is a *planned*
  POI category.
- **A post-2003 Baghdad restricted operating zone**, and the famous BIAP
  "corkscrew" approach. Widely repeated; no citable authority found. What *is*
  documented is the 22 November 2003 DHL A300 hit by an SA-14 at ~8,000 ft
  during a rapid climbout.
- **Seasons** for Iraq — never announced either way.

## Roadmap

1. **Iraq South** — southern Iraq, western Iran, Kuwait, Bahrain, Qatar, Saudi.
   Named in progress: Kuwait International, Ali Al-Salem, Jubail, Ras Al-Mishab,
   Riffa, Sakhir, Shiraz, Omidiyeh, Al-Udeid, Prince Sultan. **No date.** ED's
   2026 roadmap warns "not all are expected to be released in 2026."
2. **Eastward into Iran — evaluation only.** *"Following the Iraq map expansion
   to the south, we will then evaluate expanding the Iraq map to the east to
   include several important Iranian airbases that were critical during the
   Iran-Iraq War."* That is the only thing standing between us and a properly
   supported Iran–Iraq era, and it is not a commitment.
3. Size-optimisation technology, terrain refinements, expanded landmarks and
   regional POIs (oil plants, power infrastructure, hospitals), road network,
   additional airfield layouts.

## What we did about it

| Finding | Action in v1.69.0 |
|---|---|
| North region built for GWOT/ISIS; we had no such era | **New `gwot` era**, Iraq + Afghanistan presets, six corridors |
| Desert Storm / OIF band is undetailed | Kharg, Southern Watch and Karbala Gap keep their place in the picker but now carry a `terrain_note` briefed verbatim |
| Iran–Iraq unsupported by ED, and only "under evaluation" | Cold War corridors stay — DCS lets you fly any era on any map, and the geometry is real. The scenery caveat is briefed. |
| Nine dams + Kharg terminal modelled | `infrastructure` and `oil_terminal` target packages |
| Dukan Dam now a real 3D model | Jafati Valley re-anchored onto it |
| Our 20-airfield table | Confirmed complete; **expect churn when Iraq South ships** — plan to re-export |

## Sources

- [Iraq is now available! (ED, 13 Dec 2024)](https://www.digitalcombatsimulator.com/en/news/2024-12-13/) · [pre-order announcement (19 Oct 2024)](https://www.digitalcombatsimulator.com/en/news/2024-10-19/)
- [DCS: Iraq Release FAQ (ED Forums)](https://forum.dcs.world/topic/365676-dcs-iraq-release-faq/)
- [DCS: Iraq product page](https://www.digitalcombatsimulator.com/en/products/terrains/iraq_terrain/) · [Iraq North store page](https://www.digitalcombatsimulator.com/en/shop/terrains/iraq_north_terrain/) · [ED terrains catalog](https://www.digitalcombatsimulator.com/en/shop/terrains/)
- [Iraqi map development progress (ED, 29 Aug 2025)](https://www.digitalcombatsimulator.com/en/news/2025-08-29/)
- [2026 Roadmap Part 2 (ED, 9 Jan 2026)](https://www.digitalcombatsimulator.com/en/news/2026-01-09/) · [Iraq and Afghanistan Dev Reports (ED, 16 May 2026)](https://www.digitalcombatsimulator.com/en/news/2026-05-16/)
- [Changelog 2.9.28.26283, 22 Jul 2026](https://www.digitalcombatsimulator.com/en/news/changelog/release/2.9.28.26283/) · [changelog index](https://www.digitalcombatsimulator.com/en/news/changelog/release/)
- [MOOSE Wrapper.Airbase documentation](https://flightcontrol-master.github.io/MOOSE_DOCS_DEVELOP/Documentation/Wrapper.Airbase.html)
- [Stormbirds — Iraq launch](https://stormbirds.blog/2024/12/11/dcs-iraq-lauches-together-with-new-update/) · [May 2026 dual status reports](https://stormbirds.blog/2026/05/15/eagle-dynamics-provides-dual-status-reports-on-dcs-iraq-and-afghanistan-maps/) · [Threshold — pre-purchase writeup](https://www.thresholdx.net/news/ediraq)
