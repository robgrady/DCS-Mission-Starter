"""Sponsor / brand-ad store.

Manages a small library of sponsor logos; exactly one is *active* and gets baked
into every generated mission's launch splash (cosmetic only — see branding.py).
The owner manages this through the password-gated /admin section (server/admin.py).

Design: see project doc `claude/sponsor-ads-design.md`.

- Source of truth is a tiny `manifest.json`; processed splash PNGs are a
  regenerable cache. A sponsor is sourced from an image URL (pulled + processed
  server-side) or a direct upload.
- If no store exists / no active sponsor, missions fall back to the shipped
  Authentic Media asset, so behaviour is unchanged out of the box.
- PIL-only (no numpy — not installed in the deploy container).
"""
from __future__ import annotations

import io
import os
import re
import json
import socket
import ipaddress
import threading
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError

from PIL import Image, ImageChops, ImageDraw

# Where the manifest + cache live. Override with SPONSOR_DATA_DIR (e.g. a Fly
# volume mount at /data/sponsors). Default is writable inside the container
# (/app is chown'd to the app user) — ephemeral without a volume.
DATA_DIR = Path(os.environ.get(
    "SPONSOR_DATA_DIR", str(Path(__file__).parent.parent / "instance" / "sponsors")))
_MANIFEST = DATA_DIR / "manifest.json"
_CACHE = DATA_DIR / "cache"

# Fallback splash shipped with the app (the Authentic Media wordmark).
_DEFAULT_ASSET = Path(__file__).parent / "data" / "brand" / "authentic_media.png"

DEFAULT_SPLASH_SIZE = 30       # % of window (DCS PictureToAll size)
DEFAULT_PANEL_OPACITY = 90     # 0–255 white-panel alpha
MAX_FETCH_BYTES = 5 * 1024 * 1024

_lock = threading.RLock()


# --------------------------------------------------------------------------- #
# Image pipeline (shared by uploads and URL pulls)
# --------------------------------------------------------------------------- #
def _open(src) -> Image.Image:
    if isinstance(src, (bytes, bytearray)):
        return Image.open(io.BytesIO(src))
    return Image.open(str(src))


def render_splash(src, panel_opacity: int = DEFAULT_PANEL_OPACITY,
                  target_w: int = 1600) -> Image.Image:
    """Turn a raw logo into the mission splash: knock out the near-white
    background, crop to the artwork, composite onto a semi-transparent white
    rounded panel, and downscale. Returns an RGBA PIL image.

    Re-encoding here also sanitises the upload (drops EXIF / malformed data)
    before the bytes are ever embedded in a user's .miz."""
    img = _open(src).convert("RGBA")
    r, g, b, a = img.split()
    # per-pixel min(R,G,B): high everywhere the pixel is near-white
    min_rgb = ImageChops.darker(ImageChops.darker(r, g), b)
    knock = min_rgb.point(lambda p: 0 if p > 235 else 255)   # 0 = white -> transparent
    img.putalpha(ImageChops.darker(a, knock))                # respect existing transparency

    bbox = img.getchannel("A").getbbox()
    if bbox:
        img = img.crop(bbox)
    aw, ah = img.size

    pad_x, pad_y = max(1, int(aw * 0.10)), max(1, int(ah * 0.22))
    W, H = aw + pad_x * 2, ah + pad_y * 2
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    op = max(0, min(255, int(panel_opacity)))
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=int(H * 0.14),
                        fill=(255, 255, 255, op))
    canvas.alpha_composite(img, (pad_x, pad_y))

    if W > target_w:
        canvas = canvas.resize((target_w, round(H * target_w / W)), Image.LANCZOS)
    return canvas


