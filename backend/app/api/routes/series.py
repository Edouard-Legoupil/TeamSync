"""Meeting series endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_team_access
from app.database import get_db
from app.models import MeetingSeries, User
from app.schemas import SeriesCreate, SeriesOut

router = APIRouter(tags=["series"])


@router.post("/api/series", response_model=SeriesOut, status_code=201)
def create_series(
    payload: SeriesCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_team_access(db, user, payload.team_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Series name is required")

    series = MeetingSeries(
        name=name, team_id=payload.team_id, description=payload.description
    )
    db.add(series)
    db.commit()
    db.refresh(series)
    return SeriesOut.model_validate(series)


@router.get("/api/teams/{team_id}/series", response_model=list[SeriesOut])
def team_series(
    team_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    require_team_access(db, user, team_id)
    series = (
        db.query(MeetingSeries)
        .filter(MeetingSeries.team_id == team_id)
        .order_by(MeetingSeries.name)
        .all()
    )
    return [SeriesOut.model_validate(s) for s in series]
