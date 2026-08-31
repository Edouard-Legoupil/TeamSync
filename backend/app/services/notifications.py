"""@mention detection and in-app notification creation."""

from __future__ import annotations

import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ActionItem, Meeting, Notification, TeamMember, User

# Matches "@name", "@first.last", "@name@example.org", "@name+tag@example.org".
_MENTION_RE = re.compile(r"@([A-Za-z0-9._%+-]+(?:@[A-Za-z0-9.-]+\.[A-Za-z]{2,})?)")


def _find_member(members: list[User], token: str) -> Optional[User]:
    needle = token.lower()
    for member in members:
        full = (member.full_name or "").strip().lower()
        email = (member.email or "").strip().lower()
        first = full.split()[0] if full else ""
        local = email.split("@")[0] if email else ""
        if needle and needle in (full, first, email, local):
            return member
    return None


def notify_mentions(
    db: Session, *, actor: User, action_item: ActionItem, body: str
) -> list[Notification]:
    """Create one Notification per resolved @mention in ``body``.

    Mentions resolve against the action item's team members only; the actor is
    never notified for mentioning themselves.
    """
    tokens = set(_MENTION_RE.findall(body or ""))
    if not tokens:
        return []

    meeting = db.get(Meeting, action_item.meeting_id)
    if meeting is None:
        return []

    members = (
        db.query(User)
        .join(TeamMember, TeamMember.user_id == User.id)
        .filter(TeamMember.team_id == meeting.team_id, User.is_active.is_(True))
        .all()
    )

    created: list[Notification] = []
    for token in tokens:
        target = _find_member(members, token)
        if target is None or target.id == actor.id:
            continue
        notification = Notification(
            recipient_id=target.id,
            actor_id=actor.id,
            kind="mention",
            entity_type="action_item",
            entity_id=action_item.id,
            meeting_id=meeting.id,
            text=f"{actor.full_name or actor.email} mentioned you on an action item",
        )
        db.add(notification)
        created.append(notification)
    return created
