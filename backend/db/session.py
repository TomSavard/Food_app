import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def _get_database_url():
    """Lazily retrieve DATABASE_URL so the backend can be imported without it."""
    return os.getenv("DATABASE_URL")


def _build_url(raw):
    if not raw:
        return None
    if "sslmode" not in raw:
        separator = "&" if "?" in raw else "?"
        return f"{raw}{separator}sslmode=require"
    return raw


_DATABASE_URL = None
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine. Raises if DATABASE_URL is not configured."""
    global _engine, _DATABASE_URL
    if _engine is None:
        url = _DATABASE_URL or _get_database_url()
        if not url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set"
            )
        _DATABASE_URL = _build_url(url)
        _engine = create_engine(
            _DATABASE_URL,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            pool_recycle=300,
            echo=False,
        )
    return _engine

def get_db():
    """Dependency for getting database session"""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Base class for SQLAlchemy models
Base = declarative_base()

