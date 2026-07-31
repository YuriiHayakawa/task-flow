from enum import Enum


class TaskSortBy(str, Enum):
    DUE_DATE = "due_date"
    PRIORITY = "priority"
    CREATED_AT = "created_at"
