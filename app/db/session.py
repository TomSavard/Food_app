import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

# Ensure SSL mode is set for Neon
if "sslmode" not in DATABASE_URL:
    separator = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL = f"{DATABASE_URL}{separator}sslmode=require"

_engine = None
_SessionLocal = None

def get_engine():
    """Get or create the database engine"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=5,  # Number of connections to keep in pool
            max_overflow=10,  # Additional connections beyond pool_size
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False  # Set to True for SQL query logging in development
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

