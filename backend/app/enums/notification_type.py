from enum import Enum


class NotificationType(str, Enum):
    DUE_SOON = "DUE_SOON"
    NEW_COMMENT = "NEW_COMMENT"
    TASK_CHANGED = "TASK_CHANGED"
