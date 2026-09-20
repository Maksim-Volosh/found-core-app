from fastapi import APIRouter

from .routers import router, user

api_v1_router = APIRouter(prefix="/v1")
router_list = [router, user]

for router in router_list:
    api_v1_router.include_router(router.router)