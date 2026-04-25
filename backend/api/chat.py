"""
In-app assistant: streams Gemini 2.5 Flash responses with one read-only tool
(list_recipes). Tools are plain Python functions — the SDK introspects their
type hints + docstrings and handles automatic function calling.
"""
import json
import os
import random
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from google import genai
from google.genai import types
from pydantic import BaseModel
from sqlalchemy import String, desc, func
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.db.models import Ingredient, MealPlanSlot, Recipe
from backend.db.session import get_db
from backend.schemas import SLOTS

router = APIRouter(prefix="/api/chat", tags=["chat"])

SYSTEM_INSTRUCTION = (
    "You are a helpful in-app assistant for the user's personal food app. "
    "Tools available: list_recipes (browse the user's saved recipes); "
    "get_meal_plan, set_meal_plan_slot, clear_meal_plan_slot, generate_meal_plan "
    "(read and edit the weekly meal plan — 7 days × 4 slots: breakfast, lunch, dinner, extra). "
    "Dates are ISO YYYY-MM-DD; weeks start on Monday. "
    "When the user asks about their recipes or meal plan, call the relevant tools "
    "and answer from what they return. Be concise. Reply in the user's language."
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


def _build_meal_plan_tools(db: Session):
    """Returns 4 tool functions bound to this request's DB session."""

    def _parse(s: str) -> date:
        return datetime.strptime(s, "%Y-%m-%d").date()

    def _slot_dict(s: MealPlanSlot) -> dict:
        return {
            "date": s.slot_date.isoformat(),
            "slot": s.slot,
            "recipe_id": str(s.recipe_id),
            "recipe_name": s.recipe.name if s.recipe else "",
            "servings": s.servings,
        }

    def get_meal_plan(week_start: str) -> dict:
        """Return the meal plan for a given week.

        Args:
            week_start: Monday of the week, YYYY-MM-DD.
        """
        monday = _parse(week_start)
        if monday.weekday() != 0:
            return {"error": "week_start must be a Monday"}
        sunday = monday + timedelta(days=6)
        slots = (
            db.query(MealPlanSlot)
            .options(joinedload(MealPlanSlot.recipe))
            .filter(MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday)
            .all()
        )
        return {"week_start": monday.isoformat(), "slots": [_slot_dict(s) for s in slots]}

    def set_meal_plan_slot(slot_date: str, slot: str, recipe_id: str, servings: int = 1) -> dict:
        """Assign a recipe to a (date, slot). Overwrites any existing recipe in that slot.

        Args:
            slot_date: YYYY-MM-DD.
            slot: One of breakfast, lunch, dinner, extra.
            recipe_id: UUID of an existing recipe.
            servings: How many people this slot serves (>=1).
        """
        if slot not in SLOTS:
            return {"error": f"slot must be one of {SLOTS}"}
        if servings < 1:
            return {"error": "servings must be >= 1"}
        try:
            d = _parse(slot_date)
            rid = UUID(recipe_id)
        except (ValueError, TypeError) as e:
            return {"error": str(e)}
        recipe = db.query(Recipe).filter(Recipe.recipe_id == rid).first()
        if not recipe:
            return {"error": f"Recipe {recipe_id} not found"}

        existing = (
            db.query(MealPlanSlot)
            .filter(MealPlanSlot.slot_date == d, MealPlanSlot.slot == slot)
            .first()
        )
        if existing:
            existing.recipe_id = rid
            existing.servings = servings
            slot_obj = existing
        else:
            slot_obj = MealPlanSlot(slot_date=d, slot=slot, recipe_id=rid, servings=servings)
            db.add(slot_obj)
        db.commit()
        db.refresh(slot_obj)
        _ = slot_obj.recipe
        return _slot_dict(slot_obj)

    def clear_meal_plan_slot(slot_date: str, slot: str) -> dict:
        """Remove the recipe assigned to a (date, slot).

        Args:
            slot_date: YYYY-MM-DD.
            slot: One of breakfast, lunch, dinner, extra.
        """
        if slot not in SLOTS:
            return {"error": f"slot must be one of {SLOTS}"}
        try:
            d = _parse(slot_date)
        except ValueError as e:
            return {"error": str(e)}
        deleted = (
            db.query(MealPlanSlot)
            .filter(MealPlanSlot.slot_date == d, MealPlanSlot.slot == slot)
            .delete(synchronize_session=False)
        )
        db.commit()
        return {"deleted": bool(deleted)}

    def generate_meal_plan(week_start: str, overwrite: bool = False) -> dict:
        """Auto-fill empty slots of a week with random recipes (favorites first if any).

        Args:
            week_start: Monday of the week, YYYY-MM-DD.
            overwrite: If true, replace any already-filled slots that week.
        """
        try:
            monday = _parse(week_start)
        except ValueError as e:
            return {"error": str(e)}
        if monday.weekday() != 0:
            return {"error": "week_start must be a Monday"}
        sunday = monday + timedelta(days=6)

        existing = (
            db.query(MealPlanSlot)
            .filter(MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday)
            .all()
        )
        if overwrite:
            for s in existing:
                db.delete(s)
            db.flush()
            existing_keys = set()
        else:
            existing_keys = {(s.slot_date, s.slot) for s in existing}

        favorites = db.query(Recipe).filter(Recipe.is_favorite == True).all()  # noqa: E712
        pool = favorites or db.query(Recipe).limit(50).all()
        if not pool:
            return {"error": "No recipes available"}

        for day_offset in range(7):
            d = monday + timedelta(days=day_offset)
            for slot_name in SLOTS:
                if (d, slot_name) in existing_keys:
                    continue
                recipe = random.choice(pool)
                db.add(
                    MealPlanSlot(
                        slot_date=d,
                        slot=slot_name,
                        recipe_id=recipe.recipe_id,
                        servings=recipe.servings or 1,
                    )
                )
        db.commit()
        slots = (
            db.query(MealPlanSlot)
            .options(joinedload(MealPlanSlot.recipe))
            .filter(MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday)
            .all()
        )
        return {"week_start": monday.isoformat(), "slots": [_slot_dict(s) for s in slots]}

    return [get_meal_plan, set_meal_plan_slot, clear_meal_plan_slot, generate_meal_plan]


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
        tools=[_build_list_recipes_tool(db), *_build_meal_plan_tools(db)],
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
