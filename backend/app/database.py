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
    """Create tables that do not exist yet and apply dev column migrations.

    NOTE: For production this is a convenience only. Use Alembic (or another
    migration tool) for real schema migrations.
    """
    from app import models  # noqa: F401  (registers all mapped models)

    Base.metadata.create_all(bind=engine)
    _ensure_dev_columns()


# Columns added to existing tables after the initial schema. ``create_all``
# creates new tables but not new columns on existing tables, so these are
# applied as best-effort migrations for both SQLite and PostgreSQL.
_DEV_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "meetings": [
        ("series_id", "VARCHAR(36)"),
        ("source_filename", "VARCHAR(500)"),
    ],
    "teams": [
        ("kind", "VARCHAR(32) NOT NULL DEFAULT 'team'"),
    ],
    "action_items": [
        ("duplicate_of_id", "VARCHAR(36)"),
        ("source_excerpt", "TEXT"),
        ("source_speaker", "VARCHAR(255)"),
        ("source_timestamp", "VARCHAR(64)"),
        ("confidence", "FLOAT"),
        ("attribution_method", "VARCHAR(32)"),
        ("requester", "VARCHAR(255)"),
        ("related_participants", "JSON"),
        ("completion_notes", "TEXT"),
        ("completion_links", "TEXT"),
        ("completion_follow_up", "TEXT"),
    ],
    "action_item_comments": [
        ("parent_id", "VARCHAR(36)"),
    ],
}


def _ensure_dev_columns() -> None:
    """Best-effort column migration for an existing dev database.

    ``create_all`` creates new tables but does not add columns to existing
    tables. This keeps ``./start.sh`` working after a schema change without
    forcing developers to delete their local DB.
    """
    if settings.DATABASE_URL.startswith("sqlite"):
        inspector = inspect(engine)
        for table, columns in _DEV_COLUMNS.items():
            if table not in inspector.get_table_names():
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            for column, ddl_type in columns:
                if column not in existing:
                    with engine.begin() as conn:
                        conn.execute(
                            text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")
                        )
        return

    # PostgreSQL (and other SQL-standard databases): idempotent column add.
    with engine.begin() as conn:
        for table, columns in _DEV_COLUMNS.items():
            for column, ddl_type in columns:
                conn.execute(
                    text(
                        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl_type}"
                    )
                )
