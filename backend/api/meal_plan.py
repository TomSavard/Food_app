"""Weekly meal plan: each day is an ordered stack of meals."""
import random
from datetime import date, datetime, timedelta
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from backend.db.models import MealPlanSlot, Recipe
from backend.db.session import get_db
from backend.schemas import (
    MealPlanReorderRequest,
    MealPlanSlotCreate,
    MealPlanSlotResponse,
    MealPlanSlotUpdate,
    MealPlanWeekResponse,
)

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
    db.commit()
    db.refresh(slot)
    _ = slot.recipe
    return _to_response(slot)


@router.patch("/{slot_id}", response_model=MealPlanSlotResponse)
def update_meal(slot_id: UUID, payload: MealPlanSlotUpdate, db: Session = Depends(get_db)):
    slot = db.query(MealPlanSlot).filter(MealPlanSlot.slot_id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")
    if payload.servings is not None:
        if payload.servings < 1:
            raise HTTPException(status_code=400, detail="servings must be >= 1")
        slot.servings = payload.servings
    db.commit()
    db.refresh(slot)
    _ = slot.recipe
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
    deleted = (
        db.query(MealPlanSlot)
        .filter(MealPlanSlot.slot_id == slot_id)
        .delete(synchronize_session=False)
    )
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

    for day_offset in range(7):
        d = monday + timedelta(days=day_offset)
        existing = _next_position(db, d)
        for i in range(meals_per_day - existing if not overwrite else meals_per_day):
            recipe = random.choice(pool)
            db.add(
                MealPlanSlot(
                    slot_date=d,
                    position=existing + i if not overwrite else i,
                    recipe_id=recipe.recipe_id,
                    servings=recipe.servings or 1,
                )
            )
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
