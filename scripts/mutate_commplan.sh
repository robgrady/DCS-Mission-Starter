#!/usr/bin/env bash
# Mutation harness for the comm table (missiongen/commplan.py, comms.py,
# presets.py). Each mutation weakens one rule; the suite must go RED for
# every one. A mutation the suite survives is a rule with no proof.
#   bash scripts/mutate_commplan.sh
set -u
cd "$(dirname "$0")/.."
T=tests/test_commplan.py
run(){ python3 -m pytest -q -x "$T" "${@}" >/tmp/mut_cp.log 2>&1; local rc=$?; [ $rc -eq 5 ] && rc=99; return $rc; }
caught=0; missed=0
mut(){ # name file sed-expr
  local name="$1" f="$2" expr="$3"
  cp "$f" "$f.orig"
  sed -i -E "$expr" "$f"
  if cmp -s "$f" "$f.orig"; then echo "  ?? $name — sed changed nothing"; missed=$((missed+1)); mv "$f.orig" "$f"; return; fi
  if run; then echo "  MISSED  $name"; missed=$((missed+1)); else echo "  caught  $name"; caught=$((caught+1)); fi
  mv "$f.orig" "$f"
}
CP=missiongen/commplan.py; CM=missiongen/comms.py; PR=missiongen/presets.py; RC=missiongen/recipe.py; AP=server/app.py
echo "commplan mutations:"
mut "guard becomes editable"           $CP 's/^LOCKED = \{"guard"\}/LOCKED = set()/'
mut "raster check dropped"             $CP 's/if abs\(s - v\) > 1e-6:/if False:/'
mut "band check dropped"               $CP 's/if not \(in_uhf or in_own\):/if False:/'
mut "airframe band ignored"            $CP 's/in_own = any\(.*\)$/in_own = False/'
mut "unknown row accepted"             $CP 's/if key not in KEYS:/if False:/'
mut "guard collision allowed"          $CP 's/if abs\(s - guard\) < 1e-6:/if False:/'
mut "defaults kept as overrides"       $CP 's/if abs\(s - default_mhz\(key\)\) < 1e-6:/if False:/'
mut "co-channel warning dropped"       $CP 's/warnings.append\(\{"key": k,/pass; (\{"key": k,/'
mut "bool accepted as MHz"             $CP 's/if isinstance\(raw, bool\) or not math.isfinite\(v\):/if not math.isfinite(v):/'
mut "AEW never takes CH3"              $CP 's/if key == "aew" and not has_awacs:/if False:/'
mut "absent rows called generated"     $CP 's/elif not exists:/elif False:/'
mut "held ignores the airframe"        $CP 's/"held": holds\(radios, ch\) if exists else False,/"held": True,/'
mut "clean not returned to recipe"     $RC 's/self.comms = v\["clean"\] or None/self.comms = self.comms/'
mut "recipe ignores errors"            $RC 's/if v\["errors"\]:/if False:/'
echo "comms.py mutations:"
mut "override ignored by freq()"       $CM 's/if key in self.overrides:/if False:/'
mut "cfg() reads the plan not freq()"  $CM 's/d\["freq"\] = self.freq\(key\)/d["freq"] = snap(d["freq"])/'
mut "guard override honored"           $CM 's/if k != "guard" and v is not None/if v is not None/'
mut "custom note dropped"              $CM 's/if self.is_custom\(agency\):/if False:/'
mut "card header never says custom"    $CM 's/\("custom ladder" if self.overrides else "standard ladder"\)/"standard ladder"/'
mut "builder passes no overrides"      missiongen/builder.py 's/comms = CommsPlan\(r.comms\)/comms = CommsPlan()/'
mut "stats drop comms_custom"          missiongen/builder.py 's/stats\["comms_custom"\] = _cp.describe\(comms.overrides\)/pass/'
echo "presets.py mutations:"
mut "only the first UHF radio"         $PR 's/for uhf in _uhf_radio_ids\(radio\):/for uhf in _uhf_radio_ids(radio)[:1]:/'
mut "channel names not written"        $PR 's/names\[ch\] = agency/pass/'
mut "guard name not written"           $PR 's/names\[last\] = "Guard"/pass/'
echo "api mutations:"
mut "validate endpoint ignores aircraft" $AP 's/return _cp.validate\(req.comms, _cp.unit_type_for\(req.aircraft\)\)/return _cp.validate(req.comms, None)/'
mut "table endpoint ignores flags"     $AP 's/return \{"rows": _cp.rows\(ut, present\)/return {"rows": _cp.rows(ut, None)/'
echo; echo "caught $caught  missed $missed"
[ $missed -eq 0 ]
