# Library correction evidence — 1.108.0

3 October 2026. Corrective follow-up to the frozen
[original audit](library-validation-2026-10-02.md). All 17 affected entries in
C1–C6 and the cross-entry preset issue C7 have corrective changes. Historical
findings in the original audit are not closed by these behavioral checks.

| Finding | Corrective behavior | Emitted evidence |
|---|---|---|
| C1: seven role/store mismatches | Explicit SEAD/strike/CAS roles; precision bombs plus designator; unguided F-100 attack stores | Actual player payload CLSIDs, not template flags |
| C2: TIC, convoy, Fulda | Friendly patrol plus hostile group and native FAC task; moving friendly trucks with zone-triggered ambush; moving armor column | FAC group ID/frequency; multi-point OnRoad routes; late activation and group-in-zone trigger/actions |
| C3: TI-1, WK-9/10, Sabre Dance | Clean weapon-hold radar target; WK-10 player and AI wingman plus separate target; guns-only BFM adversary | Target routes/tasks/stores and actual flight unit counts |
| C4: Alpha Strike Escort | Bomb-armed A-6s attack a generated depot, then recover at their carrier | Bomb CLSIDs, AttackGroup target ID, landing route linked to ship unit |
| C5: CQ, TARPS | Empty CQ pylons; verified F-14BU TARPS pod and manual imagery instructions | Empty payload or exact `{F14-TARPS}` on exported pylon 6 |
| C6: LASDT, WK-11, SAT-2 | Clearly labeled self-directed/instructor-led syllabi; SAT-2 unguided bombs, two clients, human instructor simulates wounded bird | Pre-generation premise and embedded mission disclosure, appropriate stores; no invented coaching/grading claims |
| C7: preset selection | Base + era + map merging, complete fresh card defaults, intentional edits preserved, lineup-specific home options | API/Node preset parity; actual browser form submissions after stale kind/slots/lineup settings, including Sinai/Beni Suef |

## Verification before release generation

- Full source-generated Library matrix: **334 successful builds, zero failures**,
  all 111 entries and 167 advertised era/map variants, seeds 7 and 19. The
  audit uses unmodified published flags, including documents and dressing.
- **44 affected variant/seed archives** pass the same behavioral contracts as
  the regression suite. Fixtures inspect native PyDCS-generated mission Lua.
- **23 real Chromium form submissions** across affected advertised presets
  and a separate Sinai WK-10 case pass after unrelated stale Builder settings.
  Complete metadata tests also cover the API and Quick Flight preset contract.
- **17 actual Library Generate downloads** completed through the real drawer
  button and passed emitted actor/store/task contracts.
- Added a dropdown regression: Sinai's Proud Phantom lineup exposes Cairo West
  and Beni Suef rather than silently restoring a field outside the options.

Reproducible evidence collector:

```sh
PYTHONPATH=.:vendor python scripts/audit_library.py outputs/library-validation-1.108.0 --workers 4
PYTHONPATH=.:vendor pytest tests/test_library_contracts.py
```

`outputs/library-validation-1.108.0/mission-evidence.json` and
`case-summary.csv` contain full emitted facts. The browser probe evidence is
stored beside them. Outputs are local evidence, not versioned source.
The complete release gate also runs the full test suite, regenerates all
published packs/screenshots/docs and checks artifact freshness.

## Limits

OnRoad movement, native JTAC behavior, A-6 attack/recovery and TARPS recording
still require DCS flight checks. Road geometry is a notional local exercise,
not a surveyed historical operation. C6 is resolved by truthful capability
labels, not by implementing staged coaching or damage simulation. The three
exercises require manual execution or a human instructor as described.

TARPS encoding comes from pinned exported DCS aircraft data, with Heatblur's
manual cited in [Sources](SOURCES.md). Historical zone validity, precise dated
operators and weapon service by actual mission year remain separate roadmap
work. No measured airport stand coordinates/headings or vendor PyDCS files
were changed by these fixes.
