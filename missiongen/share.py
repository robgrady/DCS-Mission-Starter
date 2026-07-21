"""Shareable recipe links: recipe <-> URL-safe code.

A share link fully regenerates the mission (recipes-not-artifacts principle).
Encoding is plain base64url(JSON) so the frontend can decode without a server call.

Versioned envelope
------------------
The code carries a schema version so that a future change to the recipe fields
or their defaults can be detected instead of silently mis-decoding an old link
into a *different* mission. Format:

    {"v": <int schema>, "r": {<non-default recipe fields>}}

Legacy codes (pre-v1) were a bare diff dict with no envelope; they still decode
(treated as schema 0). If a code declares a schema NEWER than this build knows,
we refuse rather than guess — the user is on an older client.
"""
import base64
import json

from .recipe import Recipe, RecipeError

# Bump when a recipe field is renamed/removed or a default changes in a way that
# would make an existing share code decode to a different mission. Same-meaning
# additive fields do NOT require a bump (a missing field just takes its default).
SHARE_SCHEMA = 1


def encode_recipe(recipe: Recipe) -> str:
    # only non-default fields, keeps codes short
    defaults = Recipe().to_dict()
    diff = {k: v for k, v in recipe.to_dict().items() if defaults.get(k) != v}
    payload = {"v": SHARE_SCHEMA, "r": diff}
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_recipe(code: str) -> Recipe:
    pad = "=" * (-len(code) % 4)
    raw = base64.urlsafe_b64decode(code + pad)
    obj = json.loads(raw)
    if isinstance(obj, dict) and "v" in obj and "r" in obj:
        ver, diff = obj["v"], obj["r"]
        if ver > SHARE_SCHEMA:
            raise RecipeError(
                f"This share link was created with a newer version of Mission "
                f"Starter (link schema v{ver}, this build supports v{SHARE_SCHEMA}). "
                f"Update to open it.")
    else:
        diff = obj  # legacy pre-envelope code (schema 0)
    if not isinstance(diff, dict):
        raise RecipeError("Malformed share link.")
    return Recipe.from_dict(diff)
