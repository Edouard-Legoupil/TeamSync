"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


# --- User & auth ------------------------------------------------------------

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    avatar_url: Optional[str] = None


class TeamMineOut(BaseModel):
    """A team as shown in the top-bar switcher."""

    id: str
    name: str
    description: Optional[str] = None
    kind: str = "team"
    slug: Optional[str] = None
    role: str
    is_manager: bool = False

    @field_validator("kind", mode="before")
    @classmethod
    def _default_kind(cls, value: object) -> str:
        # Legacy rows may have NULL kind from before the column existed.
        return value or "team"


class TeamCreate(BaseModel):
    """Self-serve workspace/team creation."""

    name: str
    kind: str = "team"
    description: Optional[str] = None


class MeOut(BaseModel):
    user: UserOut
    primary_team_id: Optional[str] = None
    teams: list[TeamMineOut] = []


# --- Teams ------------------------------------------------------------------

class TeamInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    slug: Optional[str] = None


class MeetingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    date: datetime
    status: str
    team_id: str = ""
    team_name: str = ""
    series_id: Optional[str] = None
    series_name: Optional[str] = None


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    type: str = "thematic"


class TagUpsert(BaseModel):
    name: str
    type: str = "thematic"


class TagCreate(BaseModel):
    name: str
    type: str = "thematic"


class ActionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    meeting_id: str
    description: str
    assignee_id: Optional[str] = None
    assignee_name: Optional[str] = None
    due_date: Optional[date] = None
    priority: str
    status: str
    source_markdown: Optional[str] = None
    overdue: bool = False
    due_soon: bool = False
    duplicate_of_id: Optional[str] = None
    duplicate_of_title: Optional[str] = None
    duplicate_meeting_id: Optional[str] = None
    duplicate_meeting_title: Optional[str] = None
    team_id: str = ""
    team_name: str = ""
    series_id: Optional[str] = None
    series_name: Optional[str] = None
    meeting_title: str = ""
    tags: list[TagOut] = []
    source_excerpt: Optional[str] = None
    source_speaker: Optional[str] = None
    source_timestamp: Optional[str] = None
    confidence: Optional[float] = None
    attribution_method: Optional[str] = None
    requester: Optional[str] = None
    related_participants: Optional[list[str]] = None
    completion_notes: Optional[str] = None
    completion_links: Optional[str] = None
    completion_follow_up: Optional[str] = None


class MeetingFollowUpOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    follow_up_type: str
    title: str
    issue: Optional[str] = None
    participants: Optional[list[str]] = None
    rationale: Optional[str] = None
    status: str = "suggested"
    created_at: datetime


class DashboardOut(BaseModel):
    team_info: TeamInfo
    recent_meetings: list[MeetingSummary] = []
    open_action_items: list[ActionItemOut] = []
    follow_ups: list[MeetingFollowUpOut] = []


class AllDashboardOut(BaseModel):
    """Aggregated dashboard across every team the user can access."""

    recent_meetings: list[MeetingSummary] = []
    open_action_items: list[ActionItemOut] = []
    follow_ups: list[MeetingFollowUpOut] = []


class MeetingDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    date: datetime
    team_id: str
    organizer_id: Optional[str] = None
    status: str
    series_id: Optional[str] = None
    minutes_markdown: Optional[str] = None
    action_items_markdown: Optional[str] = None
    next_agenda_markdown: Optional[str] = None
    follow_ups: list[MeetingFollowUpOut] = []
    confidence: Optional[float] = None
    raw_transcript: str = ""
    source_filename: Optional[str] = None
    my_role: str = "viewer"


