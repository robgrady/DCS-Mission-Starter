import io
import json
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


def upload(profile, version, include_campaign=True):
    files = {}
    syllabus = []
    for n, lesson in enumerate(profile["lessons"], 1):
        path = f"missions/{lesson['mission']}"
        files[path] = zip_bytes({"mission": 'mission = { ["theatre"] = "Caucasus" }'})
        syllabus.append({"n": n, "label": lesson["title"], "files": {"mission": path}})
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
        assert f"v{__version__}" in client.get("/").text

        packs.delete(profile["id"])
        assert client.get("/api/first-flight").json() == {"profiles": []}


def test_wizard_catalog_follows_the_pack_volume_owner():
    assert replay_target("/api/first-flight", "owner", "peer") == "owner"
    assert replay_target("/api/first-flight", "owner", "owner") is None
