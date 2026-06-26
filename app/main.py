import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import api_v1_router
from app.core.config import settings
from app.infrastructure.helpers.db import db_helper
from app.infrastructure.schedulers.subscription import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize
    scheduler = start_scheduler()
    yield  # ---------

    # Cleanup
    scheduler.shutdown()
    await db_helper.dispose()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("app.log", encoding="utf-8") 
    ]
)

main_app = FastAPI(
    lifespan=lifespan,
    title=settings.details.title,
    description=settings.details.description,
)
main_app.include_router(api_v1_router, prefix=settings.api.prefix)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:main_app",
        host=settings.run.host,
        port=settings.run.port,
        reload=settings.run.reload,
    )
