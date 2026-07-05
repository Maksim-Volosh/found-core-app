class DirectionsNotFound(Exception):
    message = "No directions found in the database."

    def __init__(self) -> None:
        super().__init__(self.message)


class DirectionNotFound(Exception):
    message = "Direction with given telegram_chat_id not found."

    def __init__(self) -> None:
        super().__init__(self.message)


class UserDirectionAccessNotFound(Exception):
    message = "Direction access with given user_id and telegram_chat_id not found."

    def __init__(self) -> None:
        super().__init__(self.message)


class DirectionAlreadyExists(Exception):
    message = "Direction with given telegram_chat_id already exists."

    def __init__(self) -> None:
        super().__init__(self.message)


class UserDirectionAccessAlreadyExists(Exception):
    message = "Direction access with given user_id and telegram_chat_id already exists."

    def __init__(self) -> None:
        super().__init__(self.message)
