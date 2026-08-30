"""Audit trail helper.

Call ``log_audit`` inside an existing request/transaction; the caller is
responsible for committing. Keeps every write path accountable without
coupling the audit store to business logic.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models import AuditLog

# Action vocabulary (kept as constants so callers stay consistent).
MEETING_UPLOADED = "meeting.uploaded"
MEETING_IMPORTED = "meeting.imported"
MEETING_PROCESSED = "meeting.processed"
MEETING_PROCESS_FAILED = "meeting.process_failed"
MEETING_UPDATED = "meeting.updated"
MEETING_REPROCESSED = "meeting.reprocessed"
MEETING_EXPORTED = "meeting.exported"
ACTION_ITEM_UPDATED = "action_item.updated"

USER_UPDATED = "user.updated"
TEAM_CREATED = "team.created"
TEAM_UPDATED = "team.updated"
TEAM_DELETED = "team.deleted"
MEMBER_ADDED = "member.added"
MEMBER_UPDATED = "member.updated"
MEMBER_REMOVED = "member.removed"


def log_audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_id: Optional[str] = None,
    team_id: Optional[str] = None,
    meeting_id: Optional[str] = None,
    detail: Optional[str] = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            team_id=team_id,
            meeting_id=meeting_id,
            detail=detail,
        )
    )
