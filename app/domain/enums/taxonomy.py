from enum import StrEnum


class RoleFieldType(StrEnum):
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    NUMBER = "number"
    TEXT = "text"
    BOOLEAN = "boolean"


class TagStatus(StrEnum):
    APPROVED = "approved"
    PENDING = "pending"
    REJECTED = "rejected"
