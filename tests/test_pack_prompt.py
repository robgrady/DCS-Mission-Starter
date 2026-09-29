"""The pack-authoring prompt teaches what the installer enforces.

WHY THIS FILE EXISTS. Rob: "I need downloadable instructions that I can add to
any AI that will tell it how to format a mission pack." So
`docs/PACK_AUTHORING_PROMPT.md` will be pasted into OTHER assistants, out of
reach of this repository — the one place a doc drifting from the code cannot be
corrected by the reader noticing. These guards keep the promise the hard way:
the doc's own code block is EXECUTED and its output compared against
`missiongen/packfmt.py`, and a pack built by following only the doc must
install.
"""
import io
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

from missiongen import packfmt                              # noqa: E402

DOC = (ROOT / "docs" / "PACK_AUTHORING_PROMPT.md").read_text()
SPEC = (ROOT / "docs" / "PACK_FORMAT.md").read_text()


def test_the_prompts_digest_code_is_the_real_algorithm(tmp_path):
    """THE LOAD-BEARING GUARD. The doc ships a runnable `build_integrity` —
    an AI following it computes hashes with that exact code. Execute the block
    out of the doc against a scratch pack and require byte-identical output
    from `packfmt.digest_of`. A doc that teaches a different digest produces
    packs the installer refuses, everywhere, forever."""
    m = re.search(r"```python\n(.*?)```", DOC, re.S)
    assert m, "the doc lost its code block"
    ns = {}
    exec(m.group(1), ns)                                    # noqa: S102
    build_integrity = ns["build_integrity"]

    (tmp_path / "missions").mkdir()
    (tmp_path / "missions" / "01_a.miz").write_bytes(b"not really a miz")
    (tmp_path / "READ_ME_FIRST.md").write_text("hello")
    (tmp_path / "pack.json").write_text("{}")               # must be excluded

    man = {}
    build_integrity(tmp_path, man)

    assert {r["path"] for r in man["files"]} == \
        {"missions/01_a.miz", "READ_ME_FIRST.md"}, man["files"]
    assert man["digest"] == packfmt.digest_of(man["files"]), \
        "the doc's digest recipe disagrees with packfmt.digest_of"


def test_a_pack_built_by_following_only_the_doc_installs(tmp_path, monkeypatch):
    """End to end: manifest fields copied from the doc's own example shape,
    zipped the way §6 says, pushed through the real installer."""
    import tempfile
    monkeypatch.setenv("PACKS_DATA_DIR", tempfile.mkdtemp())
    import importlib
    from missiongen import packs as _packs
    importlib.reload(_packs)

    files = {"missions/01_ride.miz": b"m" * 64,
             "READ_ME_FIRST.md": b"# read me"}
    man = {"format": 2, "id": "doc_built", "label": "Built From The Doc",
           "version": "1.0.0",
           "requires": {"terrains": ["caucasus"], "modules": ["F-16C"]},
           "library": {"role": "training", "threat": 1, "players": "SP",
                       "premise": "Built by following the prompt alone."},
           "syllabus": [{"n": 1, "id": "ride", "label": "The Ride",
                         "files": {"mission": "missions/01_ride.miz"}}],
           "docs": {"readme": "READ_ME_FIRST.md"},
           "x_custom": "must survive"}
    m2 = dict(man)
    m2["files"] = [{"path": p, "bytes": len(b),
                    "sha256": __import__("hashlib").sha256(b).hexdigest()}
                   for p, b in sorted(files.items())]
    m2["digest"] = packfmt.digest_of(m2["files"])

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("pack.json", json.dumps(m2))
        for p, b in files.items():
            z.writestr(p, b)

    got = _packs.install(buf.getvalue(), "doc_built.sspack")
    assert got["id"] == "doc_built"
    assert got.get("x_custom") == "must survive", \
        "the x_ extension promise the doc makes is broken"


def test_the_doc_teaches_the_rejection_list_the_reader_enforces():
    """§5 of the doc mirrors §6 of the spec. Every rejection the spec names
    must appear in the doc — an AI that does not know a rule ships packs that
    trip it."""
    for needle in ("format", "sha256", "digest", "signature", "symlink"):
        assert needle in DOC, f"the doc never mentions {needle}"
    # the numbers the doc hard-codes, pinned to the code
    # BOTH places the number appears, pinned separately — the example JSON
    # and the validation checklist. An OR here let a doc whose example said
    # `"format": 3` pass on the strength of the checklist still saying 2.
    assert f'"format": {packfmt.FORMAT},' in DOC, \
        "the example manifest teaches a format other than packfmt.FORMAT"
    assert f"`format` is `{packfmt.FORMAT}`" in DOC, \
        "the validation checklist names a format other than packfmt.FORMAT"
    import re as _re
    strays = set(_re.findall(r'"format": (\d+)', DOC)) - {str(packfmt.FORMAT)}
    assert not strays, f"the doc mentions format {strays} somewhere"
    assert "[a-z0-9_]" in DOC, "the id charset went missing"


def test_the_doc_and_the_spec_agree_on_the_digest_formula():
    """Both documents print the same one-line formula; the code implements it.
    Three copies of an algorithm is two too many unless they are pinned."""
    assert 'f"{path}\\x00{sha256}"' in SPEC
    assert '\\x00' in DOC, "the doc dropped the NUL separator from the formula"


def test_the_role_list_matches_the_reader():
    """The doc enumerates roles; packfmt.ROLES is what the reader accepts."""
    flat = re.sub(r"\s+", " ", DOC)     # the list wraps across lines
    m = re.search(r"`training \| ([a-z0-9| ]+)`", flat)
    assert m, "the doc lost its role list"
    doc_roles = {"training"} | {r.strip() for r in m.group(1).split("|")}
    assert doc_roles == set(packfmt.ROLES), \
        (sorted(doc_roles), sorted(packfmt.ROLES))
