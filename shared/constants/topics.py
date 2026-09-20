from enum import Enum

class KafkaTopic(str, Enum):
    USER_EVENTS = "user-events"
    STORY_EVENTS = "story-events"
    COMMUNITY_EVENTS = "community-events"
    EXPEDITION_EVENTS = "expedition-events"
    GUIDE_EVENTS = "guide-events"
    NOTIFICATION_EVENTS = "notification-events"
    RECOMMENDATION_EVENTS = "recommendation-events"
    MODERATION_EVENTS = "moderation-events"
    CHAT_EVENTS = "chat-events"
    SYSTEM_EVENTS = "system-events"
