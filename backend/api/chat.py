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

router = APIRouter(prefix="/api/chat", tags=["chat"])

SYSTEM_INSTRUCTION = (
    "You are a helpful in-app assistant for the user's personal food app. "
    "Tools available: list_recipes (browse the user's saved recipes); "
    "get_meal_plan, add_meal_to_day, remove_meal, generate_meal_plan "
    "(read and edit the weekly meal plan — each day is an ordered stack of meals); "
    "categorize_shopping_list (sort the shopping list into supermarket sections "
    "for efficient shopping). "
    "Dates are ISO YYYY-MM-DD; weeks start on Monday. "
    "When the user asks about their recipes, meal plan, or shopping list "
    "organization, call the relevant tools and answer from what they return. "
    "Be concise. Reply in the user's language."
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
    """4 tools bound to this request's DB session — stack-of-meals model."""

    def _parse(s: str) -> date:
        return datetime.strptime(s, "%Y-%m-%d").date()

    def _slot_dict(s: MealPlanSlot) -> dict:
        return {
            "slot_id": str(s.slot_id),
            "date": s.slot_date.isoformat(),
            "position": s.position,
            "recipe_id": str(s.recipe_id),
            "recipe_name": s.recipe.name if s.recipe else "",
            "servings": s.servings,
        }

    def _next_position(d: date) -> int:
        last = (
            db.query(MealPlanSlot)
            .filter(MealPlanSlot.slot_date == d)
            .order_by(MealPlanSlot.position.desc())
            .first()
        )
        return (last.position + 1) if last else 0

    def get_meal_plan(week_start: str) -> dict:
        """Return the meal plan for a given week, ordered by date then position.

        Args:
            week_start: Monday of the week, YYYY-MM-DD.
        """
        try:
            monday = _parse(week_start)
        except ValueError as e:
            return {"error": str(e)}
        if monday.weekday() != 0:
            return {"error": "week_start must be a Monday"}
        sunday = monday + timedelta(days=6)
        slots = (
            db.query(MealPlanSlot)
            .options(joinedload(MealPlanSlot.recipe))
            .filter(MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday)
            .order_by(MealPlanSlot.slot_date, MealPlanSlot.position)
            .all()
        )
        return {"week_start": monday.isoformat(), "slots": [_slot_dict(s) for s in slots]}

    def add_meal_to_day(slot_date: str, recipe_id: str, servings: int = 1) -> dict:
        """Append a meal to the end of a day's stack.

        Args:
            slot_date: YYYY-MM-DD.
            recipe_id: UUID of an existing recipe.
            servings: How many people this meal serves (>=1).
        """
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
        slot = MealPlanSlot(
            slot_date=d, position=_next_position(d), recipe_id=rid, servings=servings,
        )
        db.add(slot); db.commit(); db.refresh(slot)
        _ = slot.recipe
        return _slot_dict(slot)

    def remove_meal(slot_id: str) -> dict:
        """Remove a meal by its slot_id (use get_meal_plan first to find it).

        Args:
            slot_id: UUID of the meal slot to remove.
        """
        try:
            sid = UUID(slot_id)
        except (ValueError, TypeError) as e:
            return {"error": str(e)}
        deleted = (
            db.query(MealPlanSlot)
            .filter(MealPlanSlot.slot_id == sid)
            .delete(synchronize_session=False)
        )
        db.commit()
        return {"deleted": bool(deleted)}

    def generate_meal_plan(
        week_start: str, meals_per_day: int = 3, overwrite: bool = False
    ) -> dict:
        """Auto-fill the week with N random meals per day (favorites if any).

        Args:
            week_start: Monday of the week, YYYY-MM-DD.
            meals_per_day: How many meals to ensure per day (default 3).
            overwrite: If true, replace any existing meals in the week.
        """
        try:
            monday = _parse(week_start)
        except ValueError as e:
            return {"error": str(e)}
        if monday.weekday() != 0:
            return {"error": "week_start must be a Monday"}
        if meals_per_day < 1 or meals_per_day > 10:
            return {"error": "meals_per_day must be between 1 and 10"}
        sunday = monday + timedelta(days=6)

        if overwrite:
            db.query(MealPlanSlot).filter(
                MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday
            ).delete(synchronize_session=False)
            db.flush()

        favorites = db.query(Recipe).filter(Recipe.is_favorite == True).all()  # noqa: E712
        pool = favorites or db.query(Recipe).limit(50).all()
        if not pool:
            return {"error": "No recipes available"}

        for day_offset in range(7):
            d = monday + timedelta(days=day_offset)
            existing_count = _next_position(d)  # next position == current count
            target = meals_per_day if overwrite else max(0, meals_per_day - existing_count)
            for i in range(target):
                recipe = random.choice(pool)
                db.add(
                    MealPlanSlot(
                        slot_date=d,
                        position=(existing_count + i) if not overwrite else i,
                        recipe_id=recipe.recipe_id,
                        servings=recipe.servings or 1,
                    )
                )
        db.commit()
        slots = (
            db.query(MealPlanSlot)
            .options(joinedload(MealPlanSlot.recipe))
            .filter(MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday)
            .order_by(MealPlanSlot.slot_date, MealPlanSlot.position)
            .all()
        )
        return {"week_start": monday.isoformat(), "slots": [_slot_dict(s) for s in slots]}

    return [get_meal_plan, add_meal_to_day, remove_meal, generate_meal_plan]


def _build_shopping_tools(db: Session):
    """Tools for organising the shopping list."""

    def categorize_shopping_list(only_uncertain: bool = True) -> dict:
        """Sort each shopping-list ingredient into a supermarket section
        (Fruits & Légumes, Boulangerie, Viandes & Poissons, …) so the user
        walks the store efficiently. Persists each decision to the
        ingredient knowledge base.

        Args:
            only_uncertain: If True (default), only re-categorize items
                currently unknown or in 'Autres'. If False, re-categorize
                every item.
        """
        # Reuse the REST handler so logic stays in one place.
        from backend.api.shopping_list import categorize_with_ai
        try:
            res = categorize_with_ai(only_uncertain=only_uncertain, db=db)
            return {
                "ok": True,
                "total": res.total,
                "items": [
                    {"name": it.name, "category": it.category} for it in res.items
                ],
            }
        except Exception as e:
            return {"error": str(e)}

    return [categorize_shopping_list]


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
        tools=[
            _build_list_recipes_tool(db),
            *_build_meal_plan_tools(db),
            *_build_shopping_tools(db),
        ],
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
