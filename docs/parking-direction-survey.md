# Capture exact parked-aircraft directions

Surveyed static aircraft now use their recorded heading without the old ±3°
random offset. Unsurveyed stands retain the geometric/field-default fallback.
The RNG draw is retained to keep the seeded sequence aligned. Ground equipment keeps
its independent parking variation and clearance decisions.

New surveys identify stands by airport + crossroad id, keep the display name
and source-export coordinates, and record direction in degrees true. This
separates stands with duplicate names and detects geometry drift on updates.
Existing name-keyed measurements remain supported.

## Missing-map survey packet

Prepared .miz files cover every declared airplane or helicopter stand on:

| Mission | Airfields | Survey aircraft |
|---|---:|---:|
| survey_thechannel.miz | 12 | 572 |
| survey_falklands.miz | 26 | 277 |
| survey_iraq.miz | 20 | 1,397 |

The survey observer is an airborne Su-25T, so it does not consume a stand.
Airplane stands use a compact MiG-15bis; helicopter-only stands use a UH-1H.
Generated archives contain all 2,246 survey units with unique names. This is a
construction check; only DCS can supply their actual spawned directions.

1. Open one survey mission in DCS on a machine with that terrain installed.
2. Start the mission, wait about 20 seconds for "Parking survey done", then exit.
3. Copy `Saved Games/DCS/Logs/dcs.log` (or the corresponding DCS profile folder)
   before running another mission. The log is the default output; no changes to
   MissionScripting.lua are needed. A separate parking_survey.txt is optional
   when the existing installation permits file output.
4. From the updated application checkout, validate and import that map:

   ```sh
   python3 scripts/import_survey.py thechannel path/to/dcs.log --dry-run
   python3 scripts/import_survey.py thechannel path/to/dcs.log
   ```

   Use `falklands` or `iraq` for the other files. The importer rejects unknown
   maps, fields, stands, stale coordinates, and non-finite measurements. It
   merges partial surveys with existing measurements and publishes the JSON
   through a temporary file/rename. Existing measurements are retained.

The all-map missions can be heavy, especially Iraq. If performance prevents a
complete capture, build and run smaller batches using airfield names:

```sh
python3 scripts/build_survey_mission.py iraq "Al-Kut Airport" "Kharg Airfield"
```

Merge each batch into the same map key. Rebuild the survey after changing its
terrain export; do not reuse a log against different stand coordinates.

The three maps still have **zero verified per-stand headings** until their DCS
logs are imported. The packet does not invent headings or mark these maps as
surveyed. Extend the same process to unsurveyed fields on the other ten maps.
