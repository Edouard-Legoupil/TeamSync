"""Authentication and team-access dependencies (RBAC)."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database import get_db
from app.models import MeetingPermission, Team, TeamMember, User
from app.models.enums import TeamMemberRole, UserRole

ACCESS_TOKEN_COOKIE = "teamsync_access_token"

MEETING_ROLE_OWNER = "owner"
MEETING_ROLE_CONTRIBUTOR = "contributor"
MEETING_ROLE_VIEWER = "viewer"
_VALID_MEETING_ROLES = {
    MEETING_ROLE_OWNER,
    MEETING_ROLE_CONTRIBUTOR,
    MEETING_ROLE_VIEWER,
}


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(ACCESS_TOKEN_COOKIE)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Restrict a route to SUPER_ADMIN users."""
    if user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user


# --- RBAC -------------------------------------------------------------------

def get_team_descendant_ids(db: Session, team_ids: set[str]) -> set[str]:
    """Expand a set of team ids to include all descendant child teams."""
    result = set(team_ids)
    frontier = set(team_ids)
    while frontier:
        children = {
            t.id
            for t in db.query(Team).filter(Team.parent_team_id.in_(frontier)).all()
        }
        new = children - result
        if not new:
            break
        result |= new
        frontier = new
    return result


def get_accessible_team_ids(db: Session, user: User) -> set[str]:
    """Resolve every team id the given user may view."""
    if user.role == UserRole.SUPER_ADMIN.value:
        return {t.id for t in db.query(Team).all()}

    member_team_ids = {
        m.team_id
        for m in db.query(TeamMember).filter(TeamMember.user_id == user.id).all()
    }

    if user.role == UserRole.SUPERVISOR.value:
        managed = {
            t.id for t in db.query(Team).filter(Team.manager_id == user.id).all()
        }
        return get_team_descendant_ids(db, managed | member_team_ids)

    # MEMBER: only explicit team memberships.
    return member_team_ids


def require_team_access(db: Session, user: User, team_id: str) -> None:
    """Raise 403 unless the user can access the given team."""
    if team_id not in get_accessible_team_ids(db, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this team",
        )


def get_primary_team_id(db: Session, user: User) -> str | None:
    """Pick the most sensible default team for a user's landing context."""
    accessible = get_accessible_team_ids(db, user)
    if not accessible:
        return None

    # Prefer a team the supervisor manages, then any team, deterministically.
    managed = {t.id for t in db.query(Team).filter(Team.manager_id == user.id).all()}
    preferred = managed & accessible
    pool = sorted(preferred or accessible)
    return pool[0] if pool else None


def get_meeting_role(db: Session, user: User, meeting) -> str:
    """Resolve a user's effective role on a meeting.

    Highest precedence wins: super admin > organizer > explicit per-meeting
    permission > team manager / LEAD > CONTRIBUTOR > viewer.
    """
    if user.role == UserRole.SUPER_ADMIN.value:
        return MEETING_ROLE_OWNER
    if meeting.organizer_id == user.id:
        return MEETING_ROLE_OWNER

    permission = (
        db.query(MeetingPermission)
        .filter(
            MeetingPermission.meeting_id == meeting.id,
            MeetingPermission.user_id == user.id,
        )
        .first()
    )
    if permission is not None:
        return permission.role

    team = db.get(Team, meeting.team_id)
    if team is not None and team.manager_id == user.id:
        return MEETING_ROLE_OWNER

    membership = (
        db.query(TeamMember)
        .filter(
            TeamMember.team_id == meeting.team_id,
            TeamMember.user_id == user.id,
        )
        .first()
    )
    if membership is not None:
        if membership.role == TeamMemberRole.LEAD.value:
            return MEETING_ROLE_OWNER
        if membership.role == TeamMemberRole.CONTRIBUTOR.value:
            return MEETING_ROLE_CONTRIBUTOR

    return MEETING_ROLE_VIEWER
