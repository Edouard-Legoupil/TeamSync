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

from app.api.helpers import (
    action_item_out,
    meeting_list_row_out,
    meeting_summary_out,
    today_in_app_tz,
)  # noqa: E402
from app.auth.dependencies import get_accessible_team_ids, get_meeting_role  # noqa: E402
from app.database import Base  # noqa: E402
from app.models import (  # noqa: E402
    ActionItem,
    Meeting,
    MeetingPermission,
    MeetingSeries,
    Tag,
    Team,
    TeamMember,
    User,
)
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
from app.services.processing import (  # noqa: E402
    _build_follow_up_context,
    _find_duplicate,
    _follow_ups_to_markdown,
    _normalize,
    _parse_follow_ups,
    _parse_meeting_date,
)
from app.services.tagging import parse_action_item_tags, upsert_tag  # noqa: E402
from app.services.transcript_parser import find_evidence, parse_segments  # noqa: E402
from app.services.notifications import notify_mentions  # noqa: E402
from app.api.routes.analytics import _group_tags  # noqa: E402
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


class TestActionItemContext(BaseTestCase):
    def test_identification_fields(self):
        team = self._team("Ops")
        series = MeetingSeries(name="Weekly Ops", team_id=team.id)
        self.db.add(series)
        self.db.flush()

        meeting = self._meeting(team, "Ops Standup")
        meeting.series_id = series.id
        assigned = ActionItem(
            meeting_id=meeting.id,
            description="Do the thing",
            assignee_id=self.admin.id,
            status=ActionItemStatus.OPEN.value,
        )
        self.db.add(assigned)
        self.db.flush()

        out = action_item_out(assigned)
        self.assertEqual(out.team_id, team.id)
        self.assertEqual(out.team_name, "Ops")
        self.assertEqual(out.series_id, series.id)
        self.assertEqual(out.series_name, "Weekly Ops")
        self.assertEqual(out.meeting_title, "Ops Standup")
        self.assertEqual(out.assignee_name, "Admin")

    def test_unassigned_and_no_series(self):
        team = self._team("Ops")
        meeting = self._meeting(team, "Ad hoc")
        item = ActionItem(
            meeting_id=meeting.id,
            description="Someone must do this",
            status=ActionItemStatus.OPEN.value,
        )
        self.db.add(item)
        self.db.flush()

        out = action_item_out(item)
        self.assertIsNone(out.assignee_name)
        self.assertIsNone(out.series_id)
        self.assertIsNone(out.series_name)
        self.assertEqual(out.team_name, "Ops")
        self.assertEqual(out.meeting_title, "Ad hoc")


class TestMeetingContext(BaseTestCase):
    def test_meeting_summary_out(self):
        team = self._team("Ops")
        series = MeetingSeries(name="Weekly Ops", team_id=team.id)
        self.db.add(series)
        self.db.flush()
        meeting = self._meeting(team, "Ops Standup")
        meeting.series_id = series.id
        self.db.flush()

        summary = meeting_summary_out(meeting)
        self.assertEqual(summary.team_name, "Ops")
        self.assertEqual(summary.series_name, "Weekly Ops")
        self.assertEqual(summary.id, meeting.id)

    def test_meeting_list_row_out(self):
        team = self._team("Ops")
        meeting = self._meeting(team, "Ops Standup")
        item = ActionItem(
            meeting_id=meeting.id,
            description="Do the thing",
            status=ActionItemStatus.OPEN.value,
        )
        self.db.add(item)
        self.db.flush()

        row = meeting_list_row_out(meeting)
        self.assertEqual(row.team_name, "Ops")
        self.assertEqual(row.action_count, 1)

    def test_parse_meeting_date(self):
        self.assertIsNone(_parse_meeting_date(None))
        self.assertIsNone(_parse_meeting_date(""))
        self.assertIsNone(_parse_meeting_date("not a date"))
        parsed = _parse_meeting_date("2026-08-31")
        self.assertIsNotNone(parsed)
        self.assertEqual((parsed.year, parsed.month, parsed.day), (2026, 8, 31))


