from src.api.api_client import api
from src.api.services import (AccessService, AuthService, PaymentService,
                              UserService, AdminService)


class Container:
    def __init__(self):
        self.api = api

        # Setup Services
        self.auth_service = AuthService(self.api)
        self.user_service = UserService(self.api)
        self.payment_service = PaymentService(self.api)
        self.access_service = AccessService(self.api)
        self.admin_service = AdminService(self.api)


container = Container()