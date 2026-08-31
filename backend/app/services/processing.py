"""Background meeting processing.

``process_meeting`` is deliberately synchronous and idempotent so it can run
from FastAPI ``BackgroundTasks`` in development, and from an Azure Queue /
Timer triggered Function in production (see ``function_app.py``). On any
failure the meeting stays ``DRAFT`` and the error is recorded in
``ai_metadata`` so the UI can offer a manual retry.
"""

from __future__ import annotations

import re
import time
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ActionItem, Meeting, MeetingFollowUp, User
from app.models.enums import ActionItemStatus, MeetingStatus
from app.services import ai_service
from app.services import audit
from app.services.audit import MEETING_PROCESSED, MEETING_PROCESS_FAILED
from app.services.sanitize import sanitize_markdown
from app.services.tagging import parse_action_item_tags, upsert_tag
from app.services.transcript_parser import find_evidence, parse_segments


def _parse_due_date(value: str) -> Optional[date]:
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_meeting_date(value: object) -> Optional[datetime]:
    """Parse the AI-extracted meeting date; None if missing or invalid."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _resolve_assignee(db: Session, name: str) -> Optional[str]:
    name = name.strip()
    if not name or name.lower() in {"unassigned", "n/a", "tbd", "-"}:
        return None
    user = (
        db.query(User)
        .filter(User.full_name.ilike(f"%{name}%") | User.email.ilike(f"%{name}%"))
        .first()
    )
    return user.id if user else None


def _build_action_item_rows(db: Session, meeting: Meeting, action_md: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fields in ai_service.parse_action_items(action_md):
        rows.append(
            {
                "meeting_id": meeting.id,
                "description": fields["description"],
                "assignee_id": _resolve_assignee(db, fields["assignee"]),
                "due_date": _parse_due_date(fields["due_date"]),
                "priority": fields["priority"],
                "status": fields["status"],
            }
        )
    return rows


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _parse_action_item_details(value: object) -> dict[str, dict]:
    result: dict[str, dict] = {}
    if not isinstance(value, list):
        return result
    for entry in value:
        if not isinstance(entry, dict):
            continue
        task = str(entry.get("task", "") or "").strip()
        if task:
            result[_normalize(task)] = entry
    return result


def _confidence(value: object) -> Optional[float]:
    try:
        conf = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, conf))


_VALID_FOLLOW_UP_TYPES = {"meeting", "email", "document_sharing", "one_on_one", "ad_hoc"}


def _parse_follow_ups(value: object) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return result
    for entry in value:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "") or "").strip()
        if not title:
            continue
        ftype = str(entry.get("follow_up_type", "ad_hoc") or "").strip().lower()
        if ftype not in _VALID_FOLLOW_UP_TYPES:
            ftype = "ad_hoc"
        participants = entry.get("participants")
        result.append(
            {
                "follow_up_type": ftype,
                "title": title,
                "issue": str(entry.get("issue", "") or "").strip() or None,
                "participants": participants if isinstance(participants, list) else None,
                "rationale": str(entry.get("rationale", "") or "").strip() or None,
                "status": "suggested",
            }
        )
    return result


def _follow_ups_to_markdown(follow_ups: list[dict[str, Any]]) -> str:
    if not follow_ups:
        return ""
    lines = ["## Suggested Follow-Up"]
    for fu in follow_ups:
        lines.append(f"- **{fu['title']}** ({fu['follow_up_type']})")
        participants = fu.get("participants")
        if participants:
            lines.append(f"  - Participants: {', '.join(participants)}")
        if fu.get("rationale"):
            lines.append(f"  - Reason: {fu['rationale']}")
    return "\n".join(lines)


def _find_duplicate(db: Session, meeting: Meeting, description: str) -> Optional[str]:
    """Return an existing open ActionItem (in another meeting, same team) that
    matches this description, so we don't double-track the same commitment."""
    norm = _normalize(description)
    if not norm:
        return None
    candidates = (
        db.query(ActionItem)
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(
            Meeting.team_id == meeting.team_id,
            Meeting.id != meeting.id,
            ActionItem.status.in_(
                [ActionItemStatus.OPEN.value, ActionItemStatus.IN_PROGRESS.value]
            ),
            ActionItem.duplicate_of_id.is_(None),
        )
        .all()
    )
    for item in candidates:
        if _normalize(item.description) == norm:
            return item.id
    return None


def _roll_forward(db: Session, meeting: Meeting, agenda_md: str) -> str:
    """Prepend open action items from the previous meeting in the series."""
    previous = (
        db.query(Meeting)
        .filter(
            Meeting.series_id == meeting.series_id,
            Meeting.id != meeting.id,
            Meeting.status == MeetingStatus.PROCESSED.value,
        )
        .order_by(Meeting.date.desc())
        .first()
    )
    if previous is None:
        return agenda_md

    open_items = (
        db.query(ActionItem)
        .filter(
            ActionItem.meeting_id == previous.id,
            ActionItem.status.in_(
                [ActionItemStatus.OPEN.value, ActionItemStatus.IN_PROGRESS.value]
            ),
            ActionItem.duplicate_of_id.is_(None),
        )
        .all()
    )
    if not open_items:
        return agenda_md

    lines = [f"## Carried forward from {previous.title}"]
    lines.extend(f"- {item.description}" for item in open_items)
    carried = "\n".join(lines)
    return (agenda_md + "\n\n" + carried).strip() if agenda_md else carried


