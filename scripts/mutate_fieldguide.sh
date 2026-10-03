#!/usr/bin/env bash
# Mutation harness for the airfield guide (missiongen/fieldguide.py, the
# brief page, the markdown, the kneeboard page) and the field-elevation fix
# in pattern.py. Each mutation weakens one guard; tests/test_fieldguide.py
# must go RED for every one.
#   bash scripts/mutate_fieldguide.sh
set -u
cd "$(dirname "$0")/.."
T=tests/test_fieldguide.py
run(){ python3 -m pytest -q -x "$T" >/tmp/mut_fg.log 2>&1; local rc=$?; [ $rc -eq 5 ] && rc=99; return $rc; }
caught=0; missed=0
mut(){ local name="$1" f="$2" expr="$3"
  cp "$f" "$f.orig"; sed -i -E "$expr" "$f"
  if cmp -s "$f" "$f.orig"; then echo "  ?? $name — sed changed nothing"; missed=$((missed+1)); mv "$f.orig" "$f"; return; fi
  if run; then echo "  MISSED  $name"; missed=$((missed+1)); else echo "  caught  $name"; caught=$((caught+1)); fi
  mv "$f.orig" "$f"; }
FG=missiongen/fieldguide.py; PT=missiongen/pattern.py; BR=missiongen/brief.py; DJ=missiongen/data/airfield_elevations.json
echo "fieldguide.py:"
mut "ATC read from the wrong band"        $FG 's/"uhf": _mhz\(r.uhf_hz\), "vhf": _mhz\(r.vhf_high_hz\)/"uhf": _mhz(r.vhf_high_hz), "vhf": _mhz(r.uhf_hz)/'
mut "runway opposite end dropped"         $FG 's/\(rw.opposite.name, int\(rw.opposite.heading\)\)/(rw.main.name, int(rw.main.heading))/'
mut "elevation back to the stand height"  $FG 's/^    t = _elev_table\(\)$/    return int(round(float(airport.parking_slots[0].height) * FT))/'
mut "elevation table ignores the map"     $FG 's/        v = \(\(t.get\(mk\) or \{\}\).get\("fields"\) or \{\}\).get\(getattr\(airport, "name", ""\)\)/        v = 1868/'
mut "divert order not by range"           $FG 's/    own.sort\(key=lambda r: \(not r\["home"\], r\["range_nm"\]\)\)/    pass/'
mut "home not first"                      $FG 's/    own.sort\(key=lambda r: \(not r\["home"\], r\["range_nm"\]\)\)/    own.sort(key=lambda r: r["range_nm"])/'
mut "first_only ignored"                  $FG 's/    for rw in \(r\["runways"\]\[:1\] if first_only else r\["runways"\]\):/    for rw in r["runways"]:/'
mut "NORDO forgets the runway"            $FG 's/overhead for RWY \{rw\}, rock wings on initial./rock wings on initial./'
echo "pattern.py:"
mut "landers spawn without an elevation"  $PT 's/    if elev is None and mode != "takeoff":/    if False:/'
mut "warning dropped"                     $PT 's/                f"no field elevation on record for \{airport.name\} - pattern "/                f"pattern "/'
mut "elevation from the stand again"      $PT 's/    return elevation_m\(airport, map_key\)/    return float(airport.parking_slots[0].height)/'
echo "brief.py / data:"
mut "guide page dropped from the brief"   $BR 's/        page_airfield_guide\(ctx\),//'
mut "markdown table dropped"              $BR 's/    L \+= \["", "## Airfield guide", "",/    L += ["", "## Airfield guide (table omitted)", "",/; s/^    for r in table\["own"\]:$/    for r in []:/'
mut "a Nevada field missing from the table" $DJ 's/"Creech": 3133, //'
echo; echo "caught $caught  missed $missed"; [ $missed -eq 0 ]
