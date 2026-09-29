#!/usr/bin/env bash
# Prove the Google Analytics guards by breaking them.
#
# TWO KINDS OF DEFECT LIVE HERE AND ONLY ONE OF THEM IS TECHNICAL.
#
# The technical one is ordinary: the tag does not load, or it loads twice, or a
# malformed environment variable puts broken JavaScript in the head.
#
# The other one is a PROMISE. This site's footer told every visitor "No IP
# address, no account, no name — nothing that says who you are", offered an
# off-switch, and honored Do Not Track. Google Analytics collects an IP, a
# user agent and device details, sets cookies, and reads neither the switch nor
# DNT. Ship the tag under the old wording and the privacy notice becomes a
# false statement — in the one place on the site where a false statement is
# least forgivable, and eight releases after we celebrated removing Google
# Fonts so the page would stop sending Google your IP.
#
# So half the mutations below are edits to prose, and they matter as much as
# the ones that break the script.
set -uo pipefail
cd "$(dirname "$0")/.."

SNAP=$(mktemp -d)
FILES=(
  server/ga.py
  server/app.py
  frontend/index.html
  fly.toml
)
for f in "${FILES[@]}"; do mkdir -p "$SNAP/$(dirname "$f")"; cp "$f" "$SNAP/$f"; done

baseline() {
  find server frontend tests -type f \( -name '*.py' -o -name '*.html' \) \
       ! -path '*/__pycache__/*' -print0 | sort -z | xargs -0 md5sum
  md5sum fly.toml
}
baseline > "$SNAP/baseline.txt"
purge_pyc() { find server missiongen tests -name __pycache__ -type d -prune \
              -exec rm -rf {} + 2>/dev/null || true; }
restore() { purge_pyc; for f in "${FILES[@]}"; do cp "$SNAP/$f" "$f"; done; }
trap restore EXIT

PASS=0; WEAK=0

# THE BASELINE MUST BE GREEN BEFORE ANY OF THIS MEANS ANYTHING. See
# scripts/mutate_case3.sh for the run this cost.
baseline_green() {
  if ! PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:vendor python3 -m pytest \
       "$@" -q > /tmp/mut_baseline.log 2>&1; then
    echo "  ABORT     the suite is RED before any mutation was applied."
    echo "            Every mutation below would report 'caught' and mean nothing."
    tail -15 /tmp/mut_baseline.log | sed 's/^/            /'
    exit 3
  fi
  echo "  baseline  green"
}

