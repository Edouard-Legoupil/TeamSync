"""Full-text search across meeting Markdown content."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import get_accessible_team_ids, get_current_user
from app.database import get_db
from app.models import Meeting, User
from app.schemas import SearchResult

router = APIRouter(tags=["search"])


def _snippet(text: str | None, query: str, radius: int = 120) -> str:
    if not text:
        return ""
    idx = text.lower().find(query.lower())
    if idx == -1:
        return text[:radius].strip()
    start = max(0, idx - radius // 2)
    end = min(len(text), idx + len(query) + radius // 2)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return (prefix + text[start:end].strip() + suffix).strip()


@router.get("/api/search", response_model=list[SearchResult])
def search(
    q: str = Query(..., min_length=2),
    team_id: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    accessible = get_accessible_team_ids(db, user)
    if not accessible:
        return []

    scope = accessible
    if team_id:
        if team_id not in accessible:
            raise HTTPException(status_code=403, detail="Access denied to this team")
        scope = {team_id}

    pattern = f"%{q}%"
    meetings = (
        db.query(Meeting)
        .options(joinedload(Meeting.team))
        .filter(
            Meeting.team_id.in_(scope),
            or_(
                Meeting.title.ilike(pattern),
                Meeting.minutes_markdown.ilike(pattern),
                Meeting.action_items_markdown.ilike(pattern),
                Meeting.next_agenda_markdown.ilike(pattern),
            ),
        )
        .order_by(Meeting.date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    results: list[SearchResult] = []
    for meeting in meetings:
        snippet = (
            _snippet(meeting.minutes_markdown, q)
            or _snippet(meeting.action_items_markdown, q)
            or _snippet(meeting.next_agenda_markdown, q)
            or meeting.title
        )
        results.append(
            SearchResult(
                meeting_id=meeting.id,
                title=meeting.title,
                date=meeting.date,
                status=meeting.status,
                team_name=meeting.team.name if meeting.team else "",
                snippet=snippet,
            )
        )
    return results
