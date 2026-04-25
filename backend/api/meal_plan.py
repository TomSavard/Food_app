"""Weekly meal plan: 7 days × 4 slots (breakfast/lunch/dinner/extra)."""
import random
from datetime import date, datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from backend.db.models import MealPlanSlot, Recipe
from backend.db.session import get_db
from backend.schemas import (
    MealPlanSlotResponse,
    MealPlanSlotUpsert,
    MealPlanWeekResponse,
    SLOTS,
)

router = APIRouter(prefix="/api/meal-plan", tags=["meal-plan"])


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
        slot=s.slot,
        recipe_id=s.recipe_id,
        recipe_name=s.recipe.name if s.recipe else "",
        servings=s.servings,
    )


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
        .all()
    )
    return MealPlanWeekResponse(
        week_start=monday.isoformat(),
        slots=[_to_response(s) for s in slots],
    )


@router.put("/slot", response_model=MealPlanSlotResponse)
def upsert_slot(payload: MealPlanSlotUpsert, db: Session = Depends(get_db)):
    if payload.slot not in SLOTS:
        raise HTTPException(status_code=400, detail=f"slot must be one of {SLOTS}")
    if payload.servings < 1:
        raise HTTPException(status_code=400, detail="servings must be >= 1")
    d = _parse_date(payload.slot_date)
    recipe = db.query(Recipe).filter(Recipe.recipe_id == payload.recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recipe {payload.recipe_id} not found")

    existing = (
        db.query(MealPlanSlot)
        .filter(MealPlanSlot.slot_date == d, MealPlanSlot.slot == payload.slot)
        .first()
    )
    if existing:
        existing.recipe_id = payload.recipe_id
        existing.servings = payload.servings
        slot = existing
    else:
        slot = MealPlanSlot(
            slot_date=d,
            slot=payload.slot,
            recipe_id=payload.recipe_id,
            servings=payload.servings,
        )
        db.add(slot)
    db.commit()
    db.refresh(slot)
    # ensure relationship loaded for response
    _ = slot.recipe
    return _to_response(slot)


@router.delete("/slot", status_code=204)
def clear_slot(
    slot_date: str = Query(...),
    slot: str = Query(...),
    db: Session = Depends(get_db),
):
    if slot not in SLOTS:
        raise HTTPException(status_code=400, detail=f"slot must be one of {SLOTS}")
    d = _parse_date(slot_date)
    deleted = (
        db.query(MealPlanSlot)
        .filter(MealPlanSlot.slot_date == d, MealPlanSlot.slot == slot)
        .delete(synchronize_session=False)
    )
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="No slot at that date+slot")


@router.post("/generate", response_model=MealPlanWeekResponse)
def generate(
    week_start: str = Query(...),
    overwrite: bool = Query(False, description="Replace any existing slots"),
    db: Session = Depends(get_db),
):
    """Fill empty slots of the week with random recipes (favorites first if any)."""
    monday = _ensure_monday(_parse_date(week_start))
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
        raise HTTPException(status_code=400, detail="No recipes available to generate from")

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
    return MealPlanWeekResponse(
        week_start=monday.isoformat(),
        slots=[_to_response(s) for s in slots],
    )
