class InitDataMalformedError(Exception):
    message = "Telegram init_data is malformed or missing required fields."

    def __init__(self) -> None:
        super().__init__(self.message)


class InitDataSignatureInvalidError(Exception):
    message = "Telegram init_data signature is invalid."

    def __init__(self) -> None:
        super().__init__(self.message)


class InitDataExpiredError(Exception):
    message = "Telegram init_data has expired."

    def __init__(self) -> None:
        super().__init__(self.message)


class TokenExpiredError(Exception):
    message = "Access token has expired."

    def __init__(self) -> None:
        super().__init__(self.message)


class TokenInvalidError(Exception):
    message = "Access token is invalid."

    def __init__(self) -> None:
        super().__init__(self.message)
