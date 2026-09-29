#!/usr/bin/env bash
# Prove Authentic Style v2.1 by breaking it.
#
# WHAT IS BEING PROTECTED. Every generated document — the mission brief, the
# kneeboard, the track guides, the user guide, the squadron kit, the HTML
# documentation pages — draws the specimen: the v2.1 palette from the token
# file, the six faces embedded (with a real bold for prose), the navy band
# with identity and locator, the non-affiliation footer. Each mutation is a
# way one document could quietly drift back to Helvetica and cream paper.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  missiongen/authentic.py
  missiongen/brief.py
  missiongen/kneeboard.py
  missiongen/aar_guide.py
  missiongen/course_kit.py
  missiongen/data/brand/flightline.json
  scripts/build_guide_pdf.py
)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

baseline() {
  find missiongen tests scripts -type f \( -name '*.py' -o -name '*.json' \) ! -path '*/__pycache__/*' -print0 \
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
       tests/test_authentic.py -q -x -k "$k" > /tmp/mut_authentic.log 2>&1; then
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

baseline_green tests/test_authentic.py

echo "== the tokens =="

mut missiongen/data/brand/flightline.json '"navy": "#00205B",' '"navy": "#17324D",'
run "put the old Flightline navy back" "palette_is_the_specimen"

mut missiongen/data/brand/flightline.json '"paper": "#FFFFFF",' '"paper": "#F4F0E6",'
run "put the cream paper back" "palette_is_the_specimen or white_paper"

echo "== the faces =="

mut missiongen/authentic.py '    "SourceSerif4": "SourceSerif4-Regular.ttf",' '    "SourceSerif4": "NoSuchFile.ttf",'
run "let the serif fall back to Times" "registers_without_falling_back"

mut missiongen/authentic.py '    "SourceSerif4-Bold": "SourceSerif4-Bold.ttf",' '    "SourceSerif4-Bold": "SourceSerif4-Regular.ttf",'
run "ship the regular face under the bold name" "real_bold"

mut missiongen/authentic.py '        "title": ParagraphStyle("title", fontName=f["banner"], fontSize=27, leading=30,' '        "title": ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=27, leading=30,'
run "set the banner title in Helvetica" "six_faces"

mut missiongen/course_kit.py '            ("FONT", (0, 1), (-1, -1), _auth.register_fonts()["sans"], 8),' '            ("FONT", (0, 1), (-1, -1), "Helvetica", 8),'
run "set the kit tables in Helvetica" "six_faces"

mut scripts/build_guide_pdf.py 'NAVY = HexColor(_H["navy"])' 'NAVY = HexColor("#17324D")'
run "put the old navy back in the user guide" "user_guide_builder"

echo "== the PIL documents =="

mut missiongen/kneeboard.py '    _auth.pil_band(d, W, rail_text(""), f"SORTIE STARTER / {title}",\n                   f["tiny"], band_h=44, pad=28)' '    pass'
run "drop the band from the kneeboard" "kneeboard_draws"

mut missiongen/brief.py '    _auth.pil_band(d, W, rail_text(""), f"SORTIE STARTER / {title}",\n                   f["mono_s"], band_h=56, pad=60)' '    pass'
run "drop the band from the brief" "brief_pdf_pages"

mut missiongen/brief.py '        "banner": _brand_font("banner", 66),' '        "banner": _brand_font("sans_bold", 66),'
run "set the brief banner in Source Sans" "banner_and_section_faces"

mut missiongen/kneeboard.py '        "h2": _bfont("display", 30),           # SECTION: Barlow Condensed ExtraBold' '        "h2": _bfont("sans_bold", 30),         # SECTION: Barlow Condensed ExtraBold'
run "set kneeboard section heads in Source Sans" "banner_and_section_faces"

echo "== the furniture =="

mut missiongen/authentic.py '            c.drawRightString(W - rm, 9.5 * mm, tail)' '            pass'
run "drop the non-affiliation footer" "identity_locator"

mut missiongen/authentic.py '                if stringWidth(text, font, size) <= room:\n                    return text' '                if True:\n                    return text'
run "draw a long identity over the locator" "identity_locator"

mut missiongen/authentic.py '    "INFO": ("panel", "accent"), "PASS": ("#E6F4EA", "ok"),' '    "INFO": ("panel", "accent"), "OK": ("#E6F4EA", "ok"),'
run "rename the PASS pill" "four_states"

echo "== the HTML pages =="


echo
echo "caught $PASS / $((PASS+WEAK))  (weak: $WEAK)"
[ "$WEAK" -eq 0 ]
