# Requirements — Carrier Identity (callsign, TACAN ident, hull-matched channel)
**Feature:** "The boat answers to her real name."
**Author:** Claude (naval research + design/dev perspective) · For: Rob Grady · 2026-07-16 · Status: DRAFT for approval

---

## 1. Problem statement

Every carrier we spawn currently answers to the same generic identity: callsign "Mother", TACAN 71X ident "STN" — regardless of hull. A George Washington (CVN-73) mission broadcasts the Stennis' channel and a placeholder name. Each boat should carry her own verified voice callsign, her own 3-letter TACAN ident, and a TACAN channel that matches her hull number — the convention carrier pilots actually use to keep boats deconflicted.

## 2. Research findings (verified vs convention — flagged honestly)

**Voice callsigns — VERIFIED (official, per ACP 113(AI), corroborated on the ED forums):**

| Hull | Ship | Voice callsign |
|---|---|---|
| CVN-71 | Theodore Roosevelt | **Rough Rider** |
| CVN-72 | Abraham Lincoln | **Union** |
| CVN-73 | George Washington | **Warfighter** |
| CVN-74 | John C. Stennis | **Courage** |
| CVN-75 | Harry S. Truman | **Lone Warrior** |

(Trivia worth a kneeboard footnote: TR's CO traded the ship's originally assigned callsign with USS Los Angeles to get "Rough Rider.")

**Not reliably documented — proposed fallbacks:**
- **CV-59 Forrestal:** no verifiable voice callsign found. Her documented fleet nickname is **"FID"** (*First In Defense*, bestowed by Adm. Zumwalt). Proposal: voice callsign "Fid", TACAN ident FID. Marked as convention, not record.
- **CV-9 Essex (1944):** WWII voice calls rotated per operation for security; also no TACAN existed. She keeps generic "Mother" on the radio row and (per v1.9.0) radiates nothing — era-true.
- **R05 Invincible (1982):** RN procedures differ; no public voice callsign. Keep "Mother" with ident INV.

**TACAN idents — 3-letter Morse idents are conventions, not published records. Proposed set** (ship initials/nicknames, the pattern DCS squadrons use):

| Hull | Channel (= hull number) | Ident | Basis |
|---|---|---|---|
| CVN-71 | **71X** | TDR | initials |
| CVN-72 | **72X** | ABE | ship's famous nickname |
| CVN-73 | **73X** | GWN | initials |
| CVN-74 | **74X** | STN | initials (already our value) |
| CVN-75 | **75X** | HST | initials |
| CV-59 | **59X** | FID | documented nickname |
| R05 | **5X** | INV | pennant R05 → channel 5 |
| CV-9 | — | — | no TACAN in 1944 |

**Conflict audit:** all channels are valid (1–126) and on the X band; our tanker (39Y) and the fallback allocator (40Y+) live on the Y band — no collision. One boat per mission today, so no boat-vs-boat dedup needed, but the per-hull table makes multi-carrier futures collision-free by construction.

## 3. Functional requirements

**FR-1 — Per-hull identity data.** `carrier_decks.json` gains, per hull: `voice_callsign`, `tacan_channel` (int, = hull number), `tacan_ident` (3 letters), and an optional `callsign_verified` flag (true for the five ACP-documented boats). The global `comms_plan.json` carrier block becomes the fallback for anything a hull doesn't specify.

**FR-2 — The boat uses her identity everywhere.** `naval.add_carrier_group` activates TACAN on the hull's channel with the hull's ident; the comm card row reads e.g. `Carrier · Warfighter (Mother) · 264.425 · CH2 · 73X GWN`. "Mother" stays in parentheses — it's the brevity word pilots actually say, so we keep both the identity and the procedure. Marshal frequency stays global (one learnable ladder — unchanged design).

**FR-3 — Downstream consistency.** Kneeboard comms page, briefing Boat Card, YOUR FLIGHT line ("Warfighter is Mother on CH 2"), F10 map carrier label, and the guide's comm table all read from the same hull data. The guide's fixed "71X STN" text becomes "TACAN = hull number (73X on the GW)".

**FR-4 — Verification.** Per-hull .miz asserts: ActivateBeacon channel == hull number, ident == 3-letter code, comm card carries the voice callsign; Essex asserts no beacon; Invincible asserts 5X INV.

## 4. Non-functional requirements

- Zero UI change; no recipe field; share links unaffected.
- Player-side note (guide + Boat Card): your jet's TACAN must be dialed to the hull's channel — presets can't set cockpit TACAN (v1.9.0 engine limit), so the kneeboard value is what you dial.
- Unverified callsigns are marked as convention in the guide's carrier table — we don't present invention as record.

## 5. Plan & effort

1. **Data** — add the identity table to `carrier_decks.json` (10 min).
2. **Wiring** — `naval.add_carrier_group` + comms fallback logic (30 min).
3. **Downstream** — briefing/kneeboard/guide text (30 min).
4. **Verify + release** — FR-4 assertions, samples, guide rebuild, ship as **v1.9.1** (PATCH: data correction + wiring, no new capability surface) (30 min).

Total: about one focused session-hour. Risk: minimal — single call-site change; the only judgment calls are the unverified idents/callsigns, flagged above for your veto.

## 6. Open question for Rob

Forrestal's voice callsign: go with **"Fid"** (documented nickname, marked as convention), or keep generic **"Mother"** for her? Everything else uses verified data.