class TestTagging(BaseTestCase):
    def test_upsert_tag_first_write_wins(self):
        first = upsert_tag(self.db, "Fundraising", "thematic")
        second = upsert_tag(self.db, "fundraising", "geographic")
        self.assertEqual(first.id, second.id)
        self.assertEqual(first.type, "thematic")
        self.db.commit()
        self.assertEqual(self.db.query(Tag).count(), 1)

    def test_parse_action_item_tags(self):
        parsed = parse_action_item_tags(
            [
                {
                    "task": "Share flexible funding report",
                    "tags": [{"name": "Reporting", "type": "process"}, {"name": "MENA"}],
                },
                {"task": "Fix generator", "tags": ["RAF"]},
            ]
        )
        self.assertEqual(
            parsed["share flexible funding report"][0],
            {"name": "Reporting", "type": "process"},
        )
        self.assertEqual(
            parsed["fix generator"][0], {"name": "RAF", "type": "thematic"}
        )

    def test_action_item_out_includes_tags(self):
        team = self._team()
        meeting = self._meeting(team)
        item = ActionItem(
            meeting_id=meeting.id,
            description="Do the thing",
            status=ActionItemStatus.OPEN.value,
        )
        tag = upsert_tag(self.db, "Fundraising", "thematic")
        item.tags.append(tag)
        self.db.add(item)
        self.db.flush()

        out = action_item_out(item)
        self.assertEqual([t.name for t in out.tags], ["Fundraising"])
        self.assertEqual(out.tags[0].type, "thematic")


class TestTranscriptParser(BaseTestCase):
    def test_vtt_with_speakers(self):
        raw = (
            "WEBVTT\n\n"
            "00:14:23.000 --> 00:14:26.000\n"
            "Laurie: I need the flexible funding report\n\n"
            "00:14:30.000 --> 00:14:33.000\n"
            "Sam: I will share it\n"
        )
        result = parse_segments(raw)
        self.assertTrue(result["has_speakers"])
        self.assertTrue(result["has_timestamps"])
        self.assertEqual(result["segments"][0]["speaker"], "Laurie")
        self.assertEqual(result["segments"][0]["timestamp"], "00:14:23")

    def test_bracketed_timestamp(self):
        result = parse_segments("[14:23] Laurie: hello there")
        seg = result["segments"][0]
        self.assertEqual(seg["speaker"], "Laurie")
        self.assertEqual(seg["timestamp"], "14:23")

    def test_find_evidence(self):
        segs = parse_segments("[14:23] Laurie: I need the flexible funding report")[
            "segments"
        ]
        ev = find_evidence(segs, "flexible funding report")
        self.assertEqual(ev["speaker"], "Laurie")
        self.assertEqual(ev["timestamp"], "14:23")

    def test_no_cues(self):
        result = parse_segments("Just plain prose with no structure.")
        self.assertFalse(result["has_speakers"])
        self.assertFalse(result["has_timestamps"])


class TestActionItemEvidence(BaseTestCase):
    def test_action_item_out_evidence(self):
        team = self._team()
        meeting = self._meeting(team)
        item = ActionItem(
            meeting_id=meeting.id,
            description="Share report",
            status=ActionItemStatus.OPEN.value,
            source_speaker="Laurie",
            source_timestamp="14:23",
            confidence=0.9,
            attribution_method="transcript",
            requester="Rep",
            related_participants=["MENA", "DIPS"],
            completion_notes="Sent to team",
        )
        self.db.add(item)
        self.db.flush()

        out = action_item_out(item)
        self.assertEqual(out.source_speaker, "Laurie")
        self.assertEqual(out.confidence, 0.9)
        self.assertEqual(out.attribution_method, "transcript")
        self.assertEqual(out.related_participants, ["MENA", "DIPS"])
        self.assertEqual(out.completion_notes, "Sent to team")


class TestNotifications(BaseTestCase):
    def test_mention_resolution(self):
        team = self._team("Ops")
        member = User(
            email="laurie@example.org",
            full_name="Laurie Smith",
            role=UserRole.MEMBER.value,
        )
        self.db.add(member)
        self.db.flush()
        self.db.add(
            TeamMember(
                team_id=team.id,
                user_id=member.id,
                role=TeamMemberRole.CONTRIBUTOR.value,
            )
        )
        meeting = self._meeting(team)
        item = ActionItem(
            meeting_id=meeting.id,
            description="Do the thing",
            status=ActionItemStatus.OPEN.value,
        )
        self.db.add(item)
        self.db.flush()

        created = notify_mentions(
            self.db, actor=self.admin, action_item=item, body="please handle @Laurie"
        )
        self.db.commit()
        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].recipient_id, member.id)
        self.assertEqual(created[0].meeting_id, meeting.id)

    def test_mention_skips_self_and_unknown(self):
        team = self._team("Ops")
        meeting = self._meeting(team)
        item = ActionItem(
            meeting_id=meeting.id,
            description="Do the thing",
            status=ActionItemStatus.OPEN.value,
        )
        self.db.add(item)
        self.db.flush()

        self.assertEqual(
            notify_mentions(
                self.db, actor=self.admin, action_item=item, body="cc @Admin @nobody"
            ),
            [],
        )


