from src.api.api_client import api
from src.api.services import AuthService, UserService, PaymentService


class Container:
    def __init__(self):
        self.api = api

        # Setup Services
        self.auth_service = AuthService(self.api)
        self.user_service = UserService(self.api)
        self.payment_service = PaymentService(self.api)


container = Container()