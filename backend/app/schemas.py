"""Pydantic schemas for API requests and responses."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


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
    role: str
    is_manager: bool = False


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


class MeetingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    date: datetime
    status: str


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


class DashboardOut(BaseModel):
    team_info: TeamInfo
    recent_meetings: list[MeetingSummary] = []
    open_action_items: list[ActionItemOut] = []
    next_agenda_preview: str = ""


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
    confidence: Optional[float] = None


class MeetingListRow(BaseModel):
    id: str
    title: str
    date: datetime
    status: str
    action_count: int = 0


class MeetingCreatedOut(BaseModel):
    meeting_id: str
    status: str


# --- Action items -----------------------------------------------------------

class ActionItemUpdate(BaseModel):
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[date] = None


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
    meeting_id: str
    title: str
    date: datetime
    status: str
    team_name: str
    snippet: str


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


class ActionItemWithContext(ActionItemOut):
    team_id: str = ""
    team_name: str = ""
    meeting_title: str = ""


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


class AdminTeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    manager_id: Optional[str] = None
    parent_team_id: Optional[str] = None


class AdminTeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    manager_id: Optional[str] = None
    parent_team_id: Optional[str] = None
    member_count: int = 0


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
