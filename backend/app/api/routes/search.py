"""Search across meetings, action items, and follow-ups (canonical transcript)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.auth.dependencies import get_accessible_team_ids, get_current_user
from app.database import get_db
from app.models import ActionItem, Meeting, MeetingFollowUp, User
from app.schemas import SearchResult

router = APIRouter(tags=["search"])


def _snippet(text: str | None, query: str, radius: int = 120) -> str:
    if not text:
        return ""
    q = (query or "").strip()
    if not q:
        return text[:radius].strip()
    idx = text.lower().find(q.lower())
    if idx == -1:
        return text[:radius].strip()
    start = max(0, idx - radius // 2)
    end = min(len(text), idx + len(q) + radius // 2)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return (prefix + text[start:end].strip() + suffix).strip()


@router.get("/api/search", response_model=list[SearchResult])
def search(
    q: str = Query("", max_length=200),
    team_id: str | None = None,
    tag: str | None = None,
    speaker: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    kind: str | None = None,
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

    query = (q or "").strip()
    tag_filter = (tag or "").strip()
    speaker_filter = (speaker or "").strip()
    if not (query or tag_filter or speaker_filter):
        raise HTTPException(
            status_code=400, detail="Provide a query, tag, or speaker filter"
        )

    if kind not in (None, "meeting", "action_item", "follow_up"):
        raise HTTPException(status_code=422, detail="Invalid search kind")

    pattern = f"%{query}%" if query else None
    results: list[SearchResult] = []

    # --- Meetings ---
    if kind in (None, "meeting"):
        filters = [Meeting.team_id.in_(scope)]
        if pattern:
            filters.append(
                or_(
                    Meeting.title.ilike(pattern),
                    Meeting.minutes_markdown.ilike(pattern),
                    Meeting.raw_transcript.ilike(pattern),
                    Meeting.next_agenda_markdown.ilike(pattern),
                )
            )
        if date_from:
            filters.append(func.date(Meeting.date) >= date_from)
        if date_to:
            filters.append(func.date(Meeting.date) <= date_to)
        meetings = (
            db.query(Meeting)
            .options(joinedload(Meeting.team))
            .filter(*filters)
            .order_by(Meeting.date.desc())
            .all()
        )
        for m in meetings:
            snippet = (
                _snippet(m.minutes_markdown, query)
                or _snippet(m.raw_transcript, query)
                or m.title
            )
            results.append(
                SearchResult(
                    kind="meeting",
                    meeting_id=m.id,
                    title=m.title,
                    date=m.date,
                    status=m.status,
                    team_name=m.team.name if m.team else "",
                    snippet=snippet,
                )
            )

    # --- Action items ---
    if kind in (None, "action_item"):
        filters = [Meeting.team_id.in_(scope)]
        if pattern:
            filters.append(
                or_(
                    ActionItem.description.ilike(pattern),
                    ActionItem.source_speaker.ilike(pattern),
                    ActionItem.requester.ilike(pattern),
                    ActionItem.completion_notes.ilike(pattern),
                )
            )
        if date_from:
            filters.append(func.date(Meeting.date) >= date_from)
        if date_to:
            filters.append(func.date(Meeting.date) <= date_to)
        rows = (
            db.query(ActionItem, Meeting)
            .options(selectinload(ActionItem.tags), joinedload(Meeting.team))
            .join(Meeting, ActionItem.meeting_id == Meeting.id)
            .filter(*filters)
            .all()
        )
        tag_lower = tag_filter.lower()
        speaker_lower = speaker_filter.lower()
        for item, m in rows:
            if tag_lower and not any(t.name.lower() == tag_lower for t in item.tags):
                continue
            if speaker_lower and (item.source_speaker or "").lower() != speaker_lower:
                continue
            results.append(
                SearchResult(
                    kind="action_item",
                    meeting_id=m.id,
                    title=m.title,
                    date=m.date,
                    team_name=m.team.name if m.team else "",
                    snippet=_snippet(item.description, query),
                    speaker=item.source_speaker,
                    action_item_id=item.id,
                )
            )

    # --- Follow-ups ---
    if kind in (None, "follow_up"):
        filters = [Meeting.team_id.in_(scope)]
        if pattern:
            filters.append(
                or_(
                    MeetingFollowUp.title.ilike(pattern),
                    MeetingFollowUp.issue.ilike(pattern),
                    MeetingFollowUp.rationale.ilike(pattern),
                )
            )
        if date_from:
            filters.append(func.date(Meeting.date) >= date_from)
        if date_to:
            filters.append(func.date(Meeting.date) <= date_to)
        rows = (
            db.query(MeetingFollowUp, Meeting)
            .options(joinedload(Meeting.team))
            .join(Meeting, MeetingFollowUp.meeting_id == Meeting.id)
            .filter(*filters)
            .all()
        )
        for fu, m in rows:
            results.append(
                SearchResult(
                    kind="follow_up",
                    meeting_id=m.id,
                    title=m.title,
                    date=m.date,
                    team_name=m.team.name if m.team else "",
                    snippet=_snippet(fu.title, query),
                )
            )

    results.sort(key=lambda r: r.date, reverse=True)
    return results[offset : offset + limit]