class TestMeetingPermissions(BaseTestCase):
    def test_organizer_is_owner(self):
        team = self._team("Ops")
        meeting = self._meeting(team)
        meeting.organizer_id = self.admin.id
        self.db.flush()
        self.assertEqual(get_meeting_role(self.db, self.admin, meeting), "owner")

    def test_team_member_roles(self):
        team = self._team("Ops")
        lead = User(
            email="lead@example.org", full_name="Lead", role=UserRole.MEMBER.value
        )
        contributor = User(
            email="contrib@example.org", full_name="Contrib", role=UserRole.MEMBER.value
        )
        viewer = User(
            email="viewer@example.org", full_name="Viewer", role=UserRole.MEMBER.value
        )
        self.db.add_all([lead, contributor, viewer])
        self.db.flush()
        self.db.add_all(
            [
                TeamMember(
                    team_id=team.id, user_id=lead.id, role=TeamMemberRole.LEAD.value
                ),
                TeamMember(
                    team_id=team.id,
                    user_id=contributor.id,
                    role=TeamMemberRole.CONTRIBUTOR.value,
                ),
                TeamMember(
                    team_id=team.id, user_id=viewer.id, role=TeamMemberRole.VIEWER.value
                ),
            ]
        )
        meeting = self._meeting(team)
        self.db.flush()

        self.assertEqual(get_meeting_role(self.db, lead, meeting), "owner")
        self.assertEqual(
            get_meeting_role(self.db, contributor, meeting), "contributor"
        )
        self.assertEqual(get_meeting_role(self.db, viewer, meeting), "viewer")

    def test_explicit_permission_override(self):
        team = self._team("Ops")
        viewer = User(
            email="viewer@example.org", full_name="Viewer", role=UserRole.MEMBER.value
        )
        self.db.add(viewer)
        self.db.flush()
        self.db.add(
            TeamMember(
                team_id=team.id, user_id=viewer.id, role=TeamMemberRole.VIEWER.value
            )
        )
        meeting = self._meeting(team)
        self.db.flush()
        self.db.add(
            MeetingPermission(meeting_id=meeting.id, user_id=viewer.id, role="owner")
        )
        self.db.flush()

        self.assertEqual(get_meeting_role(self.db, viewer, meeting), "owner")


class TestFollowUps(BaseTestCase):
    def test_parse_and_render(self):
        parsed = _parse_follow_ups(
            [
                {
                    "follow_up_type": "meeting",
                    "title": "Sync on RAF",
                    "participants": ["Laurie", "Ops"],
                    "rationale": "RAF questions",
                },
                {"follow_up_type": "email", "title": "Send report"},
                {"follow_up_type": "bogus", "title": "Bad type"},
            ]
        )
        self.assertEqual(len(parsed), 3)
        self.assertEqual(parsed[0]["follow_up_type"], "meeting")
        self.assertEqual(parsed[2]["follow_up_type"], "ad_hoc")
        md = _follow_ups_to_markdown(parsed)
        self.assertIn("## Suggested Follow-Up", md)
        self.assertIn("Sync on RAF", md)

    def test_build_context_includes_completion_notes(self):
        team = self._team()
        meeting = self._meeting(team)
        meeting.minutes_markdown = "## Summary\nDone things"
        item = ActionItem(
            meeting_id=meeting.id,
            description="Share report",
            status=ActionItemStatus.DONE.value,
            completion_notes="Sent to team",
            completion_follow_up="Schedule review",
        )
        self.db.add(item)
        self.db.flush()

        ctx = _build_follow_up_context(self.db, meeting)
        self.assertIn("Share report", ctx)
        self.assertIn("Sent to team", ctx)
        self.assertIn("Schedule review", ctx)


class TestAnalyticsHelpers(BaseTestCase):
    def test_group_tags_by_type(self):
        team = self._team()
        meeting = self._meeting(team)
        item = ActionItem(
            meeting_id=meeting.id,
            description="Share report",
            status=ActionItemStatus.OPEN.value,
        )
        tag = Tag(name="RAF", type="thematic")
        item.tags.append(tag)
        self.db.add(item)
        self.db.flush()

        thematic = _group_tags([item], "thematic")
        self.assertEqual(len(thematic), 1)
        self.assertEqual(thematic[0].label, "RAF")
        self.assertEqual(thematic[0].count, 1)
        self.assertEqual(_group_tags([item], "geographic"), [])


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
