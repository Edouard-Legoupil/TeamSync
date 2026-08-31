"""Executive analytics: cross-team aggregations and theme heatmap."""

from __future__ import annotations

from typing import Callable, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.helpers import today_in_app_tz
from app.auth.dependencies import get_accessible_team_ids, get_current_user
from app.database import get_db
from app.models import ActionItem, Meeting, MeetingFollowUp, User
from app.models.enums import ActionItemStatus
from app.schemas import AnalyticsOut, CountByKey

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

_OPEN_STATUSES = [ActionItemStatus.OPEN.value, ActionItemStatus.IN_PROGRESS.value]


def _group(
    items: list[ActionItem],
    key_fn: Callable[[ActionItem], str],
    label_fn: Callable[[ActionItem], str],
) -> list[CountByKey]:
    agg: dict[str, dict] = {}
    for item in items:
        key = key_fn(item)
        if key not in agg:
            agg[key] = {"label": label_fn(item), "count": 0}
        agg[key]["count"] += 1
    rows = [
        CountByKey(key=key, label=value["label"], count=value["count"])
        for key, value in agg.items()
    ]
    rows.sort(key=lambda r: (-r.count, r.label.lower()))
    return rows


def _group_tags(items: list[ActionItem], tag_type: str) -> list[CountByKey]:
    agg: dict[str, dict] = {}
    for item in items:
        for tag in item.tags:
            if tag.type == tag_type:
                if tag.id not in agg:
                    agg[tag.id] = {"label": tag.name, "count": 0}
                agg[tag.id]["count"] += 1
    rows = [
        CountByKey(key=key, label=value["label"], count=value["count"])
        for key, value in agg.items()
    ]
    rows.sort(key=lambda r: (-r.count, r.label.lower()))
    return rows


def _follow_up_types(db: Session, scope: set[str]) -> list[CountByKey]:
    rows = (
        db.query(MeetingFollowUp)
        .join(Meeting, MeetingFollowUp.meeting_id == Meeting.id)
        .filter(Meeting.team_id.in_(scope))
        .all()
    )
    agg: dict[str, int] = {}
    for fu in rows:
        agg[fu.follow_up_type] = agg.get(fu.follow_up_type, 0) + 1
    out = [
        CountByKey(key=key, label=key.replace("_", " "), count=value)
        for key, value in agg.items()
    ]
    out.sort(key=lambda r: (-r.count, r.label.lower()))
    return out


@router.get("", response_model=AnalyticsOut)
def analytics(
    team_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    accessible = get_accessible_team_ids(db, user)
    if not accessible:
        return AnalyticsOut()

    scope = accessible
    if team_id:
        if team_id not in accessible:
            raise HTTPException(status_code=403, detail="You do not have access to this team")
        scope = {team_id}

    statuses = _OPEN_STATUSES if not status else [status]

    items = (
        db.query(ActionItem)
        .options(
            joinedload(ActionItem.assignee),
            selectinload(ActionItem.tags),
            joinedload(ActionItem.meeting).joinedload(Meeting.team),
        )
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(
            Meeting.team_id.in_(scope),
            ActionItem.status.in_(statuses),
            ActionItem.duplicate_of_id.is_(None),
        )
        .all()
    )

    if assignee_id:
        items = [i for i in items if i.assignee_id == assignee_id]

    tag_lower = (tag or "").strip().lower()
    if tag_lower:
        items = [i for i in items if any(t.name.lower() == tag_lower for t in i.tags)]

    today = today_in_app_tz()
    overdue = [
        i
        for i in items
        if i.status != ActionItemStatus.DONE.value and i.due_date and i.due_date < today
    ]

    by_theme = _group_tags(items, "thematic")
    by_region = _group_tags(items, "geographic")

    return AnalyticsOut(
        open_count=len(items),
        overdue_count=len(overdue),
        by_team=_group(
            items,
            key_fn=lambda i: i.meeting.team_id,
            label_fn=lambda i: (i.meeting.team.name if i.meeting and i.meeting.team else ""),
        ),
        by_theme=by_theme,
        by_region=by_region,
        by_assignee=_group(
            items,
            key_fn=lambda i: i.assignee_id or "unassigned",
            label_fn=lambda i: (
                (i.assignee.full_name or i.assignee.email) if i.assignee else "Unassigned"
            ),
        ),
        top_themes=by_theme[:10],
        follow_up_types=_follow_up_types(db, scope),
    )
