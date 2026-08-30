"""Shared helpers for serializing action items across route modules."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import case

from app.config import settings
from app.models import ActionItem, Meeting
from app.schemas import ActionItemOut, MeetingDetailOut

PRIORITY_ORDER = case(
    (ActionItem.priority == "HIGH", 0),
    (ActionItem.priority == "MEDIUM", 1),
    (ActionItem.priority == "LOW", 2),
    else_=3,
)

DUE_SOON_DAYS = 3


def today_in_app_tz() -> date:
    """Today's date in the configured organisation timezone (default UTC)."""
    try:
        return datetime.now(ZoneInfo(settings.APP_TIMEZONE)).date()
    except Exception:
        return datetime.utcnow().date()


def _due_flags(item: ActionItem) -> tuple[bool, bool]:
    if item.status == "DONE" or not item.due_date:
        return False, False
    delta = (item.due_date - today_in_app_tz()).days
    overdue = delta < 0
    due_soon = not overdue and delta <= DUE_SOON_DAYS
    return overdue, due_soon


def action_item_out(item: ActionItem) -> ActionItemOut:
    assignee = item.assignee
    overdue, due_soon = _due_flags(item)
    duplicate = item.duplicate_of
    return ActionItemOut(
        id=item.id,
        meeting_id=item.meeting_id,
        description=item.description,
        assignee_id=item.assignee_id,
        assignee_name=(assignee.full_name or assignee.email) if assignee else None,
        due_date=item.due_date,
        priority=item.priority,
        status=item.status,
        source_markdown=item.source_markdown,
        overdue=overdue,
        due_soon=due_soon,
        duplicate_of_id=item.duplicate_of_id,
        duplicate_of_title=duplicate.description if duplicate else None,
        duplicate_meeting_id=duplicate.meeting_id if duplicate else None,
        duplicate_meeting_title=(
            duplicate.meeting.title if duplicate and duplicate.meeting else None
        ),
    )


def meeting_confidence(meeting: Meeting) -> Optional[float]:
    """Read the AI confidence score stored in ``ai_metadata`` (if any)."""
    meta = meeting.ai_metadata or {}
    conf = meta.get("confidence")
    if conf is None:
        return None
    try:
        return float(conf)
    except (TypeError, ValueError):
        return None


def meeting_detail_out(meeting: Meeting) -> MeetingDetailOut:
    return MeetingDetailOut(
        id=meeting.id,
        title=meeting.title,
        date=meeting.date,
        team_id=meeting.team_id,
        organizer_id=meeting.organizer_id,
        status=meeting.status,
        series_id=meeting.series_id,
        minutes_markdown=meeting.minutes_markdown,
        action_items_markdown=meeting.action_items_markdown,
        next_agenda_markdown=meeting.next_agenda_markdown,
        confidence=meeting_confidence(meeting),
    )
