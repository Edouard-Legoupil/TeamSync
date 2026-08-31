"""Meeting endpoints: upload, import, process, detail, edit, audit, action items."""

from __future__ import annotations

import os
import re

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import nulls_last
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.helpers import (
    ACTION_ITEM_CONTEXT_LOAD,
    ACTION_ITEM_TAGS_LOAD,
    PRIORITY_ORDER,
    action_item_out,
    meeting_detail_out,
    meeting_list_row_out,
)
from app.auth.dependencies import (
    MEETING_ROLE_CONTRIBUTOR,
    MEETING_ROLE_OWNER,
    MEETING_ROLE_VIEWER,
    _VALID_MEETING_ROLES,
    get_accessible_team_ids,
    get_current_user,
    get_meeting_role,
    require_team_access,
)
from app.database import get_db
from app.models import ActionItem, AuditLog, Meeting, MeetingPermission, MeetingSeries, User
from app.models.enums import MeetingStatus
from app.rate_limit import rate_limit
from app.schemas import (
    ActionItemOut,
    AuditLogOut,
    MeetingCreatedOut,
    MeetingDetailOut,
    MeetingImportRequest,
    MeetingListRow,
    MeetingPermissionOut,
    MeetingPermissionUpsert,
    MeetingUpdate,
)
from app.services import audit
from app.services.audit import (
    MEETING_DELETED,
    MEETING_IMPORTED,
    MEETING_REPROCESSED,
    MEETING_UPDATED,
    MEETING_UPLOADED,
)
from app.services.file_parser import extract_text
from app.services.processing import process_meeting, refresh_follow_ups
from app.services.sanitize import sanitize_markdown

router = APIRouter(prefix="/api/meetings", tags=["meetings"])

