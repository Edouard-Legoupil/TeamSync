"""Shared helpers for serializing action items across route modules."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import case
from sqlalchemy.orm import joinedload, selectinload

from app.config import settings
from app.models import ActionItem, Meeting, Tag
from app.schemas import (
    ActionItemOut,
    MeetingDetailOut,
    MeetingFollowUpOut,
    MeetingListRow,
    MeetingSummary,
    TagOut,
)

PRIORITY_ORDER = case(
    (ActionItem.priority == "HIGH", 0),
    (ActionItem.priority == "MEDIUM", 1),
    (ActionItem.priority == "LOW", 2),
    else_=3,
)

# Eager-load the identification context (team + series + meeting title) that
# ``action_item_out`` serializes onto every action item.
ACTION_ITEM_CONTEXT_LOAD = (
    joinedload(ActionItem.meeting).joinedload(Meeting.team),
    joinedload(ActionItem.meeting).joinedload(Meeting.series),
)

# Eager-load the action item's tags (many-to-many).
ACTION_ITEM_TAGS_LOAD = (selectinload(ActionItem.tags),)

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
    meeting = item.meeting
    team = meeting.team if meeting else None
    series = meeting.series if meeting else None
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
        team_id=meeting.team_id if meeting else "",
        team_name=team.name if team else "",
        series_id=meeting.series_id if meeting else None,
        series_name=series.name if series else None,
        meeting_title=meeting.title if meeting else "",
        tags=[TagOut(id=t.id, name=t.name, type=t.type) for t in item.tags],
        source_excerpt=item.source_excerpt,
        source_speaker=item.source_speaker,
        source_timestamp=item.source_timestamp,
        confidence=item.confidence,
        attribution_method=item.attribution_method,
        requester=item.requester,
        related_participants=item.related_participants,
        completion_notes=item.completion_notes,
        completion_links=item.completion_links,
        completion_follow_up=item.completion_follow_up,
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


def meeting_follow_up_out(fu) -> MeetingFollowUpOut:
    return MeetingFollowUpOut(
        id=fu.id,
        follow_up_type=fu.follow_up_type,
        title=fu.title,
        issue=fu.issue,
        participants=fu.participants,
        rationale=fu.rationale,
        status=fu.status,
        created_at=fu.created_at,
    )


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
        raw_transcript=meeting.raw_transcript or "",
        source_filename=meeting.source_filename,
        follow_ups=[meeting_follow_up_out(fu) for fu in meeting.follow_ups],
    )


def meeting_summary_out(meeting: Meeting) -> MeetingSummary:
    """Serialize a meeting summary with team/series identification."""
    team = meeting.team
    series = meeting.series
    return MeetingSummary(
        id=meeting.id,
        title=meeting.title,
        date=meeting.date,
        status=meeting.status,
        team_id=meeting.team_id,
        team_name=team.name if team else "",
        series_id=meeting.series_id,
        series_name=series.name if series else None,
    )


def meeting_list_row_out(meeting: Meeting) -> MeetingListRow:
    """Serialize a meeting list row with team/series identification."""
    team = meeting.team
    series = meeting.series
    return MeetingListRow(
        id=meeting.id,
        title=meeting.title,
        date=meeting.date,
        status=meeting.status,
        action_count=len(meeting.action_items),
        team_id=meeting.team_id,
        team_name=team.name if team else "",
        series_id=meeting.series_id,
        series_name=series.name if series else None,
    )
