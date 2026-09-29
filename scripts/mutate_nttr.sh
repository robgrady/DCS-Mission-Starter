#!/usr/bin/env bash
# Prove the corridors — NTTR, the Levant and the Central Region — by breaking them.
#
# WHAT IS BEING PROTECTED. corridors.py threads every routed flight plan on
# the Nevada and Syria maps through the published corridors: the sector picker, the low /
# high road, the crossing restrictions (FLEX <= 4,000, STRYK >= 9,500), the
# Alamo block, the west road round R-4808N, WP1 on the gate, unique waypoint
# names so the ETAs land on the right points, the brief, the F10 lanes and
# gates, the split kneeboard, and the fallbacks. Each mutation is a way one of
# those could quietly stop being true while the suite stayed green.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/corridors.py
  missiongen/corridor_chart.py
  missiongen/nttr.py
  missiongen/nttr_chart.py
  missiongen/builder.py
  missiongen/brief.py
  missiongen/kneeboard.py
  missiongen/routing.py
  missiongen/data/corridors/nevada.json
  missiongen/data/corridors/syria.json
  missiongen/data/corridors/germany.json
  missiongen/data/mission_templates.json
  missiongen/recipe.py
  server/app.py
)
SUITES=(tests/test_nttr.py tests/test_corridors_syria.py tests/test_corridors_germany.py)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

baseline() {
  find missiongen tests -type f \( -name '*.py' -o -name '*.json' \) ! -path '*/__pycache__/*' -print0 \
    | sort -z | xargs -0 md5sum
}
baseline > "$SNAP/baseline.txt"
purge_pyc() { find missiongen tests -name __pycache__ -type d -prune \
              -exec rm -rf {} + 2>/dev/null || true; }
restore() { purge_pyc; for f in "${FILES[@]}"; do cp "$SNAP/$f" "$f"; done; }
trap restore EXIT

PASS=0; WEAK=0

baseline_green() {
  if ! PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:vendor python3 -m pytest \
       "$@" -q > /tmp/mut_baseline.log 2>&1; then
    echo "  ABORT     the suite is RED before any mutation was applied."
    tail -15 /tmp/mut_baseline.log | sed 's/^/            /'
    exit 3
  fi
  echo "  baseline  green"
}

run() {
  local name="$1" k="$2"
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:vendor python3 -m pytest \
       "${SUITES[@]}" -q -x -k "$k" > /tmp/mut_nttr.log 2>&1; then
    echo "  WEAK      $name — suite still green"; WEAK=$((WEAK+1))
  else
    echo "  caught    $name"; PASS=$((PASS+1))
  fi
  restore
  local drift
  drift=$(baseline | diff - "$SNAP/baseline.txt" | grep '^<' || true)
  if [ -n "$drift" ]; then
    echo "  ABORT     restore missed a file — add it to FILES:"
    echo "$drift" | sed 's/^< [0-9a-f]*  /            /'
    exit 2
  fi
}

mut() {
  purge_pyc
  python3 - "$1" "$2" "$3" <<'PY' || { echo "  ANCHOR MISSING in $1"; exit 9; }
import io, sys
def unesc(x):
    return x.replace("\\n", "\n").replace("\\x27", "'")
p, o, n = sys.argv[1], unesc(sys.argv[2]), unesc(sys.argv[3])
s = io.open(p).read()
assert s.count(o) == 1, (p, s.count(o), o[:70])
io.open(p, "w").write(s.replace(o, n))
PY
}

baseline_green "${SUITES[@]}"

echo "== the data =="

mut missiongen/data/corridors/nevada.json '"cap_ft": 4000' '"cap_ft": 14000'
run "let a jet cross FLEX at 14,000" "crossing_restrictions or published_facts"

mut missiongen/data/corridors/nevada.json '"floor_ft": 9500' '"floor_ft": 5000'
run "cross STRYK at 5,000" "crossing_restrictions or published_facts"

mut missiongen/data/corridors/nevada.json '"STUDENT GAP"\n   ],\n   "block_ft": [\n    10000,\n    17000' '"STUDENT GAP"\n   ],\n   "block_ft": [\n    5000,\n    17000'
run "run the Sally Corridor below NATCF radar" "published_facts"

mut missiongen/data/corridors/nevada.json '"gate_in": "STUDENT GAP",\n     "gate_out": "STUDENT GAP",\n     "back": "mintt"' '"gate_in": "TEXAS LAKE",\n     "gate_out": "STUDENT GAP",\n     "back": "mintt"'
run "enter the north range at a gate the outbound corridor does not reach" "plan_names_known or north_range_plan"

