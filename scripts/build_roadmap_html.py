#!/usr/bin/env python3
"""Render docs/ROADMAP.md into the styled docs/roadmap.html served at
/admin/roadmap (owner-only since v1.93.0).

This exists because the HTML page drifted 17 minor versions behind the product
while the Markdown fallback (which nothing served) got updated. One source of
truth (ROADMAP.md), one command to publish it:

    python3 scripts/build_roadmap_html.py

Run it in the same commit as any release that ships a roadmap item — that's
the rule printed at the bottom of the page.
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent


def _ver() -> str:
    """The version string, read from the file — importing missiongen pulls
    in pydcs, which these page builders have no business needing."""
    import re as _re
    src = (ROOT / "missiongen" / "__init__.py").read_text()
    return _re.search(r'__version__ = "([^"]+)"', src).group(1)
SRC = ROOT / "docs" / "ROADMAP.md"
OUT = ROOT / "docs" / "roadmap.html"

STYLE = """
  @font-face{font-family:'Barlow Condensed';src:url('/fonts/BarlowCondensed-Bold.ttf') format('truetype');font-weight:700;font-display:swap}
  @font-face{font-family:'Barlow Condensed';src:url('/fonts/BarlowCondensed-ExtraBold.ttf') format('truetype');font-weight:800;font-display:swap}
  @font-face{font-family:'Bangers';src:url('/fonts/Bangers-Regular.ttf') format('truetype');font-weight:400;font-display:swap}
  @font-face{font-family:'Source Sans 3';src:url('/fonts/SourceSans3-VF.ttf') format('truetype');font-weight:300 900;font-display:swap}
  @font-face{font-family:'Source Serif 4';src:url('/fonts/SourceSerif4-VF.ttf') format('truetype');font-weight:300 900;font-display:swap}
  @font-face{font-family:'IBM Plex Mono';src:url('/fonts/IBMPlexMono-Regular.ttf') format('truetype');font-weight:400;font-display:swap}
  @font-face{font-family:'IBM Plex Mono';src:url('/fonts/IBMPlexMono-Bold.ttf') format('truetype');font-weight:700;font-display:swap}
  :root{/* AUTHENTIC STYLE v2.1 — data/brand/flightline.json, docs/brand/authentic-style-specimen.pdf */
    --bg:#FFFFFF;--panel:#F4F6F8;--line:#D0D5DD;--text:#101828;
    --dim:#475467;--accent:#1D4E89;--navy:#00205B;--teal:#1D4E89;--amber:#B45309;
    --disp:'Barlow Condensed','Arial Narrow',sans-serif;--banner:'Bangers','Barlow Condensed',Impact,sans-serif;
    --serif:'Source Serif 4',Georgia,serif;--sans:'Source Sans 3',system-ui,Helvetica,Arial,sans-serif;
    --mono:'IBM Plex Mono',ui-monospace,Menlo,monospace}
  .aband{background:var(--navy);color:#fff;font-family:var(--mono);font-size:12px;letter-spacing:.06em;
    text-transform:uppercase;padding:12px 24px;display:flex;justify-content:space-between;gap:16px}
  .aband b{font-weight:700}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--text);line-height:1.65;
    font-family:var(--serif)}
  .wrap{max-width:860px;margin:0 auto;padding:40px 24px 90px}
  a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
  h1{font-family:var(--banner);font-weight:400;font-size:44px;line-height:1;margin:0 0 4px;letter-spacing:.01em;color:var(--navy)}
  h1 span{color:var(--accent)}
  .sub{font-family:var(--sans);color:var(--dim);margin:0 0 8px;font-size:14px}
  .north{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--teal);
    border-radius:10px;padding:14px 18px;margin:22px 0 30px;font-size:15px}
  .north b{color:var(--teal)}
  h2{font-family:var(--disp);font-weight:800;font-size:18px;text-transform:uppercase;letter-spacing:.02em;color:var(--text);border-bottom:1px solid var(--line);padding-bottom:4px;
    display:flex;align-items:center;gap:10px;margin:34px 0 14px}
  h2::after{content:"";flex:1;height:1px;background:var(--line)}
  ul{margin:0;padding-left:0;list-style:none}
  li{background:var(--panel);border:1px solid var(--line);border-radius:10px;
     padding:12px 16px;margin-bottom:10px;font-size:14px;color:var(--dim)}
  li b{color:var(--text)}
  p{font-size:14.5px;color:var(--dim)}
  .rule{margin-top:40px;border-top:1px solid var(--line);padding-top:16px;
        font-size:12.5px;color:var(--dim);font-style:italic}
"""


def md_inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def build() -> str:
    lines = SRC.read_text().splitlines()
    body = []
    list_kind = None
    paragraph, item = [], []

    def flush_item():
        if item:
            body.append(f"<li>{md_inline(' '.join(item))}</li>")
            item.clear()

    def close_list():
        nonlocal list_kind
        flush_item()
        if list_kind:
            body.append(f"</{list_kind}>")
            list_kind = None

    def flush_paragraph():
        if not paragraph:
            return
        text = ' '.join(paragraph)
        paragraph.clear()
        if text.startswith("**North star:**"):
            body.append(f"<div class=north>{md_inline(text)}</div>")
        elif text.startswith("*Rule of the page"):
            body.append(f"<div class=rule>{md_inline(text.strip('*'))}</div>")
        elif text.startswith("*") and "CHANGELOG" in text:
            body.append(f"<p class=sub>{md_inline(text.strip('*'))}</p>")
        else:
            body.append(f"<p>{md_inline(text)}</p>")

    title_seen = False
    for raw in lines:
        line = raw.rstrip()
        if line.startswith("# ") and not title_seen:
            title_seen = True
            continue                    # rendered in the header block below
        if not line.strip():
            close_list()
            flush_paragraph()
        elif line.startswith("## "):
            close_list()
            flush_paragraph()
            body.append(f"<h2>{md_inline(line[3:])}</h2>")
        elif line.startswith("- ") or re.match(r"\d+\. ", line):
            flush_paragraph()
            kind = "ul" if line.startswith("- ") else "ol"
            if list_kind != kind:
                close_list()
                body.append(f"<{kind}>")
                list_kind = kind
            else:
                flush_item()
            item.append(re.sub(r"^(?:- |\d+\. )", "", line))
        elif line.startswith("---"):
            close_list()
            flush_paragraph()
        elif item and raw.startswith("  "):
            item.append(line.strip())
        else:
            close_list()
            paragraph.append(line.strip())
    close_list()
    flush_paragraph()

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Roadmap — DCS Sortie Starter</title>
<style>{STYLE}</style>
</head>
<body><div class="aband"><b>DCS Sortie Starter · v{_ver()} · Roadmap</b><span>SORTIE STARTER / ROADMAP</span></div><div class="wrap">
<h1>DCS <span>Sortie Starter</span> — Roadmap</h1>
{''.join(body)}
</div></body></html>
"""


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) from {SRC.name}")
