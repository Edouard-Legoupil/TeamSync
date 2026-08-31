"""URL slug generation for teams (stable permalinks)."""

from __future__ import annotations

import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Team

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    """Turn a name into a URL-safe slug."""
    value = _SLUG_RE.sub("-", (name or "").strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "team"


def unique_slug(db: Session, name: str, exclude_team_id: Optional[str] = None) -> str:
    """Return a slug for ``name`` that is unique among existing teams."""
    base = slugify(name)
    candidate = base
    n = 2
    while True:
        query = db.query(Team).filter(Team.slug == candidate)
        if exclude_team_id:
            query = query.filter(Team.id != exclude_team_id)
        if query.first() is None:
            return candidate
        candidate = f"{base}-{n}"
        n += 1
