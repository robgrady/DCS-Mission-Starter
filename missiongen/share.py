"""Shareable recipe links: recipe <-> URL-safe code.

A share link fully regenerates the mission (recipes-not-artifacts principle).
Encoding is plain base64url(JSON) so the frontend can decode without a server call.
"""
import base64
import json

from .recipe import Recipe


def encode_recipe(recipe: Recipe) -> str:
    # only non-default fields, keeps codes short
    defaults = Recipe().to_dict()
    diff = {k: v for k, v in recipe.to_dict().items() if defaults.get(k) != v}
    raw = json.dumps(diff, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_recipe(code: str) -> Recipe:
    pad = "=" * (-len(code) % 4)
    raw = base64.urlsafe_b64decode(code + pad)
    return Recipe.from_dict(json.loads(raw))
