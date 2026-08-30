"""Core unit tests for the fragile logic (no network, no external services).

Run from the backend directory:

    ./venv/bin/python -m unittest discover -s tests
"""

import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ.setdefault("APP_TIMEZONE", "UTC")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.api.helpers import action_item_out, today_in_app_tz  # noqa: E402
from app.auth.dependencies import get_accessible_team_ids  # noqa: E402
from app.database import Base  # noqa: E402
from app.models import ActionItem, Meeting, Team, TeamMember, User  # noqa: E402
from app.models.enums import (  # noqa: E402
    ActionItemPriority,
    ActionItemStatus,
    MeetingStatus,
    TeamMemberRole,
    UserRole,
)
from app.services.email_draft import build_email_draft, markdown_to_text  # noqa: E402
from app.services.markdown_sync import sync_action_item_to_markdown  # noqa: E402
from app.services.outlook import build_ics  # noqa: E402
from app.services.processing import _find_duplicate, _normalize  # noqa: E402
from app.services.word_export import markdown_to_docx_bytes  # noqa: E402


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()
        self.admin = User(
            email="admin@example.org", full_name="Admin", role=UserRole.SUPER_ADMIN.value
        )
        self.db.add(self.admin)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _team(self, name="Team", manager=None, parent=None):
        team = Team(name=name, manager_id=(manager or self.admin).id, parent_team_id=parent)
        self.db.add(team)
        self.db.flush()
        return team

    def _meeting(self, team, title="Meeting", status=MeetingStatus.PROCESSED.value):
        meeting = Meeting(title=title, team_id=team.id, raw_transcript="x", status=status)
        self.db.add(meeting)
        self.db.flush()
        return meeting


class TestRBAC(BaseTestCase):
    def test_member_sees_only_membership(self):
        member = User(email="m@example.org", full_name="M", role=UserRole.MEMBER.value)
        self.db.add(member)
        self.db.flush()
        t1 = self._team("T1")
        t2 = self._team("T2")
        self.db.add(TeamMember(team_id=t1.id, user_id=member.id, role=TeamMemberRole.VIEWER.value))
        self.db.commit()
        self.assertEqual(get_accessible_team_ids(self.db, member), {t1.id})

    def test_super_admin_sees_all(self):
        t1 = self._team("T1")
        self.db.commit()
        self.assertIn(t1.id, get_accessible_team_ids(self.db, self.admin))

    def test_supervisor_sees_descendants(self):
        supervisor = User(
            email="s@example.org", full_name="S", role=UserRole.SUPERVISOR.value
        )
        self.db.add(supervisor)
        self.db.flush()
        parent = self._team("Parent", manager=supervisor)
        child = self._team("Child", parent=parent.id)
        grand = self._team("Grand", parent=child.id)
        self.db.commit()
        self.assertEqual(
            get_accessible_team_ids(self.db, supervisor), {parent.id, child.id, grand.id}
        )


class TestDedup(BaseTestCase):
    def test_normalize(self):
        self.assertEqual(
            _normalize("  Follow-Up   ON the WATER point! "),
            "follow up on the water point",
        )

    def test_find_duplicate(self):
        team = self._team()
        m1 = self._meeting(team, "M1")
        m2 = self._meeting(team, "M2", status=MeetingStatus.DRAFT.value)
        item = ActionItem(
            meeting_id=m1.id,
            description="Fix the generator",
            status=ActionItemStatus.OPEN.value,
        )
        self.db.add(item)
        self.db.commit()
        self.assertEqual(_find_duplicate(self.db, m2, "fix THE generator"), item.id)
        self.assertIsNone(_find_duplicate(self.db, m2, "Something brand new"))


class TestMarkdownSync(BaseTestCase):
    def test_sync_replaces_row(self):
        team = self._team()
        meeting = self._meeting(team)
        item = ActionItem(
            meeting_id=meeting.id,
            description="Do the thing",
            assignee_id=self.admin.id,
            priority=ActionItemPriority.HIGH.value,
            status=ActionItemStatus.OPEN.value,
        )
        self.db.add(item)
        self.db.flush()
        old_row = "| Do the thing | Unassigned |  | MEDIUM | OPEN |"
        meeting.action_items_markdown = (
            "| Task | Assignee | Due Date | Priority | Status |\n"
            "|---|---|---|---|---|\n" + old_row
        )
        item.source_markdown = old_row
        item.status = ActionItemStatus.DONE.value
        sync_action_item_to_markdown(self.db, meeting, item)
        self.assertIn("| Do the thing | Admin |  | HIGH | DONE |", meeting.action_items_markdown)
        self.assertNotIn(old_row, meeting.action_items_markdown)


class TestDueFlags(BaseTestCase):
    def test_overdue_due_soon(self):
        today = today_in_app_tz()
        team = self._team()
        meeting = self._meeting(team)
        overdue = ActionItem(
            meeting_id=meeting.id, description="o",
            due_date=today - timedelta(days=1), status=ActionItemStatus.OPEN.value,
        )
        soon = ActionItem(
            meeting_id=meeting.id, description="s",
            due_date=today + timedelta(days=1), status=ActionItemStatus.OPEN.value,
        )
        far = ActionItem(
            meeting_id=meeting.id, description="f",
            due_date=today + timedelta(days=10), status=ActionItemStatus.OPEN.value,
        )
        self.db.add_all([overdue, soon, far])
        self.db.flush()

        o = action_item_out(overdue)
        s = action_item_out(soon)
        f = action_item_out(far)
        self.assertTrue(o.overdue and not o.due_soon)
        self.assertTrue(s.due_soon and not s.overdue)
        self.assertFalse(f.overdue or f.due_soon)


class TestExport(BaseTestCase):
    def test_word_export(self):
        data = markdown_to_docx_bytes(
            "# Title\n\n## Summary\n\n- one\n- two\n\n| A | B |\n|---|---|\n| 1 | 2 |",
            "Meeting",
        )
        self.assertGreater(len(data), 0)
        self.assertEqual(data[:2], b"PK")  # .docx is a zip archive

    def test_ics(self):
        team = self._team()
        meeting = self._meeting(team)
        meeting.date = datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc)
        meeting.minutes_markdown = "## Summary\n\n- hello"
        ics = build_ics(meeting)
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("BEGIN:VEVENT", ics)
        self.assertIn("SUMMARY:Meeting Minutes: Meeting", ics)
        self.assertIn("DTSTART:20260830T100000Z", ics)

    def test_email_draft(self):
        team = self._team()
        meeting = self._meeting(team)
        meeting.date = datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc)
        meeting.minutes_markdown = "## Summary\n\nHello **world**"
        draft = build_email_draft(meeting)
        self.assertIn("Meeting Minutes: Meeting", draft["subject"])
        self.assertIn("Hello world", draft["body"])
        self.assertIn("mailto:", draft["mailto"])

    def test_markdown_to_text(self):
        self.assertEqual(markdown_to_text("## Hi\n\n- a\n- b\n\n**bold**"), "Hi\n\n- a\n- b\n\nbold")


if __name__ == "__main__":
    unittest.main()
