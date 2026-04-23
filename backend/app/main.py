import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.logging_config import setup_logging
from app.routes import api_router
from app.tracing import TraceMiddleware

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema is managed with Alembic (see README: Database migrations).
    logger.info(
        "op=startup review_provider=%s openai_key_set=%s outscraper_key_set=%s mongo_uri_set=%s",
        settings.REVIEW_PROVIDER,
        bool(settings.OPENAI_API_KEY),
        bool(settings.OUTSCRAPER_API_KEY),
        bool(settings.MONGO_URI),
    )
    if settings.MONGO_URI:
        from app.mongo import _init_mongo

        _init_mongo()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Review Insight Tool",
        description="Analyze Google Maps reviews with AI-powered insights.",
        version="1.0.0",
        lifespan=lifespan,
    )

    cors_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    if settings.CORS_ORIGINS:
        cors_origins.extend(o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip())

    if settings.DEBUG_TRACE:
        app.add_middleware(TraceMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    from app.database import engine
    from app.observability import init_observability

    init_observability(app, engine)

    return app


app = create_app()