mut missiongen/data/corridors/nevada.json '"INDIAN SPRINGS",\n    "MERCURY",\n    "AMARGOSA VALLEY"' '"INDIAN SPRINGS",\n    "AMARGOSA VALLEY"'
run "cut Mercury out of the west road" "far_west_road or flight_carries"

mut missiongen/data/corridors/nevada.json '"lat": 36.64,\n   "lon": -116.41' '"lat": 36.90,\n   "lon": -116.20'
run "put the Amargosa gate inside the Box" "far_west_road"

echo "== the router =="

mut missiongen/corridors.py '        if _nm_between(lat, lon, c["center"][0], c["center"][1]) <= float(c.get("local_nm", 22)):' '        if False:'
run "send a pattern ride up the Sally Corridor" "sector_picker or no_corridor_for"

mut missiongen/corridors.py '    return "high" if t_alt_m / FT >= 19000 else "low"' '    return "low"'
run "never take the Alamo Corridor" "low_and_high or high_road"

mut missiongen/corridors.py '    return "high" if t_alt_m / FT >= 19000 else "low"' '    return "high"'
run "put a Phantom on the Alamo block" "low_and_high or north_range_plan"

mut missiongen/corridors.py '        if f.get("cap_ft"):\n            alt_m = min(alt_m, f["cap_ft"] * FT)' '        if False:\n            alt_m = min(alt_m, f["cap_ft"] * FT)'
run "ignore the crossing caps" "crossing_restrictions"

mut missiongen/corridors.py '            if name in ("WP1", "EXIT"):\n                legs[-1]["name"] = name' '            if False:\n                legs[-1]["name"] = name'
run "leave the gate without the WP1 name the clock hangs on" "north_range_plan or east_plan or timing_card"

mut missiongen/corridors.py '        if name in taken:' '        if False:'
run "let MERCURY out and MERCURY back share a name" "timing_card_and_coach"

mut missiongen/corridors.py '    if not has(map_key) or home_pos is None or target_pos is None:' '    if home_pos is None or target_pos is None:'
run "thread the Caucasus through Nellis corridors" "no_corridor_for or other_maps or no_cluster_or_no_sector"

mut missiongen/corridors.py '    out_ids = [c for c in p["out"] if in_cluster or corridor(c, map_key)["role"] != "departure"]' '    out_ids = list(p["out"])'
run "fly the FLEX turnout out of Creech" "from_creech"

mut missiongen/corridors.py '                         (axis + 180 + side * 30) % 360)' '                         (axis + 180) % 360)'
run "run in on the direct radial from the gate" "ip_is_not"

echo "== the paperwork =="

mut missiongen/corridors.py '    ap = approx_fixes(plan)\n    if ap:\n        L += ["", "Curated positions' '    ap = []\n    if ap:\n        L += ["", "Curated positions'
run "hide which fixes are curated" "brief_names"

mut missiongen/builder.py '                if self._nttr:\n                    _nttr.draw(m, self._nttr, r.map)' '                if False:\n                    _nttr.draw(m, self._nttr, r.map)'
run "leave the lanes off the F10 map" "lanes_and_gates"

mut missiongen/corridors.py '        tag = "~" if fix(g, mk).get("approx") else ""' '        tag = ""'
run "draw a curated gate as surveyed" "lanes_and_gates"

mut missiongen/builder.py '        if stats.get("nttr"):\n            # THE CORRIDORS, in the text the pilot reads in the sim.' '        if False:\n            # THE CORRIDORS, in the text the pilot reads in the sim.'
run "leave the corridors out of the in-game brief" "stats_and_brief"

mut missiongen/builder.py '            _extra_issues += _nttr0.known_issue_lines(self._nttr)' '            pass'
run "leave the corridor caveat off the known-issues page" "stats_and_brief"

mut missiongen/brief.py '    if stats.get("nttr"):\n        n = stats["nttr"]' '    if False:\n        n = stats["nttr"]'
run "leave the corridors out of the PDF" "pdf_brief"

mut missiongen/kneeboard.py '        long_plan = len(route) > 7' '        long_plan = False'
run "cram thirteen legs and the clock on one page" "flight_plan_page_and_a_clock"

mut missiongen/builder.py '            legs = (self._nttr["legs"] if self._nttr else' '            legs = (None if self._nttr else'
run "plan the corridors and then not fly them" "flight_carries or stats_and_brief"

echo "== the chart =="