run() {
  local name="$1" k="$2"
  if PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:vendor python3 -m pytest \
       tests/test_ga.py -q -x -k "$k" > /tmp/mut_ga.log 2>&1; then
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

baseline_green tests/test_ga.py

echo "== it must ship off =="

# THE ONE THAT MATTERS MOST. An id in the page means every self-hosted copy of
# this app reports into our property, and their visitors are measured by a
# party they have never heard of.
mut frontend/index.html '<footer style="text-align:center' \
                        '<script async src="https://www.googletagmanager.com/gtag/js?id=G-B406V24KN5"></script>\n  <footer style="text-align:center'
run "hard-code the measurement id into the page" "hardcoded_in_the_page"

mut server/ga.py '    raw = (os.environ.get(ENV_VAR) or "").strip()' \
                 '    raw = (os.environ.get(ENV_VAR) or "G-B406V24KN5").strip()'
run "default the id when the environment does not set one" \
    "unconfigured_deployment"

mut server/ga.py 'ID_RE = re.compile(r"^G-[A-Z0-9]{4,20}$")' \
                 'ID_RE = re.compile(r".*")'
run "accept any string as a measurement id" "malformed_id_is_refused"

mut server/ga.py 'ID_RE = re.compile(r"^G-[A-Z0-9]{4,20}$")' \
                 'ID_RE = re.compile(r"G-[A-Z0-9]{4,20}")'
run "leave the pattern unanchored so an id can carry a payload" \
    "malformed_id_is_refused"

echo "== the tag itself =="

mut server/ga.py '    if not tag or "googletagmanager.com/gtag/js" in html:' \
                 '    if not tag:'
run "inject the tag twice and double every page view" "idempotent"

mut server/ga.py '    i = lowered.find("</head>")' '    i = lowered.find("</body>")'
run "put the tag at the end of the body instead of the head" "goes_in_the_head"

mut server/app.py '        return HTMLResponse(_ga.inject(ROADMAP_HTML.read_text()))' \
                  '        return HTMLResponse(ROADMAP_HTML.read_text())'
run "serve one page without the tag" "every_html_response"

mut server/app.py '    return _ga.inject(FRONTEND.read_text())' \
                  '    return FRONTEND.read_text()'
run "serve the FRONT page without the tag" "every_html_response"

mut fly.toml "  GA_MEASUREMENT_ID = 'G-B406V24KN5'\n" ''
run "deploy with no measurement id configured" "fly_config"

echo "== the promise on the page =="

# THE OLD WORDING, RESTORED. True before this release, false the moment the tag
# ships, and sitting on the privacy notice.
mut frontend/index.html '    <b>Two things measure this site, and they are not the same.</b><br>\n    <b>Ours.</b> We count' \
                        '    We count'
run "run Google Analytics under the old no-IP wording" \
    "names_google_analytics or promise_the_page_breaks"

mut frontend/index.html 'The switch below does <b>not</b> turn that off — to stop it, use a content blocker, your browser\x27s tracking protection, or Google\x27s own opt-out add-on.' \
                        'You can turn it off with the switch below.'
run "claim the off-switch stops Google too" "does_not_cover_google"

mut frontend/index.html '      ? "<b>Our</b> counting is <b>off</b> for this browser. Google Analytics is unaffected. "' \
                        '      ? "Counting is <b>off</b> for this browser. "'
run "let the switch say \x27counting is off\x27 while Google keeps counting" \
    "off_switch_label"

mut frontend/index.html '    ? "Your browser sends <b>Do Not Track</b> — <b>our</b> counting is off for this browser. "\n      + "Google Analytics does not read that signal; use a content blocker to stop it."' \
                        '    ? "Your browser sends <b>Do Not Track</b> — we\x27re counting nothing from this browser."'
run "tell a Do Not Track browser it is not being counted at all" "off_switch_label"

# Our own counting losing its DNT check while attention was on Google.
mut frontend/index.html '  if (dntOn() || analyticsOff()) return null;' '  if (analyticsOff()) return null;'
run "stop honouring Do Not Track for our own counter" "do_not_track_is_still_honoured"

echo "== the events =="

mut frontend/index.html '    if (typeof gtag !== \x27function\x27) return;\n' ''
run "call gtag without checking it exists" \
    "helper_cannot_break_the_app or app_survives_it_failing"

mut frontend/index.html '  ga(ev);            // the same signal, to the other ledger\n' ''
run "stop forwarding track() to GA" "feeds_both_ledgers"

mut frontend/index.html "    ga('generate', {source: _src});\n" ''
run "stop reporting the event the product exists for" \
    "behaviours_that_matter or which_door_was_used"

mut frontend/index.html "  ga('view_change', {view: v});\n" ''
run "leave two of the three doors invisible in the reports" \
    "behaviours_that_matter or view_change_event"

mut frontend/index.html "  ga('library_open', {mission: k});\n" ''
run "stop reporting Library opens" "behaviours_that_matter"

mut frontend/index.html "    ga('generate', {source: _src});" \
                        "    ga('generate', {source: _src, map: rc.map, aircraft: rc.aircraft});"
run "send the recipe to Google as well as to our own ledger" \
    "recipe_is_not_sent_to_google"

echo
echo "caught $PASS, weak $WEAK"
[ "$WEAK" -eq 0 ]
