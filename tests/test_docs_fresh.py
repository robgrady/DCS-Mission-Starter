"""Nothing derived is allowed to be stale at release time.

`test_release_notes.py` already proves this works: it regenerates
`docs/whatsnew.html` and compares byte-for-byte, so that page cannot drift. The
problem Rob raised is that we had done it exactly ONCE. An audit at v1.48.0
found everything else maintained by remembering, and remembering had failed
everywhere:

    docs/ROADMAP.md         v1.37     11 releases behind
    docs/roadmap.html       v1.37     the page that ALREADY drifted 17 versions
    guide PDF cover         v1.46.1    2 behind
    REPLIT.md               v1.16.2   32 behind
    docs/img/*.png          pre-dated the entire Builder rework
    claude/build-status.md  v1.21.1   27 behind

So this file generalises the whatsnew guard to every derived artifact, driven
by the registry in `scripts/artifacts.py`. The registry is the point: a new
derived file is only refreshed by `release.sh` and only enforced here if it has
an entry, which makes "declare how this stays fresh" a required step rather
than a good intention.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import artifacts as A  # noqa: E402

from missiongen import __version__  # noqa: E402

BY_RULE = {}
for _a in A.ARTIFACTS:
    BY_RULE.setdefault(_a["rule"], []).append(_a)


def _ids(arts):
    return [a["path"] for a in arts]


# --- the registry itself ----------------------------------------------------

def test_the_registry_is_not_empty():
    """Every check below iterates the registry, so an empty one turns this
    whole file green while enforcing nothing."""
    assert len(A.ARTIFACTS) >= 5, f"only {len(A.ARTIFACTS)} artifacts registered"
    assert set(BY_RULE) <= {"rebuild", "stamp", "version"}, \
        f"unknown freshness rules: {set(BY_RULE) - {'rebuild', 'stamp', 'version'}}"


@pytest.mark.parametrize("art", A.ARTIFACTS, ids=_ids(A.ARTIFACTS))
def test_every_artifact_says_why_it_matters(art):
    """An entry with no rationale is an entry nobody will dare delete and
    nobody will understand. The `why` is what makes the list maintainable."""
    assert len(art.get("why", "")) > 40, f"{art['path']} has no useful 'why'"
    assert (ROOT / art["path"]).exists(), f"{art['path']} does not exist"


@pytest.mark.parametrize("art", BY_RULE.get("rebuild", []) + BY_RULE.get("stamp", []),
                         ids=_ids(BY_RULE.get("rebuild", []) + BY_RULE.get("stamp", [])))
def test_generated_artifacts_name_a_real_generator_and_real_inputs(art):
    rel = art["generator"][0]
    assert (ROOT / rel).is_file(), f"{art['path']}: generator {rel} is missing"
    assert art.get("inputs"), f"{art['path']} declares no inputs"
    for rel in art["inputs"]:
        assert any(path.is_file() for path in ROOT.glob(rel)), f"{art['path']}: input {rel} is missing"


def test_the_exclusions_are_documented_decisions():
    """The whole failure mode here is a derived file nobody declared. An
    exclusion list with reasons is how you tell "we thought about it" from "we
    forgot", six months later."""
    assert A.EXCLUDED, "nothing is excluded — that is suspicious, not clean"
    for ex in A.EXCLUDED:
        assert len(ex.get("why", "")) > 60, \
            f"{ex['path']} is excluded without a real reason"


# --- rule 1: regenerate and compare ----------------------------------------

@pytest.mark.parametrize("art", BY_RULE.get("rebuild", []),
                         ids=_ids(BY_RULE.get("rebuild", [])))
def test_rebuildable_pages_match_their_source(art):
    """The strongest rule, and the one already proven to work: run the
    generator and compare bytes. Catches a stale page AND a hand-edit to the
    generated file, which would otherwise survive until the next build silently
    reverted it."""
    path = ROOT / art["path"]
    before = path.read_bytes()
    r = subprocess.run([sys.executable] + art["generator"], cwd=str(ROOT),
                       capture_output=True, text=True)
    after = path.read_bytes()
    if before != after:
        path.write_bytes(before)          # leave the tree as we found it
        pytest.fail(
            f"{art['path']} is not what {art['generator'][0]} produces from "
            f"{', '.join(art['inputs'])} right now. Re-run it and commit the "
            f"result — or use: bash scripts/release.sh <version>")
    assert r.returncode == 0, r.stderr[-800:]


# --- rule 2: input hashes ---------------------------------------------------

@pytest.mark.parametrize("art", BY_RULE.get("stamp", []),
                         ids=_ids(BY_RULE.get("stamp", [])))
def test_expensive_artifacts_were_built_from_the_current_inputs(art):
    """For things too slow to rebuild inside a test — a PDF, a browser
    screenshot run. Hash-based rather than mtime-based on purpose: git does not
    preserve mtimes, so an mtime rule passes on a fresh clone no matter how
    stale the file actually is."""
    want = A.input_hashes(art)
    have = A.load_stamps().get(art["path"], {})
    changed = [i for i, h in want.items() if have.get(i) != h]
    assert not changed, (
        f"{art['path']} was generated before {', '.join(changed)} last "
        f"changed. Re-run {art['generator'][0]} (or scripts/release.sh) and "
        f"commit both the artifact and docs/.artifacts.json.")


def test_the_stamp_file_ships_and_covers_every_stamped_artifact():
    assert A.STAMPS.exists(), "docs/.artifacts.json is missing — nothing is stamped"
    stamps = A.load_stamps()
    for art in BY_RULE.get("stamp", []):
        assert art["path"] in stamps, f"{art['path']} has never been stamped"


