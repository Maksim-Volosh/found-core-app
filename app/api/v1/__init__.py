from fastapi import APIRouter

from .routers import admin, payment, user, webhook

api_v1_router = APIRouter(prefix="/v1")
router_list = [user, payment, admin, webhook]

for router in router_list:
    api_v1_router.include_router(router.router)