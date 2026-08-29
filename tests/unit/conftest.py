"""
SQLite-based pytest fixtures for fast, local unit testing.

Uses an in-memory SQLite database so tests never hit the network.
Tables are created once per session and torn down between runs.
"""
import os
import sys
import uuid
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.elements import ColumnElement

# Ensure the app can import backend modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Set DATABASE_URL to SQLite BEFORE importing app modules.
# This makes backend/db/models.py select SQLite-compatible types.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.db.session import get_db  # noqa: E402
from backend.db.models import Base  # noqa: E402
from backend.main import app  # noqa: E402


# ---------------------------------------------------------------------------
# SQLite "ilike" support — maps ilike -> LOWER(a) LIKE LOWER(b)
# ---------------------------------------------------------------------------
@compiles(ColumnElement.ilike, "sqlite")
def ilike_impl(element, compiler, **kw):
    return "LOWER(%s) LIKE LOWER(%s)" % (
        compiler.process(element.left, **kw),
        compiler.process(element.right, **kw),
    )


# ---------------------------------------------------------------------------
# SQLite UUID adapter — converts Python UUID -> str for binding
# ---------------------------------------------------------------------------
def _adapt_uuid(u):
    if isinstance(u, uuid.UUID):
        return str(u)
    return u


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sqlite_engine():
    """Create an in-memory SQLite engine shared across the test session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Register UUID adapter
    import sqlite3
    sqlite3.register_adapter(uuid.UUID, _adapt_uuid)

    # Create all tables
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)


@pytest.fixture
def db_session(sqlite_engine):
    """Per-test session: transaction rolled back after each test."""
    connection = sqlite_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
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
    """TestClient with get_db overridden to use the SQLite session."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
