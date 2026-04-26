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

from backend.db.models import (
    Ingredient,
    IngredientAlias,
    IngredientDatabase,
    Instruction,
    MealPlanSlot,
    Recipe,
    ShoppingList,
    ShoppingListContribution,
)
from backend.db.session import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])

SYSTEM_INSTRUCTION = (
    "You are a helpful in-app assistant for the user's personal food app.\n"
    "\n"
    "You can:\n"
    "- browse the user's recipes (search, fetch detail, fetch nutrition)\n"
    "- read and edit the weekly meal plan (add/remove meals, regenerate the week)\n"
    "- read the shopping list and re-categorize it by supermarket section\n"
    "- create new recipes; edit recipe metadata; add/update/remove ingredients on a recipe; delete recipes\n"
    "- bulk-rename an ingredient across all recipes\n"
    "- look up the ingredient reference DB\n"
    "- answer nutrition questions (weekly intake, ANSES targets, untracked items)\n"
    "  and seasonality questions (what's in season this month; suggest seasonal recipes)\n"
    "\n"
    "For destructive operations (delete, bulk replace) ALWAYS run with dry_run=true "
    "first, show the preview, and only re-run with dry_run=false on user confirmation.\n"
    "\n"
    "Dates are ISO YYYY-MM-DD; weeks start on Monday. Be concise. "
    "Reply in the user's language."
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


def _build_recipe_edit_tools(db: Session):
    """Tools that write to recipes. Default to dry-run for safety."""

    def replace_ingredient_in_recipes(
        old_name: str,
        new_name: str,
        relink_to_db_name: Optional[str] = None,
        dry_run: bool = True,
    ) -> dict:
        """Bulk-rename ingredient rows across all recipes. Match is
        case-insensitive on a trimmed comparison of the ingredient's
        free-text name. Default is dry-run — call again with
        dry_run=False after the user confirms.

        Args:
            old_name: The free-text ingredient name to replace
                (e.g. "Beurre à 82% MG, doux"). Match is case-
                insensitive after trimming.
            new_name: The replacement free-text name
                (e.g. "Beurre à 80% MG minimum, doux").
            relink_to_db_name: Optional. If set, look up an
                IngredientDatabase row whose alim_nom_fr matches this
                exactly (case-insensitive) and set the FK on every
                renamed ingredient. Use this when the new_name should
                also relink the nutrition canonical reference.
            dry_run: If True (default), report what would change without
                writing. Set False only after the user confirms.

        Returns:
            {
              "matched": int,
              "preview": [{"recipe_name": str, "current_name": str}, ...],
              "applied": bool,
              "relinked_to_id": str | None,
            }
        """
        needle = old_name.strip().lower()
        if not needle or not new_name.strip():
            return {"error": "old_name and new_name are required"}

        rows = (
            db.query(Ingredient)
            .options(joinedload(Ingredient.recipe))
            .filter(func.lower(func.trim(Ingredient.name)) == needle)
            .all()
        )

        target_id = None
        if relink_to_db_name:
            target = (
                db.query(IngredientDatabase)
                .filter(
                    func.lower(IngredientDatabase.alim_nom_fr)
                    == relink_to_db_name.strip().lower()
                )
                .first()
            )
            if target is None:
                return {
                    "error": (
                        f"Reference ingredient '{relink_to_db_name}' not found "
                        "in the knowledge base."
                    )
                }
            target_id = str(target.id)

        preview = [
            {"recipe_name": r.recipe.name if r.recipe else "?", "current_name": r.name}
            for r in rows
        ]

        if dry_run:
            return {
                "matched": len(rows),
                "preview": preview,
                "applied": False,
                "relinked_to_id": target_id,
            }

        for r in rows:
            r.name = new_name.strip()
            if target_id is not None:
                r.ingredient_db_id = target_id
        db.commit()
        return {
            "matched": len(rows),
            "preview": preview,
            "applied": True,
            "relinked_to_id": target_id,
        }

    def create_recipe(
        name: str,
        ingredients: List[dict],
        instructions: List[str],
        servings: int = 2,
        cuisine_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        prep_time: int = 0,
        cook_time: int = 0,
    ) -> dict:
        """Create a new recipe. Each ingredient is auto-linked to the
        reference DB via case-insensitive exact / alias match when possible.

        Args:
            name: Recipe name (required, non-empty).
            ingredients: List of {name, quantity, unit, notes?} dicts.
            instructions: List of step strings, in order.
            servings: Default 2.
            cuisine_type: Optional cuisine tag (e.g. "italienne").
            tags: Optional free-form tags.
            description: Optional short description.
            prep_time: Minutes (default 0).
            cook_time: Minutes (default 0).
        """
        from backend.services.ingredient_match import lookup_exact

        if not name or not name.strip():
            return {"error": "name is required"}
        recipe = Recipe(
            name=name.strip(),
            description=(description or "").strip() or None,
            prep_time=prep_time,
            cook_time=cook_time,
            servings=servings,
            cuisine_type=(cuisine_type or "").strip() or None,
            tags=tags or [],
        )
        db.add(recipe); db.flush()
        n_linked = 0
        for ing in ingredients or []:
            ing_name = (ing.get("name") or "").strip()
            if not ing_name:
                continue
            match = lookup_exact(db, ing_name)
            if match:
                n_linked += 1
            db.add(Ingredient(
                recipe_id=recipe.recipe_id,
                name=ing_name,
                quantity=float(ing.get("quantity") or 0),
                unit=(ing.get("unit") or "").strip(),
                notes=(ing.get("notes") or "").strip(),
                ingredient_db_id=match.id if match else None,
            ))
        for idx, text in enumerate(instructions or []):
            if not text or not text.strip():
                continue
            db.add(Instruction(
                recipe_id=recipe.recipe_id,
                step_number=idx + 1,
                instruction_text=text.strip(),
            ))
        db.commit()
        return {
            "recipe_id": str(recipe.recipe_id),
            "name": recipe.name,
            "ingredients_added": len(ingredients or []),
            "ingredients_linked_to_db": n_linked,
            "instructions_added": len(instructions or []),
        }

    def update_recipe_metadata(
        recipe_id: str,
        name: Optional[str] = None,
        servings: Optional[int] = None,
        cuisine_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        prep_time: Optional[int] = None,
        cook_time: Optional[int] = None,
    ) -> dict:
        """Update a recipe's top-level fields (does NOT touch ingredients
        or instructions). Only provided fields are changed.

        Args:
            recipe_id: UUID of the recipe.
            name: New name.
            servings: New servings count.
            cuisine_type: New cuisine type.
            tags: Replace the tags list entirely.
            description: New description.
            prep_time: Minutes.
            cook_time: Minutes.
        """
        try:
            rid = UUID(recipe_id)
        except (ValueError, TypeError) as e:
            return {"error": str(e)}
        r = db.query(Recipe).filter(Recipe.recipe_id == rid).first()
        if not r:
            return {"error": "Recipe not found"}
        changed = {}
        if name is not None:
            r.name = name.strip(); changed["name"] = r.name
        if servings is not None:
            r.servings = servings; changed["servings"] = servings
        if cuisine_type is not None:
            r.cuisine_type = cuisine_type.strip() or None; changed["cuisine_type"] = r.cuisine_type
        if tags is not None:
            r.tags = list(tags); changed["tags"] = r.tags
        if description is not None:
            r.description = description.strip() or None; changed["description"] = r.description
        if prep_time is not None:
            r.prep_time = prep_time; changed["prep_time"] = prep_time
        if cook_time is not None:
            r.cook_time = cook_time; changed["cook_time"] = cook_time
        db.commit()
        return {"recipe_id": str(r.recipe_id), "changed": changed}

    def add_ingredient_to_recipe(
        recipe_id: str,
        name: str,
        quantity: float = 0,
        unit: str = "",
        notes: str = "",
    ) -> dict:
        """Append an ingredient to a recipe. Auto-runs lookup_exact and sets
        ingredient_db_id when a canonical match is found.

        Args:
            recipe_id: UUID of the recipe.
            name: Free-text ingredient name.
            quantity: Numeric amount (default 0).
            unit: Unit string ("g", "ml", "pcs", ...).
            notes: Optional notes.
        """
        from backend.services.ingredient_match import lookup_exact
        try:
            rid = UUID(recipe_id)
        except (ValueError, TypeError) as e:
            return {"error": str(e)}
        if not name or not name.strip():
            return {"error": "name is required"}
        r = db.query(Recipe).filter(Recipe.recipe_id == rid).first()
        if not r:
            return {"error": "Recipe not found"}
        match = lookup_exact(db, name)
        ing = Ingredient(
            recipe_id=rid,
            name=name.strip(),
            quantity=quantity,
            unit=unit.strip(),
            notes=notes.strip(),
            ingredient_db_id=match.id if match else None,
        )
        db.add(ing); db.commit(); db.refresh(ing)
        return {
            "ingredient_id": str(ing.ingredient_id),
            "name": ing.name,
            "linked_to_db": bool(match),
            "ingredient_db_id": str(ing.ingredient_db_id) if ing.ingredient_db_id else None,
        }

    def update_ingredient_in_recipe(
        ingredient_id: str,
        name: Optional[str] = None,
        quantity: Optional[float] = None,
        unit: Optional[str] = None,
        notes: Optional[str] = None,
        relink: bool = False,
    ) -> dict:
        """Update fields of one ingredient row. If `relink` is True or `name`
        changes, re-runs lookup_exact and updates ingredient_db_id.

        Args:
            ingredient_id: UUID of the ingredient row.
            name: New name.
            quantity: New quantity.
            unit: New unit.
            notes: New notes.
            relink: Force re-running canonical lookup even if name unchanged.
        """
        from backend.services.ingredient_match import lookup_exact
        try:
            iid = UUID(ingredient_id)
        except (ValueError, TypeError) as e:
            return {"error": str(e)}
        ing = db.query(Ingredient).filter(Ingredient.ingredient_id == iid).first()
        if not ing:
            return {"error": "Ingredient not found"}
        name_changed = False
        if name is not None and name.strip() and name.strip() != ing.name:
            ing.name = name.strip(); name_changed = True
        if quantity is not None:
            ing.quantity = quantity
        if unit is not None:
            ing.unit = unit.strip()
        if notes is not None:
            ing.notes = notes.strip()
        relinked_to = None
        if relink or name_changed:
            match = lookup_exact(db, ing.name)
            ing.ingredient_db_id = match.id if match else None
            relinked_to = str(match.id) if match else None
        db.commit()
        return {
            "ingredient_id": str(ing.ingredient_id),
            "name": ing.name,
            "quantity": ing.quantity,
            "unit": ing.unit,
            "ingredient_db_id": str(ing.ingredient_db_id) if ing.ingredient_db_id else None,
            "relinked_to": relinked_to,
        }

    def remove_ingredient_from_recipe(ingredient_id: str) -> dict:
        """Delete one ingredient row from its recipe.

        Args:
            ingredient_id: UUID of the ingredient row.
        """
        try:
            iid = UUID(ingredient_id)
        except (ValueError, TypeError) as e:
            return {"error": str(e)}
        deleted = (
            db.query(Ingredient)
            .filter(Ingredient.ingredient_id == iid)
            .delete(synchronize_session=False)
        )
        db.commit()
        return {"deleted": bool(deleted)}

    def delete_recipe(recipe_id: str, dry_run: bool = True) -> dict:
        """Delete a recipe (and its ingredients/instructions via cascade).
        Defaults to dry_run — call again with dry_run=False after the user
        confirms.

        Args:
            recipe_id: UUID of the recipe.
            dry_run: If True (default), report what would be deleted.
        """
        try:
            rid = UUID(recipe_id)
        except (ValueError, TypeError) as e:
            return {"error": str(e)}
        r = (
            db.query(Recipe)
            .options(selectinload(Recipe.ingredients), selectinload(Recipe.instructions))
            .filter(Recipe.recipe_id == rid)
            .first()
        )
        if not r:
            return {"error": "Recipe not found"}
        preview = {
            "recipe_id": str(r.recipe_id),
            "name": r.name,
            "ingredients_count": len(r.ingredients or []),
            "instructions_count": len(r.instructions or []),
        }
        if dry_run:
            return {"applied": False, "preview": preview}
        db.delete(r); db.commit()
        return {"applied": True, "preview": preview}

    return [
        replace_ingredient_in_recipes,
        create_recipe,
        update_recipe_metadata,
        add_ingredient_to_recipe,
        update_ingredient_in_recipe,
        remove_ingredient_from_recipe,
        delete_recipe,
    ]


def _build_recipe_read_tools(db: Session):
    """Read-only recipe access — full detail, overview, per-recipe nutrition."""

    def get_recipe(recipe_id: str) -> dict:
        """Fetch one recipe in full: name, description, prep/cook time, servings,
        cuisine, tags, every ingredient (with its CIQUAL FK if linked) and every
        instruction in step order.

        Args:
            recipe_id: UUID of the recipe.
        """
        from uuid import UUID
        try:
            uid = UUID(recipe_id)
        except ValueError:
            return {"error": f"Invalid recipe_id: {recipe_id}"}
        r = (
            db.query(Recipe)
            .options(selectinload(Recipe.ingredients), selectinload(Recipe.instructions))
            .filter(Recipe.recipe_id == uid)
            .first()
        )
        if not r:
            return {"error": "Recipe not found"}
        return {
            "recipe_id": str(r.recipe_id),
            "name": r.name,
            "description": r.description or "",
            "prep_time": r.prep_time,
            "cook_time": r.cook_time,
            "servings": r.servings,
            "cuisine_type": r.cuisine_type or "",
            "tags": list(r.tags or []),
            "is_favorite": bool(r.is_favorite),
            "ingredients": [
                {
                    "ingredient_id": str(i.ingredient_id),
                    "name": i.name,
                    "quantity": i.quantity,
                    "unit": i.unit,
                    "notes": i.notes or "",
                    "ingredient_db_id": str(i.ingredient_db_id) if i.ingredient_db_id else None,
                }
                for i in r.ingredients
            ],
            "instructions": [
                {"step_number": s.step_number, "text": s.instruction_text}
                for s in r.instructions
            ],
        }

    def recipe_overview() -> dict:
        """Summarise the user's recipe collection: total count, favorites,
        top cuisines, top tags, and how many ingredients are linked to a
        CIQUAL canonical row vs. unlinked. Useful for orienting the
        assistant before deciding what to do next."""
        all_recipes = (
            db.query(Recipe).options(selectinload(Recipe.ingredients)).all()
        )
        total = len(all_recipes)
        favorites = sum(1 for r in all_recipes if r.is_favorite)
        cuisines: dict[str, int] = {}
        tag_counts: dict[str, int] = {}
        n_ings = 0
        n_linked = 0
        for r in all_recipes:
            if r.cuisine_type:
                cuisines[r.cuisine_type] = cuisines.get(r.cuisine_type, 0) + 1
            for t in r.tags or []:
                tag_counts[t] = tag_counts.get(t, 0) + 1
            for ing in r.ingredients or []:
                n_ings += 1
                if ing.ingredient_db_id is not None:
                    n_linked += 1
        top = lambda d, k=5: sorted(d.items(), key=lambda x: -x[1])[:k]  # noqa: E731
        return {
            "total_recipes": total,
            "favorites": favorites,
            "top_cuisines": [{"name": n, "count": c} for n, c in top(cuisines)],
            "top_tags": [{"name": n, "count": c} for n, c in top(tag_counts, 8)],
            "total_ingredients": n_ings,
            "linked_to_db": n_linked,
            "unlinked": n_ings - n_linked,
        }

    def get_recipe_nutrition(recipe_id: str) -> dict:
        """Compute total + per-serving nutrition for a recipe (calories,
        proteins, lipides, glucides, salt, AG saturés). Backed by the same
        logic as /api/recipes/{id}/nutrition.

        Args:
            recipe_id: UUID of the recipe.
        """
        from uuid import UUID
        from backend.utils.nutrition import compute_recipe_nutrition
        try:
            uid = UUID(recipe_id)
        except ValueError:
            return {"error": f"Invalid recipe_id: {recipe_id}"}
        r = (
            db.query(Recipe)
            .options(selectinload(Recipe.ingredients))
            .filter(Recipe.recipe_id == uid)
            .first()
        )
        if not r:
            return {"error": "Recipe not found"}
        nutrition = compute_recipe_nutrition(r.ingredients, db)
        servings = r.servings if r.servings and r.servings > 0 else 1
        nutrition["per_serving"] = {k: round(v / servings, 2) for k, v in nutrition.items()}
        nutrition["servings"] = servings
        nutrition["recipe_name"] = r.name
        return nutrition

    return [get_recipe, recipe_overview, get_recipe_nutrition]


def _build_shopping_read_tools(db: Session):
    """Read-only access to the shopping list."""

    def get_shopping_list() -> dict:
        """Current shopping list: every ingredient with its category, check
        state, and contributing source (manual or which recipe added it)."""
        from backend.api.shopping_list import _query_items  # reuse the existing serializer
        items = _query_items(db, include_checked=True)
        return {
            "total": len(items),
            "items": [
                {
                    "item_id": str(it.item_id),
                    "name": it.name,
                    "category": it.category,
                    "is_checked": it.is_checked,
                    "contributions": [
                        {"quantity_text": c.quantity_text, "source_label": c.source_label}
                        for c in it.contributions
                    ],
                }
                for it in items
            ],
        }

    return [get_shopping_list]


def _build_nutrition_tools(db: Session):
    """Read-only access to weekly aggregated nutrition."""

    def get_weekly_nutrition(week_start: str, sex: str = "male") -> dict:
        """Aggregate nutrition over the given week: per-day macros, week totals
        for every CIQUAL nutrient, ANSES daily targets for the given sex,
        and a list of ingredients that couldn't be tracked (missing FK,
        missing density, or empty nutrition row).

        Args:
            week_start: Monday of the week, ISO YYYY-MM-DD.
            sex: 'male' or 'female'. Selects the ANSES target column.
        """
        from backend.api.meal_plan import get_weekly_nutrition as endpoint
        try:
            res = endpoint(week_start=week_start, sex=sex, db=db)
        except HTTPException as e:
            return {"error": e.detail}
        return res.model_dump() if hasattr(res, "model_dump") else dict(res)

    return [get_weekly_nutrition]


def _build_seasonality_tools(db: Session):
    """Seasonality lookup + ranked recipe suggestions for a given month."""

    def get_in_season(month: Optional[int] = None) -> dict:
        """Fruits and vegetables in season for the given month (1–12).
        Defaults to the current month. Each item carries a level:
        'coeur' (cœur de saison) > 'saison' > 'disponibilite'.

        Args:
            month: 1..12. Optional; current month if omitted.
        """
        from backend.services.reference import seasonality_for
        m = month if month is not None else date.today().month
        items = seasonality_for(m)
        return {"month": m, "items": items}

    def suggest_seasonal_recipes(month: Optional[int] = None, k: int = 5) -> dict:
        """Rank the user's saved recipes by how well their ingredients align
        with what's in season for the given month. Returns the top-k.

        Args:
            month: 1..12. Optional; current month if omitted.
            k: number of recipes to return (default 5, max 20).
        """
        from backend.services.seasonality_match import rank_recipes
        m = month if month is not None else date.today().month
        kk = max(1, min(k, 20))
        recipes = (
            db.query(Recipe)
            .options(selectinload(Recipe.ingredients))
            .all()
        )
        ranked = rank_recipes(recipes, m, k=kk)
        return {"month": m, "k": kk, "recipes": ranked}

    return [get_in_season, suggest_seasonal_recipes]


def _build_reference_read_tools(db: Session):
    """Read-only lookup into the ingredient reference DB (CIQUAL + curated)."""

    def find_ingredient_in_db(name: str) -> dict:
        """Search the ingredient knowledge base by name OR alias. Returns
        up to 8 candidates ranked by relevance, with each row's category,
        source, modified flag, density (when set), and which nutrient
        cells are missing — useful before deciding to curate.

        Args:
            name: free-text query; matches alim_nom_fr or any alias.
        """
        from backend.api.ingredients import search_ingredients, get_ingredient
        hits = search_ingredients(q=name, limit=8, db=db)
        out = []
        for h in hits:
            detail = get_ingredient(ingredient_id=h.id, db=db)
            d = detail.model_dump() if hasattr(detail, "model_dump") else dict(detail)
            missing = [
                k for k, v in (d.get("nutrition_data") or {}).items()
                if v is None or v == ""
            ]
            out.append({
                "id": d["id"],
                "name": d["name"],
                "category": d.get("category"),
                "source": d.get("source"),
                "modified": d.get("modified", False),
                "modified_by": d.get("modified_by"),
                "density_g_per_ml": d.get("density_g_per_ml"),
                "aliases": [a["alias_text"] for a in d.get("aliases", [])],
                "missing_nutrients_count": len(missing),
            })
        return {"query": name, "candidates": out}

    return [find_ingredient_in_db]


def _build_shopping_write_tools(db: Session):
    """Add/toggle/remove shopping-list items."""

    def add_shopping_item(name: str, quantity_text: str = "") -> dict:
        """Append a manual item to the shopping list. If an item with the
        same canonical name exists it is reused and a new contribution is
        added.

        Args:
            name: Free-text item name.
            quantity_text: Optional quantity string (e.g. "1 L", "2 pcs").
        """
        from backend.services.shopping_list_sync import _find_or_create_item
        if not name or not name.strip():
            return {"error": "name is required"}
        item = _find_or_create_item(db, name.strip())
        db.add(ShoppingListContribution(
            item_id=item.item_id,
            quantity_text=(quantity_text or "").strip(),
            source_label="Manuel",
        ))
        db.commit(); db.refresh(item)
        return {
            "item_id": str(item.item_id),
            "name": item.name,
            "category": item.category,
            "is_checked": item.is_checked,
        }

    def toggle_shopping_item(item_id: str, is_checked: bool) -> dict:
        """Mark a shopping-list item checked/unchecked.

        Args:
            item_id: UUID of the item.
            is_checked: True to check, False to uncheck.
        """
        try:
            iid = UUID(item_id)
        except (ValueError, TypeError) as e:
            return {"error": str(e)}
        item = db.query(ShoppingList).filter(ShoppingList.item_id == iid).first()
        if not item:
            return {"error": "Item not found"}
        item.is_checked = bool(is_checked)
        db.commit()
        return {"item_id": str(item.item_id), "is_checked": item.is_checked}

    def remove_shopping_item(item_id: str) -> dict:
        """Delete a shopping-list item (and all its contributions via cascade).

        Args:
            item_id: UUID of the item.
        """
        try:
            iid = UUID(item_id)
        except (ValueError, TypeError) as e:
            return {"error": str(e)}
        deleted = (
            db.query(ShoppingList)
            .filter(ShoppingList.item_id == iid)
            .delete(synchronize_session=False)
        )
        db.commit()
        return {"deleted": bool(deleted)}

    return [add_shopping_item, toggle_shopping_item, remove_shopping_item]


def _build_reference_write_tools(db: Session):
    """Curate the ingredient reference DB: category, density, aliases,
    LLM-assisted nutrition fill."""

    from datetime import datetime as _dt, timezone as _tz

    def _mark(row: IngredientDatabase, by: str = "user") -> None:
        row.modified = True
        row.modified_by = by
        row.modified_at = _dt.now(_tz.utc)

    def _resolve(uid_str: str) -> tuple[Optional[IngredientDatabase], Optional[dict]]:
        try:
            uid = UUID(uid_str)
        except (ValueError, TypeError) as e:
            return None, {"error": str(e)}
        row = db.get(IngredientDatabase, uid)
        if not row:
            return None, {"error": "Ingredient not found"}
        return row, None

    def set_ingredient_category(ingredient_db_id: str, category: str) -> dict:
        """Set the supermarket-section category for a reference ingredient.
        Allowed values: Fruits & Légumes, Boulangerie, Viandes & Poissons,
        Produits Laitiers, Surgelés, Épicerie, Épices & Herbes, Boissons,
        Sucreries, Autres.

        Args:
            ingredient_db_id: UUID of the IngredientDatabase row.
            category: One of the 10 allowed labels.
        """
        from backend.services.categorize import CATEGORIES
        if category not in CATEGORIES:
            return {"error": f"category must be one of {CATEGORIES}"}
        row, err = _resolve(ingredient_db_id)
        if err:
            return err
        row.category = category
        _mark(row); db.commit()
        return {"id": str(row.id), "name": row.alim_nom_fr, "category": row.category}

    def set_ingredient_density(ingredient_db_id: str, value: float) -> dict:
        """Set density in g/ml (e.g. eau≈1.0, lait≈1.03, huile≈0.92).

        Args:
            ingredient_db_id: UUID of the IngredientDatabase row.
            value: g/ml, > 0.
        """
        if value is None or value <= 0:
            return {"error": "value must be > 0"}
        row, err = _resolve(ingredient_db_id)
        if err:
            return err
        row.density_g_per_ml = float(value)
        _mark(row); db.commit()
        return {"id": str(row.id), "name": row.alim_nom_fr, "density_g_per_ml": row.density_g_per_ml}

    def add_ingredient_alias(ingredient_db_id: str, alias_text: str) -> dict:
        """Add an alias so future name-lookups find this canonical row.
        Skips if alias equals the canonical name or already exists.

        Args:
            ingredient_db_id: UUID of the IngredientDatabase row.
            alias_text: New alias.
        """
        row, err = _resolve(ingredient_db_id)
        if err:
            return err
        text = (alias_text or "").strip()
        if not text:
            return {"error": "alias_text is required"}
        if text.lower() == row.alim_nom_fr.lower():
            return {"skipped": "alias equals canonical name", "id": str(row.id)}
        existing = (
            db.query(IngredientAlias)
            .filter(IngredientAlias.alias_text.ilike(text))
            .first()
        )
        if existing is not None:
            return {"skipped": "alias already exists", "id": str(row.id)}
        db.add(IngredientAlias(
            ingredient_db_id=row.id, alias_text=text, created_by="user",
        ))
        _mark(row); db.commit()
        return {"id": str(row.id), "name": row.alim_nom_fr, "alias_added": text}

    def fill_ingredient_nutrition(ingredient_db_id: str, dry_run: bool = True) -> dict:
        """Use the LLM to propose values for missing nutrient cells. With
        dry_run=true (default) returns the proposal for review. With
        dry_run=false the proposal is generated AND merged into the row.

        Args:
            ingredient_db_id: UUID of the IngredientDatabase row.
            dry_run: If True (default), return the proposal without writing.
        """
        from backend.api.ingredients import llm_fill_proposal
        row, err = _resolve(ingredient_db_id)
        if err:
            return err
        try:
            res = llm_fill_proposal(ingredient_id=str(row.id), db=db)
        except HTTPException as e:
            return {"error": e.detail}
        proposal = res.proposal if hasattr(res, "proposal") else (res.get("proposal") or {})
        if dry_run:
            return {
                "id": str(row.id),
                "name": row.alim_nom_fr,
                "applied": False,
                "proposal": proposal,
            }
        if not proposal:
            return {"id": str(row.id), "applied": False, "note": "no missing nutrients to fill"}
        merged = dict(row.nutrition_data or {})
        merged.update(proposal)
        row.nutrition_data = merged
        _mark(row, by="llm")
        db.commit()
        return {
            "id": str(row.id),
            "name": row.alim_nom_fr,
            "applied": True,
            "filled": list(proposal.keys()),
        }

    return [
        set_ingredient_category,
        set_ingredient_density,
        add_ingredient_alias,
        fill_ingredient_nutrition,
    ]


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
            *_build_recipe_read_tools(db),
            *_build_meal_plan_tools(db),
            *_build_shopping_tools(db),
            *_build_shopping_read_tools(db),
            *_build_recipe_edit_tools(db),
            *_build_nutrition_tools(db),
            *_build_seasonality_tools(db),
            *_build_reference_read_tools(db),
            *_build_shopping_write_tools(db),
            *_build_reference_write_tools(db),
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