# --------------------------------------------------------------------------- #
# SSRF-guarded fetch
# --------------------------------------------------------------------------- #
def fetch_image(url: str, max_bytes: int = MAX_FETCH_BYTES, timeout: int = 8) -> bytes:
    """Download an image from an https URL with SSRF protection: https-only,
    the host must not resolve to a private/loopback/link-local/metadata
    address, response must be an image, and it is size-capped."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Logo URL must start with https://")
    host = parsed.hostname
    if not host:
        raise ValueError("Invalid URL")
    port = parsed.port or 443
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        raise ValueError("Could not resolve that host")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise ValueError("URL resolves to a blocked (internal) address")
    req = Request(url, headers={"User-Agent": "SortieStarter/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:   # noqa: S310 (guarded above)
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if not ctype.startswith("image/"):
                raise ValueError(f"That URL is not an image (got {ctype or 'unknown type'})")
            data = resp.read(max_bytes + 1)
    except (URLError, TimeoutError) as e:
        raise ValueError(f"Could not fetch the image: {e}")
    if not data:
        raise ValueError("The image URL returned no data")
    if len(data) > max_bytes:
        raise ValueError(f"Image too large (max {max_bytes // (1024*1024)} MB)")
    return data


# --------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------- #
def _default_manifest() -> dict:
    return {"active": None, "branding_enabled": True, "sponsors": {}}


def _load() -> dict:
    if not _MANIFEST.exists():
        return _default_manifest()
    try:
        m = json.loads(_MANIFEST.read_text())
    except (json.JSONDecodeError, OSError):
        return _default_manifest()
    m.setdefault("active", None)
    m.setdefault("branding_enabled", True)
    m.setdefault("sponsors", {})
    return m


def _save(m: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, indent=2))
    os.replace(tmp, _MANIFEST)          # atomic


def _slug(name: str, existing: dict) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", (name or "sponsor").lower()).strip("-") or "sponsor"
    slug, n = base, 2
    while slug in existing:
        slug = f"{base}-{n}"
        n += 1
    return slug


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def list_sponsors() -> dict:
    """Full manifest view: {active, branding_enabled, sponsors:{id:{...}}}."""
    with _lock:
        return _load()


def branding_enabled() -> bool:
    with _lock:
        return bool(_load().get("branding_enabled", True))


def set_branding_enabled(on: bool) -> None:
    with _lock:
        m = _load()
        m["branding_enabled"] = bool(on)
        _save(m)


def active_splash() -> dict | None:
    """The active sponsor's baked splash for the builder, or None to fall back
    to the shipped Authentic asset. Returns {id, name, path, size}."""
    with _lock:
        m = _load()
        aid = m.get("active")
        if not aid or aid not in m["sponsors"]:
            return None
        sp = m["sponsors"][aid]
        cache = _CACHE / f"{aid}.png"
        if not cache.exists():
            return None
        return {"id": aid, "name": sp.get("name", aid),
                "path": str(cache), "size": int(sp.get("splash_size", DEFAULT_SPLASH_SIZE))}


def add_sponsor(name: str, *, url: str | None = None, image_bytes: bytes | None = None,
                splash_size: int = DEFAULT_SPLASH_SIZE,
                panel_opacity: int = DEFAULT_PANEL_OPACITY,
                make_active: bool = False) -> str:
    """Add a sponsor from a URL or uploaded bytes. Fetches (if URL), renders the
    splash, caches it, and records it in the manifest. Returns the sponsor id."""
    if not name or not name.strip():
        raise ValueError("Sponsor name is required")
    if not url and not image_bytes:
        raise ValueError("Provide an image URL or upload a file")
    raw = image_bytes if image_bytes is not None else fetch_image(url)
    try:
        splash = render_splash(raw, panel_opacity=panel_opacity)
    except Exception as e:
        raise ValueError(f"Could not process that image: {e}")
    with _lock:
        m = _load()
        sid = _slug(name, m["sponsors"])
        _CACHE.mkdir(parents=True, exist_ok=True)
        splash.save(_CACHE / f"{sid}.png")
        m["sponsors"][sid] = {
            "name": name.strip(),
            "source_url": url or None,
            "splash_size": int(splash_size),
            "panel_opacity": int(panel_opacity),
            "impressions": 0,
        }
        if make_active or m.get("active") is None:
            m["active"] = sid
        _save(m)
        return sid


def set_active(sid: str) -> None:
    with _lock:
        m = _load()
        if sid not in m["sponsors"]:
            raise ValueError("No such sponsor")
        m["active"] = sid
        _save(m)


def delete_sponsor(sid: str) -> None:
    with _lock:
        m = _load()
        m["sponsors"].pop(sid, None)
        if m.get("active") == sid:
            m["active"] = next(iter(m["sponsors"]), None)
        _save(m)
    cache = _CACHE / f"{sid}.png"
    if cache.exists():
        cache.unlink()


def refresh_sponsor(sid: str) -> None:
    """Re-pull a URL-sourced sponsor and re-render its splash."""
    with _lock:
        m = _load()
        sp = m["sponsors"].get(sid)
        if not sp:
            raise ValueError("No such sponsor")
        url = sp.get("source_url")
        opacity = int(sp.get("panel_opacity", DEFAULT_PANEL_OPACITY))
    if not url:
        raise ValueError("This sponsor was uploaded (no URL to refresh)")
    raw = fetch_image(url)
    splash = render_splash(raw, panel_opacity=opacity)
    with _lock:
        _CACHE.mkdir(parents=True, exist_ok=True)
        splash.save(_CACHE / f"{sid}.png")


def increment_impressions(sid: str) -> None:
    """Bump a sponsor's baked-into-mission counter. Best-effort; never raises."""
    try:
        with _lock:
            m = _load()
            if sid in m["sponsors"]:
                m["sponsors"][sid]["impressions"] = int(
                    m["sponsors"][sid].get("impressions", 0)) + 1
                _save(m)
    except Exception:
        pass


def cache_path(sid: str) -> Path:
    return _CACHE / f"{sid}.png"
