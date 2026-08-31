"""Database engine, session factory, and declarative base."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite requires special connect args when used across threads (e.g. in
# FastAPI BackgroundTasks / Azure Functions workers).
_connect_args: dict = {}
if settings.DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables that do not exist yet.

    NOTE: For production this is a convenience only. Use Alembic (or another
    migration tool) for real schema migrations.
    """
    from app import models  # noqa: F401  (registers all mapped models)

    Base.metadata.create_all(bind=engine)
    _ensure_dev_columns()


def _ensure_dev_columns() -> None:
    """Best-effort column migration for an existing SQLite dev database.

    ``create_all`` creates new tables but does not add columns to existing
    tables. This keeps ``./start.sh`` working after a schema change without
    forcing developers to delete their local DB. Production uses Alembic.
    """
    if not settings.DATABASE_URL.startswith("sqlite"):
        return

    inspector = inspect(engine)
    _ensure_column(inspector, "meetings", "series_id", "VARCHAR(36)")
    _ensure_column(inspector, "meetings", "source_filename", "VARCHAR(500)")
    _ensure_column(inspector, "teams", "kind", "VARCHAR(32)")
    _ensure_column(inspector, "action_items", "duplicate_of_id", "VARCHAR(36)")
    _ensure_column(inspector, "action_item_comments", "parent_id", "VARCHAR(36)")
    _ensure_column(inspector, "action_items", "source_excerpt", "TEXT")
    _ensure_column(inspector, "action_items", "source_speaker", "VARCHAR(255)")
    _ensure_column(inspector, "action_items", "source_timestamp", "VARCHAR(64)")
    _ensure_column(inspector, "action_items", "confidence", "FLOAT")
    _ensure_column(inspector, "action_items", "attribution_method", "VARCHAR(32)")
    _ensure_column(inspector, "action_items", "requester", "VARCHAR(255)")
    _ensure_column(inspector, "action_items", "related_participants", "JSON")
    _ensure_column(inspector, "action_items", "completion_notes", "TEXT")
    _ensure_column(inspector, "action_items", "completion_links", "TEXT")
    _ensure_column(inspector, "action_items", "completion_follow_up", "TEXT")


def _ensure_column(inspector, table: str, column: str, ddl_type: str) -> None:
    if table not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns(table)}
    if column not in columns:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))
