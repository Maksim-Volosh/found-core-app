from fastapi import APIRouter

from .routers import admin, payment, user, webhook, access, direction

api_v1_router = APIRouter(prefix="/v1")
router_list = [user, payment, admin, webhook, access, direction]

for router in router_list:
    api_v1_router.include_router(router.router)
