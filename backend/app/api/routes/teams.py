"""Team endpoints: switcher list, dashboard, and meeting listing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import nulls_last
from sqlalchemy.orm import Session, joinedload, selectinload

from app.api.helpers import (
    ACTION_ITEM_CONTEXT_LOAD,
    ACTION_ITEM_TAGS_LOAD,
    PRIORITY_ORDER,
    action_item_out,
    meeting_follow_up_out,
    meeting_list_row_out,
    meeting_summary_out,
)
from app.auth.dependencies import (
    get_accessible_team_ids,
    get_current_user,
    get_team_descendant_ids,
    require_team_access,
)
from app.database import get_db
from app.models import ActionItem, Meeting, Team, TeamMember, User
from app.models.enums import ActionItemStatus, TeamMemberRole, UserRole
from app.schemas import (
    ActionItemOut,
    AllDashboardOut,
    DashboardOut,
    MeetingListRow,
    MemberOut,
    TeamCreate,
    TeamInfo,
    TeamMineOut,
    TeamRollupOut,
    TeamTreeOut,
)
from app.services import audit
from app.services.audit import TEAM_CREATED
from app.services.slugify import unique_slug

router = APIRouter(prefix="/api/teams", tags=["teams"])

_VALID_TEAM_KINDS = {"team", "personal", "project", "donor", "operation"}


@router.get("/mine", response_model=list[TeamMineOut])
def my_teams(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accessible = get_accessible_team_ids(db, user)
    if not accessible:
        return []

    result: list[TeamMineOut] = []
    for team in db.query(Team).filter(Team.id.in_(accessible)).order_by(Team.name).all():
        is_manager = team.manager_id == user.id
        if user.role == UserRole.SUPER_ADMIN.value:
            role = "SUPER_ADMIN"
        elif is_manager:
            role = "LEAD"
        else:
            membership = (
                db.query(TeamMember)
                .filter(TeamMember.team_id == team.id, TeamMember.user_id == user.id)
                .first()
            )
            role = membership.role if membership else "VIEWER"
        result.append(
            TeamMineOut(
                id=team.id,
                name=team.name,
                description=team.description,
                kind=team.kind,
                slug=team.slug,
                role=role,
                is_manager=is_manager,
            )
        )
    return result


@router.post("", response_model=TeamMineOut, status_code=201)
def create_team(
    payload: TeamCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Self-serve workspace creation: the caller becomes manager + sole member."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Team name is required")
    if payload.kind not in _VALID_TEAM_KINDS:
        raise HTTPException(status_code=422, detail="Invalid team kind")

    team = Team(
        name=name,
        description=payload.description,
        kind=payload.kind,
        manager_id=user.id,
        slug=unique_slug(db, name),
    )
    db.add(team)
    db.flush()
    db.add(
        TeamMember(team_id=team.id, user_id=user.id, role=TeamMemberRole.LEAD.value)
    )
    audit.log_audit(
        db,
        action=TEAM_CREATED,
        entity_type="team",
        entity_id=team.id,
        actor_id=user.id,
        team_id=team.id,
    )
    db.commit()
    db.refresh(team)
    return TeamMineOut(
        id=team.id,
        name=team.name,
        description=team.description,
        kind=team.kind,
        slug=team.slug,
        role=TeamMemberRole.LEAD.value,
        is_manager=True,
    )


@router.get("/{team_id}/dashboard", response_model=DashboardOut)
def dashboard(team_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_team_access(db, user, team_id)
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    recent_meetings = (
        db.query(Meeting)
        .options(joinedload(Meeting.team), joinedload(Meeting.series))
        .filter(Meeting.team_id == team_id)
        .order_by(Meeting.date.desc())
        .limit(5)
        .all()
    )

    open_items = (
        db.query(ActionItem)
        .options(
            joinedload(ActionItem.assignee),
            joinedload(ActionItem.duplicate_of).joinedload(ActionItem.meeting),
            *ACTION_ITEM_CONTEXT_LOAD,
            *ACTION_ITEM_TAGS_LOAD,
        )
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(
            Meeting.team_id == team_id,
            ActionItem.status.in_(
                [ActionItemStatus.OPEN.value, ActionItemStatus.IN_PROGRESS.value]
            ),
            ActionItem.duplicate_of_id.is_(None),
        )
        .order_by(nulls_last(ActionItem.due_date), PRIORITY_ORDER)
        .all()
    )

    latest = (
        db.query(Meeting)
        .options(selectinload(Meeting.follow_ups))
        .filter(Meeting.team_id == team_id)
        .order_by(Meeting.date.desc())
        .first()
    )
    follow_ups = [meeting_follow_up_out(fu) for fu in latest.follow_ups] if latest else []

    return DashboardOut(
        team_info=TeamInfo.model_validate(team),
        recent_meetings=[meeting_summary_out(m) for m in recent_meetings],
        open_action_items=[action_item_out(item) for item in open_items],
        follow_ups=follow_ups,
    )


@router.get("/dashboard", response_model=AllDashboardOut)
def all_teams_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dashboard aggregated across every team the user can access."""
    accessible = get_accessible_team_ids(db, user)
    if not accessible:
        return AllDashboardOut()

    recent = (
        db.query(Meeting)
        .options(joinedload(Meeting.team), joinedload(Meeting.series))
        .filter(Meeting.team_id.in_(accessible))
        .order_by(Meeting.date.desc())
        .limit(8)
        .all()
    )

    open_items = (
        db.query(ActionItem)
        .options(
            joinedload(ActionItem.assignee),
            joinedload(ActionItem.duplicate_of).joinedload(ActionItem.meeting),
            *ACTION_ITEM_CONTEXT_LOAD,
            *ACTION_ITEM_TAGS_LOAD,
        )
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(
            Meeting.team_id.in_(accessible),
            ActionItem.status.in_(
                [ActionItemStatus.OPEN.value, ActionItemStatus.IN_PROGRESS.value]
            ),
            ActionItem.duplicate_of_id.is_(None),
        )
        .order_by(nulls_last(ActionItem.due_date), PRIORITY_ORDER)
        .all()
    )

    latest = (
        db.query(Meeting)
        .options(selectinload(Meeting.follow_ups))
        .filter(Meeting.team_id.in_(accessible))
        .order_by(Meeting.date.desc())
        .first()
    )
    follow_ups = [meeting_follow_up_out(fu) for fu in latest.follow_ups] if latest else []

    return AllDashboardOut(
        recent_meetings=[meeting_summary_out(m) for m in recent],
        open_action_items=[action_item_out(item) for item in open_items],
        follow_ups=follow_ups,
    )


