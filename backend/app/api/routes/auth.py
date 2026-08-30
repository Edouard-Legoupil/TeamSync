"""Authentication endpoints: Azure AD SSO, callback, current user, logout."""

from __future__ import annotations

import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.azure_ad import acquire_token_by_code, get_authorization_url
from app.auth.dependencies import (
    ACCESS_TOKEN_COOKIE,
    get_accessible_team_ids,
    get_current_user,
    get_primary_team_id,
)
from app.auth.security import create_access_token
from app.config import settings
from app.database import get_db
from app.models import Team, TeamMember, User
from app.models.enums import TeamMemberRole, UserRole
from app.rate_limit import rate_limit
from app.schemas import MeOut, TeamMineOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _set_auth_cookie(response: RedirectResponse, token: str) -> None:
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )


def _azure_configured() -> bool:
    return bool(
        settings.AZURE_AD_CLIENT_ID
        and settings.AZURE_AD_TENANT_ID
        and settings.AZURE_AD_CLIENT_SECRET
    )


@router.get("/login")
def login(
    state: str | None = None, _rate_limit: None = Depends(rate_limit)
) -> RedirectResponse:
    if _azure_configured():
        nonce = state or secrets.token_urlsafe(16)
        return RedirectResponse(get_authorization_url(nonce))

    if settings.ALLOW_DEV_LOGIN:
        # Dev mode without Azure AD: skip SSO entirely and use the local login.
        return RedirectResponse(
            url=f"/api/auth/dev-login?email={quote(settings.DEV_LOGIN_EMAIL)}",
            status_code=302,
        )

    raise HTTPException(
        status_code=500,
        detail=(
            "Azure AD is not configured. Set AZURE_AD_CLIENT_ID, "
            "AZURE_AD_TENANT_ID and AZURE_AD_CLIENT_SECRET, or enable "
            "ALLOW_DEV_LOGIN for local development."
        ),
    )


@router.get("/callback")
def callback(code: str, state: str | None = None, db: Session = Depends(get_db)) -> RedirectResponse:
    token = acquire_token_by_code(code)
    claims = token.get("id_token_claims") or {}
    email = claims.get("preferred_username") or claims.get("email")
    name = claims.get("name") or email

    if not email:
        raise HTTPException(status_code=400, detail="Azure AD did not return an email address")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(email=email, full_name=name or "", role=UserRole.MEMBER.value)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if name:
            user.full_name = name
        user.is_active = True
        db.commit()

    response = RedirectResponse(url="/team", status_code=302)
    _set_auth_cookie(response, create_access_token(user.id))
    return response


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> MeOut:
    accessible = get_accessible_team_ids(db, user)
    teams: list[TeamMineOut] = []
    if accessible:
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
            teams.append(
                TeamMineOut(
                    id=team.id,
                    name=team.name,
                    description=team.description,
                    role=role,
                    is_manager=is_manager,
                )
            )

    return MeOut(
        user=UserOut.model_validate(user),
        primary_team_id=get_primary_team_id(db, user),
        teams=teams,
    )


@router.get("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse(url="/team", status_code=302)
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")
    return response


def _ensure_dev_team(db: Session, user: User) -> None:
    """Give a dev user a working team so the dashboard isn't empty."""
    if get_accessible_team_ids(db, user):
        return
    team = Team(
        name="My Team",
        description="Your personal development workspace",
        manager_id=user.id,
    )
    db.add(team)
    db.flush()
    db.add(TeamMember(team_id=team.id, user_id=user.id, role=TeamMemberRole.LEAD.value))


@router.get("/dev-login")
def dev_login(
    email: str,
    request: Request,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(rate_limit),
) -> RedirectResponse:
    """Local-only convenience login. Requires ALLOW_DEV_LOGIN=true."""
    if not settings.ALLOW_DEV_LOGIN:
        raise HTTPException(status_code=403, detail="Dev login is disabled")

    host = (request.headers.get("host") or "").split(":")[0]
    if host not in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} and not host.endswith(
        ".localhost"
    ):
        raise HTTPException(
            status_code=403, detail="Dev login is only available on localhost"
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            full_name=email.split("@")[0],
            role=UserRole.SUPER_ADMIN.value,
        )
        db.add(user)
        db.flush()
    else:
        user.is_active = True

    _ensure_dev_team(db, user)
    db.commit()

    response = RedirectResponse(url="/team", status_code=302)
    _set_auth_cookie(response, create_access_token(user.id))
    return response
