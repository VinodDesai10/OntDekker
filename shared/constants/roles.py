from enum import Enum

class UserRole(str, Enum):
    USER = "USER"
    GUIDE = "GUIDE"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"
