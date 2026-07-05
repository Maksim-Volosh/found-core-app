class NoPaymentRequired(Exception):
    message = "User with given user_id does not require payment. Subscription is already active."

    def __init__(self) -> None:
        super().__init__(self.message)


class InvalidPaymentMonths(Exception):
    message = "Payment months must be between 1 and 12."

    def __init__(self) -> None:
        super().__init__(self.message)
