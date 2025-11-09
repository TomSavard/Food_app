from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.db.session import get_engine
from sqlalchemy import text
from app.api import recipes

# Load environment variables from .env file
load_dotenv()

app = FastAPI(
    title="Food App API",
    description="Backend API for recipe management and meal planning",
    version="1.0.0"
)

# CORS middleware - configure allowed origins for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(recipes.router)

@app.get("/")
def root():
    """Root endpoint - basic health check"""
    return {"message": "Backend is running", "status": "ok"}

@app.get("/health")
def health():
    """Health check endpoint with database connectivity test"""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}

