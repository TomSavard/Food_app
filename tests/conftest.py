"""
Pytest fixtures.

Tests run against a dedicated Neon test branch (TEST_DATABASE_URL).
Each test wraps its work in a transaction that is rolled back on teardown,
so the schema persists between runs but no row state leaks.
"""
import os
from pathlib import Path
import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load .env.test before importing app modules — they read env at import time.
load_dotenv(Path(__file__).resolve().parent.parent / ".env.test")

if not os.getenv("TEST_DATABASE_URL"):
    raise RuntimeError(
        "TEST_DATABASE_URL is not set. Copy .env.test.example to .env.test "
        "and fill in your Neon test-branch connection string."
    )

# Point the app's DATABASE_URL at the test DB before app modules import it.
os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

from backend.db.session import get_db  # noqa: E402
from backend.main import app  # noqa: E402


def _ensure_embedding_column(session):
    """Ensure pgvector extension exists and migration runs (if table/column exist).

    Gracefully skips if the test database lacks pgvector or the table.
    If pgvector is unavailable, ensure the column exists as float8[]
    so that embedding writes don't leave the transaction in a failed state.
    """
    try:
        session.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        # Check if embedding column exists (it might be float8[] or missing).
        has_col = session.execute(text('''
            SELECT count(*) FROM information_schema.columns
            WHERE table_name = 'ingredient_database' AND column_name = 'embedding'
        ''')).scalar()
        if has_col == 0:
            return  # no embedding column at all — skip.
        session.execute(text('''
            ALTER TABLE ingredient_database
            ALTER COLUMN embedding TYPE vector(256)
            USING embedding::vector(256)
        '''))
        session.flush()
    except Exception:
        # pgvector not available or column doesn't exist.
        # Ensure the column exists as float8[] so embedding writes don't abort the transaction.
        try:
            session.execute(text('''
                ALTER TABLE ingredient_database
                ADD COLUMN IF NOT EXISTS embedding float8[]
            '''))
            session.flush()
        except Exception:
            pass  # column might already exist — skip.


def _truncate_tables(session):
    """Delete all rows in FK order so each test starts from a clean slate."""
    tables = [
        "ingredient_aliases",
        "shopping_list_contributions",
        "shopping_list",
        "instructions",
        "ingredients",
        "meal_plan_slots",
        "recipes",
        "ingredient_database",
    ]
    for table in tables:
        try:
            session.execute(text(f"DELETE FROM {table}"))
            session.flush()
        except Exception:
            # Table might not exist yet — skip.
            pass


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
        _ensure_embedding_column(session)
        _truncate_tables(session)
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
