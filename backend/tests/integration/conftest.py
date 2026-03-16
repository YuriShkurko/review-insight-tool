"""Integration test fixtures.

Uses an in-memory SQLite database so tests run without PostgreSQL.
Forces mock review provider and mock LLM regardless of .env settings.
"""

import os
import uuid

os.environ["REVIEW_PROVIDER"] = "mock"
os.environ["OPENAI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db

SQLITE_URL = "sqlite://"


@pytest.fixture(scope="session")
def _engine():
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_fk(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(_engine):
    """Clear all table data between tests for isolation."""
    yield
    with _engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


@pytest.fixture()
def db_session(_engine):
    Session = sessionmaker(bind=_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def client(db_session, _engine):
    """FastAPI TestClient wired to the test database with mock providers."""
    import app.database as db_mod
    import app.config as config_mod

    original_engine = db_mod.engine
    db_mod.engine = _engine

    original_provider = config_mod.settings.REVIEW_PROVIDER
    original_openai = config_mod.settings.OPENAI_API_KEY
    object.__setattr__(config_mod.settings, "REVIEW_PROVIDER", "mock")
    object.__setattr__(config_mod.settings, "OPENAI_API_KEY", "")

    from app.main import create_app
    app = create_app()

    def _override_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    db_mod.engine = original_engine
    object.__setattr__(config_mod.settings, "REVIEW_PROVIDER", original_provider)
    object.__setattr__(config_mod.settings, "OPENAI_API_KEY", original_openai)


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    """Register a fresh user and return Authorization headers."""
    email = f"test-{uuid.uuid4().hex[:8]}@test.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "testpass123"})
    assert r.status_code == 201
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


SAMPLE_MAPS_URL = (
    "https://www.google.com/maps/place/Test+Business/"
    "@0,0,17z/data=!4m2!3m1!1s0x0:0x1"
)

SAMPLE_MAPS_URL_2 = (
    "https://www.google.com/maps/place/Other+Business/"
    "@0,0,17z/data=!4m2!3m1!1s0x0:0x2"
)

SAMPLE_MAPS_URL_3 = (
    "https://www.google.com/maps/place/Third+Business/"
    "@0,0,17z/data=!4m2!3m1!1s0x0:0x3"
)
