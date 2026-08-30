"""Outlook / calendar export endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_team_access
from app.config import settings
from app.database import get_db
from app.models import Meeting, User
from app.schemas import OutlookOut
from app.services import audit
from app.services.audit import MEETING_EXPORTED
from app.services.email_draft import build_email_draft, markdown_to_text
from app.services.outlook import build_calendar_web_url, build_email_web_url, build_ics

router = APIRouter(prefix="/api/meetings", tags=["outlook"])


def _require_meeting(db: Session, user: User, meeting_id: str) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    require_team_access(db, user, meeting.team_id)
    if not meeting.minutes_markdown:
        raise HTTPException(status_code=404, detail="Meeting has not been processed yet")
    return meeting


@router.get("/{meeting_id}/outlook", response_model=OutlookOut)
def outlook_actions(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    meeting = _require_meeting(db, user, meeting_id)
    draft = build_email_draft(meeting)
    return OutlookOut(
        subject=draft["subject"],
        body=markdown_to_text(meeting.minutes_markdown),
        ics_url=f"/api/meetings/{meeting_id}/export/ics",
        calendar_web_url=build_calendar_web_url(meeting, draft["subject"], draft["body"]),
        email_web_url=build_email_web_url(draft["subject"], draft["body"]),
        server_send_enabled=settings.MICROSOFT_GRAPH_ENABLED,
    )


@router.get("/{meeting_id}/export/ics")
def export_ics(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    meeting = _require_meeting(db, user, meeting_id)
    ics = build_ics(meeting)

    audit.log_audit(
        db,
        action=MEETING_EXPORTED,
        entity_type="meeting",
        entity_id=meeting.id,
        actor_id=user.id,
        team_id=meeting.team_id,
        meeting_id=meeting.id,
        detail="ics",
    )
    db.commit()

    return Response(
        content=ics,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="meeting-{meeting_id}.ics"'
        },
    )
