"""
In-app assistant: streams Gemini 2.5 Flash responses with one read-only tool
(list_recipes). Tools are plain Python functions — the SDK introspects their
type hints + docstrings and handles automatic function calling.
"""
import json
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types
from pydantic import BaseModel
from sqlalchemy import String, desc, func
from sqlalchemy.orm import Session, selectinload

from app.db.models import Ingredient, Recipe
from app.db.session import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])

SYSTEM_INSTRUCTION = (
    "You are a helpful in-app assistant for the user's personal food app. "
    "When the user asks about their recipes, call the `list_recipes` tool "
    "and answer based on what it returns. Be concise. Reply in the user's "
    "language."
)


class ChatMessage(BaseModel):
    role: str  # "user" or "model"
    text: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


def _build_list_recipes_tool(db: Session):
    """Returns a Python function bound to this request's DB session.
    The SDK reads its signature + docstring as the tool schema."""

    def list_recipes(
        search: Optional[str] = None,
        cuisine: Optional[str] = None,
        ingredient: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 20,
    ) -> List[dict]:
        """Search the user's saved recipes and return summaries.

        Args:
            search: Free-text search in recipe name and description.
            cuisine: Filter by cuisine type (partial, case-insensitive).
            ingredient: Filter to recipes containing this ingredient.
            tag: Filter by tag.
            limit: Max recipes to return (default 20).
        """
        q = db.query(Recipe).options(selectinload(Recipe.ingredients))
        if search:
            q = q.filter(
                Recipe.name.ilike(f"%{search}%")
                | Recipe.description.ilike(f"%{search}%")
            )
        if cuisine:
            q = q.filter(Recipe.cuisine_type.ilike(f"%{cuisine}%"))
        if ingredient:
            q = q.join(Ingredient).filter(
                Ingredient.name.ilike(f"%{ingredient}%")
            ).distinct()
        if tag:
            q = q.filter(
                func.lower(func.cast(Recipe.tags, String)).contains(tag.lower())
            )
        recipes = (
            q.order_by(desc(Recipe.is_favorite), desc(Recipe.created_at))
            .limit(limit)
            .all()
        )
        return [
            {
                "name": r.name,
                "description": r.description or "",
                "cuisine_type": r.cuisine_type or "",
                "tags": list(r.tags or []),
                "servings": r.servings,
                "ingredients": [i.name for i in r.ingredients],
            }
            for r in recipes
        ]

    return list_recipes


def _to_contents(messages: List[ChatMessage]) -> List[types.Content]:
    return [
        types.Content(role=m.role, parts=[types.Part(text=m.text)])
        for m in messages
    ]


@router.post("")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    if not req.messages:
        raise HTTPException(status_code=400, detail="messages is empty")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[_build_list_recipes_tool(db)],
    )

    def event_stream():
        try:
            for chunk in client.models.generate_content_stream(
                model="gemini-2.5-flash",
                contents=_to_contents(req.messages),
                config=config,
            ):
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
