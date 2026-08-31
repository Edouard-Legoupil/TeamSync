"""Tag endpoints: list and create multi-dimensional tags."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import Tag, User
from app.schemas import TagCreate, TagOut
from app.services.tagging import VALID_TAG_TYPES, upsert_tag

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagOut])
def list_tags(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    tags = db.query(Tag).order_by(Tag.type, Tag.name).all()
    return [TagOut.model_validate(t) for t in tags]


@router.post("", response_model=TagOut, status_code=201)
def create_tag(
    payload: TagCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tag name is required")
    if payload.type not in VALID_TAG_TYPES:
        raise HTTPException(status_code=422, detail="Invalid tag type")
    tag = upsert_tag(db, name, payload.type)
    db.commit()
    db.refresh(tag)
    return TagOut.model_validate(tag)