@router.get("/{team_id}/action-items", response_model=list[ActionItemOut])
def team_action_items(
    team_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Open action items for a team and its descendants (hierarchy roll-up)."""
    require_team_access(db, user, team_id)
    scope = get_team_descendant_ids(db, {team_id})
    items = (
        db.query(ActionItem)
        .options(
            joinedload(ActionItem.assignee),
            joinedload(ActionItem.duplicate_of).joinedload(ActionItem.meeting),
            *ACTION_ITEM_CONTEXT_LOAD,
            *ACTION_ITEM_TAGS_LOAD,
        )
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(
            Meeting.team_id.in_(scope),
            ActionItem.status.in_(
                [ActionItemStatus.OPEN.value, ActionItemStatus.IN_PROGRESS.value]
            ),
            ActionItem.duplicate_of_id.is_(None),
        )
        .order_by(nulls_last(ActionItem.due_date), PRIORITY_ORDER)
        .all()
    )
    return [action_item_out(item) for item in items]


@router.get("/{team_id}/meetings", response_model=list[MeetingListRow])
def team_meetings(
    team_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_team_access(db, user, team_id)
    meetings = (
        db.query(Meeting)
        .options(
            selectinload(Meeting.action_items),
            joinedload(Meeting.team),
            joinedload(Meeting.series),
        )
        .filter(Meeting.team_id == team_id)
        .order_by(Meeting.date.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [meeting_list_row_out(m) for m in meetings]


@router.get("/{team_id}/members", response_model=list[MemberOut])
def team_members(
    team_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    require_team_access(db, user, team_id)
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    members = (
        db.query(User)
        .join(TeamMember, TeamMember.user_id == User.id)
        .filter(TeamMember.team_id == team_id, User.is_active.is_(True))
        .order_by(User.full_name)
        .all()
    )
    seen = {m.id for m in members}
    if team.manager_id and team.manager_id not in seen:
        manager = db.get(User, team.manager_id)
        if manager and manager.is_active:
            members.insert(0, manager)
    return [MemberOut.model_validate(m) for m in members]


@router.get("/{team_id}/tree", response_model=TeamTreeOut)
def team_tree(
    team_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    require_team_access(db, user, team_id)
    root = db.get(Team, team_id)
    if root is None:
        raise HTTPException(status_code=404, detail="Team not found")

    accessible = get_accessible_team_ids(db, user)
    children_map: dict[str | None, list[Team]] = {}
    for team in db.query(Team).all():
        if team.id in accessible:
            children_map.setdefault(team.parent_team_id, []).append(team)

    def build(node: Team) -> TeamTreeOut:
        kids = sorted(children_map.get(node.id, []), key=lambda t: t.name)
        return TeamTreeOut(
            id=node.id,
            name=node.name,
            description=node.description,
            children=[build(child) for child in kids],
        )

    return build(root)


@router.get("/{team_id}/rollup", response_model=TeamRollupOut)
def team_rollup(
    team_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    require_team_access(db, user, team_id)
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    scope = get_team_descendant_ids(db, {team_id})
    open_count = (
        db.query(ActionItem)
        .join(Meeting, ActionItem.meeting_id == Meeting.id)
        .filter(
            Meeting.team_id.in_(scope),
            ActionItem.status.in_(
                [ActionItemStatus.OPEN.value, ActionItemStatus.IN_PROGRESS.value]
            ),
            ActionItem.duplicate_of_id.is_(None),
        )
        .count()
    )
    recent = (
        db.query(Meeting)
        .options(joinedload(Meeting.team), joinedload(Meeting.series))
        .filter(Meeting.team_id.in_(scope))
        .order_by(Meeting.date.desc())
        .limit(5)
        .all()
    )
    return TeamRollupOut(
        team=TeamInfo.model_validate(team),
        descendant_count=len(scope),
        open_action_items=open_count,
        recent_meetings=[meeting_summary_out(m) for m in recent],
    )


@router.get("/available", response_model=list[TeamInfo])
def available_teams(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Teams the current user has not joined yet (for first-login selection)."""
    joined = {
        m.team_id for m in db.query(TeamMember).filter(TeamMember.user_id == user.id).all()
    }
    teams = db.query(Team).order_by(Team.name).all()
    return [TeamInfo.model_validate(t) for t in teams if t.id not in joined]


@router.post("/{team_id}/join", response_model=TeamMineOut)
def join_team(team_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Self-serve: join a team as a VIEWER (first-login onboarding)."""
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    membership = (
        db.query(TeamMember)
        .filter(TeamMember.team_id == team_id, TeamMember.user_id == user.id)
        .first()
    )
    if membership is None:
        # Self-join is only for first-login onboarding. Once a user belongs to
        # a team, access changes must go through an administrator.
        already_member = (
            db.query(TeamMember).filter(TeamMember.user_id == user.id).first()
        )
        if already_member is not None:
            raise HTTPException(
                status_code=409,
                detail="You already belong to a team. Ask an administrator to change your access.",
            )
        membership = TeamMember(
            team_id=team_id, user_id=user.id, role=TeamMemberRole.VIEWER.value
        )
        db.add(membership)
        db.commit()
        db.refresh(membership)

    return TeamMineOut(
        id=team.id,
        name=team.name,
        description=team.description,
        kind=team.kind,
        slug=team.slug,
        role=membership.role,
        is_manager=team.manager_id == user.id,
    )
