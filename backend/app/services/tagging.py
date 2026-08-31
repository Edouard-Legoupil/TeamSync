"""Tag helpers shared by the processing pipeline and the action-item API."""

from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Tag
from app.models.enums import TagType

VALID_TAG_TYPES = {t.value for t in TagType}

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def normalize_tag_key(text: str) -> str:
    return _NORMALIZE_RE.sub(" ", (text or "").lower()).strip()


def upsert_tag(
    db: Session, name: str, type_: str = TagType.THEMATIC.value
) -> Optional[Tag]:
    """Return an existing tag (case-insensitive) or create it. First write wins
    on ``type``; later upserts of the same name keep the existing type."""
    name = (name or "").strip()
    if not name:
        return None
    existing = db.query(Tag).filter(func.lower(Tag.name) == name.lower()).first()
    if existing:
        return existing
    tag = Tag(
        name=name,
        type=type_ if type_ in VALID_TAG_TYPES else TagType.THEMATIC.value,
    )
    db.add(tag)
    db.flush()
    return tag


def parse_action_item_tags(value: Any) -> dict[str, list[dict[str, str]]]:
    """Map a normalized task description to its list of ``{name, type}`` specs.

    Accepts either ``{"task": ..., "tags": [{"name", "type"}, ...]}`` objects or
    plain string tags.
    """
    result: dict[str, list[dict[str, str]]] = {}
    if not isinstance(value, list):
        return result
    for entry in value:
        if not isinstance(entry, dict):
            continue
        task = str(entry.get("task", "") or "").strip()
        raw_tags = entry.get("tags")
        if not task or not isinstance(raw_tags, list):
            continue
        specs: list[dict[str, str]] = []
        for item in raw_tags:
            if isinstance(item, str):
                name = item.strip()
                if name:
                    specs.append({"name": name, "type": TagType.THEMATIC.value})
            elif isinstance(item, dict):
                name = str(item.get("name", "") or "").strip()
                if name:
                    specs.append(
                        {
                            "name": name,
                            "type": str(item.get("type", TagType.THEMATIC.value)),
                        }
                    )
        if specs:
            result[normalize_tag_key(task)] = specs
    return result
