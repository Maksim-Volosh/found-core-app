class UserNotFoundByTelegramId(Exception):
    message = "User with given telegram_id not found."

    def __init__(self) -> None:
        super().__init__(self.message)
        
class UserNotFoundByUserId(Exception):
    message = "User with given user_id not found."

    def __init__(self) -> None:
        super().__init__(self.message)


class UsersNotFound(Exception):
    message = "No users found in the database."

    def __init__(self) -> None:
        super().__init__(self.message)


class UserIsBanned(Exception):
    message = "User with given telegram_id is banned. Contact support for more information."

    def __init__(self) -> None:
        super().__init__(self.message)