mut missiongen/data/corridors/nevada.json '"approx": true,\n    "poly": [\n     [\n      36.55,\n      -115.934' '"approx": false,\n    "poly": [\n     [\n      36.55,\n      -115.934'
run "pass a curated outline off as surveyed" "legal_polygons"

mut missiongen/corridor_chart.py '            _draw_lanes(cv, P, c, mk, HOT, HOT_FILL, fs, set())' '            _draw_lanes(cv, P, c, mk, GHOST, GHOST_FILL, fs, set())'
run "draw the flown road like every other" "renders_deterministically or plan_is_red"

mut missiongen/corridor_chart.py '        L.insert(0, f"RED = this mission' '        L.insert(1, f"RED = this mission'
run "bury the mission line in the legend" "renders_deterministically"

mut missiongen/corridor_chart.py '    def pil(self, ss=3) -> Image.Image:' '    def pil(self, ss=1) -> Image.Image:'
run "render the PNG aliased at 1x" "renders_deterministically or docs_chart"

mut missiongen/kneeboard.py '    if nttr_plan:\n        # THE CHART.' '    if False:\n        # THE CHART.'
run "leave the chart out of the kneeboard" "flight_plan_page_and_a_clock"

mut missiongen/brief.py '    if kb_ctx.get("nttr_plan"):\n        # The NTTR corridor chart' '    if False:\n        # The NTTR corridor chart'
run "leave the chart out of the PDF" "pdf_brief"

echo "== the Levant (v1.102.0) =="

mut missiongen/data/corridors/syria.json '"when": "lat >= 33.05 and lat <= 34.75 and lon >= 35.05 and lon <= 36.0"' '"when": "lat >= 33.05 and lat <= 34.75 and lon >= 35.05 and lon <= 36.35"'
run "file Damascus under Lebanon" "sector_picker_puts_syria"

mut missiongen/data/corridors/syria.json '"central": {\n    "low": {\n     "out": [\n      "il_coast",\n      "il_bekaa"\n     ],\n     "gate_in": "RAS BAALBEK"' '"central": {\n    "low": {\n     "out": [\n      "il_coast",\n      "il_bekaa"\n     ],\n     "gate_in": "HERMON"'
run "enter the Bekaa at a gate the coast road does not reach" "galilee_plan or every_corridor_point_gate"

mut missiongen/corridors.py '    for cid, c in d["clusters"].items():\n        if home_name in c.get("fields", []):\n            return cid, True' '    for cid, c in d["clusters"].items():\n        if False:\n            return cid, True'
run "forget which fields belong to which cluster" "home_field_picks or galilee_plan or akrotiri_incirlik"

mut missiongen/corridors.py '    p = ps.get(mode) or ps.get("low") or ps.get("any")' '    p = ps.get(mode)'
run "refuse the modern era a road the data only has as low" "modern_high_road or galilee_flight"

mut missiongen/corridors.py '    fmt = t.get("md_line", "**{summary}**' '    fmt = ("**{summary}**'
run "give the Levant Nevada's Bravo line" "maps_own_words or galilee_brief_f10"

mut missiongen/corridors.py '    L += ["", f"{t.get(\x27gate_in_label\x27, \x27ENTRY GATE\x27)} (WP1)' '    L += ["", f"ENTRY GATE (WP1)'
run "take Nevada's RANGE ENTRY away" "brief_names_the_corridors or nevada_keeps"

mut missiongen/corridors.py '    return labels.get(plan["sector"], plan["sector"])' '    return plan["sector"]'
run "call the sector by its key, not its name" "maps_own_words or nevada_keeps"

mut missiongen/corridor_chart.py '    cv.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill=SEA_FILL)' '    cv.polygon([(0, 0), (cv.w, 0), (cv.w, cv.h), (0, cv.h)], fill=SEA_FILL)'
run "paint the letterbox sea" "sea_is_painted"

mut missiongen/corridor_chart.py '        poly = _clip_poly([P(la, lo) for la, lo in land], P.w, P.h)\n        if len(poly) >= 3:\n            cv.polygon(poly, fill=PAPER)' '        pass'
run "drown the Levant" "sea_is_painted"

mut missiongen/corridor_chart.py '    cols = max(1, int(chart.get("panel_cols", 1)))' '    cols = 1'
run "stack four panels in one column" "page_is_sized"

mut missiongen/corridor_chart.py '    pg = _D(mk)["chart"].get("page") or [1600, 1000]' '    pg = [1600, 1000]'
run "render every map at Nevada's page size" "page_is_sized or site_serves_the_syria"

