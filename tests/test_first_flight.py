import io
import json
from pathlib import Path
import zipfile

from fastapi.testclient import TestClient

from missiongen import __version__, packs
from missiongen.resolver import load_json
from server.app import app
from server.catalog_owner import replay_target


def zip_bytes(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def upload(profile, version, include_campaign=True, include_briefs=True, valid_brief=True):
    files = {}
    syllabus = []
    for n, lesson in enumerate(profile["lessons"], 1):
        path = f"missions/{lesson['mission']}"
        brief = f"briefs/{Path(lesson['mission']).stem}-brief.pdf"
        files[path] = zip_bytes({"mission": 'mission = { ["theatre"] = "Caucasus" }'})
        if include_briefs:
            files[brief] = b"%PDF-1.4\n%%EOF" if valid_brief else b"<html>Not a PDF</html>"
        syllabus.append({"n": n, "label": lesson["title"], "files": {"mission": path, "brief": brief}})
    if include_campaign:
        files[profile["archive"]] = zip_bytes({"First-Flight.cmp": "campaign = {}"})
    files["pack.json"] = json.dumps({
        "format": 2,
        "id": profile["id"],
        "label": "First Flight test fixture",
        "version": version,
        "syllabus": syllabus,
    })
    packs.install(zip_bytes(files), "first_flight.sspack")
    return files


def test_wizard_lists_only_the_installed_matching_campaign(tmp_path, monkeypatch):
    monkeypatch.setattr(packs, "DATA_DIR", tmp_path)
    profile = load_json("first_flight")["profiles"][0]

    with TestClient(app) as client:
        assert client.get("/api/first-flight").json() == {"profiles": []}
        upload(profile, "0.0.1")
        assert client.get("/api/first-flight").json() == {"profiles": []}
        upload(profile, profile["version"], include_campaign=False)
        assert client.get("/api/first-flight").json() == {"profiles": []}
        upload(profile, profile["version"], include_briefs=False)
        assert client.get("/api/first-flight").json() == {"profiles": []}

        files = upload(profile, profile["version"])
        response = client.get("/api/first-flight")
        assert response.headers["cache-control"] == "no-store"
        (entry,) = response.json()["profiles"]
        assert entry["id"] == profile["id"]
        assert entry["map"]["id"] == "caucasus"
        assert entry["aircraft"]["id"] == "vnao_t45c"
        assert [lesson["id"] for lesson in entry["lessons"]] == ["FAM-01", "FAM-02"]
        assert entry["status"] == "flight_test_pending"
        download = client.get(entry["download_url"])
        assert download.status_code == 200
        assert download.headers["content-type"] == "application/zip"
        assert download.content == files[profile["archive"]]
        for lesson, expected in zip(entry["lessons"], profile["lessons"], strict=True):
            preview = client.get(lesson["brief_url"])
            brief_name = f"{Path(expected['mission']).stem}-brief.pdf"
            assert preview.status_code == 200
            assert preview.headers["content-type"] == "application/pdf"
            assert preview.headers["content-disposition"] == f'inline; filename="{brief_name}"'
            assert preview.headers["x-content-type-options"] == "nosniff"
            assert preview.content == files[f"briefs/{brief_name}"]
            attachment = client.get(lesson["brief_url"].split("?")[0])
            assert attachment.headers["content-disposition"] == f'attachment; filename="{brief_name}"'
            mission = client.get(lesson["mission_url"] + "?inline=1")
            assert mission.status_code == 200
            assert mission.headers["content-type"] == "application/zip"
            assert mission.headers["content-disposition"].startswith("attachment;")
            assert mission.content == files[f"missions/{expected['mission']}"]
        assert f"v{__version__}" in client.get("/").text

        packs.delete(profile["id"])
        assert client.get("/api/first-flight").json() == {"profiles": []}


def test_wizard_catalog_follows_the_pack_volume_owner():
    assert replay_target("/api/first-flight", "owner", "peer") == "owner"
    assert replay_target("/api/first-flight", "owner", "owner") is None


def test_inline_pack_preview_rejects_non_pdf_content(tmp_path, monkeypatch):
    monkeypatch.setattr(packs, "DATA_DIR", tmp_path)
    profile = load_json("first_flight")["profiles"][0]
    upload(profile, profile["version"], valid_brief=False)
    with TestClient(app) as client:
        entry = client.get("/api/first-flight").json()["profiles"][0]
        inline_url = entry["lessons"][0]["brief_url"]
        assert client.get(inline_url).status_code == 415
        attachment = client.get(inline_url.split("?")[0])
        assert attachment.status_code == 200
        assert attachment.headers["content-disposition"].startswith("attachment;")
