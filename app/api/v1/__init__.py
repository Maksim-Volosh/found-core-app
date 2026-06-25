from fastapi import APIRouter

from .routers import user, payment, admin

api_v1_router = APIRouter(prefix="/v1")
router_list = [user, payment, admin]

for router in router_list:
    api_v1_router.include_router(router.router)