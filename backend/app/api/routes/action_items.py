"""Action item endpoints: update (with Markdown sync), mine, and team listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import nulls_last
from sqlalchemy.orm import Session, joinedload

from app.api.helpers import PRIORITY_ORDER, action_item_out
from app.auth.dependencies import (
    get_accessible_team_ids,
    get_current_user,
    require_team_access,
)
from app.database import get_db
from app.models import ActionItem, Meeting, Team, User
from app.models.enums import ActionItemStatus
from app.schemas import ActionItemOut, ActionItemUpdate, ActionItemWithContext
from app.services import audit
from app.services.audit import ACTION_ITEM_UPDATED
from app.services.markdown_sync import sync_action_item_to_markdown

router = APIRouter(prefix="/api/action-items", tags=["action-items"])

_VALID_STATUSES = {
    ActionItemStatus.OPEN.value,
    ActionItemStatus.IN_PROGRESS.value,
    ActionItemStatus.DONE.value,
}

_OPEN_STATUSES = [ActionItemStatus.OPEN.value, ActionItemStatus.IN_PROGRESS.value]


@router.patch("/{item_id}", response_model=ActionItemOut)
def update_action_item(
    item_id: str,
    payload: ActionItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(ActionItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Action item not found")

    meeting = db.get(Meeting, item.meeting_id)
    require_team_access(db, user, meeting.team_id)

    fields = payload.model_fields_set
    if "status" in fields and payload.status is not None:
        if payload.status not in _VALID_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid action item status")
        item.status = payload.status
    if "assignee_id" in fields:
        item.assignee_id = payload.assignee_id  # may be None to unassign
    if "due_date" in fields:
        item.due_date = payload.due_date  # may be None to clear

    sync_action_item_to_markdown(db, meeting, item)
    audit.log_audit(
        db,
        action=ACTION_ITEM_UPDATED,
        entity_type="action_item",
        entity_id=item.id,
        actor_id=user.id,
        team_id=meeting.team_id,
        meeting_id=meeting.id,
        detail=",".join(sorted(fields)),
    )
    db.commit()
    db.refresh(item)
    return action_item_out(item)


@router.get("/mine", response_model=list[ActionItemWithContext])
def my_action_items(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    accessible = get_accessible_team_ids(db, user)
    if not accessible:
        return []

    items = (
        db.query(ActionItem)
        .options(
            joinedload(ActionItem.assignee),
            joinedload(ActionItem.meeting).joinedload(Meeting.team),
            joinedload(ActionItem.duplicate_of).joinedload(ActionItem.meeting),
        )
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(Meeting.team_id.in_(accessible), ActionItem.status.in_(_OPEN_STATUSES), ActionItem.duplicate_of_id.is_(None))
        .order_by(nulls_last(ActionItem.due_date), PRIORITY_ORDER)
        .offset(offset)
        .limit(limit)
        .all()
    )

    result: list[ActionItemWithContext] = []
    for item in items:
        base = action_item_out(item)
        meeting = item.meeting
        team = meeting.team if meeting else None
        result.append(
            ActionItemWithContext(
                **base.model_dump(),
                team_id=meeting.team_id if meeting else "",
                team_name=team.name if team else "",
                meeting_title=meeting.title if meeting else "",
            )
        )
    return result


@router.get("/team/{team_id}", response_model=list[ActionItemOut])
def team_action_items(
    team_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_team_access(db, user, team_id)
    items = (
        db.query(ActionItem)
        .options(
            joinedload(ActionItem.assignee),
            joinedload(ActionItem.duplicate_of).joinedload(ActionItem.meeting),
        )
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(Meeting.team_id == team_id, ActionItem.status.in_(_OPEN_STATUSES), ActionItem.duplicate_of_id.is_(None))
        .order_by(nulls_last(ActionItem.due_date), PRIORITY_ORDER)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [action_item_out(item) for item in items]
