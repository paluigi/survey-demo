"""FastAPI application assembly: lifespan, static files, routers, healthcheck."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient

from survey.config import Settings
from survey.repository import SurveyRepository
from survey.web import api, partials, routes

logger = logging.getLogger("survey")

STATIC_DIR = Path(__file__).resolve().parents[2] / "static"


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings.from_env()
    client = AsyncIOMotorClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
    repository = SurveyRepository(client, settings)
    try:
        await repository.ping()
    except Exception:
        logger.exception("MongoDB is not reachable at %s", settings.mongodb_uri)
        raise
    await repository.ensure_indexes()
    app.state.repository = repository
    logger.info("Connected to MongoDB (db=%s)", settings.mongodb_db)
    yield
    client.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Travel Survey", lifespan=lifespan)
    app.include_router(routes.router)
    app.include_router(partials.router)
    app.include_router(api.router)
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        await app.state.repository.ping()
        return {"status": "ok"}

    return app


app = create_app()
