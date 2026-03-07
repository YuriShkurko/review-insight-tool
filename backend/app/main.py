import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routes import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info(
        "Config loaded — REVIEW_PROVIDER=%s, OPENAI_API_KEY set=%s, OUTSCRAPER_API_KEY set=%s",
        settings.REVIEW_PROVIDER,
        bool(settings.OPENAI_API_KEY),
        bool(settings.OUTSCRAPER_API_KEY),
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Review Insight Tool",
        description="Analyze Google Maps reviews with AI-powered insights.",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
