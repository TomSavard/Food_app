"""
Pytest fixtures for integration tests.

Tests run against a dedicated Neon test branch (TEST_DATABASE_URL).
Each test wraps its work in a transaction that is rolled back on teardown,
so the schema persists between runs but no row state leaks.

Place integration tests in tests/integration/ and mark them with
@pytest.mark.integration so they are skipped when running the default
pytest command (which only runs unit tests against SQLite).

When TEST_DATABASE_URL is not set, this conftest defines no fixtures
and does not import any backend modules, allowing the unit test
conftest (tests/unit/conftest.py) to work without conflicts.
"""
import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Only import backend modules when a test DB is configured.
# This prevents the PostgreSQL models from being loaded during unit
# test runs (which use SQLite).
if os.getenv("TEST_DATABASE_URL"):
    from pathlib import Path

    # Load .env.test before importing app modules — they read env at import time.
    load_dotenv(Path(__file__).resolve().parent.parent / ".env.test")

    # Point the app's DATABASE_URL at the test DB before app modules import it.
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

    from backend.db.session import get_db  # noqa: E402
    from backend.main import app  # noqa: E402

    @pytest.fixture(scope="session")
    def engine():
        return create_engine(os.environ["TEST_DATABASE_URL"], pool_pre_ping=True)

    @pytest.fixture
    def db_session(engine):
        """Per-test session: outer transaction always rolled back; route-level
        db.commit() lands on a savepoint via join_transaction_mode."""
        connection = engine.connect()
        transaction = connection.begin()
        SessionLocal = sessionmaker(
            bind=connection,
            autocommit=False,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        )
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
            connection.close()

    @pytest.fixture
    def client(db_session):
        """TestClient with get_db dependency overridden to use the rolled-back session."""
        def _override_get_db():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = _override_get_db
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()