# --- rule 3: version stamps -------------------------------------------------

@pytest.mark.parametrize("art", BY_RULE.get("version", []),
                         ids=_ids(BY_RULE.get("version", [])))
def test_hand_written_docs_mention_this_release(art):
    """A version stamp cannot prove prose is correct. What it does is force
    someone to open the file at release time, which is the most a check can do
    for something a script cannot generate — and strictly more than the nothing
    that let REPLIT.md describe a build thirty-two releases old."""
    text = (ROOT / art["path"]).read_text(errors="ignore")
    assert f"v{__version__}" in text, (
        f"{art['path']} does not mention v{__version__}. It is hand-written, so "
        f"read it and update what has actually changed — do not just bump the "
        f"number.")


# --- the gate ---------------------------------------------------------------

def test_nothing_is_stale_right_now():
    """The single assertion that matters, and the same call preflight makes."""
    stale = A.stale(__version__)
    assert not stale, "stale artifacts:\n  " + "\n  ".join(
        f"{p}: {why}" for p, why in stale)


def test_preflight_blocks_on_staleness():
    """Rob chose "block the release". A check that only warns is the honor
    system with extra steps, and the honor system is what produced the audit
    at the top of this file."""
    pre = (ROOT / "scripts" / "preflight.sh").read_text()
    assert "artifacts" in pre, \
        "scripts/preflight.sh no longer runs the staleness check"
    after = pre.split("import artifacts", 1)[1][:900]
    assert "bad " in after, \
        "preflight reports staleness with note/ok instead of bad — it warns "
    assert "FAIL=1" in pre, "preflight has no failure mechanism at all"


def test_the_release_script_regenerates_everything_registered():
    """A registry entry is worthless if the release command doesn't run its
    generator, and the drift would be invisible until someone read the file."""
    rel = (ROOT / "scripts" / "release.sh").read_text()
    commands = [command for stage in ('before-shots', 'screenshots', 'after-shots')
                for command in A.release_generators(stage)]
    for art in BY_RULE.get("rebuild", []) + BY_RULE.get("stamp", []):
        assert art['generator'] in commands
    assert 'scripts/artifacts.py' in rel and 'restamp' in rel


def test_the_release_script_refuses_to_skip_the_writing():
    """The one thing that cannot be generated is the one that matters most.
    release.sh must check them BEFORE the slow steps, or you spend a minute on
    screenshots to fail on a missing changelog entry."""
    rel = (ROOT / "scripts" / "release.sh").read_text()
    # since v1.105.0 the changelog is the one hand-written record (What's new
    # and RELEASE_NOTES.md were retired); it is still checked before the slow steps
    assert "CHANGELOG.md" in rel and "RELEASE_NOTES.md" not in rel
    notes_at = rel.index("CHANGELOG.md")
    shots_at = rel.index("artifacts.py screenshots")
    assert notes_at < shots_at, \
        "release.sh runs the slow steps before checking the changelog entry exists"


def test_every_registered_generator_runs_and_is_deterministic(tmp_path):
    """THE HOLE UNDER THE FRESHNESS SYSTEM, closed.

    `scripts/release.sh` used to invoke each generator as `cmd && ok "label"`.
    `set -e` does not fire for a command on the LEFT of `&&`, so a generator
    that crashed printed its traceback, skipped its tick, and the release
    carried on — and then `artifacts.restamp()` recorded the current input
    hashes regardless, marking a file that had never been rebuilt as fresh,
    permanently. A staleness checker certifying a stale file is worse than no
    checker.

    It happened: `build_wk_coach_cards.py` unpacked a fixed-width tuple, the
    phase table grew a field, and the generator was dead for a whole release
    while every check stayed green.

    So: run each registered generator for real, assert it exits 0, and assert
    it did not change its own output — which is both a determinism check and
    proof the committed artifact matches what the code produces today.
    """
    import hashlib
    import subprocess
    import sys

    def digest(art):
        paths = sorted(ROOT.glob(art["covers"])) if art.get("covers") \
            else [ROOT / art["path"]]
        h = hashlib.sha256()
        for p in paths:
            h.update(p.read_bytes() if p.exists() else b"")
        return h.hexdigest(), len(paths)

    ran = 0
    for art in A.ARTIFACTS:
        gen = (art.get("generator") or [None])[0]
        # Only the cheap, side-effect-free generators. The screenshot run needs
        # a live server and a browser; the guide PDF is downstream of it; and
        # `build_pack.py` generates forty-four missions, which is ninety
        # seconds and belongs in the release, not in every test run. Their
        # staleness is still caught by the `stamp` rule — this test adds the
        # extra guarantee that a generator RUNS, and buying that guarantee for
        # the expensive three would cost more than it is worth.
        if not gen or any(x in gen for x in ("capture_screenshots",
                                             "build_guide_pdf",
                                             "build_pack.py")):
            continue
        before, n = digest(art)
        assert n and before, art["path"]
        env = dict(os.environ, PYTHONPATH=f"{ROOT}:{ROOT / 'vendor'}",
                   PYTHONDONTWRITEBYTECODE="1")
        r = subprocess.run([sys.executable, str(ROOT / gen)], cwd=ROOT,
                           env=env, capture_output=True, text=True)
        assert r.returncode == 0, f"{gen} failed:\n{r.stderr[-1500:]}"
        after, _ = digest(art)
        assert after == before, \
            f"{gen} rebuilt {art['path']} differently — commit the rebuild"
        ran += 1
    assert ran >= 4, ran
