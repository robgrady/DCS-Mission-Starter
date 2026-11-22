"""Keep guide links, embedded images and the offline PDF usable."""
from fastapi.testclient import TestClient
import pytest

from missiongen import __version__
from server.app import app
from test_refactor_browser import site


def test_web_guide_is_primary_and_existing_pdf_url_still_downloads():
    with TestClient(app) as client:
        assert 'href="/guide">User guide</a>' in client.get("/").text
        guide = client.get("/guide")
        assert guide.status_code == 200
        assert guide.headers["cache-control"] == "no-store"
        assert f'v{__version__}' in guide.text
        assert 'href="/api/guide"' in guide.text
        pdf = client.get("/api/guide")
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.headers["content-disposition"].startswith("attachment;")
        assert pdf.content.startswith(b"%PDF")
        assert client.get("/guide/images/guide-fly-now.png").headers["content-type"] == "image/png"
        assert client.get("/guide/images/roadmap.html").status_code == 404


@pytest.mark.parametrize("width", [320, 1280])
def test_guide_tasks_are_linkable_and_readable_without_javascript(site, width):
    pw = pytest.importorskip("playwright.sync_api")
    with pw.sync_playwright() as playwright, playwright.chromium.launch() as browser:
        page = browser.new_page(viewport={"width": width, "height": 900}, java_script_enabled=False)
        page.goto(site + "/guide#install-a-miz-mission")
        install = page.get_by_role("heading", name="Install a .miz mission", exact=True)
        pw.expect(install).to_be_in_viewport()
        pw.expect(install.locator("xpath=following-sibling::p[1]")).to_contain_text(r"Saved Games\DCS\Missions")

        page.get_by_role("link", name="Back to top", exact=True).click()
        page.get_by_role("main").get_by_role("link", name="Start the First Flight campaign", exact=True).click()
        pw.expect(page).to_have_url(site + "/guide#install-the-first-flight-campaign")
        chapter = page.get_by_role("heading", name="Install the First Flight campaign", exact=True)
        pw.expect(chapter).to_be_in_viewport()
        pw.expect(chapter.locator("xpath=following-sibling::p[1]")).to_contain_text("VNAO T-45C v1.02")

        screenshot = page.get_by_alt_text("First Flight lesson.", exact=False)
        screenshot.scroll_into_view_if_needed()
        pw.expect(screenshot).to_be_visible()
        assert screenshot.evaluate("img => img.complete && img.naturalWidth > 0")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")

        with page.expect_download() as result:
            page.get_by_role("link", name="Download PDF", exact=True).click()
        assert result.value.suggested_filename.endswith(".pdf")
