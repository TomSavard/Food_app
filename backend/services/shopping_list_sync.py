"""
Single source of truth for keeping the shopping list in sync with meal-plan
slots. Called from meal-plan endpoints (and transitively, the chat tools).

Auto-removal of contributions when a slot is deleted is handled by the FK
ON DELETE CASCADE; this module additionally cleans up any item left with
zero contributions (auto-vanishing items).
"""
from __future__ import annotations

from datetime import date
from typing import Iterable

from sqlalchemy.orm import Session

from backend.db.models import (
    MealPlanSlot,
    Recipe,
    ShoppingList,
    ShoppingListContribution,
)
from backend.services.categorize import categorize


_FR_WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]


def _weekday_fr(d: date) -> str:
    return _FR_WEEKDAYS[d.weekday()]


def _source_label(recipe: Recipe, slot_date: date) -> str:
    return f"{recipe.name} · {_weekday_fr(slot_date)}"


def _scaled_quantity_text(qty: float, unit: str, ratio: float) -> str:
    if not qty:
        # No quantity on the recipe ingredient → keep the unit as-is, no number.
        return (unit or "").strip()
    scaled = qty * ratio
    # Trim 2-decimal noise: 1.0 → "1", 1.5 → "1.5", 0.33 → "0.33".
    if scaled == int(scaled):
        num = str(int(scaled))
    else:
        num = f"{round(scaled, 2)}".rstrip("0").rstrip(".")
    return f"{num} {unit}".strip() if unit else num


def _next_position(db: Session) -> int:
    last = (
        db.query(ShoppingList)
        .order_by(ShoppingList.position.desc())
        .first()
    )
    return (last.position + 1) if last else 0


def _find_or_create_item(db: Session, name: str, ingredient_db_id=None) -> ShoppingList:
    """Match by lowercased+trimmed name. Create if missing, with category
    resolved via the categorize service (db lookup → heuristic → 'Autres').
    Carries the recipe ingredient's `ingredient_db_id` FK forward when known."""
    needle = name.strip()
    item = (
        db.query(ShoppingList)
        .filter(ShoppingList.name.ilike(needle))
        .first()
    )
    if item:
        if ingredient_db_id and not item.ingredient_db_id:
            item.ingredient_db_id = ingredient_db_id
            db.flush()
        return item
    item = ShoppingList(
        name=needle,
        position=_next_position(db),
        is_checked=False,
        category=categorize(db, needle),
        ingredient_db_id=ingredient_db_id,
    )
    db.add(item)
    db.flush()
    return item


def sync_slot_added(db: Session, slot: MealPlanSlot) -> None:
    """Pull each ingredient of `slot.recipe` into the shopping list,
    scaled by the slot's servings vs. recipe's default servings."""
    recipe = slot.recipe
    if recipe is None or not recipe.ingredients:
        return
    base_servings = recipe.servings or 1
    ratio = (slot.servings or 1) / max(1, base_servings)
    label = _source_label(recipe, slot.slot_date)

    for ing in recipe.ingredients:
        if not ing.name:
            continue
        item = _find_or_create_item(db, ing.name, ingredient_db_id=ing.ingredient_db_id)
        db.add(
            ShoppingListContribution(
                item_id=item.item_id,
                quantity_text=_scaled_quantity_text(ing.quantity or 0, ing.unit or "", ratio),
                source_label=label,
                recipe_id=recipe.recipe_id,
                slot_id=slot.slot_id,
            )
        )
    db.flush()


def sync_slot_changed(db: Session, slot: MealPlanSlot) -> None:
    """Replace this slot's contributions (used when servings or recipe changes)."""
    db.query(ShoppingListContribution).filter(
        ShoppingListContribution.slot_id == slot.slot_id
    ).delete(synchronize_session=False)
    db.flush()
    sync_slot_added(db, slot)
    cleanup_orphan_items(db)


def cleanup_orphan_items(db: Session) -> int:
    """Delete items whose contributions list is now empty.

    Returns the number of deleted items.
    """
    orphan_ids = [
        row[0]
        for row in db.query(ShoppingList.item_id)
        .outerjoin(ShoppingListContribution)
        .group_by(ShoppingList.item_id)
        .having(_count_zero())
        .all()
    ]
    if not orphan_ids:
        return 0
    db.query(ShoppingList).filter(ShoppingList.item_id.in_(orphan_ids)).delete(
        synchronize_session=False
    )
    db.flush()
    return len(orphan_ids)


def _count_zero():
    from sqlalchemy import func
    return func.count(ShoppingListContribution.contribution_id) == 0


def sync_slots_added(db: Session, slots: Iterable[MealPlanSlot]) -> None:
    for slot in slots:
        sync_slot_added(db, slot)
