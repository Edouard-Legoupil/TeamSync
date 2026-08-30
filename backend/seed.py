"""Seed a local development database with demo users, teams, and membership.

Usage (from the ``backend/`` directory, inside the virtualenv):

    python -m seed

Then log in without Azure AD (requires ALLOW_DEV_LOGIN=true):

    GET /api/auth/dev-login?email=supervisor@example.org
"""

from __future__ import annotations

from app.database import SessionLocal, init_db
from app.models import Team, TeamMember, User
from app.models.enums import TeamMemberRole, UserRole


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.org").first()
        if admin is None:
            admin = User(
                email="admin@example.org",
                full_name="Admin User",
                role=UserRole.SUPER_ADMIN.value,
            )
            db.add(admin)
            db.flush()

        supervisor = (
            db.query(User).filter(User.email == "supervisor@example.org").first()
        )
        if supervisor is None:
            supervisor = User(
                email="supervisor@example.org",
                full_name="Field Supervisor",
                role=UserRole.SUPERVISOR.value,
            )
            db.add(supervisor)
            db.flush()

        team = db.query(Team).filter(Team.name == "Field Operations - Syria").first()
        if team is None:
            team = Team(
                name="Field Operations - Syria",
                description="Humanitarian field operations coordination",
                manager_id=supervisor.id,
            )
            db.add(team)
            db.flush()

        if (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.user_id == supervisor.id)
            .first()
            is None
        ):
            db.add(
                TeamMember(
                    team_id=team.id,
                    user_id=supervisor.id,
                    role=TeamMemberRole.LEAD.value,
                )
            )

        if (
            db.query(TeamMember)
            .filter(TeamMember.team_id == team.id, TeamMember.user_id == admin.id)
            .first()
            is None
        ):
            db.add(
                TeamMember(
                    team_id=team.id,
                    user_id=admin.id,
                    role=TeamMemberRole.VIEWER.value,
                )
            )

        db.commit()
        print("Seeded demo data.")
        print("Dev login: /api/auth/dev-login?email=supervisor@example.org")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
