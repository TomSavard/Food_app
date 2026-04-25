"""Weekly meal plan: each day is an ordered stack of meals."""
import random
from datetime import date, datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from pydantic import BaseModel

from backend.db.models import IngredientDatabase, MealPlanSlot, Recipe
from backend.db.session import get_db
from backend.schemas import (
    MealPlanReorderRequest,
    MealPlanSlotCreate,
    MealPlanSlotResponse,
    MealPlanSlotUpdate,
    MealPlanWeekResponse,
)
from backend.services.anses import DAILY_MACROS, RDI
from backend.services.shopping_list_sync import (
    cleanup_orphan_items,
    sync_slot_added,
    sync_slot_changed,
)
from backend.utils.nutrition import convert_to_grams, safe_float

router = APIRouter(prefix="/api/meal-plan", tags=["meal-plan"])

DEFAULT_MEALS_PER_DAY = 3


def _parse_date(s: str) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date '{s}', expected YYYY-MM-DD")


def _ensure_monday(d: date) -> date:
    if d.weekday() != 0:
        raise HTTPException(status_code=400, detail=f"week_start {d} must be a Monday")
    return d


def _to_response(s: MealPlanSlot) -> MealPlanSlotResponse:
    return MealPlanSlotResponse(
        slot_id=s.slot_id,
        slot_date=s.slot_date.isoformat(),
        position=s.position,
        recipe_id=s.recipe_id,
        recipe_name=s.recipe.name if s.recipe else "",
        servings=s.servings,
    )


def _next_position(db: Session, d: date) -> int:
    last = (
        db.query(MealPlanSlot)
        .filter(MealPlanSlot.slot_date == d)
        .order_by(MealPlanSlot.position.desc())
        .first()
    )
    return (last.position + 1) if last else 0


