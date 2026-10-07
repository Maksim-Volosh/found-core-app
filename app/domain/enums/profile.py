from enum import StrEnum


class ProfileStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    HIDDEN_BY_ADMIN = "hidden_by_admin"
