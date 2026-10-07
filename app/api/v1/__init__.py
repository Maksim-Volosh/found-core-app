from fastapi import APIRouter

from .routers import auth, profiles, taxonomy

api_v1_router = APIRouter(prefix="/v1")
router_list = [auth, taxonomy, profiles]

for router in router_list:
    api_v1_router.include_router(router.router)
