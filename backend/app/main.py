import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.logging_config import setup_logging
from app.routes import api_router

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info(
        "op=startup review_provider=%s openai_key_set=%s outscraper_key_set=%s",
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
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