@router.get("", response_model=MealPlanWeekResponse)
def get_meal_plan(
    week_start: str = Query(..., description="Monday in YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    monday = _ensure_monday(_parse_date(week_start))
    sunday = monday + timedelta(days=6)
    slots = (
        db.query(MealPlanSlot)
        .options(joinedload(MealPlanSlot.recipe))
        .filter(MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday)
        .order_by(MealPlanSlot.slot_date, MealPlanSlot.position)
        .all()
    )
    return MealPlanWeekResponse(
        week_start=monday.isoformat(),
        slots=[_to_response(s) for s in slots],
    )


@router.post("", response_model=MealPlanSlotResponse, status_code=201)
def add_meal(payload: MealPlanSlotCreate, db: Session = Depends(get_db)):
    if payload.servings < 1:
        raise HTTPException(status_code=400, detail="servings must be >= 1")
    d = _parse_date(payload.slot_date)
    recipe = db.query(Recipe).filter(Recipe.recipe_id == payload.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe {payload.recipe_id} not found")

    pos = payload.position if payload.position is not None else _next_position(db, d)
    slot = MealPlanSlot(
        slot_date=d,
        position=pos,
        recipe_id=payload.recipe_id,
        servings=payload.servings,
    )
    db.add(slot)
    db.flush()
    _ = slot.recipe
    sync_slot_added(db, slot)
    db.commit()
    db.refresh(slot)
    return _to_response(slot)


@router.patch("/{slot_id}", response_model=MealPlanSlotResponse)
def update_meal(slot_id: UUID, payload: MealPlanSlotUpdate, db: Session = Depends(get_db)):
    slot = db.query(MealPlanSlot).filter(MealPlanSlot.slot_id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    servings_changed = False
    if payload.servings is not None:
        if payload.servings < 1:
            raise HTTPException(status_code=400, detail="servings must be >= 1")
        if slot.servings != payload.servings:
            slot.servings = payload.servings
            servings_changed = True
    db.flush()
    if servings_changed:
        _ = slot.recipe
        sync_slot_changed(db, slot)
    db.commit()
    db.refresh(slot)
    return _to_response(slot)


@router.put("/reorder", response_model=MealPlanWeekResponse)
def reorder(payload: MealPlanReorderRequest, db: Session = Depends(get_db)):
    """Bulk-apply new (slot_date, position) values for a set of slots.

    To avoid temporarily violating UNIQUE(slot_date, position), we first
    move every affected row to a negative position, then apply the new ones.
    """
    if not payload.items:
        return MealPlanWeekResponse(week_start="", slots=[])

    ids = [item.slot_id for item in payload.items]
    slots = db.query(MealPlanSlot).filter(MealPlanSlot.slot_id.in_(ids)).all()
    if len(slots) != len(payload.items):
        raise HTTPException(status_code=404, detail="One or more slots not found")
    by_id = {s.slot_id: s for s in slots}

    # Stage 1: park every row at -1 - i to clear collisions.
    for i, s in enumerate(slots):
        s.position = -1 - i
    db.flush()

    # Stage 2: apply final coordinates.
    for item in payload.items:
        s = by_id[item.slot_id]
        s.slot_date = _parse_date(item.slot_date)
        s.position = item.position
    db.commit()

    # Return the whole affected week (anchored on the first item's Monday).
    anchor = _parse_date(payload.items[0].slot_date)
    monday = anchor - timedelta(days=anchor.weekday())
    sunday = monday + timedelta(days=6)
    rows = (
        db.query(MealPlanSlot)
        .options(joinedload(MealPlanSlot.recipe))
        .filter(MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday)
        .order_by(MealPlanSlot.slot_date, MealPlanSlot.position)
        .all()
    )
    return MealPlanWeekResponse(
        week_start=monday.isoformat(),
        slots=[_to_response(s) for s in rows],
    )


@router.delete("/{slot_id}", status_code=204)
def delete_meal(slot_id: UUID, db: Session = Depends(get_db)):
    # FK ON DELETE CASCADE on shopping_list_contributions.slot_id removes the
    # contributions; we then prune any items left empty.
    deleted = (
        db.query(MealPlanSlot)
        .filter(MealPlanSlot.slot_id == slot_id)
        .delete(synchronize_session=False)
    )
    db.flush()
    cleanup_orphan_items(db)
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Slot not found")


@router.post("/generate", response_model=MealPlanWeekResponse)
def generate(
    week_start: str = Query(...),
    meals_per_day: int = Query(DEFAULT_MEALS_PER_DAY, ge=1, le=10),
    overwrite: bool = Query(False),
    db: Session = Depends(get_db),
):
    monday = _ensure_monday(_parse_date(week_start))
    sunday = monday + timedelta(days=6)

    if overwrite:
        db.query(MealPlanSlot).filter(
            MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday
        ).delete(synchronize_session=False)
        db.flush()

    favorites = db.query(Recipe).filter(Recipe.is_favorite == True).all()  # noqa: E712
    pool = favorites or db.query(Recipe).limit(50).all()
    if not pool:
        raise HTTPException(status_code=400, detail="No recipes available")

    new_slots: list[MealPlanSlot] = []
    for day_offset in range(7):
        d = monday + timedelta(days=day_offset)
        existing = _next_position(db, d)
        for i in range(meals_per_day - existing if not overwrite else meals_per_day):
            recipe = random.choice(pool)
            slot = MealPlanSlot(
                slot_date=d,
                position=existing + i if not overwrite else i,
                recipe_id=recipe.recipe_id,
                servings=recipe.servings or 1,
            )
            db.add(slot)
            new_slots.append(slot)
    db.flush()
    if overwrite:
        cleanup_orphan_items(db)
    for s in new_slots:
        sync_slot_added(db, s)
    db.commit()

    rows = (
        db.query(MealPlanSlot)
        .options(joinedload(MealPlanSlot.recipe))
        .filter(MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday)
        .order_by(MealPlanSlot.slot_date, MealPlanSlot.position)
        .all()
    )
    return MealPlanWeekResponse(
        week_start=monday.isoformat(),
        slots=[_to_response(s) for s in rows],
    )


# ---- Weekly nutrition ----

class NutritionDay(BaseModel):
    date: str
    macros: dict[str, float]


class UntrackedItem(BaseModel):
    slot_date: str
    recipe_name: str
    ingredient_name: str
    reason: str  # 'missing_fk' | 'missing_density' | 'no_data' | 'unknown_unit'


class WeeklyNutritionResponse(BaseModel):
    week_start: str
    days: list[NutritionDay]
    week: dict[str, float]
    rdi: dict[str, float]
    untracked: list[UntrackedItem]


def _zero_macros() -> dict[str, float]:
    return {k: 0.0 for k in DAILY_MACROS}


@router.get("/nutrition", response_model=WeeklyNutritionResponse)
def get_weekly_nutrition(
    week_start: str = Query(..., description="Monday in YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """Aggregate nutrition over the week's slots.

    For each `MealPlanSlot.recipe.ingredients`:
      - Resolve the canonical row via `ingredient_db_id` (NULL → untracked).
      - Convert quantity to grams via `convert_to_grams` (spoon table +
        density). Failure modes recorded as `missing_density` / `unknown_unit`.
      - Multiply each per-100g nutrient by `grams * (slot.servings / recipe.servings)`.
    """
    monday = _ensure_monday(_parse_date(week_start))
    sunday = monday + timedelta(days=6)

    slots = (
        db.query(MealPlanSlot)
        .options(joinedload(MealPlanSlot.recipe))
        .filter(MealPlanSlot.slot_date >= monday, MealPlanSlot.slot_date <= sunday)
        .order_by(MealPlanSlot.slot_date, MealPlanSlot.position)
        .all()
    )

    days_macros: dict[date, dict[str, float]] = {
        monday + timedelta(days=i): _zero_macros() for i in range(7)
    }
    week_full: dict[str, float] = {}
    untracked: list[UntrackedItem] = []

    for slot in slots:
        recipe = slot.recipe
        if recipe is None or not recipe.ingredients:
            continue
        ratio = (slot.servings or 1) / max(1, recipe.servings or 1)
        for ing in recipe.ingredients:
            if ing.ingredient_db_id is None:
                untracked.append(UntrackedItem(
                    slot_date=slot.slot_date.isoformat(),
                    recipe_name=recipe.name,
                    ingredient_name=ing.name,
                    reason="missing_fk",
                ))
                continue
            row = db.get(IngredientDatabase, ing.ingredient_db_id)
            if row is None:
                continue
            grams = convert_to_grams(ing.quantity or 0, ing.unit or "", row.density_g_per_ml)
            if grams is None:
                u = (ing.unit or "").strip().lower()
                volume_or_spoon = u in {"ml", "cl", "l"} or any(
                    sp in u for sp in ("cuillere", "cuillère", "cas", "cac", "verre", "tasse")
                )
                reason = "missing_density" if volume_or_spoon else "unknown_unit"
                untracked.append(UntrackedItem(
                    slot_date=slot.slot_date.isoformat(),
                    recipe_name=recipe.name,
                    ingredient_name=ing.name,
                    reason=reason,
                ))
                continue
            if not row.nutrition_data:
                untracked.append(UntrackedItem(
                    slot_date=slot.slot_date.isoformat(),
                    recipe_name=recipe.name,
                    ingredient_name=ing.name,
                    reason="no_data",
                ))
                continue

            scale = grams * ratio / 100.0
            for key, raw in row.nutrition_data.items():
                v = safe_float(raw)
                if v is None:
                    continue
                contribution = v * scale
                week_full[key] = week_full.get(key, 0.0) + contribution
                if key in DAILY_MACROS:
                    days_macros[slot.slot_date][key] = (
                        days_macros[slot.slot_date].get(key, 0.0) + contribution
                    )

    days = [
        NutritionDay(
            date=d.isoformat(),
            macros={k: round(days_macros[d].get(k, 0.0), 2) for k in DAILY_MACROS},
        )
        for d in sorted(days_macros)
    ]
    week = {k: round(v, 2) for k, v in week_full.items()}
    return WeeklyNutritionResponse(
        week_start=monday.isoformat(),
        days=days,
        week=week,
        rdi=dict(RDI),
        untracked=untracked,
    )
