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
    """No-op: embedding column handled by schema migration."""
    pass


def _ensure_recipe_images_table(session):
    """Create recipe_images table if missing on the test Neon branch."""
    has = session.execute(text('''
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'recipe_images'
    ''')).scalar() > 0
    if not has:
        session.execute(text('''
            CREATE TABLE recipe_images (
                image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                recipe_id UUID NOT NULL REFERENCES recipes(recipe_id) ON DELETE CASCADE,
                object_key TEXT NOT NULL,
                original_filename TEXT,
                content_type TEXT,
                size_bytes BIGINT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        '''))
        session.commit()


def _truncate_tables(session):
    """Delete all rows so each test starts from a clean slate."""
    # Only truncate tables that actually exist
    existing_tables = session.execute(text('''
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('ingredient_aliases', 'shopping_list_contributions', 
                           'shopping_list', 'instructions', 'ingredients',
                           'meal_plan_slots', 'recipes', 'recipe_images',
                           'ingredient_database', 'recipe_notes')
    ''')).fetchall()
    existing_names = {row[0] for row in existing_tables}
    
    tables_to_truncate = [
        "ingredient_aliases",
        "shopping_list_contributions",
        "shopping_list",
        "instructions",
        "ingredients",
        "meal_plan_slots",
        "recipe_notes",
        "recipes",
        "recipe_images",
        "ingredient_database",
    ]
    
    for table in tables_to_truncate:
        if table in existing_names:
            session.execute(text(f"DELETE FROM {table}"))
            session.flush()


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
        _ensure_recipe_images_table(session)
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
