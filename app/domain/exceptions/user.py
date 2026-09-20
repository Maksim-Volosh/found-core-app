class UserBannedError(Exception):
    message = "User is banned."

    def __init__(self, ban_reason: str | None) -> None:
        self.ban_reason = ban_reason
        super().__init__(self.message)
