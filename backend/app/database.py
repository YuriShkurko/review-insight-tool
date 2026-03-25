from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

try:
    engine = create_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
except Exception as _db_init_error:
    # DATABASE_URL is missing or malformed (e.g. local dev without .env, or bad Railway URL).
    # Set placeholders so the module can be imported; actual DB calls will fail at runtime.
    import warnings

    warnings.warn(
        f"Could not initialise database engine: {_db_init_error}. "
        "Check DATABASE_URL in your .env file.",
        stacklevel=1,
    )
    engine = None  # type: ignore[assignment]
    SessionLocal = None  # type: ignore[assignment]


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
