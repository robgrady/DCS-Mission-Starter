#!/usr/bin/env python3
"""Render docs/SOURCES.md into the styled docs/sources.html served at
/api/sources.

Same one-source-of-truth contract as scripts/build_roadmap_html.py: the
Markdown is the document, the HTML is a build artifact, and
`scripts/artifacts.py` blocks a release where the two have drifted.

    python3 scripts/build_sources_html.py

Handles tables, which the roadmap builder does not need — most of this page's
substance is tabular (data pack -> method, component -> license).
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
SRC = ROOT / "docs" / "SOURCES.md"
OUT = ROOT / "docs" / "sources.html"

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
  .wrap{max-width:900px;margin:0 auto;padding:40px 24px 90px}
  a{color:var(--accent);text-decoration:underline}
  a:hover{text-decoration:none}
  h1{font-family:var(--banner);font-weight:400;font-size:44px;line-height:1;margin:0 0 4px;letter-spacing:.01em;color:var(--navy)}
  h1 span{color:var(--accent)}
  .sub{font-family:var(--sans);color:var(--dim);margin:0 0 8px;font-size:14px}
  .north{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--teal);
    border-radius:10px;padding:14px 18px;margin:22px 0 30px;font-size:15px}
  h2{font-family:var(--disp);font-weight:800;font-size:18px;text-transform:uppercase;letter-spacing:.02em;color:var(--text);border-bottom:1px solid var(--line);padding-bottom:4px;
    display:flex;align-items:center;gap:10px;margin:38px 0 14px}
  h2::after{content:"";flex:1;height:1px;background:var(--line)}
  h3{font-size:16px;margin:24px 0 8px}
  ul{margin:0 0 14px;padding-left:0;list-style:none}
  li{background:var(--panel);border:1px solid var(--line);border-radius:10px;
     padding:11px 15px;margin-bottom:8px;font-size:14px;color:var(--dim)}
  li b{color:var(--text)}
  p{font-size:14.5px;color:var(--dim)}
  code{background:#EFEADF;border:1px solid var(--line);border-radius:4px;
       padding:1px 5px;font-size:13px;color:var(--text)}
  table{width:100%;border-collapse:collapse;background:var(--panel);
        border:1px solid var(--line);border-radius:10px;overflow:hidden;
        margin:0 0 18px;font-size:13.5px}
  th{background:#EFEADF;text-align:left;padding:9px 12px;color:var(--text);
     font-size:12px;text-transform:uppercase;letter-spacing:.07em}
  td{padding:9px 12px;border-top:1px solid var(--line);color:var(--dim);
     vertical-align:top}
  td b{color:var(--text)}
  .rule{margin-top:40px;border-top:1px solid var(--line);padding-top:16px;
        font-size:12.5px;color:var(--dim);font-style:italic}
"""


def md_inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def build() -> str:
    lines = SRC.read_text().splitlines()
    body, in_list, in_table = [], False, False
    title_seen = False

    def close():
        nonlocal in_list, in_table
        if in_list:
            body.append("</ul>")
            in_list = False
        if in_table:
            body.append("</table>")
            in_table = False

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        nxt = lines[i + 1].rstrip() if i + 1 < len(lines) else ""

        if line.startswith("# ") and not title_seen:
            title_seen = True
        elif line.startswith("## "):
            close()
            body.append(f"<h2>{md_inline(line[3:])}</h2>")
        elif line.startswith("### "):
            close()
            body.append(f"<h3>{md_inline(line[4:])}</h3>")
        # a table: a pipe row whose next row is the |---| separator
        elif line.startswith("|") and re.match(r"^\|[\s:|-]+\|$", nxt):
            close()
            in_table = True
            body.append("<table><tr>"
                        + "".join(f"<th>{md_inline(c)}</th>" for c in _cells(line))
                        + "</tr>")
            i += 1
        elif in_table and line.startswith("|"):
            body.append("<tr>" + "".join(f"<td>{md_inline(c)}</td>"
                                         for c in _cells(line)) + "</tr>")
        elif line.startswith("- "):
            if in_table:
                close()
            if not in_list:
                body.append("<ul>")
                in_list = True
            body.append(f"<li>{md_inline(line[2:])}</li>")
        elif line.startswith("---"):
            close()
        elif line.startswith("**Rule of the page:**"):
            close()
            body.append(f"<div class=rule>{md_inline(line)}</div>")
        elif line.startswith("*Where the facts"):
            body.append(f"<p class=sub>{md_inline(line.strip('*'))}</p>")
        elif line.strip():
            if in_list:                 # continuation of the previous bullet
                body[-1] = body[-1][:-5] + " " + md_inline(line.strip()) + "</li>"
            elif in_table:
                close()
                body.append(f"<p>{md_inline(line)}</p>")
            else:
                body.append(f"<p>{md_inline(line)}</p>")
        else:
            if in_table:
                close()
        i += 1
    close()

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sources — DCS Sortie Starter</title>
<style>{STYLE}</style>
</head>
<body><div class="aband"><b>DCS Sortie Starter · v{_ver()} · Sources</b><span>SORTIE STARTER / SOURCES</span></div><div class="wrap">
<h1>DCS <span>Sortie Starter</span> — Sources</h1>
{''.join(body)}
</div></body></html>
"""


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) from {SRC.name}")
