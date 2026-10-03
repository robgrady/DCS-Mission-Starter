"""The bibliography has to stay true, or it is worse than not having one.

`docs/SOURCES.md` is the product's claim that its numbers are traceable — every
assertion measured, cited, or admitted as an estimate. A sources page that has
quietly gone stale is a stronger lie than no sources page, because it looks
like diligence. Specifically, it can rot in three ways:

  * it cites a **pinned commit** for a vendored terrain we have since replaced;
  * it stops covering a data pack whose provenance is external, so a whole
    category of claim becomes untraceable without anyone noticing;
  * the **served HTML** drifts from the Markdown, which is exactly what
    happened to `docs/roadmap.html` (17 minor versions behind while the source
    it is built from was kept current — see `scripts/artifacts.py`).

Each is asserted against the real files.
"""
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SRC = ROOT / "docs" / "SOURCES.md"
TEXT = SRC.read_text()


def test_the_page_exists_and_is_substantial():
    assert SRC.exists()
    assert len(TEXT) > 4000, "a bibliography this short is a gesture"


def test_every_pinned_commit_matches_the_terrain_it_claims():
    """The failure that would embarrass us most: citing the commit a terrain
    came from after swapping the terrain. The provenance is duplicated by
    design — once in the page, once in the terrain's own header — so this
    checks the two agree rather than trusting either."""
    cited = set(re.findall(r"\b([0-9a-f]{8,40})\b", TEXT))
    assert cited, "the page pins no commit at all"
    for pkg in ("iraq", "afghanistan"):
        header = (ROOT / "missiongen" / "terrains" / pkg / f"{pkg}.py").read_text()
        in_src = set(re.findall(r"\b([0-9a-f]{8,40})\b", header))
        assert in_src, f"{pkg}.py records no source commit"
        # every short form in the page must prefix a commit the package claims
        assert any(any(long.startswith(short) or short.startswith(long)
                       for long in in_src) for short in cited), (
            f"SOURCES.md pins no commit matching {pkg}'s recorded provenance "
            f"{sorted(in_src)}")


# Data packs whose numbers come from OUTSIDE this repository — a published
# source, an export from another project, or a measurement session. Each must
# be traceable from the sources page. Packs that are purely our own product
# decisions (which airframe a theme parks, what a threat tier means) are not
# listed, because there is nothing external to cite.
EXTERNALLY_SOURCED = {
    "parking_headings": "legacy stand measurements and identified in-sim surveys",
    "static_liveries": "exact-model livery IDs with external source evidence",
    "airframe_dimensions": "read out of dcs.log by an in-sim survey",
    "aircraft_service": "real service windows gate every era",
    "weapon_service": "same, for stores",
    "historical_airspace": "real corridors and no-fly zones",
    "theater_identity": "real national ownership of real airbases",
    "air_corridors": "researched historical lanes",
    "callsigns": "documented squadron callsigns, tagged against invented ones",
    "squadrons": "real squadron identities",
    "comms_plan": "real, legal frequencies",
}


@pytest.mark.parametrize("pack,why", sorted(EXTERNALLY_SOURCED.items()))
def test_an_externally_sourced_data_pack_is_traceable(pack, why):
    """Named in the page, or in a document the page points at. Either is fine —
    what is not fine is a pack full of external facts with no route to where
    they came from."""
    if pack in TEXT:
        return
    for doc in re.findall(r"`?(docs/[\w.-]+\.md)`?", TEXT):
        p = ROOT / doc
        if p.exists() and pack in p.read_text():
            return
    pytest.fail(f"data/{pack}.json is externally sourced ({why}) but neither "
                f"SOURCES.md nor any document it links names it")


def test_the_licences_we_actually_ship_are_all_declared():
    """Vendored code with a license file on disk must appear in the licensing
    table. Shipping someone's LGPL library and not saying so is the one failure
    here with legal weight, not just editorial."""
    for path, token in (("vendor/dcs/COPYING.LESSER", "LGPL-3.0"),
                        ("vendor/axe-core/LICENSE", "MPL-2.0"),
                        ("missiongen/data/brand/LICENSE-lucide.txt", "ISC"),
                        ("missiongen/data/brand/fonts/OFL-ibmplexmono.txt", "OFL"),
                        ("LICENSE", "MIT")):
        assert (ROOT / path).exists(), f"{path} is referenced but missing"
        assert token in TEXT, f"{path} ships but {token} is not declared"


def test_it_admits_what_it_cannot_source():
    """The part that makes the rest credible. Two live examples: magnetic
    variation, which we label rather than guess, and the Baghdad ROZ /
    'corkscrew' approach, which is widely repeated and which we deliberately
    left out of the product for want of an authority."""
    low = TEXT.lower()
    assert "estimate" in low or "could not" in low or "admitted" in low, \
        "a sources page with no admitted gaps is not a sources page"
    assert "magnetic variation" in low, \
        "the TRUE-heading caveat is the clearest example of labelling over guessing"


def test_no_bare_placeholder_links():
    """A citation that goes nowhere is worse than a missing one."""
    bad = [u for u in re.findall(r"\]\((.+?)\)", TEXT)
           if u.strip() in ("", "#", "TODO", "http://", "https://")]
    assert not bad, f"placeholder links: {bad}"


def test_the_served_page_is_regenerable_and_matches():
    """Byte-identical to what the builder produces right now — the guard
    `docs/roadmap.html` did not have when it drifted 17 versions."""
    import subprocess
    import sys
    out = ROOT / "docs" / "sources.html"
    assert out.exists(), "the page served at /api/sources has not been built"
    before = out.read_bytes()
    subprocess.run([sys.executable, "scripts/build_sources_html.py"],
                   cwd=str(ROOT), capture_output=True, text=True)
    after = out.read_bytes()
    if before != after:
        out.write_bytes(before)
        pytest.fail("docs/sources.html is not what scripts/build_sources_html.py "
                    "produces from the current SOURCES.md — re-run it and commit "
                    "the result.")


def test_the_artifact_registry_knows_about_it():
    """Belt and braces: the release script's pre-deploy check must block on a
    stale sources page the same way it blocks on a stale roadmap."""
    reg = (ROOT / "scripts" / "artifacts.py").read_text()
    assert "docs/sources.html" in reg
    assert "scripts/build_sources_html.py" in reg


def test_the_endpoint_serves_it():
    from fastapi.testclient import TestClient
    from server.app import app
    r = TestClient(app).get("/api/sources")
    assert r.status_code == 200
    assert "LGPL" in r.text, "the licensing section did not survive rendering"
    assert "<table>" in r.text, "the tables did not survive rendering"
