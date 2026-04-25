from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from backend.db.session import get_engine
from sqlalchemy import text
from backend.api import recipes, ingredients, shopping_list, chat, meal_plan, match

load_dotenv()

app = FastAPI(
    title="Food App API",
    description="Backend API for recipe management and meal planning",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recipes.router)
app.include_router(ingredients.router)
app.include_router(shopping_list.router)
app.include_router(chat.router)
app.include_router(meal_plan.router)
app.include_router(match.router)


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
