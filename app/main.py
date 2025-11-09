from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from app.db.session import get_engine
from sqlalchemy import text
from app.api import recipes
import os

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

# Serve static files (frontend)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    # Mount static files (CSS, JS, images)
    app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")
    app.mount("/images", StaticFiles(directory=os.path.join(frontend_path, "images")), name="images")
    
    # Serve manifest and service worker
    @app.get("/manifest.json")
    async def serve_manifest():
        manifest_path = os.path.join(frontend_path, "manifest.json")
        if os.path.exists(manifest_path):
            return FileResponse(manifest_path)
    
    @app.get("/sw.js")
    async def serve_sw():
        sw_path = os.path.join(frontend_path, "sw.js")
        if os.path.exists(sw_path):
            return FileResponse(sw_path, media_type="application/javascript")
    
    # Serve frontend index.html at root
    @app.get("/")
    async def serve_frontend():
        """Serve the frontend index.html"""
        index_path = os.path.join(frontend_path, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend not found. API is available at /docs"}
else:
    @app.get("/")
    def root():
        """Root endpoint - basic health check"""
        return {"message": "Backend is running", "status": "ok", "docs": "/docs"}

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