class MeetingPermissionOut(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str


class MeetingPermissionUpsert(BaseModel):
    user_id: str
    role: str


class MeetingListRow(BaseModel):
    id: str
    title: str
    date: datetime
    status: str
    action_count: int = 0
    team_id: str = ""
    team_name: str = ""
    series_id: Optional[str] = None
    series_name: Optional[str] = None


class MeetingCreatedOut(BaseModel):
    meeting_id: str
    status: str


# --- Action items -----------------------------------------------------------

class ActionItemUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[date] = None
    priority: Optional[str] = None
    tags: Optional[list[TagUpsert]] = None
    completion_notes: Optional[str] = None
    completion_links: Optional[str] = None
    completion_follow_up: Optional[str] = None


class ActionItemCommentCreate(BaseModel):
    body: str
    parent_id: Optional[str] = None


class ActionItemCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action_item_id: str
    author_id: Optional[str] = None
    author_name: Optional[str] = None
    body: str
    parent_id: Optional[str] = None
    created_at: datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    meeting_id: Optional[str] = None
    text: Optional[str] = None
    read: bool = False
    actor_name: Optional[str] = None
    created_at: datetime


class UnreadCountOut(BaseModel):
    count: int = 0


class ActionItemHistoryEntry(BaseModel):
    type: str  # "change" | "comment"
    field: Optional[str] = None
    from_value: Optional[str] = None
    to_value: Optional[str] = None
    comment: Optional[str] = None
    actor_name: Optional[str] = None
    created_at: datetime


# --- Email draft ------------------------------------------------------------

class EmailDraftOut(BaseModel):
    subject: str
    body: str
    mailto: str


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: str


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    minutes_markdown: Optional[str] = None
    next_agenda_markdown: Optional[str] = None
    team_id: Optional[str] = None
    series_id: Optional[str] = None
    date: Optional[datetime] = None


class MeetingImportRequest(BaseModel):
    team_id: str
    text: str
    title: Optional[str] = None
    series_id: Optional[str] = None


class SeriesCreate(BaseModel):
    team_id: str
    name: str
    description: Optional[str] = None


class SeriesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    team_id: str
    description: Optional[str] = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    entity_type: str
    entity_id: str
    actor_id: Optional[str] = None
    detail: Optional[str] = None
    created_at: datetime


class SearchResult(BaseModel):
    kind: str = "meeting"  # meeting | action_item | follow_up
    meeting_id: str
    title: str = ""
    date: datetime
    status: str = ""
    team_name: str = ""
    snippet: str = ""
    speaker: Optional[str] = None
    action_item_id: Optional[str] = None


class TeamTreeOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    children: list["TeamTreeOut"] = []


class TeamRollupOut(BaseModel):
    team: TeamInfo
    descendant_count: int
    open_action_items: int
    recent_meetings: list[MeetingSummary] = []


class CountByKey(BaseModel):
    key: str
    label: str
    count: int


class AnalyticsOut(BaseModel):
    open_count: int = 0
    overdue_count: int = 0
    by_team: list[CountByKey] = []
    by_theme: list[CountByKey] = []
    by_region: list[CountByKey] = []
    by_assignee: list[CountByKey] = []
    top_themes: list[CountByKey] = []
    follow_up_types: list[CountByKey] = []


class ActionItemWithContext(ActionItemOut):
    """An action item enriched with its team/series/meeting identification.

    Kept as a distinct response model so the frontend can type it separately,
    but the fields now live on ``ActionItemOut`` and are always populated.
    """


class DigestItemOut(BaseModel):
    description: str
    assignee_name: Optional[str] = None
    due_date: Optional[date] = None
    priority: str
    overdue: bool = False
    team_name: str = ""
    meeting_title: str = ""


class DigestOut(BaseModel):
    subject: str
    body: str
    mailto: str
    items: list[DigestItemOut] = []


class OutlookOut(BaseModel):
    subject: str
    body: str
    ics_url: str
    calendar_web_url: str
    email_web_url: str
    server_send_enabled: bool = False


# --- Admin ------------------------------------------------------------------

class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    team_count: int = 0


class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None


class AdminTeamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    manager_id: Optional[str] = None
    parent_team_id: Optional[str] = None
    kind: str = "team"


class AdminTeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    manager_id: Optional[str] = None
    parent_team_id: Optional[str] = None
    kind: Optional[str] = None


class AdminTeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    manager_id: Optional[str] = None
    parent_team_id: Optional[str] = None
    kind: str = "team"
    slug: Optional[str] = None
    member_count: int = 0

    @field_validator("kind", mode="before")
    @classmethod
    def _default_kind(cls, value: object) -> str:
        # Legacy rows may have NULL kind from before the column existed.
        return value or "team"


class AdminMemberOut(BaseModel):
    user_id: str
    full_name: str
    email: str
    role: str


class AdminMemberAdd(BaseModel):
    user_id: str
    role: str = "VIEWER"


class AdminMemberUpdate(BaseModel):
    role: str
