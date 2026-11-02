import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.endpoints import router
from .config import get_settings
from .database import create_tables

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.include_router(router)


@app.get("/", tags=["system"])
def root() -> dict:
    return {"message": settings.app_name, "docs": "/docs"}
