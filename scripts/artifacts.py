"""The registry of DERIVED artifacts — the one place that knows what is
generated from what, and how each one is kept honest.

WHY THIS FILE EXISTS
--------------------
Rob asked how we stop things going stale. The honest answer was that we had
solved it exactly once. `docs/whatsnew.html` cannot drift, because a test
regenerates it and compares byte-for-byte. Nothing else had any rule at all,
and an audit found:

    docs/ROADMAP.md         said v1.37     — 11 releases behind
    docs/roadmap.html       said v1.37     — and this is the file that ALREADY
                                             drifted 17 versions once before
    guide PDF cover         said v1.46.1   — 2 behind
    REPLIT.md               said v1.16.2   — 32 behind
    docs/img/*.png          pre-dated the entire Builder rework
    claude/build-status.md  said v1.21.1   — 27 behind

Every one of those was maintained by remembering. The fix is not to remember
harder; it is to make "remembering" a thing the build checks.

THE THREE RULES
---------------
Each artifact declares ONE freshness rule, chosen by how expensive it is to
regenerate:

  "rebuild"  Regenerate into a temp copy and compare bytes. Exact, catches any
             drift including a hand-edit, and only viable when generation is
             fast and deterministic. Markdown -> HTML pages.

  "stamp"    Record a hash of the INPUTS at generation time in
             docs/.artifacts.json, and fail when the inputs have changed since.
             For artifacts too slow to rebuild inside a test (a PDF, a browser
             screenshot run). Deliberately hash-based and not mtime-based:
             git does not preserve mtimes, so an mtime rule passes on a fresh
             clone no matter how stale the file is.

  "version"  The file must mention the current __version__. For hand-written
             prose that a script cannot generate but that goes wrong silently
             when nobody revisits it. This does not prove the prose is right —
             it forces a human to look at it at release time, which is the most
             a check can do for prose.

ADDING A DERIVED FILE
---------------------
Add it here. `tests/test_docs_fresh.py` walks this list, and
`scripts/release.sh` regenerates from it, so an entry is the only thing needed
to make a new artifact both refreshed and enforced. A derived file that is NOT
in this list is invisible to both — which is precisely how the roadmap page
drifted the first time.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAMPS = ROOT / "docs" / ".artifacts.json"


ARTIFACTS = [
    {
        'path': 'docs/historical_library.html',
        'rule': 'stamp',
        'generator': ['scripts/build_historical_library.py'],
        'inputs': ['missiongen/data/historical_library.json', 'missiongen/historical_library.py',
                   'missiongen/historical_reference_chart.py', 'scripts/build_historical_library.py',
                   'scripts/build_sources_html.py', 'frontend/assets/historical-library.js',
                   'missiongen/data/maps.json', 'missiongen/__init__.py'],
        'why': 'Dated reference readings, point diagrams and unit observations must match their provenance data.',
    },
    {
        'path': 'docs/historical_coverage.html',
        'rule': 'stamp',
        'generator': ['scripts/build_historical_coverage.py'],
        'inputs': ['scripts/build_historical_coverage.py', 'missiongen/data/historical_coverage.json', 'missiongen/historical_coverage.py',
                   'missiongen/historical_symbols.py', 'missiongen/corridor_chart.py',
                   'scripts/build_sources_html.py', 'missiongen/data/maps.json',
                   'missiongen/data/eras.json', 'missiongen/__init__.py'],
        'covers': 'docs/img/historical_symbols.*',
        'why': 'Public map/era research and symbols must match the audited register.',
    },
    {
        'path': 'docs/research/HISTORICAL_AIRSPACE_RESEARCH.md',
        'rule': 'stamp',
        'generator': ['scripts/build_historical_coverage.py'],
        'inputs': ['scripts/build_historical_coverage.py', 'missiongen/data/historical_coverage.json', 'missiongen/historical_coverage.py',
                   'missiongen/__init__.py'],
        'why': 'Research conclusions and primary sources are generated from the register.',
    },
    {
        # The site's color/font tokens are WRITTEN into frontend/index.html by
        # gen_theme.py from the same flightline.json every document renders
        # from. Registered so the site palette can never silently fork from
        # the documents' — the whole point of adopting one design system.
        "path": "frontend/index.html",
        "rule": "rebuild",
        "generator": ["scripts/gen_theme.py"],
        "inputs": ["missiongen/data/brand/flightline.json"],
        "why": "Flightline token block, generated between markers. Hand-edits "
               "inside the markers or a token change without a regen means the "
               "site and the kneeboard disagree about the same design system.",
    },
    {
        "path": "docs/roadmap.html",
        "rule": "rebuild",
        "generator": ["scripts/build_roadmap_html.py"],
        "inputs": ["docs/ROADMAP.md"],
        "why": "Served at /api/roadmap. This is the file that drifted 17 minor "
               "versions behind the product while the Markdown source it is "
               "built from was being kept current.",
    },
    {
        "path": "docs/packformat.html",
        "rule": "rebuild",
        "generator": ["scripts/build_packformat_html.py"],
        "inputs": ["docs/PACK_FORMAT.md"],
        "why": "Served at /api/packformat — the public spec. The generator was "
               "lost with the 1.104-1.105 build environment and the page sat "
               "unregistered; a spec edit would have shipped a stale page.",
    },
    {
        "path": "docs/sources.html",
        "rule": "rebuild",
        "generator": ["scripts/build_sources_html.py"],
        "inputs": ["docs/SOURCES.md"],
        "why": "Served at /api/sources. This page is the product's claim to be "
               "trustworthy about its own numbers; a stale one cites the wrong "
               "commit for a terrain we have since replaced.",
    },
    {
        "path": "docs/DCS_Mission_Starter_Guide.pdf",
        "rule": "stamp",
        "generator": ["scripts/build_guide_pdf.py"],
        # The guide embeds the screenshots and prints the version on its cover,
        # so it is downstream of both the UI and the release.
        "inputs": ["docs/USER_GUIDE.md", "scripts/build_guide_pdf.py", "missiongen/authentic.py", "missiongen/data/brand/**/*", "missiongen/__init__.py",
                   "docs/img/hero.png", "docs/img/review.png"],
        "why": "Downloaded from /api/guide. Its cover prints the version, so a "
               "stale one is visibly, embarrassingly wrong.",
    },
    {
        "path": "docs/img/hero.png",
        "rule": "stamp",
        "generator": ["scripts/capture_screenshots.py"],
        "inputs": ["frontend/index.html", "frontend/assets/mission-results.js",
                   "frontend/assets/*.js", "scripts/capture_screenshots.py"],
        "why": "Every screenshot in the guide comes from this run. The Builder "
               "was rebuilt across v1.45-1.47 and these still showed the old "
               "eight-step wizard.",
        "covers": "docs/img/*.png",
    },
    {
        # The corridor charts on the site (/api/corridors/<map>/chart.*).
        # Drawn from the same data the router flies; a data or renderer
        # change without a rebuild puts a chart on the site that disagrees
        # with the flight plan.
        "path": "docs/img/nttr_corridors.png",
        "rule": "stamp",
        "generator": ["scripts/build_corridor_charts.py"],
        "inputs": ["missiongen/data/corridors/nevada.json", "missiongen/data/corridors/syria.json", "missiongen/data/corridors/germany.json",
                   "missiongen/corridor_chart.py", "missiongen/corridors.py", "missiongen/historical_coverage.py", "missiongen/data/historical_coverage.json",
                   "scripts/build_corridor_charts.py"],
        "why": "The corridor charts the site serves. Generated from the "
               "routing data; stale means the picture and the flight plan "
               "disagree about where a corridor is.",
        "covers": "docs/img/*_corridors.*",
    },
    {
        # The thirteen coached-B'NAI cue cards. Their WORDS come out of
        # `wk_coach.PHASES` and are burned into the PNG at build time, so
        # editing a directive in the module without rebuilding leaves the
        # mission drawing the OLD word at the new moment — a training aid
        # telling the pilot to do the previous version of the right thing.
        "path": "missiongen/data/wk_coach/wk_coach_pup.png",
        "rule": "stamp",
        "generator": ["scripts/build_wk_coach_cards.py"],
        "inputs": ["missiongen/wk_coach.py",
                   "missiongen/data/wk/wk_bnai.png",
                   "scripts/build_wk_coach_cards.py"],
        "why": "The card a pilot reads in the pop. Its text is generated from "
               "the phase table and its picture from the squadron's scan; "
               "either changing without a rebuild is a silent lie on screen.",
        "covers": "missiongen/data/wk_coach/wk_coach_*.png",
    },
    {
        # The six brief pages. Their TEXT is rendered into the PNG, so an edit
        # to a page's words without a rebuild leaves the pilot reading last
        # release's brief while hearing this one — and he is locked in his
        # seat while it happens.
        "path": "missiongen/data/wk_brief/wk_brief_pop.png",
        "rule": "stamp",
        "generator": ["scripts/build_wk_brief_pages.py"],
        "inputs": ["missiongen/wk_brief.py",
                   "missiongen/data/wk/wk_bnai.png",
                   "scripts/build_wk_brief_pages.py",
                   "scripts/build_wk_coach_cards.py"],
        "why": "The brief a pilot reads with his controls locked. Its text is "
               "generated from the page table and its pictures from the "
               "squadron's scan.",
        "covers": "missiongen/data/wk_brief/wk_brief_*.png",
    },
    {
        # The 26 check-ride debrief cards. Every number on them (the 90/75/50 %
        # ladder, the 60 m band, the rejoin clock, the collision band) is read
        # from checkride.py at build time, so a threshold edited there without
        # a rebuild leaves the card grading to last release's rule.
        "path": "missiongen/data/checkride/checkride_overall_q.png",
        "rule": "stamp",
        "generator": ["scripts/build_checkride_cards.py"],
        "inputs": ["missiongen/checkride.py", "scripts/build_checkride_cards.py"],
        "why": "The debrief a pilot reads after the check. Its thresholds are "
               "the module's; the generator was lost once and the cards sat "
               "unregistered, which is how a drift would have gone unnoticed.",
        "covers": "missiongen/data/checkride/checkride_*.png",
    },
    {
        # The eight formation position-ladder cards, one per
        # formation_hud.STATES entry. A state added to the module without art
        # here fails the generator rather than the sortie.
        "path": "missiongen/data/formation_hud/formation_hud_hold.png",
        "rule": "stamp",
        "generator": ["scripts/build_formation_hud.py"],
        "inputs": ["missiongen/formation_hud.py", "scripts/build_formation_hud.py"],
        "why": "The card at the pilot's left at eye level during the coached "
               "formation ride. Same reason as the check-ride cards.",
        "covers": "missiongen/data/formation_hud/formation_hud_*.png",
    },
    {
        # The bundled packs. Registered so a release cannot ship missions built
        # from a spec that has since changed — the pack IS the product's
        # flagship content and nothing else would notice it going stale.
        "path": "packs/wk_proud_phantom.sspack",
        "rule": "stamp",
        "generator": ["scripts/build_pack.py", "--all"],
        "inputs": ["missiongen/**/*.py", "missiongen/data/**/*", "vendor/dcs/**/*", "scripts/build_pack.py"],
        "why": "The published White Knights syllabus. Produced at release "
               "time and UPLOADED through /admin rather than shipped — but "
               "still registered, because a pack built from a spec that has "
               "since changed is content that quietly no longer matches the "
               "syllabus it claims to be.",
        "covers": "packs/*.sspack",
    },
    {
        "path": "docs/WK_BNAI_VOICEOVER.md",
        "rule": "stamp",
        "generator": ["scripts/build_wk_voiceover_sheet.py"],
        "inputs": ["missiongen/wk_coach.py", "missiongen/wk_brief.py"],
        "why": "The recording sheet Rob works from. It lists the exact WAV "
               "filenames the mission looks for; a stale one asks for names "
               "nothing plays, and the failure is silent in the airplane.",
    },
    {
        "path": "docs/ROADMAP.md",
        "rule": "version",
        "why": "Says where the product is today. It said v1.37 eleven releases "
               "later. Hand-written: a script cannot know what is next.",
    },
    {
        "path": "REPLIT.md",
        "rule": "version",
        "why": "The implementation contract handed to a hosting agent. It "
               "described what changed 'since v1.16.2' thirty-two releases on, "
               "which is worse than no document.",
    },
]

# Deliberately NOT enforced, recorded here so the omission is a decision rather
# than an oversight — the failure mode this whole file exists to prevent.
EXCLUDED = [
    {
        "path": "samples/*.miz",
        "why": "22 pre-built missions. Regenerating them every release would "
               "churn all 22 binaries on any engine change, and they are "
               "illustrative rather than authoritative — the Library builds "
               "live missions. Rebuild them deliberately when the output "
               "changes in a way a sample should show: "
               "python3 scripts/generate_sample.py",
    },
    {
        "path": "claude/*.md (Claude project docs)",
        "why": "Lives in the Claude project, not the repository, so no test in "
               "this suite can reach it. claude/build-status.md was 27 releases "
               "behind before this was noticed. scripts/release.sh prints a "
               "reminder; there is no way to enforce it from here.",
    },
]


def sha(path) -> str:
    p = ROOT / path
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def input_hashes(art) -> dict:
    paths = {"scripts/artifacts.py"}
    if art.get("generator"):
        paths.add(art["generator"][0])
    for pattern in art.get("inputs", []):
        if any(ch in pattern for ch in '*?['):
            paths.update(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern)
                         if p.is_file() and '__pycache__' not in p.parts)
        else:
            paths.add(pattern)
    return {i: sha(i) for i in sorted(paths)}


def load_stamps() -> dict:
    try:
        return json.loads(STAMPS.read_text())
    except Exception:
        return {}


def save_stamps(stamps: dict) -> None:
    STAMPS.parent.mkdir(parents=True, exist_ok=True)
    STAMPS.write_text(json.dumps(stamps, indent=1, sort_keys=True) + "\n")


def restamp(paths=None) -> dict:
    """Record current input hashes for every 'stamp' artifact (or just some)."""
    stamps = load_stamps()
    for art in ARTIFACTS:
        if art["rule"] != "stamp":
            continue
        if paths and art["path"] not in paths:
            continue
        stamps[art["path"]] = input_hashes(art)
    save_stamps(stamps)
    return stamps


def stale(version: str) -> list:
    """[(path, reason)] for every artifact that is out of date.

    Pure inspection — never regenerates anything. `rebuild` artifacts are
    checked by the test suite, which can afford a temp regeneration; here they
    are only checked for existence, so this stays fast enough to run from
    preflight.
    """
    out = []
    stamps = load_stamps()
    for art in ARTIFACTS:
        path, rule = art["path"], art["rule"]
        p = ROOT / path
        if not p.exists():
            out.append((path, "missing"))
            continue
        if rule == "stamp":
            want, have = input_hashes(art), stamps.get(path, {})
            changed = [i for i in sorted(want.keys() | have.keys()) if have.get(i) != want.get(i)]
            if changed:
                out.append((path, "inputs changed since it was generated: "
                                  + ", ".join(changed)))
        elif rule == "version":
            if f"v{version}" not in p.read_text(errors="ignore"):
                out.append((path, f"does not mention v{version}"))
    from manual_review import errors as manual_errors
    out.extend(('docs/manual-release-review.json', reason) for reason in manual_errors(version, ROOT))
    return out


def release_generators(stage):
    """One ordered registry drives regeneration and freshness checks."""
    seen = set()
    for artifact in ARTIFACTS:
        command = artifact.get('generator')
        if not command or tuple(command) in seen:
            continue
        seen.add(tuple(command))
        producer = command[0]
        phase = 'screenshots' if 'capture_screenshots' in producer else 'after-shots' if 'build_guide_pdf' in producer else 'before-shots'
        if phase == stage:
            yield command


def run_generators(stage, runner=None):
    import subprocess, sys
    runner = runner or subprocess.run
    for command in release_generators(stage):
        print('Generating ' + command[0], flush=True)
        runner([sys.executable, *command], cwd=ROOT, check=True)


if __name__ == '__main__':
    import sys
    run_generators(sys.argv[1])
