# Iraq parking capture and Phantom static skins

The supplied `dcs.log` reports `PSURVEY_DONE|count=1397`. All 1,397 unique
stand records across 20 airfields passed the importer's identity and geometry
checks against the current Iraq export. No existing map measurements were
removed. The Channel and Falklands remain unmeasured.

The companion `debrief.log` identifies `survey_iraq.miz` and contains 1,398
aircraft: 1,397 parked survey aircraft and the airborne observer. Matching
native mission unit IDs to debrief records confirms all surveyed aircraft.
Maximum circular heading difference from the timed survey export is
0.087264 degrees; the orientation-vector export remains authoritative.

| Supplied input | SHA-256 |
|---|---|
| dcs.log | `bb3f5d4296f72be627a0130b087040381d6a6b15dcc3b8e022a5905ca48a6ebe` |
| debrief.log | `4581909c3d92135b7bdf60dbbb79b5678426c38c9ee7ad795c3abf9d7bac99fe` |
| survey_iraq.miz | `6a0d146351552089cf2e3d4159ea838457dc5a69c9002d37b77dce84f29e1891` |

The static Phantom issue comes from leaving `livery_id` unset: the broader
authored skin pack is unverified, so DCS chooses from installed default skins.
The application now passes the selected era to static skin selection and uses
a bounded, source-backed exact-model catalog before that older pack.

- Stock `F-4E`, Cold War, USA: built-in `af standard`, documented in
  [DCS updater output](https://forum.dcs.world/topic/273353-installer-freezing/).
  This overrides the local Marine/campaign default without adding a dependency.
- Heatblur `F-4E-45MC`, Cold War, USA: `421st_TFS_SEA_68-336`, whose mounted
  texture folder appears in the supplied log at 10:06:34.942 UTC.
- No alias between these models: their textures are incompatible. No automatic
  skin is authored for other nations or periods without supporting evidence.
- Clean style and explicit user skin choices keep their existing semantics.
  Installed packs may additionally supply `static.<era>.<country>` preferences;
  missing era coverage cannot fall through to another period's skin.

This is broad era eligibility, not proof of an exact squadron at a specific
base/year. The stock skin's rendered appearance needs a DCS visual check; the
server can validate emitted IDs and source evidence but cannot render DCS.

Validation: 768 focused tests passed for native static skins, imported heading
identity and geometry, Iraq archive directions, alignment, squadron caps,
player stores and communications. Source/derived-document checks also pass.
The final full suite passed **4,359 tests, 57 skips, 9 deprecation warnings** in
163.78 seconds on four workers. The single-skin override preserves RNG state:
adding paint must not change seeded Germany corridors or subsequent placement.
All registered derived artifacts are current.

Visual-check missions are in `outputs/parking-direction-surveys/verification/`:
`iraq-parking-check.miz` has 56 exact-heading Al-Asad statics, and
`f4-static-skin-check.miz` has 28 USA stock Phantoms across friendly Germany
fields, including four at Spangdahlem, with explicit `af standard` paint.
These were development validation artifacts for `codex/refactor-2.0` before
the owner requested deployment. The imported data, skin fixes and compatible
refactor slice are included in the 1.108.1 release. Deployment evidence is
saved in `outputs/releases/1.108.1/production/` outside the versioned tree.