def process_meeting(meeting_id: str) -> None:
    db = SessionLocal()
    try:
        meeting = db.get(Meeting, meeting_id)
        if meeting is None or not meeting.raw_transcript.strip():
            return

        started = time.time()
        result = ai_service.process_transcript(meeting.raw_transcript)

        minutes = sanitize_markdown(result["minutes_markdown"])
        action_md = sanitize_markdown(result["action_items_markdown"])

        parsed_date = _parse_meeting_date(result.get("meeting_date"))
        if parsed_date is not None:
            meeting.date = parsed_date

        meeting.minutes_markdown = minutes or None
        meeting.action_items_markdown = action_md or None

        # Rebuild suggested follow-ups.
        follow_ups = _parse_follow_ups(result.get("follow_ups"))
        db.query(MeetingFollowUp).filter(
            MeetingFollowUp.meeting_id == meeting.id
        ).delete()
        for fu in follow_ups:
            db.add(MeetingFollowUp(meeting_id=meeting.id, **fu))
        meeting.next_agenda_markdown = _follow_ups_to_markdown(follow_ups) or None

        # Rebuild the trackable ActionItem rows from the Markdown table.
        db.query(ActionItem).filter(ActionItem.meeting_id == meeting.id).delete()
        rows = _build_action_item_rows(db, meeting, action_md or "")
        tags_by_task = parse_action_item_tags(result.get("action_item_tags"))
        details_by_task = _parse_action_item_details(result.get("action_item_details"))
        segments = parse_segments(meeting.raw_transcript)["segments"]
        duplicate_count = 0
        for row in rows:
            duplicate_of = _find_duplicate(db, meeting, row["description"])
            if duplicate_of:
                row["duplicate_of_id"] = duplicate_of
                duplicate_count += 1
            item = ActionItem(**row)
            db.add(item)
            db.flush()
            # Store the exact Markdown row for later in-place syncs.
            item.source_markdown = _row_for_item(db, item)
            # Attach AI-inferred tags (upsert by name; first write wins on type).
            for spec in tags_by_task.get(_normalize(row["description"]), []):
                tag = upsert_tag(db, spec["name"], spec["type"])
                if tag is not None and tag not in item.tags:
                    item.tags.append(tag)

            # Ground the item in transcript evidence (#4, #7).
            detail = details_by_task.get(_normalize(row["description"]), {})
            excerpt = str(detail.get("excerpt", "") or "").strip() or None
            item.source_excerpt = excerpt
            transcript_evidence = find_evidence(segments, excerpt) if excerpt else {}
            if transcript_evidence.get("speaker") or transcript_evidence.get("timestamp"):
                item.source_speaker = transcript_evidence.get("speaker")
                item.source_timestamp = transcript_evidence.get("timestamp")
                item.attribution_method = "transcript"
            else:
                speaker = str(detail.get("speaker", "") or "").strip() or None
                timestamp = str(detail.get("timestamp", "") or "").strip() or None
                item.source_speaker = speaker
                item.source_timestamp = timestamp
                item.attribution_method = (
                    "ai" if (speaker or timestamp) else None
                )
            item.confidence = _confidence(detail.get("confidence"))
            item.requester = str(detail.get("requester", "") or "").strip() or None
            related = detail.get("related_participants")
            item.related_participants = related if isinstance(related, list) else None

        # Carry open items forward from the previous meeting in the series.
        if meeting.series_id:
            meeting.next_agenda_markdown = _roll_forward(
                db, meeting, meeting.next_agenda_markdown or ""
            )

        meeting.ai_metadata = {
            "model": result.get("model"),
            "confidence": result.get("confidence", 0.5),
            "processing_time_ms": int((time.time() - started) * 1000),
            "action_item_count": len(rows),
            "duplicate_count": duplicate_count,
        }
        meeting.status = MeetingStatus.PROCESSED.value
        audit.log_audit(
            db,
            action=MEETING_PROCESSED,
            entity_type="meeting",
            entity_id=meeting.id,
            team_id=meeting.team_id,
            meeting_id=meeting.id,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001 - mark FAILED, record error
        db.rollback()
        meeting = db.get(Meeting, meeting_id)
        if meeting is not None:
            meta = dict(meeting.ai_metadata or {})
            meta["error"] = str(exc)
            meeting.ai_metadata = meta
            meeting.status = MeetingStatus.FAILED.value
            audit.log_audit(
                db,
                action=MEETING_PROCESS_FAILED,
                entity_type="meeting",
                entity_id=meeting.id,
                team_id=meeting.team_id,
                meeting_id=meeting.id,
                detail=str(exc),
            )
            db.commit()
    finally:
        db.close()


def _row_for_item(db: Session, item: ActionItem) -> str:
    """Build the Markdown table row for a freshly-created ActionItem."""
    from app.services.markdown_sync import build_action_item_row

    return build_action_item_row(db, item)
