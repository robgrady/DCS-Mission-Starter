"""The NTTR chart — the Nevada face of corridor_chart.py (kept for the
names the tests and docs learned in v1.100/1.101). See corridor_chart.py."""
from __future__ import annotations

from . import corridor_chart as _cc

Canvas = _cc.Canvas
Proj = _cc.Proj
HOT, HOT_FILL, GHOST, GHOST_FILL = _cc.HOT, _cc.HOT_FILL, _cc.GHOST, _cc.GHOST_FILL


def overview(w, h, plan=None, fs=1.0):
    return _cc.overview(w, h, plan, fs, mk="nevada")


def terminal(w, h, plan=None, fs=1.0):
    return _cc.terminal(w, h, plan, fs, mk="nevada")


def legend_lines(plan=None):
    return _cc.legend_lines(plan, "nevada")


def render_panel(width, height, plan=None, bounds=None, scale=1.0):
    return _cc.render_panel(width, height, plan, bounds, scale, mk="nevada")


def render_terminal(width, height, plan=None, scale=1.0):
    return _cc.render_terminal(width, height, plan, scale, mk="nevada")


def render_svg(width=1600, height=1000, plan=None):
    return _cc.render_svg(width, height, plan, mk="nevada")


def render_page(width=1600, height=1000, plan=None, title=None, scale=1.0):
    return _cc.render_page(width, height, plan, title, scale, mk="nevada")
