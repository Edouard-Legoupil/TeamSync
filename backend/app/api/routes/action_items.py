"""Action item endpoints: update (with Markdown sync), mine, and team listing."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import nulls_last
from sqlalchemy.orm import Session, joinedload

from app.api.helpers import (
    ACTION_ITEM_CONTEXT_LOAD,
    ACTION_ITEM_TAGS_LOAD,
    PRIORITY_ORDER,
    action_item_out,
)
from app.auth.dependencies import (
    MEETING_ROLE_CONTRIBUTOR,
    MEETING_ROLE_VIEWER,
    get_accessible_team_ids,
    get_current_user,
    get_meeting_role,
    require_team_access,
)
from app.database import get_db
from app.models import ActionItem, ActionItemComment, AuditLog, Meeting, User
from app.models.enums import ActionItemPriority, ActionItemStatus
from app.schemas import (
    ActionItemCommentCreate,
    ActionItemCommentOut,
    ActionItemHistoryEntry,
    ActionItemOut,
    ActionItemUpdate,
    ActionItemWithContext,
)
from app.services import audit
from app.services.audit import ACTION_ITEM_UPDATED
from app.services.markdown_sync import sync_action_item_to_markdown
from app.services.notifications import notify_mentions
from app.services.tagging import upsert_tag

router = APIRouter(prefix="/api/action-items", tags=["action-items"])

_VALID_STATUSES = {
    ActionItemStatus.OPEN.value,
    ActionItemStatus.IN_PROGRESS.value,
    ActionItemStatus.DONE.value,
}

_VALID_PRIORITIES = {
    ActionItemPriority.HIGH.value,
    ActionItemPriority.MEDIUM.value,
    ActionItemPriority.LOW.value,
}

_OPEN_STATUSES = [ActionItemStatus.OPEN.value, ActionItemStatus.IN_PROGRESS.value]


def _display_name(db: Session, user_id: str | None) -> str:
    if not user_id:
        return "Unassigned"
    user = db.get(User, user_id)
    return (user.full_name or user.email) if user else user_id


def _comment_out(comment: ActionItemComment) -> ActionItemCommentOut:
    return ActionItemCommentOut(
        id=comment.id,
        action_item_id=comment.action_item_id,
        author_id=comment.author_id,
        author_name=(
            (comment.author.full_name or comment.author.email)
            if comment.author
            else None
        ),
        body=comment.body,
        parent_id=comment.parent_id,
        created_at=comment.created_at,
    )


def _require_item(db: Session, user: User, item_id: str) -> ActionItem:
    item = db.get(ActionItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Action item not found")
    meeting = db.get(Meeting, item.meeting_id)
    require_team_access(db, user, meeting.team_id if meeting else "")
    return item


def _parse_changes(detail: str | None) -> list[dict]:
    if not detail:
        return []
    try:
        data = json.loads(detail)
    except (json.JSONDecodeError, TypeError):
        return []
    return [c for c in data if isinstance(c, dict)] if isinstance(data, list) else []


@router.patch("/{item_id}", response_model=ActionItemOut)
def update_action_item(
    item_id: str,
    payload: ActionItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.get(
        ActionItem,
        item_id,
        options=[*ACTION_ITEM_CONTEXT_LOAD, *ACTION_ITEM_TAGS_LOAD],
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Action item not found")

    meeting = item.meeting
    if meeting is None:
        raise HTTPException(status_code=404, detail="Action item not found")
    require_team_access(db, user, meeting.team_id)

    role = get_meeting_role(db, user, meeting)
    if role == MEETING_ROLE_VIEWER:
        raise HTTPException(
            status_code=403, detail="You do not have permission to edit action items"
        )
    if role == MEETING_ROLE_CONTRIBUTOR and item.assignee_id != user.id:
        raise HTTPException(
            status_code=403, detail="You can only edit action items assigned to you"
        )

    fields = payload.model_fields_set
    changes: list[dict] = []

    if "description" in fields and payload.description is not None:
        new_description = payload.description.strip()
        if new_description and new_description != item.description:
            changes.append(
                {"field": "description", "from": item.description, "to": new_description}
            )
            item.description = new_description

    if "status" in fields and payload.status is not None:
        if payload.status not in _VALID_STATUSES:
            raise HTTPException(status_code=422, detail="Invalid action item status")
        if payload.status != item.status:
            changes.append({"field": "status", "from": item.status, "to": payload.status})
        item.status = payload.status

    if "priority" in fields and payload.priority is not None:
        priority = payload.priority.upper()
        if priority not in _VALID_PRIORITIES:
            raise HTTPException(status_code=422, detail="Invalid action item priority")
        if priority != item.priority:
            changes.append({"field": "priority", "from": item.priority, "to": priority})
        item.priority = priority

    if "assignee_id" in fields:
        if payload.assignee_id != item.assignee_id:
            changes.append(
                {
                    "field": "assignee",
                    "from": _display_name(db, item.assignee_id),
                    "to": _display_name(db, payload.assignee_id),
                }
            )
        item.assignee_id = payload.assignee_id  # may be None to unassign

    if "due_date" in fields:
        if payload.due_date != item.due_date:
            changes.append(
                {
                    "field": "due_date",
                    "from": str(item.due_date or ""),
                    "to": str(payload.due_date or ""),
                }
            )
        item.due_date = payload.due_date  # may be None to clear

    if "tags" in fields and payload.tags is not None:
        old_names = ", ".join(sorted(t.name for t in item.tags))
        new_tags = []
        for spec in payload.tags:
            tag = upsert_tag(db, spec.name, spec.type)
            if tag is not None and tag not in new_tags:
                new_tags.append(tag)
        new_names = ", ".join(sorted(t.name for t in new_tags))
        if old_names != new_names:
            changes.append({"field": "tags", "from": old_names, "to": new_names})
        item.tags = new_tags

    for field in ("completion_notes", "completion_links", "completion_follow_up"):
        if field in fields and getattr(payload, field) is not None:
            new_value = getattr(payload, field)
            if new_value != getattr(item, field):
                changes.append({"field": field, "from": "—", "to": "updated"})
                setattr(item, field, new_value)

    sync_action_item_to_markdown(db, meeting, item)
    audit.log_audit(
        db,
        action=ACTION_ITEM_UPDATED,
        entity_type="action_item",
        entity_id=item.id,
        actor_id=user.id,
        team_id=meeting.team_id,
        meeting_id=meeting.id,
        detail=json.dumps(changes) if changes else None,
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
            joinedload(ActionItem.duplicate_of).joinedload(ActionItem.meeting),
            *ACTION_ITEM_CONTEXT_LOAD,
            *ACTION_ITEM_TAGS_LOAD,
        )
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(Meeting.team_id.in_(accessible), ActionItem.status.in_(_OPEN_STATUSES), ActionItem.duplicate_of_id.is_(None))
        .order_by(nulls_last(ActionItem.due_date), PRIORITY_ORDER)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [ActionItemWithContext(**action_item_out(item).model_dump()) for item in items]


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
            *ACTION_ITEM_CONTEXT_LOAD,
            *ACTION_ITEM_TAGS_LOAD,
        )
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(Meeting.team_id == team_id, ActionItem.status.in_(_OPEN_STATUSES), ActionItem.duplicate_of_id.is_(None))
        .order_by(nulls_last(ActionItem.due_date), PRIORITY_ORDER)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [action_item_out(item) for item in items]


@router.get("/{item_id}/comments", response_model=list[ActionItemCommentOut])
def list_comments(
    item_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _require_item(db, user, item_id)
    comments = (
        db.query(ActionItemComment)
        .options(joinedload(ActionItemComment.author))
        .filter(ActionItemComment.action_item_id == item_id)
        .order_by(ActionItemComment.created_at)
        .all()
    )
    return [_comment_out(c) for c in comments]


@router.post("/{item_id}/comments", response_model=ActionItemCommentOut, status_code=201)
def add_comment(
    item_id: str,
    payload: ActionItemCommentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _require_item(db, user, item_id)
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=400, detail="Comment cannot be empty")

    meeting = db.get(Meeting, item.meeting_id)
    if get_meeting_role(db, user, meeting) == MEETING_ROLE_VIEWER:
        raise HTTPException(status_code=403, detail="Viewers cannot comment")

    parent_id = payload.parent_id
    if parent_id:
        parent = db.get(ActionItemComment, parent_id)
        if parent is None or parent.action_item_id != item_id:
            raise HTTPException(status_code=400, detail="Invalid reply target")

    comment = ActionItemComment(
        action_item_id=item_id,
        author_id=user.id,
        body=body,
        parent_id=parent_id,
    )
    db.add(comment)
    db.flush()

    notify_mentions(db, actor=user, action_item=item, body=body)

    db.commit()
    db.refresh(comment)
    return _comment_out(comment)


@router.get("/{item_id}/history", response_model=list[ActionItemHistoryEntry])
def action_item_history(
    item_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _require_item(db, user, item_id)

    entries: list[ActionItemHistoryEntry] = []

    comments = (
        db.query(ActionItemComment)
        .options(joinedload(ActionItemComment.author))
        .filter(ActionItemComment.action_item_id == item_id)
        .order_by(ActionItemComment.created_at)
        .all()
    )
    for comment in comments:
        entries.append(
            ActionItemHistoryEntry(
                type="comment",
                comment=comment.body,
                actor_name=(
                    (comment.author.full_name or comment.author.email)
                    if comment.author
                    else None
                ),
                created_at=comment.created_at,
            )
        )

    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.entity_type == "action_item",
            AuditLog.entity_id == item_id,
            AuditLog.action == ACTION_ITEM_UPDATED,
        )
        .order_by(AuditLog.created_at)
        .all()
    )
    for log in logs:
        actor_name = _display_name(db, log.actor_id) if log.actor_id else None
        for change in _parse_changes(log.detail):
            entries.append(
                ActionItemHistoryEntry(
                    type="change",
                    field=change.get("field"),
                    from_value=change.get("from"),
                    to_value=change.get("to"),
                    actor_name=actor_name,
                    created_at=log.created_at,
                )
            )

    entries.sort(key=lambda e: e.created_at)
    return entries
