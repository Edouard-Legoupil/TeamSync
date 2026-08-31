"""String-backed enums shared across the ORM and API schemas."""

from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    SUPERVISOR = "SUPERVISOR"
    MEMBER = "MEMBER"


class TeamMemberRole(str, Enum):
    LEAD = "LEAD"
    CONTRIBUTOR = "CONTRIBUTOR"
    VIEWER = "VIEWER"


class MeetingStatus(str, Enum):
    DRAFT = "DRAFT"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class ActionItemStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


class ActionItemPriority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TagType(str, Enum):
    THEMATIC = "thematic"
    ORGANIZATIONAL = "organizational"
    GEOGRAPHIC = "geographic"
    PROCESS = "process"
    BEHAVIOR = "behavior"
