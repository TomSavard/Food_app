"""Shopping list — items hold contributions describing where each
piece of the quantity came from (manual or meal-plan slot)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from backend.db.models import ShoppingList, ShoppingListContribution
from backend.db.session import get_db
from backend.schemas import (
    ShoppingListItemCreate,
    ShoppingListItemResponse,
    ShoppingListItemUpdate,
    ShoppingListReorderRequest,
    ShoppingListResponse,
)
from backend.services.shopping_list_sync import _find_or_create_item

router = APIRouter(prefix="/api/shopping-list", tags=["shopping-list"])


def _query_items(db: Session, include_checked: bool = True):
    q = db.query(ShoppingList).options(selectinload(ShoppingList.contributions))
    if not include_checked:
        q = q.filter(ShoppingList.is_checked == False)  # noqa: E712
    return q.order_by(ShoppingList.is_checked, ShoppingList.position).all()


@router.get("", response_model=ShoppingListResponse)
def list_items(include_checked: bool = Query(True), db: Session = Depends(get_db)):
    items = _query_items(db, include_checked)
    return ShoppingListResponse(items=items, total=len(items))


@router.post("", response_model=ShoppingListItemResponse, status_code=201)
def add_manual(payload: ShoppingListItemCreate, db: Session = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    item = _find_or_create_item(db, name)
    db.add(
        ShoppingListContribution(
            item_id=item.item_id,
            quantity_text=payload.quantity_text.strip(),
            source_label=(payload.source_label or "Manuel").strip(),
        )
    )
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=ShoppingListItemResponse)
def update_item(
    item_id: UUID, payload: ShoppingListItemUpdate, db: Session = Depends(get_db)
):
    item = db.query(ShoppingList).filter(ShoppingList.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if payload.name is not None:
        new_name = payload.name.strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        item.name = new_name
    if payload.is_checked is not None:
        item.is_checked = payload.is_checked
    db.commit()
    db.refresh(item)
    return item


@router.put("/reorder", response_model=ShoppingListResponse)
def reorder(payload: ShoppingListReorderRequest, db: Session = Depends(get_db)):
    if not payload.items:
        items = _query_items(db)
        return ShoppingListResponse(items=items, total=len(items))

    ids = [it.item_id for it in payload.items]
    items = db.query(ShoppingList).filter(ShoppingList.item_id.in_(ids)).all()
    if len(items) != len(payload.items):
        raise HTTPException(status_code=404, detail="One or more items not found")

    # Stage at negative positions to mirror the meal-plan reorder pattern.
    for i, it in enumerate(items):
        it.position = -1 - i
    db.flush()
    by_id = {it.item_id: it for it in items}
    for entry in payload.items:
        by_id[entry.item_id].position = entry.position
    db.commit()
    refreshed = _query_items(db)
    return ShoppingListResponse(items=refreshed, total=len(refreshed))


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: UUID, db: Session = Depends(get_db)):
    deleted = db.query(ShoppingList).filter(ShoppingList.item_id == item_id).delete(
        synchronize_session=False
    )
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")


@router.delete("/contributions/{contribution_id}", status_code=204)
def delete_contribution(contribution_id: UUID, db: Session = Depends(get_db)):
    contrib = (
        db.query(ShoppingListContribution)
        .filter(ShoppingListContribution.contribution_id == contribution_id)
        .first()
    )
    if not contrib:
        raise HTTPException(status_code=404, detail="Contribution not found")
    item_id = contrib.item_id
    db.delete(contrib)
    db.flush()
    remaining = (
        db.query(ShoppingListContribution)
        .filter(ShoppingListContribution.item_id == item_id)
        .count()
    )
    if remaining == 0:
        db.query(ShoppingList).filter(ShoppingList.item_id == item_id).delete(
            synchronize_session=False
        )
    db.commit()


@router.delete("", status_code=204)
def clear_all(db: Session = Depends(get_db)):
    db.query(ShoppingList).delete(synchronize_session=False)
    db.commit()