mut missiongen/corridor_chart.py '    boxes = [] if terminal else [pn["bounds"] for pn in D["chart"].get("panels", []) if pn.get("declutter")]' '    boxes = []'
run "draw every panel fix on the overview too" "decluttered"

mut missiongen/corridor_chart.py '        if not P.visible(pl["lat"], pl["lon"]) or (pl.get("minor") and not terminal):' '        if not P.visible(pl["lat"], pl["lon"]):'
run "put Tyre and Zahle on the overview" "decluttered"

mut missiongen/corridor_chart.py '        if ov.get("hide") and not hot:\n            continue' '        if False:\n            continue'
run "label L200 on the overview as well" "label_overrides"

mut missiongen/corridor_chart.py '        nx, ny = ov.get("nudge", [0, 0])' '        nx, ny = 0, 0'
run "ignore the nudges" "label_overrides"

mut missiongen/corridor_chart.py '        seg = min(ov.get("seg", c.get("label_seg", 0)), max(0, len(pts) - 2))' '        seg = min(c.get("label_seg", 0), max(0, len(pts) - 2))'
run "ignore the per-panel label segment" "label_overrides or renders_deterministically or site_serves_the_syria"

mut missiongen/builder.py '                        "md_line": _nttr.md_line(self._nttr),' '                        "md_line": "",'
run "leave the summary line out of the brief" "galilee_brief_f10 or galilee_flight"

mut missiongen/brief.py '        body = n["brief"][n["brief"].index("") + 1:]     # after the intro block' '        body = []'
run "leave the corridor list out of the PDF markdown" "galilee_brief_f10 or pdf_brief"

mut server/app.py '    if map_key not in CORRIDOR_CHARTS or not _cor.has(map_key):' '    if False:'
run "serve a corridor chart for a map that has none" "site_serves_the_syria"

echo "== the Central Region (v1.103.0) =="

mut missiongen/corridors.py '    if d.get("eras") and era not in d["eras"]:\n        return None' '    if False:\n        return None'
run "fly the Cold War structure in 2020" "belongs_to_the_cold_war or modern_germany"

mut missiongen/data/corridors/germany.json '    "when": "lat >= 52.15 and lat <= 53.2 and lon >= 12.2"' '    "when": "lat >= 52.15 and lat <= 53.2 and lon >= 11.0"'
run "file Stendal under Berlin" "both_germanies"

mut missiongen/data/corridors/germany.json '      "ef_out",\n      "werra"\n     ],\n     "gate_in": "HERLESHAUSEN",' '      "ef_out",\n      "werra"\n     ],\n     "gate_in": "HELMSTEDT",'
run "enter Berlin at a gate the Werra road does not reach" "out_chain_ends"

mut missiongen/corridor_chart.py '            if plan.get("cluster") in p.get("clusters", [p.get("cluster")]):' '            if plan.get("cluster") == p.get("cluster"):'
run "give the Hunsrück no panel" "eight_panels"

mut missiongen/corridor_chart.py '        if not a.get("label") or not P.visible(la, lo):' '        if not P.visible(la, lo):'
run "label ED-R 34C on its own" "sub_area_without"

mut missiongen/corridor_chart.py '            if labels and ln.get("label") and pts:' '            if ln.get("label") and pts:'
run "print the GDR line label on every panel" "hides_what_the_panels_draw"

mut missiongen/corridor_chart.py '                at = ln.get("label_at") or ln["pts"][len(ln["pts"]) // 2]' '                at = ln["pts"][len(ln["pts"]) // 2]'
run "ignore the line label anchor" "hides_what_the_panels_draw or docs_image_is_the_renderers"

mut missiongen/data/corridors/germany.json '"id": "be_out_w",\n   "name": "Berlin west - Nauen to Rathenow",\n   "role": "departure",\n   "points": [\n    "NAUEN",' '"id": "be_out_w",\n   "name": "Berlin west - Nauen to Rathenow",\n   "role": "departure",\n   "points": [\n    "BERLIN",\n    "NAUEN",'
run "send the Berlin ring over the Control Zone" "other_side_flies"

mut missiongen/builder.py '                                          home_name=home.name) if r.corridors else None' '                                          home_name=home.name)'
run "thread the timing rides through the corridors regardless" "switched_off"

mut missiongen/recipe.py '    corridors: bool = True' '    corridors: bool = False'
run "turn the corridors off by default" "switched_off or galilee_flight or phantom_from_spangdahlem"

echo
echo "caught $PASS / $((PASS+WEAK))  (weak: $WEAK)"
[ "$WEAK" -eq 0 ]
