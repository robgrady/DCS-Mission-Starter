"""Read the Markdown block syntax used by both User Guide formats."""
import re
from unicodedata import normalize

HEADING = re.compile(r"^(#{1,3}) +(.+)")
LIST_ITEM = re.compile(r"^(?:[-*] |(\d+)\. )(.+)")
IMAGE = re.compile(r"!\[([^]]+)\]\(img/([a-zA-Z0-9][a-zA-Z0-9_.-]*[.]png)\)")


def heading_id(text, used):
    plain = normalize("NFKD", text.replace("&", " and ")).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-") or "topic"
    key = base
    suffix = 1
    while key in used:
        key = f"{base}-{suffix}"
        suffix += 1
    used.add(key)
    return key


def blocks(source):
    rows = source.read_text(encoding="utf-8").splitlines()
    paragraph = []
    i = 0
    while i < len(rows):
        line = rows[i].strip()
        special = (not line or line.startswith(("|", "```", "![")) or
                   HEADING.match(line) or LIST_ITEM.match(line))
        if not special:
            paragraph.append(line)
            i += 1
            continue
        if paragraph:
            yield "paragraph", " ".join(paragraph)
            paragraph.clear()
        if not line:
            i += 1
        elif line.startswith("|"):
            table = []
            while i < len(rows) and rows[i].strip().startswith("|"):
                cells = [cell.strip() for cell in rows[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"[: -]+", cell) for cell in cells):
                    table.append(cells)
                i += 1
            if table:
                yield "table", table
        elif line.startswith("```"):
            i += 1
            code = []
            while i < len(rows) and not rows[i].strip().startswith("```"):
                code.append(rows[i])
                i += 1
            yield "code", code
            i += 1
        elif line.startswith("!["):
            image = IMAGE.fullmatch(line)
            if not image or not image[1].strip():
                raise ValueError(f"{source}:{i + 1}: use ![caption](img/name.png) with a caption")
            yield "image", (image[2], image[1].strip())
            i += 1
        elif heading := HEADING.match(line):
            yield "heading", (len(heading[1]), heading[2])
            i += 1
        else:
            item = LIST_ITEM.match(line)
            number, text = item.groups()
            i += 1
            while i < len(rows) and rows[i].startswith("   ") and rows[i].strip():
                text += " " + rows[i].strip()
                i += 1
            yield "item", (number, text)
    if paragraph:
        yield "paragraph", " ".join(paragraph)
