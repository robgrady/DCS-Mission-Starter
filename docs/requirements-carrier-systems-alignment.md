# Requirements — Carrier Systems & Aircraft Alignment
**Feature:** "The boat is up, and your jet already knows it."
**Author:** Claude (DCS player / app developer perspective) · For: Rob Grady · 2026-07-16 · Status: DRAFT for approval

---

## 1. Problem statement

A carrier mission is only "ready to fly" if the ship's approach and navigation systems are radiating **and** the aircraft's cockpit is set up to use them. Today the Sortie Starter handles the first half; the second half is left to the pilot, who must build radio presets by hand or dial frequencies from the kneeboard mid-flight. The Mission Author (our generator) should deliver both halves aligned, with zero user configuration.

## 2. Current state (audited v1.8.9)

**Ship side — largely done, but un-gated.** `naval.add_carrier_group` already activates all four systems at mission start on waypoint 0: TACAN 71X "STN", ICLS channel 11, Link4 336 MHz, ACLS, plus the Marshal frequency (264.425 "Mother"). Gap: these are applied to **every hull identically** — the 1944 Essex and 1982 Invincible receive ICLS/Link4/ACLS activations they don't support in DCS (silently ignored, but wrong: it documents systems in the comm card that the boat can't actually provide).

**Aircraft side — nothing.** Player/client aircraft spawn with the module's factory-default radio presets. Our comm plan lives on the 25 kHz raster (AWACS 251.475, Tanker 253.625, Angel 262.050…) — none of it is in the cockpit. The pilot must hand-tune every frequency from the kneeboard.

**Verified pydcs capability:** `FlyingUnit.set_radio_channel_preset(radio_id, channel, MHz)` works for **87 airframes** that ship `panel_radio` templates — including every carrier-capable flyable we offer (F/A-18C, F-14A/B, AV-8B) and the major land-based ones (F-16C, F-15E SE, F-4E, A-10C…). Known engine caveat (documented in pydcs): DCS clobbers the first compatible channel with the flight's assigned frequency — so channel 1 must always BE the flight frequency by design.

**Hard constraint:** aircraft-side TACAN, ICLS and Link4 **cannot be preset from a .miz** — they are cockpit-state (the RIO types 336.0 into the Tomcat; the Hornet pilot boxes ICLS). No mission file can do it. The achievable alignment is: (a) cockpit **radio presets** that match the comm plan, and (b) a kneeboard **Boat Card** that puts every remaining knob value in one place.

## 3. Functional requirements

**FR-1 — Hull capability gating (ship side).**
Each hull declares which systems it actually supports; the generator activates exactly that set, and the comm card lists exactly that set.

| Hull | TACAN | ICLS | Link4 | ACLS | Rationale |
|---|---|---|---|---|---|
| CVN-71/72/73/75, Stennis | ● | ● | ● | ● | SuperCarrier / full support |
| Forrestal (1980s) | ● | ● | ● | — | Heatblur boat: no ACLS in DCS |
| Invincible (1982) | ● | — | — | — | No precision landing systems in DCS; Harriers recover visually |
| Essex (1944) | — | — | — | — | Era-true: nothing to radiate; briefing notes visual recovery |

Data lives in `carrier_decks.json` per hull (`"systems": ["tacan","icls","link4","acls"]`), so future hulls (Kuznetsov, Tarawa) are one data entry.

**FR-2 — Player/client radio presets aligned to the comm plan (aircraft side).**
Every player and client (multi-slot) aircraft whose module supports presets gets its radios programmed from the mission's actual comm plan at generation time:

| Channel | Assignment | Note |
|---|---|---|
| 1 | Flight (intra-flight) | DCS enforces this anyway — plan WITH the engine, not against it |
| 2 | Mother (carrier) — carrier missions only | Marshal/tower freq |
| 3 | AWACS / AEW | whichever the mission actually has |
| 4 | Tanker | if present |
| 5 | Angel (plane guard) | carrier flight-ops missions only |
| 6 | CAP common | if present |
| last channel | Guard 243.000 | always |

Rules: only frequencies for assets that **exist in this mission** are programmed; unused channels keep module defaults; both COMM1 and COMM2 get the map where the module has two presettable radios; airframes without `panel_radio` (none of our current flyables) are skipped silently. Applies to carrier AND land starts — the alignment principle isn't carrier-specific.

**FR-3 — Kneeboard "Boat Card" + channel column.**
The comm ladder gains a **CHAN** column ("Mother — CH 2 — 264.425") so the kneeboard and the cockpit speak the same language. Carrier missions get a Boat Card block: TACAN 71X STN · ICLS CH 11 · Link4 336.0 (F-14: RIO enters this) · ACLS (where supported) · BRC · expected CASE. The briefing's YOUR FLIGHT line gains one sentence: "Presets are loaded — Mother is CH 2."

**FR-4 — Verification.**
Automated .miz assertions per release: (a) each hull's activation task list == its declared systems, (b) player unit's radio dict contains the planned channels, (c) channel values sit on the 25 kHz raster, (d) kneeboard/comm card lists match what was programmed. In-game validation by Rob: Hornet spawns on deck, COMM1 CH 2 talks to Mother without touching the UFC.

## 4. Non-functional requirements

- **Zero new UI.** This is default-on correctness, not a feature toggle. No recipe field changes required; share links unaffected. (If a toggle is ever wanted, it belongs under Support, default on.)
- **Graceful degradation.** Unknown module preset shapes → skip that radio, never fail generation.
- **Era integrity.** WWII missions gain nothing anachronistic (no TACAN on Essex; WWII radios keep module defaults).
- **MP-safe.** Presets are per-unit in the .miz — every client slot gets them, nothing server-side.

## 5. Evaluation

**Feasibility: HIGH.** Everything needed is verified present in vendored pydcs today (`set_radio_channel_preset`, `panel_radio` on all our flyables, per-hull activation already working). No new dependencies, no scripting, no DCS-side install.

**Risks (all low):**
1. *Engine clobber of CH 1* — designed around: CH 1 is the flight freq by plan.
2. *Module preset-dict variance* (channel counts differ: Hornet 20, Tomcat 20+, Harrier differs) — generic code writes only channels that exist in the template; "last channel = Guard" adapts per module.
3. *Cockpit-state systems not presettable* (TACAN/ICLS/Link4 aircraft-side) — a DCS engine limit, not ours; mitigated by FR-3's Boat Card. Must be stated in the guide so users don't file it as a bug.
4. *Comm plan drift* — presets are derived from the same `comms_plan.json` the kneeboard reads, so they cannot disagree by construction.

**Effort: one PATCH-to-MINOR release (~half a build session).**
- Phase A — FR-1 hull gating + data (small)
- Phase B — FR-2 preset engine + FR-3 kneeboard/briefing (medium)
- Phase C — FR-4 verification + guide note (small)
Recommend shipping as **v1.9.0** (MINOR: new capability, backward compatible).

**Out of scope (explicitly):** aircraft-side TACAN/ICLS/Link4 preset (impossible from .miz); land-base ATC tower presets (DCS assigns tower freqs from terrain data — separate feature); Kuznetsov/Tarawa hulls (add via FR-1 data when we add the hulls).

## 6. Recommendation

Build all three phases as one release. Phase B is the visible win (the "wow, my radios are already set" moment); Phase A is a correctness debt we should not leave (the comm card currently advertises ACLS on boats that don't have it); Phase C is the ritual. The channel plan above mirrors common wing SOPs (flight on 1, Mother on 2, gas on 4, Guard last), so it will feel familiar to squadron pilots rather than invented.
