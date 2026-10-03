#!/usr/bin/env bash
# Mutation harness for formation departures (missiongen/lineup.py,
# pattern.py sections, the recipe gate, the API flag, the page). Each
# mutation weakens one guard; tests/test_lineup.py must go RED for every one.
#   bash scripts/mutate_lineup.sh
set -u
cd "$(dirname "$0")/.."
T=tests/test_lineup.py
run(){ python3 -m pytest -q -x "$T" >/tmp/mut_lu.log 2>&1; local rc=$?; [ $rc -eq 5 ] && rc=99; return $rc; }
caught=0; missed=0
mut(){ local name="$1" f="$2" expr="$3"
  cp "$f" "$f.orig"; sed -i -E "$expr" "$f"
  if cmp -s "$f" "$f.orig"; then echo "  ?? $name — sed changed nothing"; missed=$((missed+1)); mv "$f.orig" "$f"; return; fi
  if run; then echo "  MISSED  $name"; missed=$((missed+1)); else echo "  caught  $name"; caught=$((caught+1)); fi
  mv "$f.orig" "$f"; }
LU=missiongen/lineup.py; PT=missiongen/pattern.py; RC=missiongen/recipe.py; BD=missiongen/builder.py; AP=server/app.py; FE=frontend/index.html
echo "lineup.py:"
mut "apply writes when unsupported"      $LU 's/^    if not supported\(\):\n        return False//; /^def apply/,/^def carries/ s/    if not supported\(\):/    if False:/'
mut "task() hands out a placeholder"     $LU '/^def task/,/^def apply/ s/        raise RuntimeError\(NOT_SUPPORTED\)/        pass/'
mut "action lands on the wrong waypoint" $LU 's/^WAYPOINT = 0 /WAYPOINT = 1 /'
mut "register() never teaches pydcs"     $LU '/^def register/,/^def task/ s/    if not supported\(\):/    if True:/'
echo "pattern.py:"
mut "sections ignore the knob"           $PT 's/    if not lineup:\n        return \[\(leg, 1\) for leg in legs\]//; /^def _sections/,/^def _add_landing/ s/    if not lineup:/    if True:/'
mut "a section is one aircraft"          $PT 's/^SECTION = _lineup.SECTION/SECTION = 1/'
mut "landings get sections too"          $PT '/^def _sections/,/^def _add_landing/ s/        if leg == "landing":/        if False:/'
mut "a section departs without the action" $PT 's/    if size > 1 and not _lineup.apply\(fg\):/    if False:/'
mut "lineup forced on"                   $PT 's/    lineup = bool\(lineup\) and _lineup.supported\(\)/    lineup = _lineup.supported()/'
mut "brief forgets the line-up"          $PT 's/    if pat.get\("lineup"\):/    if False:/'
echo "recipe / builder / api / page:"
mut "recipe accepts the knob unverified" $RC 's/            if not _lineup.supported\(\):/            if False:/'
mut "builder drops the knob"             $BD 's/_lineup_on = bool\(getattr\(r, "pattern_lineup", False\)\)/_lineup_on = False/'
mut "stats count groups not aircraft"    $BD 's/"lineup": _lineup_on, "aircraft": _ac or len\(names\)\}/"lineup": _lineup_on, "aircraft": len(names)}/'
mut "api always says supported"          $AP 's/"lineup_supported": _lineup_mod.supported\(\),/"lineup_supported": True,/'
mut "page shows the knob unconditionally" $FE 's/id="pattern_lineup_wrap" style="display:none"/id="pattern_lineup_wrap"/'
mut "page never sends the knob"          $FE 's/    r.pattern_lineup = !!\(OPT \&\& OPT.lineup_supported\) \&\& r.pattern_mode !== .landing./    r.pattern_lineup = false \&\& r.pattern_mode !== "landing"/'
mut "page forgets the knob on restore"   $FE 's/plu.checked = !!r.pattern_lineup;/plu.checked = false;/'
echo; echo "caught $caught  missed $missed"; [ $missed -eq 0 ]
