from contextlib import asynccontextmanager
from app.core.config import settings
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize
    yield  # ---------

    # Cleanup
    

main_app = FastAPI(
    lifespan=lifespan,
    title=settings.details.title,
    description=settings.details.description,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:main_app",
        host=settings.run.host,
        port=settings.run.port,
        reload=settings.run.reload,
    )