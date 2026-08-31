"""Admin endpoints (SUPER_ADMIN only): manage users, teams, and membership.

All mutations are written to the audit log.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.dependencies import require_admin
from app.database import get_db
from app.models import Team, TeamMember, User
from app.models.enums import TeamMemberRole, UserRole
from app.schemas import (
    AdminMemberAdd,
    AdminMemberOut,
    AdminMemberUpdate,
    AdminTeamCreate,
    AdminTeamOut,
    AdminTeamUpdate,
    AdminUserOut,
    AdminUserUpdate,
)
from app.services import audit
from app.services.audit import (
    MEMBER_ADDED,
    MEMBER_REMOVED,
    MEMBER_UPDATED,
    TEAM_CREATED,
    TEAM_DELETED,
    TEAM_UPDATED,
    USER_UPDATED,
)
from app.services.slugify import unique_slug

router = APIRouter(prefix="/api/admin", tags=["admin"])

_VALID_ROLES = {r.value for r in UserRole}
_VALID_MEMBER_ROLES = {r.value for r in TeamMemberRole}
_VALID_TEAM_KINDS = {"team", "personal", "project", "donor", "operation"}


def _team_out(db: Session, team: Team) -> AdminTeamOut:
    count = (
        db.query(func.count(TeamMember.id)).filter(TeamMember.team_id == team.id).scalar()
        or 0
    )
    return AdminTeamOut(
        id=team.id,
        name=team.name,
        description=team.description,
        manager_id=team.manager_id,
        parent_team_id=team.parent_team_id,
        kind=team.kind,
        slug=team.slug,
        member_count=count,
    )


def _user_out(db: Session, user: User) -> AdminUserOut:
    count = (
        db.query(func.count(TeamMember.id)).filter(TeamMember.user_id == user.id).scalar()
        or 0
    )
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        team_count=count,
    )


# --- Users ------------------------------------------------------------------

@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    users = db.query(User).order_by(User.email).all()
    return [_user_out(db, u) for u in users]


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    fields = payload.model_fields_set
    if "role" in fields and payload.role is not None:
        if payload.role not in _VALID_ROLES:
            raise HTTPException(status_code=422, detail="Invalid role")
        user.role = payload.role
    if "is_active" in fields and payload.is_active is not None:
        user.is_active = payload.is_active
    if "full_name" in fields and payload.full_name is not None:
        user.full_name = payload.full_name.strip()

    audit.log_audit(
        db,
        action=USER_UPDATED,
        entity_type="user",
        entity_id=user.id,
        actor_id=admin.id,
        detail=",".join(sorted(fields)),
    )
    db.commit()
    db.refresh(user)
    return _user_out(db, user)


# --- Teams ------------------------------------------------------------------

@router.get("/teams", response_model=list[AdminTeamOut])
def list_teams(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    teams = db.query(Team).order_by(Team.name).all()
    return [_team_out(db, t) for t in teams]


@router.post("/teams", response_model=AdminTeamOut, status_code=201)
def create_team(
    payload: AdminTeamCreate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Team name is required")

    team = Team(
        name=name,
        description=payload.description,
        manager_id=payload.manager_id,
        parent_team_id=payload.parent_team_id,
        kind=payload.kind if payload.kind in _VALID_TEAM_KINDS else "team",
        slug=unique_slug(db, name),
    )
    db.add(team)
    db.flush()
    audit.log_audit(
        db,
        action=TEAM_CREATED,
        entity_type="team",
        entity_id=team.id,
        actor_id=admin.id,
        team_id=team.id,
    )
    db.commit()
    db.refresh(team)
    return _team_out(db, team)


@router.patch("/teams/{team_id}", response_model=AdminTeamOut)
def update_team(
    team_id: str,
    payload: AdminTeamUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    fields = payload.model_fields_set
    if "name" in fields and payload.name is not None:
        new_name = payload.name.strip() or team.name
        if new_name != team.name:
            team.name = new_name
            team.slug = unique_slug(db, team.name, exclude_team_id=team.id)
    if "description" in fields:
        team.description = payload.description
    if "manager_id" in fields:
        team.manager_id = payload.manager_id
    if "kind" in fields and payload.kind is not None and payload.kind in _VALID_TEAM_KINDS:
        team.kind = payload.kind
    if "parent_team_id" in fields:
        new_parent = payload.parent_team_id
        if new_parent == team.id:
            raise HTTPException(status_code=400, detail="A team cannot be its own parent")
        if new_parent is not None:
            parent_team = db.get(Team, new_parent)
            if parent_team is None:
                raise HTTPException(status_code=404, detail="Parent team not found")
            # Walk up from the new parent; reaching the team would create a cycle.
            cursor = parent_team.parent_team_id
            while cursor is not None:
                if cursor == team.id:
                    raise HTTPException(
                        status_code=400, detail="Cannot set a descendant as parent"
                    )
                ancestor = db.get(Team, cursor)
                cursor = ancestor.parent_team_id if ancestor else None
        team.parent_team_id = new_parent

    audit.log_audit(
        db,
        action=TEAM_UPDATED,
        entity_type="team",
        entity_id=team.id,
        actor_id=admin.id,
        team_id=team.id,
        detail=",".join(sorted(fields)),
    )
    db.commit()
    db.refresh(team)
    return _team_out(db, team)


@router.delete("/teams/{team_id}")
def delete_team(
    team_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    audit.log_audit(
        db,
        action=TEAM_DELETED,
        entity_type="team",
        entity_id=team.id,
        actor_id=admin.id,
    )
    db.delete(team)
    db.commit()
    return {"ok": True}


# --- Team membership --------------------------------------------------------

@router.get("/teams/{team_id}/members", response_model=list[AdminMemberOut])
def team_members(
    team_id: str, admin: User = Depends(require_admin), db: Session = Depends(get_db)
):
    if db.get(Team, team_id) is None:
        raise HTTPException(status_code=404, detail="Team not found")
    rows = (
        db.query(TeamMember)
        .options(joinedload(TeamMember.user))
        .filter(TeamMember.team_id == team_id)
        .all()
    )
    return [
        AdminMemberOut(
            user_id=m.user_id,
            full_name=m.user.full_name,
            email=m.user.email,
            role=m.role,
        )
        for m in rows
    ]


@router.post("/teams/{team_id}/members", response_model=AdminMemberOut, status_code=201)
def add_member(
    team_id: str,
    payload: AdminMemberAdd,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.get(Team, team_id) is None:
        raise HTTPException(status_code=404, detail="Team not found")
    user = db.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role not in _VALID_MEMBER_ROLES:
        raise HTTPException(status_code=422, detail="Invalid member role")

    existing = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == payload.user_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member of this team")

    member = TeamMember(team_id=team_id, user_id=payload.user_id, role=payload.role)
    db.add(member)
    db.flush()
    audit.log_audit(
        db,
        action=MEMBER_ADDED,
        entity_type="team_member",
        entity_id=member.id,
        actor_id=admin.id,
        team_id=team_id,
        detail=payload.role,
    )
    db.commit()
    db.refresh(member)
    return AdminMemberOut(
        user_id=member.user_id,
        full_name=user.full_name,
        email=user.email,
        role=member.role,
    )


@router.patch("/teams/{team_id}/members/{user_id}", response_model=AdminMemberOut)
def update_member(
    team_id: str,
    user_id: str,
    payload: AdminMemberUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.role not in _VALID_MEMBER_ROLES:
        raise HTTPException(status_code=422, detail="Invalid member role")
    member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        .first()
    )
    if member is None:
        raise HTTPException(status_code=404, detail="Membership not found")

    member.role = payload.role
    audit.log_audit(
        db,
        action=MEMBER_UPDATED,
        entity_type="team_member",
        entity_id=member.id,
        actor_id=admin.id,
        team_id=team_id,
        detail=payload.role,
    )
    db.commit()
    db.refresh(member)
    user = db.get(User, user_id)
    return AdminMemberOut(
        user_id=member.user_id,
        full_name=user.full_name if user else "",
        email=user.email if user else "",
        role=member.role,
    )


@router.delete("/teams/{team_id}/members/{user_id}")
def remove_member(
    team_id: str,
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    member = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id)
        .first()
    )
    if member is not None:
        audit.log_audit(
            db,
            action=MEMBER_REMOVED,
            entity_type="team_member",
            entity_id=member.id,
            actor_id=admin.id,
            team_id=team_id,
        )
        db.delete(member)
        db.commit()
    return {"ok": True}
