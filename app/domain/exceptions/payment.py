class NoPaymentRequired(Exception):
    message = "User with given user_id does not require payment. Subscription is already active."

    def __init__(self) -> None:
        super().__init__(self.message)
        
