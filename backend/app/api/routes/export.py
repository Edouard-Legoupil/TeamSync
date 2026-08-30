"""Export & portability endpoints: Word, Markdown, and email draft."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_team_access
from app.database import get_db
from app.models import Meeting, User
from app.schemas import EmailDraftOut
from app.services import audit
from app.services.audit import MEETING_EXPORTED
from app.services.email_draft import build_email_draft
from app.services.word_export import markdown_to_docx_bytes

router = APIRouter(prefix="/api/meetings", tags=["export"])

WORD_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _require_meeting(db: Session, user: User, meeting_id: str) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    require_team_access(db, user, meeting.team_id)
    if not meeting.minutes_markdown:
        raise HTTPException(
            status_code=404, detail="Meeting has not been processed yet"
        )
    return meeting


@router.get("/{meeting_id}/export/word")
def export_word(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    meeting = _require_meeting(db, user, meeting_id)
    audit.log_audit(
        db,
        action=MEETING_EXPORTED,
        entity_type="meeting",
        entity_id=meeting.id,
        actor_id=user.id,
        team_id=meeting.team_id,
        meeting_id=meeting.id,
        detail="word",
    )
    db.commit()
    data = markdown_to_docx_bytes(meeting.minutes_markdown, meeting.title)
    return Response(
        content=data,
        media_type=WORD_MEDIA_TYPE,
        headers={
            "Content-Disposition": f'attachment; filename="meeting-minutes-{meeting_id}.docx"'
        },
    )


@router.get("/{meeting_id}/export/markdown")
def export_markdown(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    meeting = _require_meeting(db, user, meeting_id)
    audit.log_audit(
        db,
        action=MEETING_EXPORTED,
        entity_type="meeting",
        entity_id=meeting.id,
        actor_id=user.id,
        team_id=meeting.team_id,
        meeting_id=meeting.id,
        detail="markdown",
    )
    db.commit()
    return Response(
        content=meeting.minutes_markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="meeting-minutes-{meeting_id}.md"'
        },
    )


@router.post("/{meeting_id}/email-draft", response_model=EmailDraftOut)
def email_draft(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    meeting = _require_meeting(db, user, meeting_id)
    audit.log_audit(
        db,
        action=MEETING_EXPORTED,
        entity_type="meeting",
        entity_id=meeting.id,
        actor_id=user.id,
        team_id=meeting.team_id,
        meeting_id=meeting.id,
        detail="email-draft",
    )
    db.commit()
    return build_email_draft(meeting)
