"""Loader for the human-editable Markdown content in ``content/``.

File format (deliberately tiny):

    # Title                 <- ignored
    Any prose before the first section is ignored.

    ## section-name         <- starts a record / section
    key: value              <- metadata line (only before the first bullet)
    - first item            <- list item; indented lines continue the item
    - second item

Files without ``##`` headings are treated as one anonymous section, so a
plain bullet list works for simple content (compliments, date ideas, ...).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from utils.logging import get_logger

logger = get_logger(__name__)

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"
_META_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")


@dataclass
class Record:
    name: str
    meta: dict[str, str] = field(default_factory=dict)
    items: list[str] = field(default_factory=list)


def _parse(text: str) -> dict[str, Record]:
    records: dict[str, Record] = {}
    current: Record | None = None
    last_item_open = False

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current = Record(name=line[3:].strip())
            records[current.name] = current
            last_item_open = False
            continue
        if line.startswith("#"):
            continue  # title / sub-headings are documentation only
        if not line.strip():
            last_item_open = False
            continue
        if current is None:
            if line.lstrip().startswith("- "):
                current = Record(name="")
                records[""] = current
            else:
                continue
        stripped = line.lstrip()
        if stripped.startswith("- "):
            current.items.append(stripped[2:].strip())
            last_item_open = True
        elif raw[:1] in (" ", "\t") and last_item_open and current.items:
            current.items[-1] += " " + stripped
        elif not current.items and (m := _META_RE.match(stripped)):
            current.meta[m.group(1).lower()] = m.group(2).strip()
    return records


@lru_cache(maxsize=None)
def load_records(relative_path: str) -> dict[str, Record]:
    """Parse ``content/<relative_path>`` into named records (cached)."""
    path = CONTENT_DIR / relative_path
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("content file missing: %s", path)
        return {}
    return _parse(text)


def load_list(relative_path: str, section: str = "") -> list[str]:
    """Return the bullet items of one section (or the whole anonymous file)."""
    records = load_records(relative_path)
    if section in records:
        return list(records[section].items)
    if not section and len(records) == 1:
        return list(next(iter(records.values())).items)
    return []


def load_pairs(relative_path: str, section: str = "", sep: str = "|") -> list[tuple[str, ...]]:
    """Items split on ``sep`` — e.g. ``A | B`` for would-you-rather pairs."""
    return [tuple(part.strip() for part in item.split(sep)) for item in load_list(relative_path, section)]


@lru_cache(maxsize=None)
def load_text(relative_path: str) -> str:
    """Raw prose of a content file with the title and indented/blank documentation
    lines before the first blank-separated body removed.

    Everything after the first line starting with ``Placeholders:`` plus its
    following blank line is returned; if there is no such marker, the whole
    file minus its ``#`` title is returned.
    """
    try:
        text = (CONTENT_DIR / relative_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.error("content file missing: %s", relative_path)
        return ""
    lines = [l for l in text.splitlines() if not l.startswith("#")]
    body = "\n".join(lines).strip()
    marker = body.find("Placeholders:")
    if marker != -1:
        _, _, body = body[marker:].partition("\n\n")
    return body.strip()


def reload_content() -> None:
    """Drop the cache so edited Markdown is picked up (used by the owner reload)."""
    load_records.cache_clear()
    load_text.cache_clear()
