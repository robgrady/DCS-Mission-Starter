#!/usr/bin/env python3
"""Render docs/PACK_FORMAT.md into the styled docs/packformat.html served at
/api/packformat.

Same contract as build_sources_html.py and build_roadmap_html.py: the
Markdown is normative, the HTML is a build artifact, and scripts/artifacts.py
refuses a release where the two have drifted.

    python3 scripts/build_packformat_html.py

Reconstructed 2026-10-03: the original died with the build environment that
produced 1.104–1.105 (see the CHANGELOG note above 1.105.0). The page it
made is the reference; this one keeps its shape — contents list, anchored
sections, fenced code, tables — and joins paragraph lines instead of
emitting one <p> per source line.
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_sources_html import STYLE, md_inline, _cells, _ver  # noqa: E402

SRC = ROOT / "docs" / "PACK_FORMAT.md"
OUT = ROOT / "docs" / "packformat.html"

EXTRA_STYLE = """
  .toc{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 18px;margin:18px 0 30px;
    font-family:var(--sans);font-size:14px;display:flex;flex-direction:column;gap:4px}
  .toc b{font-family:var(--disp);text-transform:uppercase;letter-spacing:.04em;font-size:13px;color:var(--dim);margin-bottom:4px}
  .toc a{text-decoration:none}
  .toc a:hover{text-decoration:underline}
  pre{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px;overflow:auto;
    font-family:var(--mono);font-size:13px;line-height:1.5}
  code{font-family:var(--mono);font-size:.92em}
  blockquote{margin:14px 0;padding:8px 16px;border-left:3px solid var(--amber);background:var(--panel);
    font-family:var(--sans);font-size:14px;color:var(--dim)}
  ol{padding-left:22px}
  h3{font-family:var(--disp);font-weight:700;font-size:16px;text-transform:uppercase;letter-spacing:.02em;margin:26px 0 8px}
"""


def slug(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s


def build() -> str:
    lines = SRC.read_text().splitlines()
    body, toc = [], []
    para, in_ul, in_ol, in_table, in_code, in_quote = [], False, False, False, False, False
    title_seen = False

    def flush_para():
        nonlocal para
        if para:
            body.append(f"<p>{md_inline(' '.join(para))}</p>")
            para = []

    def close():
        nonlocal in_ul, in_ol, in_table, in_quote
        flush_para()
        if in_ul:
            body.append("</ul>"); in_ul = False
        if in_ol:
            body.append("</ol>"); in_ol = False
        if in_table:
            body.append("</table>"); in_table = False
        if in_quote:
            body.append("</blockquote>"); in_quote = False

    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        nxt = lines[i + 1].rstrip() if i + 1 < len(lines) else ""

        if in_code:
            if line.startswith("```"):
                body.append("</code></pre>"); in_code = False
            else:
                body.append(html.escape(line) + "\n")
            i += 1
            continue
        if line.startswith("```"):
            close()
            body.append("<pre><code>"); in_code = True
        elif line.startswith("# ") and not title_seen:
            title_seen = True
        elif line.startswith("## "):
            close()
            text = md_inline(line[3:]); sid = slug(line[3:])
            toc.append(f'<a href="#{sid}">{text}</a>')
            body.append(f'<h2 id="{sid}">{text}</h2>')
        elif line.startswith("### "):
            close()
            body.append(f'<h3 id="{slug(line[4:])}">{md_inline(line[4:])}</h3>')
        elif line.startswith("|") and re.match(r"^\|[\s:|-]+\|$", nxt):
            close(); in_table = True
            body.append("<table><tr>" + "".join(f"<th>{md_inline(c)}</th>" for c in _cells(line)) + "</tr>")
            i += 1
        elif in_table and line.startswith("|"):
            body.append("<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in _cells(line)) + "</tr>")
        elif line.startswith("> "):
            flush_para()
            if not in_quote:
                body.append("<blockquote>"); in_quote = True
            body.append(f"<p>{md_inline(line[2:])}</p>")
        elif re.match(r"^\s*[-*] ", line):
            flush_para()
            if in_ol or in_table or in_quote:
                close()
            if not in_ul:
                body.append("<ul>"); in_ul = True
            item = re.sub(r"^\s*[-*] ", "", line)
            body.append(f"<li>{md_inline(item)}</li>")
        elif re.match(r"^\s*\d+\. ", line):
            flush_para()
            if in_ul or in_table or in_quote:
                close()
            if not in_ol:
                body.append("<ol>"); in_ol = True
            item = re.sub(r"^\s*\d+\. ", "", line)
            body.append(f"<li>{md_inline(item)}</li>")
        elif line.startswith("---"):
            close()
        elif line.strip():
            if in_ul or in_ol:
                body[-1] = body[-1][:-5] + " " + md_inline(line.strip()) + "</li>"
            elif in_quote:
                body[-1] = body[-1][:-4] + " " + md_inline(line.strip()) + "</p>"
            else:
                if in_table:
                    close()
                para.append(line.strip())
        else:
            close()
        i += 1
    close()

    sub = ("The specification for publishable content. Anyone may build a pack; "
           "this is what one is.")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pack format — DCS Sortie Starter</title>
<meta name="description" content="The normative specification for Sortie Starter content packs: mission, course, reference and theater packs, and how to author each.">
<style>{STYLE}{EXTRA_STYLE}</style>
</head>
<body><div class="aband"><b>DCS Sortie Starter · v{_ver()} · Pack format</b><span>SORTIE STARTER / PACK FORMAT</span></div><div class="wrap">
<h1>DCS <span>Sortie Starter</span> — Pack format</h1>
<p class="sub">{sub}</p>
<div class="toc"><b>Contents</b>{''.join(toc)}</div>
{''.join(body)}
</div></body></html>
"""


if __name__ == "__main__":
    OUT.write_text(build())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) from {SRC.name}")
