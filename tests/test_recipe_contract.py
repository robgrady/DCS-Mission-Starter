"""User input and browser/API sharing must describe the same mission."""
import base64
import json
from pathlib import Path
import re
import shutil
import subprocess

from fastapi.testclient import TestClient
import pytest

from missiongen.recipe import Recipe, RecipeError
from missiongen.share import decode_recipe, encode_recipe


INVALID_FIELDS = [
    ("slots", "2"), ("slots", 1.5), ("slots", True), ("slots", None),
    ("pattern_count", "2"), ("pattern_count", False),
    ("threat_intensity", None), ("threat_intensity", "3"),
    ("timing_hold_min", "abc"), ("timing_hold_min", 1.5),
    ("bb_tanker", "false"), ("bb_awacs", 1), ("bb_dtc", "true"),
    ("dress_fill", "45"), ("dress_fill", True),
    ("map", []), ("era", {}), ("template", []), ("aircraft", 42),
    ("callsign", 42), ("timing_at", 123),
    ("corridors", "FLEX"), ("corridors", [[]]),
    ("target_packages", [42]), ("carrier_deck_aircraft", [False]),
    ("map_layers", {}), ("dress_overrides", []), ("comms", []),
    ("dress_mix", {"F-16C_50": "2"}),
    ("dress_overrides", {"Kutaisi": True}),
    ("dress_overrides", {"Kutaisi": 101}),
]


@pytest.mark.parametrize("name,value", INVALID_FIELDS)
def test_bad_field_types_are_user_errors(name, value):
    with pytest.raises(RecipeError, match=name):
        Recipe.from_dict({name: value})


@pytest.mark.parametrize("name,value", INVALID_FIELDS)
def test_api_returns_field_error_without_running_generator(name, value, monkeypatch):
    from server import app as api

    def unexpected_build(*args, **kwargs):
        pytest.fail("invalid recipe reached the generator")

    monkeypatch.setattr(api, "_build_and_respond", unexpected_build)
    with TestClient(api.app, raise_server_exceptions=False) as client:
        response = client.post("/api/generate", json={"recipe": {name: value}})
    assert response.status_code == 400, response.text
    assert name in response.json()["detail"]


def test_direct_recipe_validation_also_checks_types():
    with pytest.raises(RecipeError, match="slots"):
        Recipe(slots="2").validate()


@pytest.mark.parametrize("value", [[], "mission", None, 42])
def test_recipe_requires_an_object(value):
    with pytest.raises(RecipeError, match="recipe"):
        Recipe.from_dict(value)


def test_valid_optional_values_and_zero_counts_survive():
    recipe = Recipe.from_dict({"bb_dtc": None, "dress_fill": None,
                               "dress_mix": {"F-16C_50": 0},
                               "dress_overrides": {"Kutaisi": 0},
                               "timing_hold_min": 0, "bb_tanker": False})
    assert recipe.dress_overrides == {"Kutaisi": 0}
    assert recipe.bb_tanker is False


def _code(payload):
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")


def _browser_codec(operation, value):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is needed for browser/server codec interoperability")
    html = (Path(__file__).parents[1] / "frontend/index.html").read_text()
    defaults = re.search(r"const RECIPE_DEFAULTS = (\{.*?\});", html, re.S).group(1)
    engine_fields = re.search(r"const RECIPE_ENGINE_FIELDS = (\[.*?\]);", html, re.S).group(1)
    functions = html.split("function encodeRecipe(r){", 1)[1].split("let OPT = null;", 1)[0]
    script = ("const fs = require('node:fs');\nconst RECIPE_DEFAULTS = " + defaults + ";\n"
              + "const RECIPE_ENGINE_FIELDS = " + engine_fields + ";\n"
              + "function encodeRecipe(r){" + functions
              + "\nconst input = JSON.parse(fs.readFileSync(0, 'utf8'));"
              + "try { const result = input.operation === 'encode' ? encodeRecipe(input.value) : decodeRecipe(input.value);"
              + "process.stdout.write(JSON.stringify({result})); } catch(e) { process.stdout.write(JSON.stringify({error:e.message})); }")
    return json.loads(subprocess.run([node, "-e", script],
                      input=json.dumps({"operation": operation, "value": value}),
                      capture_output=True, text=True, check=True).stdout)


SETTINGS = {"map": "syria", "era": "modern", "aircraft": "FA_18C_hornet",
            "seed": 42, "callsign": "飞行 🛫"}


def test_server_link_opens_with_same_settings_in_browser():
    code = encode_recipe(Recipe.from_dict(SETTINGS))
    decoded = _browser_codec("decode", code)["result"]
    assert all(decoded[k] == v for k, v in SETTINGS.items())


def test_unicode_browser_link_opens_with_same_settings_on_server():
    code = _browser_codec("encode", SETTINGS)["result"]
    decoded = decode_recipe(code).to_dict()
    assert all(decoded[k] == v for k, v in SETTINGS.items())


def test_legacy_unversioned_links_still_open_in_both_clients():
    settings = {**SETTINGS, "callsign": "Gypsy"}
    code = _code(settings)
    browser = _browser_codec("decode", code)["result"]
    server = decode_recipe(code).to_dict()
    assert all(browser[k] == server[k] == v for k, v in settings.items())


def test_legacy_accented_browser_callsign_is_not_lost():
    settings = {**SETTINGS, "callsign": "Équipe"}
    code = base64.urlsafe_b64encode(json.dumps(settings, ensure_ascii=False)
                                   .encode("latin-1")).decode().rstrip("=")
    assert _browser_codec("decode", code)["result"]["callsign"] == "Équipe"
    assert decode_recipe(code).callsign == "Équipe"


def test_engine_only_fields_can_be_shared():
    recipe = Recipe.from_dict({**SETTINGS, "bfm_setup": "offensive",
                               "bb_bfm": True, "coach_gates": True,
                               "corridors": ["FLEX"]})
    decoded = _browser_codec("decode", encode_recipe(recipe))["result"]
    for field in ("bfm_setup", "bb_bfm", "coach_gates", "corridors"):
        assert decoded[field] == recipe.to_dict()[field]


@pytest.mark.parametrize("payload", [
    {"v": 2, "r": {}}, {"v": True, "r": {}}, {"v": "1", "r": {}},
    {"v": 0, "r": {}}, {"v": 1}, {"r": {}},
    {"v": 1, "r": []}, {"v": 1, "r": None}, [], None,
    {"v": 1, "r": {"typo_setting": True}},
])
def test_bad_or_future_links_are_rejected_by_both_clients(payload):
    code = _code(payload)
    with pytest.raises(RecipeError):
        decode_recipe(code)
    assert "error" in _browser_codec("decode", code)
