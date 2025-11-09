from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.db.models import ShoppingList
from app.schemas import (
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    ShoppingListItemResponse,
    ShoppingListResponse
)

router = APIRouter(prefix="/api/shopping-list", tags=["shopping-list"])


@router.get("", response_model=ShoppingListResponse)
def get_shopping_list(
    include_checked: bool = True,
    db: Session = Depends(get_db)
):
    """Get all shopping list items"""
    query = db.query(ShoppingList)
    
    if not include_checked:
        query = query.filter(ShoppingList.is_checked == False)
    
    items = query.order_by(desc(ShoppingList.created_at)).all()
    total = len(items)
    
    return ShoppingListResponse(items=items, total=total)


@router.post("", response_model=ShoppingListItemResponse, status_code=status.HTTP_201_CREATED)
def create_shopping_list_item(
    item: ShoppingListItemCreate,
    db: Session = Depends(get_db)
):
    """Create a new shopping list item"""
    # Check if item with same name already exists and is not checked
    existing = db.query(ShoppingList).filter(
        ShoppingList.name.ilike(item.name),
        ShoppingList.is_checked == False
    ).first()
    
    if existing:
        # Merge quantities if both have quantities
        if existing.quantity and item.quantity:
            existing.quantity = f"{existing.quantity} + {item.quantity}"
        elif item.quantity:
            existing.quantity = item.quantity
        
        # Update source if different
        if existing.source != item.source:
            existing.source = f"{existing.source}, {item.source}"
        
        db.commit()
        db.refresh(existing)
        return existing
    
    # Create new item
    db_item = ShoppingList(
        name=item.name,
        quantity=item.quantity or "",
        source=item.source or "",
        is_checked=item.is_checked
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    return db_item


@router.put("/{item_id}", response_model=ShoppingListItemResponse)
def update_shopping_list_item(
    item_id: UUID,
    item_update: ShoppingListItemUpdate,
    db: Session = Depends(get_db)
):
    """Update a shopping list item"""
    db_item = db.query(ShoppingList).filter(ShoppingList.item_id == item_id).first()
    
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item with id {item_id} not found"
        )
    
    # Update fields if provided
    if item_update.name is not None:
        db_item.name = item_update.name
    if item_update.quantity is not None:
        db_item.quantity = item_update.quantity
    if item_update.source is not None:
        db_item.source = item_update.source
    if item_update.is_checked is not None:
        db_item.is_checked = item_update.is_checked
    
    db.commit()
    db.refresh(db_item)
    
    return db_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shopping_list_item(
    item_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete a shopping list item"""
    db_item = db.query(ShoppingList).filter(ShoppingList.item_id == item_id).first()
    
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shopping list item with id {item_id} not found"
        )
    
    db.delete(db_item)
    db.commit()
    
    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def clear_shopping_list(
    db: Session = Depends(get_db)
):
    """Clear all shopping list items"""
    db.query(ShoppingList).delete()
    db.commit()
    
    return None

