"""Authentic Style v2.1 — every generated document draws the specimen.

Rob: "This is the style guide for pdf files generated. All documentation
such as mission briefs should be generated and displayed with this style."
The specimen is docs/brand/authentic-style-specimen.pdf; its values are
literals here on purpose — a test that reads the token file to check the
token file proves nothing.

WHAT THIS FILE HOLDS THE PRODUCT TO
-----------------------------------
  1. the tokens ARE the specimen (navy #00205B, accent #1D4E89, paper white,
     panel #F4F6F8, ink #101828, dim #475467, danger/warn/ok);
  2. ReportLab embeds the six faces — Bangers, Barlow Condensed ExtraBold
     and Bold, Source Serif 4, Source Sans 3, IBM Plex Mono — in the kit,
     the track guides and the user guide, with a real bold for <b>;
  3. the PIL documents — the mission brief and the kneeboard — draw the
     navy band, the Bangers banner and white paper;
  4. the page furniture: band identity left, locator right, the
     non-affiliation line in the footer, long identities cut to fit;
  5. the HTML documentation pages carry the same tokens and faces.
"""
from __future__ import annotations

import io
import subprocess
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from missiongen import Recipe, generate, authentic, brand
from missiongen.brand import COLORS

ROOT = Path(__file__).resolve().parent.parent
SPEC = {"navy": "#00205B", "accent": "#1D4E89", "paper": "#FFFFFF", "panel": "#F4F6F8",
        "ink": "#101828", "dim": "#475467", "danger": "#9F1239", "warn": "#B45309",
        "ok": "#067647"}
FACES = ("Bangers", "BarlowCondensed-ExtraBold", "BarlowCondensed-Bold",
         "SourceSerif4", "SourceSans3", "IBMPlexMono")


def _fonts_in(pdf_path) -> set:
    out = subprocess.run(["pdffonts", str(pdf_path)], capture_output=True, text=True).stdout
    names = set()
    for line in out.splitlines()[2:]:
        if line.strip():
            names.add(line.split()[0].split("+")[-1])
    return names


def _has(names, face):
    return any(face.replace("-", "") in n.replace("-", "").replace("Roman", "") or face in n
               for n in names)


# --------------------------------------------------------------------------- #
# 1. the tokens are the specimen
# --------------------------------------------------------------------------- #
def test_the_document_palette_is_the_specimen():
    h = authentic.hexes()
    for k, v in SPEC.items():
        assert h[k].upper() == v, (k, h[k])
    assert COLORS.navy == (0x00, 0x20, 0x5B) and COLORS.paper == (0xFF, 0xFF, 0xFF)
    assert COLORS.accent == (0x1D, 0x4E, 0x89) and COLORS.panel == (0xF4, 0xF6, 0xF8)


def test_the_specimen_ships_with_the_product():
    assert (ROOT / "docs" / "brand" / "authentic-style-specimen.pdf").is_file()


# --------------------------------------------------------------------------- #
# 2. reportlab embeds the faces
# --------------------------------------------------------------------------- #
def test_every_face_registers_without_falling_back():
    f = authentic.register_fonts()
    assert f["banner"] == "Bangers" and f["section"] == "BarlowCondensed-ExtraBold"
    assert f["subhead"] == "BarlowCondensed-Bold" and f["serif"] == "SourceSerif4"
    assert f["sans"] == "SourceSans3" and f["mono"] == "IBMPlexMono"
    assert f["serif_bold"] == "SourceSerif4-Bold" and f["sans_bold"] == "SourceSans3-Bold"
    for name in ("SourceSerif4-Regular.ttf", "SourceSerif4-Bold.ttf",
                 "SourceSans3-Regular.ttf", "SourceSans3-Bold.ttf"):
        assert (authentic.FONT_DIR / name).is_file(), name


def test_bold_inside_prose_resolves_to_a_real_bold(tmp_path):
    from reportlab.platypus import Paragraph, SimpleDocTemplate
    S = authentic.styles()
    p = Paragraph("plain <b>bold</b>", S["p"])
    assert [fr.fontName for fr in p.frags] == ["SourceSerif4", "SourceSerif4-Bold"]
    out = tmp_path / "b.pdf"
    SimpleDocTemplate(str(out)).build([p, Paragraph("x <b>y</b>", S["small"])])
    names = _fonts_in(out)
    assert any("Bold" in n and "Serif" in n for n in names), names
    assert any("Bold" in n and "Sans" in n for n in names), names


def test_the_squadron_kit_is_set_in_the_six_faces(tmp_path):
    from missiongen import course_kit, courses
    c = courses.resolve("f4e_pipeline")
    pdf = course_kit.program_pdf(c, "0.0.0", tmp_path / "p.pdf")
    names = _fonts_in(pdf)
    for face in FACES:
        assert _has(names, face), (face, names)
    # pdffonts lists Helvetica whether or not a glyph was set in it, so the
    # source is the guard: no renderer names a built-in face.
    for mod in ("course_kit.py", "aar_guide.py", "wk_guide.py", "authentic.py"):
        src = (ROOT / "missiongen" / mod).read_text()
        body = src.split('"""', 2)[-1]
        if mod == "authentic.py":
            # the fallback table is the one place a built-in face may be named
            body = body.split("NOT_AFFILIATED =", 1)[-1]
        assert '"Helvetica' not in body and '"Courier' not in body, mod


