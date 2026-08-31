"""Import every model so ``Base.metadata`` is fully populated."""

from app.models.action_item import ActionItem
from app.models.action_item_comment import ActionItemComment
from app.models.audit_log import AuditLog
from app.models.meeting import Meeting
from app.models.meeting_follow_up import MeetingFollowUp
from app.models.meeting_permission import MeetingPermission
from app.models.meeting_series import MeetingSeries
from app.models.notification import Notification
from app.models.tag import Tag, action_item_tags
from app.models.team import Team, TeamMember
from app.models.user import User

__all__ = [
    "User",
    "Team",
    "TeamMember",
    "Meeting",
    "MeetingSeries",
    "MeetingPermission",
    "MeetingFollowUp",
    "ActionItem",
    "ActionItemComment",
    "AuditLog",
    "Tag",
    "action_item_tags",
    "Notification",
]
