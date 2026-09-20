from enum import Enum


# ---------------------------------------------------------------------------
# Story / Post Status
# ---------------------------------------------------------------------------

class StoryStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class PostStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


# ---------------------------------------------------------------------------
# Post / Story Visibility
# ---------------------------------------------------------------------------

class PostVisibility(str, Enum):
    PUBLIC = "PUBLIC"          # Visible to everyone
    COMMUNITY = "COMMUNITY"    # Visible only to community members
    PRIVATE = "PRIVATE"        # Visible only to the author


# ---------------------------------------------------------------------------
# Media
# ---------------------------------------------------------------------------

class MediaType(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


# ---------------------------------------------------------------------------
# Community Status & Visibility
# ---------------------------------------------------------------------------

class CommunityStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class CommunityVisibility(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


# ---------------------------------------------------------------------------
# Community Member Roles & Status
# ---------------------------------------------------------------------------

class MemberRole(str, Enum):
    OWNER = "OWNER"
    MODERATOR = "MODERATOR"
    MEMBER = "MEMBER"
    BANNED = "BANNED"


class MembershipStatus(str, Enum):
    ACTIVE = "ACTIVE"
    LEFT = "LEFT"
    REMOVED = "REMOVED"
    BANNED = "BANNED"


class JoinRequestStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Expedition & Guide Status
# ---------------------------------------------------------------------------

class ExpeditionStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class GuideStatus(str, Enum):
    APPLIED = "APPLIED"
    VERIFIED = "VERIFIED"
    SUSPENDED = "SUSPENDED"
    REJECTED = "REJECTED"