def test_the_track_guides_are_set_in_the_six_faces(tmp_path):
    from missiongen import wk_guide, aar_guide, tracks, __version__
    p = wk_guide.build("wk_checkout", tracks.get("wk_checkout"), __version__,
                       out_dir=str(tmp_path), map_key="germany")
    names = _fonts_in(p)
    for face in ("Bangers", "BarlowCondensed-ExtraBold", "SourceSerif4", "IBMPlexMono"):
        assert _has(names, face), (face, names)
    p2 = aar_guide.build("aar_boom", tracks.get("aar_boom"), __version__,
                         out_dir=str(tmp_path), aircraft="F_4E_45MC", tanker="kc135", era="coldwar")
    names = _fonts_in(p2)
    assert _has(names, "Bangers") and _has(names, "SourceSerif4")


def test_the_user_guide_builder_uses_the_module_and_no_helvetica_text():
    src = (ROOT / "scripts" / "build_guide_pdf.py").read_text()
    assert "from missiongen import authentic as _auth" in src
    assert 'fontName="Helvetica' not in src and '"Helvetica-Bold"' not in src
    assert "NOT_AFFILIATED" in src
    assert "#17324D" not in src and "#F4F0E6" not in src, "the old Flightline literals are back"
    built = ROOT / "docs" / "DCS_Mission_Starter_Guide.pdf"
    if built.exists():
        names = _fonts_in(built)
        assert _has(names, "Bangers") and _has(names, "BarlowCondensed-ExtraBold")


# --------------------------------------------------------------------------- #
# 3. the PIL documents
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def built(tmp_path_factory):
    d = tmp_path_factory.mktemp("auth")
    r = Recipe.from_dict({"template": "timing_2_hitthetot", "map": "germany",
                          "era": "coldwar", "seed": 1})
    res = generate(r, str(d / "t.miz"), brief_dir=str(d))
    return d, res


def _kneeboard_pages(miz):
    z = zipfile.ZipFile(miz)
    return [Image.open(io.BytesIO(z.read(n))).convert("RGB")
            for n in sorted(z.namelist()) if n.startswith("KNEEBOARD/IMAGES/")]


def test_the_kneeboard_draws_the_navy_band_on_white_paper(built):
    d, _res = built
    pages = _kneeboard_pages(d / "t.miz")
    assert pages
    for pg in pages:
        assert pg.getpixel((10, 10)) == (0x00, 0x20, 0x5B), "no navy band"
        assert pg.getpixel((10, pg.height // 2)) == (0xFF, 0xFF, 0xFF), "paper is not white"
        # the band is mono white text on navy: some white pixels inside it
        band = pg.crop((0, 0, pg.width, 44))
        light = [px for px in band.get_flattened_data() if min(px) > 200] \
            if hasattr(band, "get_flattened_data") else \
            [px for px in list(band.getdata()) if min(px) > 200]
        assert light, "no white mono text in the band"


def test_the_brief_pdf_pages_draw_the_band(built, tmp_path):
    d, res = built
    pdf = Path(res["brief_pdf"])
    subprocess.run(["pdftoppm", "-r", "40", "-png", "-f", "1", "-l", "1", str(pdf), str(tmp_path / "b")],
                   check=True)
    png = next(tmp_path.glob("b*.png"))
    pg = Image.open(png).convert("RGB")
    r, g, b = pg.getpixel((5, 5))
    assert r < 40 and 20 < g < 60 and 70 < b < 120, f"band pixel {pg.getpixel((5, 5))}"
    r, g, b = pg.getpixel((5, pg.height // 2))
    assert min(r, g, b) > 240, "paper is not white"


def test_the_brief_and_kneeboard_use_the_banner_and_section_faces():
    from missiongen import brief, kneeboard
    fb = brief._fonts()
    fk = kneeboard._fonts()
    assert "Bangers" in " ".join(fb["banner"].getname())
    assert "Barlow" in " ".join(fb["h3"].getname()), "section heads are Barlow Condensed"
    assert "Bangers" in " ".join(fk["banner"].getname())
    assert "Barlow" in " ".join(fk["h2"].getname())


# --------------------------------------------------------------------------- #
# 4. the furniture
# --------------------------------------------------------------------------- #
def test_the_page_carries_identity_locator_and_the_non_affiliation_line(tmp_path):
    from reportlab.platypus import Paragraph
    from pypdf import PdfReader
    doc = authentic.make_doc(str(tmp_path / "d.pdf"), identity="Very Long Identity " * 8,
                             locator="SORTIE STARTER / TEST", footer_left="Footer " * 30)
    doc.build([Paragraph("body", authentic.styles()["p"])])
    text = PdfReader(str(tmp_path / "d.pdf")).pages[0].extract_text()
    assert "SORTIE STARTER / TEST" in text
    assert "Not affiliated with Eagle Dynamics" in text
    assert "…" in text, "a long identity is cut to fit, not drawn over the locator"
    assert "page 1" in text


def test_the_pills_are_the_four_states():
    assert set(authentic.PILLS) == {"INFO", "PASS", "CAUTION", "FAIL"}
    for kind in authentic.PILLS:
        assert authentic.pill("X", kind) is not None


# --------------------------------------------------------------------------- #
# 5. the HTML documentation pages
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("script,page", [("build_sources_html.py", "sources.html"),
                                         ("build_roadmap_html.py", "roadmap.html")])
def test_the_html_documentation_pages_carry_the_tokens_and_faces(script, page):
    src = (ROOT / "scripts" / script).read_text()
    assert "AUTHENTIC STYLE v2.1" in src
    for tok in ("--navy:#00205B", "--accent:#1D4E89", "--bg:#FFFFFF", "--panel:#F4F6F8"):
        assert tok in src, (script, tok)
    for face in ("Bangers", "Barlow Condensed", "Source Serif 4", "Source Sans 3", "IBM Plex Mono"):
        assert face in src, (script, face)
    assert 'class="aband"' in src
    built = ROOT / "docs" / page
    if built.exists():
        html = built.read_text()
        assert "--navy:#00205B" in html and 'class="aband"' in html
