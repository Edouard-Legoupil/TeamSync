"""Personal reports: a digest of the user's open action items."""

from __future__ import annotations

from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.api.helpers import today_in_app_tz
from app.auth.dependencies import get_accessible_team_ids, get_current_user
from app.database import get_db
from app.models import ActionItem, Meeting, User
from app.models.enums import ActionItemStatus
from app.schemas import DigestItemOut, DigestOut

router = APIRouter(tags=["reports"])


@router.get("/api/reports/my-digest", response_model=DigestOut)
def my_digest(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accessible = get_accessible_team_ids(db, user)
    items: list[DigestItemOut] = []

    if accessible:
        rows = (
            db.query(ActionItem)
            .options(
                joinedload(ActionItem.assignee),
                joinedload(ActionItem.meeting).joinedload(Meeting.team),
            )
            .join(Meeting, ActionItem.meeting_id == Meeting.id)
            .filter(
                Meeting.team_id.in_(accessible),
                ActionItem.status.in_(
                    [ActionItemStatus.OPEN.value, ActionItemStatus.IN_PROGRESS.value]
                ),
                ActionItem.duplicate_of_id.is_(None),
            )
            .all()
        )

        today = today_in_app_tz()
        for item in rows:
            overdue = bool(item.due_date and item.due_date < today)
            meeting = item.meeting
            items.append(
                DigestItemOut(
                    description=item.description,
                    assignee_name=(
                        (item.assignee.full_name or item.assignee.email)
                        if item.assignee
                        else None
                    ),
                    due_date=item.due_date,
                    priority=item.priority,
                    overdue=overdue,
                    team_name=meeting.team.name if meeting and meeting.team else "",
                    meeting_title=meeting.title if meeting else "",
                )
            )

        items.sort(key=lambda x: (not x.overdue, x.due_date is None, x.due_date or date.max))

    subject = f"Your open action items — {user.full_name or user.email}"
    lines: list[str] = []
    for item in items:
        if item.overdue:
            flag = "OVERDUE"
        elif item.due_date:
            flag = f"due {item.due_date.strftime('%Y-%m-%d')}"
        else:
            flag = "no due date"
        team = f" · {item.team_name}" if item.team_name else ""
        lines.append(f"- [{flag}] {item.description}{team}")

    body = "\n".join(lines) if lines else "No open action items. Great job!"
    mailto = f"mailto:?subject={quote(subject)}&body={quote(body)}"

    return DigestOut(subject=subject, body=body, mailto=mailto, items=items)