ALLOWED_EXTENSIONS = {".txt", ".md", ".docx", ".vtt"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _default_title(filename: str | None) -> str:
    stem = os.path.splitext(os.path.basename(filename or ""))[0]
    stem = re.sub(r"[_-]+", " ", stem).strip()
    return stem or "Untitled Meeting"


def _require_meeting(db: Session, user: User, meeting_id: str) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    require_team_access(db, user, meeting.team_id)
    return meeting


def _require_owner(db: Session, user: User, meeting: Meeting) -> None:
    if get_meeting_role(db, user, meeting) != MEETING_ROLE_OWNER:
        raise HTTPException(
            status_code=403, detail="You need owner access to perform this action"
        )


@router.post("/upload", response_model=MeetingCreatedOut, status_code=202)
def upload_meeting(
    background: BackgroundTasks,
    team_id: str = Form(...),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    series_id: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit),
):
    require_team_access(db, user, team_id)

    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail="Unsupported file type. Upload a .txt, .vtt, or .docx file."
        )

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File is too large (max 10 MB).")

    try:
        transcript = extract_text(filename, content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    transcript = transcript.strip()
    if not transcript:
        raise HTTPException(status_code=400, detail="No text found in the uploaded file.")

    meeting = Meeting(
        title=(title or _default_title(filename)).strip() or "Untitled Meeting",
        team_id=team_id,
        organizer_id=user.id,
        series_id=series_id,
        status=MeetingStatus.DRAFT.value,
        raw_transcript=transcript,
        source_filename=filename,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    audit.log_audit(
        db,
        action=MEETING_UPLOADED,
        entity_type="meeting",
        entity_id=meeting.id,
        actor_id=user.id,
        team_id=team_id,
        meeting_id=meeting.id,
        detail=filename,
    )
    db.commit()

    background.add_task(process_meeting, meeting.id)
    return MeetingCreatedOut(meeting_id=meeting.id, status=meeting.status)


@router.post("/import", response_model=MeetingCreatedOut, status_code=202)
def import_meeting(
    payload: MeetingImportRequest,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit),
):
    require_team_access(db, user, payload.team_id)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="No text provided.")
    if len(text) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Transcript is too large (max 10 MB).")

    meeting = Meeting(
        title=(payload.title or "").strip() or "Pasted Transcript",
        team_id=payload.team_id,
        organizer_id=user.id,
        series_id=payload.series_id,
        status=MeetingStatus.DRAFT.value,
        raw_transcript=text,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    audit.log_audit(
        db,
        action=MEETING_IMPORTED,
        entity_type="meeting",
        entity_id=meeting.id,
        actor_id=user.id,
        team_id=payload.team_id,
        meeting_id=meeting.id,
    )
    db.commit()

    background.add_task(process_meeting, meeting.id)
    return MeetingCreatedOut(meeting_id=meeting.id, status=meeting.status)


@router.post("/{meeting_id}/process", response_model=MeetingCreatedOut)
def reprocess_meeting(
    meeting_id: str,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meeting = _require_meeting(db, user, meeting_id)
    if not meeting.raw_transcript.strip():
        raise HTTPException(status_code=400, detail="No transcript available to process")
    _require_owner(db, user, meeting)

    meeting.status = MeetingStatus.DRAFT.value
    audit.log_audit(
        db,
        action=MEETING_REPROCESSED,
        entity_type="meeting",
        entity_id=meeting.id,
        actor_id=user.id,
        team_id=meeting.team_id,
        meeting_id=meeting.id,
    )
    db.commit()
    background.add_task(process_meeting, meeting_id)
    return MeetingCreatedOut(meeting_id=meeting_id, status=MeetingStatus.DRAFT.value)


@router.post("/{meeting_id}/follow-ups/refresh", status_code=202)
def refresh_follow_ups_endpoint(
    meeting_id: str,
    background: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit),
):
    """Re-derive a meeting's suggested follow-ups from its current state."""
    meeting = _require_meeting(db, user, meeting_id)
    _require_owner(db, user, meeting)
    background.add_task(refresh_follow_ups, meeting_id)
    return {"queued": True}


@router.get("", response_model=list[MeetingListRow])
def all_meetings(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Meetings across every team the user can access."""
    accessible = get_accessible_team_ids(db, user)
    if not accessible:
        return []

    meetings = (
        db.query(Meeting)
        .options(
            selectinload(Meeting.action_items),
            joinedload(Meeting.team),
            joinedload(Meeting.series),
        )
        .filter(Meeting.team_id.in_(accessible))
        .order_by(Meeting.date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [meeting_list_row_out(m) for m in meetings]


@router.get("/{meeting_id}", response_model=MeetingDetailOut)
def get_meeting(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    meeting = _require_meeting(db, user, meeting_id)
    detail = meeting_detail_out(meeting)
    detail.my_role = get_meeting_role(db, user, meeting)
    return detail


@router.get("/{meeting_id}/transcript")
def meeting_transcript(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    meeting = _require_meeting(db, user, meeting_id)
    filename = meeting.source_filename or f"transcript-{meeting_id}.txt"
    filename = re.sub(r'[\\"\r\n]', "_", filename)
    return Response(
        content=meeting.raw_transcript or "",
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


@router.patch("/{meeting_id}", response_model=MeetingDetailOut)
def update_meeting(
    meeting_id: str,
    payload: MeetingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meeting = _require_meeting(db, user, meeting_id)
    _require_owner(db, user, meeting)
    fields = payload.model_fields_set

    if "title" in fields and payload.title is not None:
        meeting.title = payload.title.strip() or meeting.title
    if "minutes_markdown" in fields:
        meeting.minutes_markdown = sanitize_markdown(payload.minutes_markdown) or None
    if "next_agenda_markdown" in fields:
        meeting.next_agenda_markdown = sanitize_markdown(payload.next_agenda_markdown) or None
    if "team_id" in fields and payload.team_id is not None:
        if payload.team_id != meeting.team_id:
            require_team_access(db, user, payload.team_id)
            meeting.team_id = payload.team_id
    if "series_id" in fields:
        if payload.series_id is not None:
            series = db.get(MeetingSeries, payload.series_id)
            if series is None or series.team_id != meeting.team_id:
                raise HTTPException(
                    status_code=400, detail="Series does not belong to this team"
                )
        meeting.series_id = payload.series_id
    if "date" in fields and payload.date is not None:
        meeting.date = payload.date

    audit.log_audit(
        db,
        action=MEETING_UPDATED,
        entity_type="meeting",
        entity_id=meeting.id,
        actor_id=user.id,
        team_id=meeting.team_id,
        meeting_id=meeting.id,
        detail=",".join(sorted(fields)),
    )
    db.commit()
    db.refresh(meeting)
    return meeting_detail_out(meeting)


@router.delete("/{meeting_id}")
def delete_meeting(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    meeting = _require_meeting(db, user, meeting_id)
    _require_owner(db, user, meeting)
    team_id = meeting.team_id
    audit.log_audit(
        db,
        action=MEETING_DELETED,
        entity_type="meeting",
        entity_id=meeting.id,
        actor_id=user.id,
        team_id=team_id,
        meeting_id=meeting.id,
    )
    db.delete(meeting)
    db.commit()
    return {"ok": True}


@router.get("/{meeting_id}/permissions", response_model=list[MeetingPermissionOut])
def meeting_permissions(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    meeting = _require_meeting(db, user, meeting_id)
    _require_owner(db, user, meeting)
    rows = (
        db.query(MeetingPermission, User)
        .join(User, User.id == MeetingPermission.user_id)
        .filter(MeetingPermission.meeting_id == meeting_id)
        .order_by(User.full_name)
        .all()
    )
    return [
        MeetingPermissionOut(
            user_id=u.id,
            full_name=u.full_name,
            email=u.email,
            role=perm.role,
        )
        for perm, u in rows
    ]


@router.post(
    "/{meeting_id}/permissions", response_model=MeetingPermissionOut, status_code=201
)
def upsert_meeting_permission(
    meeting_id: str,
    payload: MeetingPermissionUpsert,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meeting = _require_meeting(db, user, meeting_id)
    _require_owner(db, user, meeting)
    if payload.role not in _VALID_MEETING_ROLES:
        raise HTTPException(status_code=422, detail="Invalid meeting role")

    target = db.get(User, payload.user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if meeting.team_id not in get_accessible_team_ids(db, target):
        raise HTTPException(
            status_code=400, detail="User does not have access to this team"
        )

    permission = (
        db.query(MeetingPermission)
        .filter(
            MeetingPermission.meeting_id == meeting_id,
            MeetingPermission.user_id == payload.user_id,
        )
        .first()
    )
    if permission is not None:
        permission.role = payload.role
    else:
        permission = MeetingPermission(
            meeting_id=meeting_id, user_id=payload.user_id, role=payload.role
        )
        db.add(permission)
    db.commit()
    db.refresh(permission)
    return MeetingPermissionOut(
        user_id=target.id,
        full_name=target.full_name,
        email=target.email,
        role=permission.role,
    )


@router.delete("/{meeting_id}/permissions/{user_id}")
def delete_meeting_permission(
    meeting_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    meeting = _require_meeting(db, user, meeting_id)
    _require_owner(db, user, meeting)
    permission = (
        db.query(MeetingPermission)
        .filter(
            MeetingPermission.meeting_id == meeting_id,
            MeetingPermission.user_id == user_id,
        )
        .first()
    )
    if permission is not None:
        db.delete(permission)
        db.commit()
    return {"ok": True}


@router.get("/{meeting_id}/action-items", response_model=list[ActionItemOut])
def meeting_action_items(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    meeting = _require_meeting(db, user, meeting_id)
    items = (
        db.query(ActionItem)
        .options(
            joinedload(ActionItem.assignee),
            joinedload(ActionItem.duplicate_of).joinedload(ActionItem.meeting),
            *ACTION_ITEM_CONTEXT_LOAD,
            *ACTION_ITEM_TAGS_LOAD,
        )
        .filter(ActionItem.meeting_id == meeting_id)
        .order_by(nulls_last(ActionItem.due_date), PRIORITY_ORDER)
        .all()
    )
    return [action_item_out(item) for item in items]


@router.get("/{meeting_id}/audit", response_model=list[AuditLogOut])
def meeting_audit(
    meeting_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _require_meeting(db, user, meeting_id)
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.meeting_id == meeting_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    return [AuditLogOut.model_validate(log) for log in logs]
