#!/usr/bin/env python3
"""Build the browser User Guide from the same source as the offline PDF."""
from html import escape
from pathlib import Path
import re
from struct import unpack

from build_sources_html import _ver
from guide_source import blocks, heading_id

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "docs" / "USER_GUIDE.md"
OUTPUT = ROOT / "docs" / "user-guide.html"

INLINE = re.compile(
    r"`(?P<code>[^`]+)`|\[(?P<link>[^\]]+)\]\((?P<href>[^\s)]+)\)|"
    r"\*\*(?P<strong>[^*]+)\*\*|\*(?P<em>[^*]+)\*"
)
SAFE_LINK = re.compile(r"(?:https?://[^\s]+|#[a-z0-9][a-z0-9-]*)")
PILOT_TASKS = (
    "install-a-miz-mission",
    "practice-a-drill-in-fly-now",
    "find-a-mission-in-the-library",
    "install-the-first-flight-campaign",
    "build-a-custom-mission",
    "use-briefings-and-kneeboards",
    "save-and-share-missions",
    "fix-common-problems",
)
APP_LINKS = {
    "practice-a-drill-in-fly-now": ("Open Fly Now", "/?v=quick"),
    "find-a-mission-in-the-library": ("Open Library", "/?v=library"),
    "install-the-first-flight-campaign": ("Open Train", "/?v=train"),
    "build-a-custom-mission": ("Open Builder", "/?v=builder"),
}


def inline(text, references):
    parts = []
    pos = 0
    for mark in INLINE.finditer(text):
        parts.append(escape(text[pos:mark.start()]))
        if href := mark["href"]:
            if SAFE_LINK.fullmatch(href):
                if href.startswith("#"):
                    references.add(href[1:])
                parts.append(f'<a href="{escape(href)}">{escape(mark["link"])}</a>')
            else:
                parts.append(escape(mark[0]))
        else:
            tag = mark.lastgroup
            parts.append(f"<{tag}>{escape(mark[tag])}</{tag}>")
        pos = mark.end()
    parts.append(escape(text[pos:]))
    return "".join(parts)


def table(rows, references):
    headers = "".join(f'<th scope="col">{inline(cell, references)}</th>' for cell in rows[0])
    body = []
    for row in rows[1:]:
        cells = "".join(f"<td>{inline(cell, references)}</td>" for cell in row)
        body.append(f"<tr>{cells}</tr>")
    return (
        '<div class="guide-table" tabindex="0" role="region" aria-label="Reference table">'
        f"<table><thead><tr>{headers}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def build():
    version = _ver()
    used = {"guide-content", "top"}
    references = set()
    topics, chapters, body = {}, [], []
    list_tag = None
    action = None

    for kind, value in blocks(SOURCE):
        if kind == "item":
            number, text = value
            tag = "ol" if number else "ul"
            if tag != list_tag:
                if list_tag:
                    body.append(f"</{list_tag}>")
                start = f' start="{number}"' if number and number != "1" else ""
                body.append(f"<{tag}{start}>")
                list_tag = tag
            body.append(f"<li>{inline(text, references)}</li>")
            continue

        if list_tag:
            body.append(f"</{list_tag}>")
            list_tag = None
        if kind == "heading":
            level, label = value
            if level == 1:
                continue
            key = heading_id(label, used)
            topics[key] = inline(label, references)
            if level == 2 and key != "start-here":
                chapters.append(key)
            body.append(
                f'<h{level} id="{key}" tabindex="-1"><a class="heading-link" href="#{key}">'
                f'{topics[key]}<span aria-hidden="true"> #</span></a></h{level}>'
            )
            action = APP_LINKS.get(key)
        elif kind == "paragraph":
            body.append(f"<p>{inline(value, references)}</p>")
            if action:
                label, href = action
                body.append(f'<p class="task-link"><a href="{href}">{label} →</a></p>')
                action = None
        elif kind == "table":
            body.append(table(value, references))
        elif kind == "code":
            code = escape("\n".join(value))
            body.append(f'<pre tabindex="0"><code>{code}</code></pre>')
        elif kind == "image":
            name, caption = value
            path = SOURCE.parent / "img" / name
            with path.open("rb") as screenshot:
                header = screenshot.read(24)
            if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError(f"Invalid guide screenshot: {name}")
            width, height = unpack(">II", header[16:24])
            url = f"/guide/images/{name}?v={version}"
            body.append(
                f'<figure><a href="{url}"><img src="{url}" loading="lazy" decoding="async" '
                f'width="{width}" height="{height}" alt="{escape(caption)}"></a>'
                f'<figcaption>{escape(caption)}</figcaption></figure>'
            )

    if list_tag:
        body.append(f"</{list_tag}>")
    missing = (references | set(PILOT_TASKS)) - topics.keys()
    if missing:
        raise ValueError(f"Unknown guide headings: {', '.join(sorted(missing))}")

    def links(keys):
        return "\n".join(f'<li><a href="#{key}">{topics[key]}</a></li>' for key in keys)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>User Guide · DCS Sortie Starter</title>
<meta name="description" content="Install a DCS mission, start First Flight, build a sortie and fix common problems.">
<link rel="stylesheet" href="/assets/user-guide.css?v={version}">
</head>
<body id="top">
<a class="skip-link" href="#guide-content">Skip to guide</a>
<header class="guide-bar">
  <a href="/">DCS <strong>Sortie Starter</strong></a>
  <span class="guide-version">v{version}</span>
  <a href="/api/guide" class="offline-link">Download PDF</a>
</header>
<div class="guide-layout">
  <nav class="guide-topics" aria-label="Guide topics">
    <p class="nav-title">Jump to a task</p>
    <ul>{links(PILOT_TASKS)}</ul>
    <details>
      <summary>All chapters</summary>
      <ul>{links(chapters)}</ul>
    </details>
  </nav>
  <main id="guide-content" tabindex="-1">
    <h1>User Guide</h1>
    {"".join(body)}
    <p class="back-top"><a href="#top">Back to top</a></p>
  </main>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    OUTPUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUTPUT}")
