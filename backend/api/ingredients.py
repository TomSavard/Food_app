"""
API endpoints for ingredient database search
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from backend.db.session import get_db
from backend.db.models import IngredientDatabase
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/api/ingredients", tags=["ingredients"])


class IngredientSearchResponse(BaseModel):
    """Ingredient search result"""
    id: str
    name: str
    has_nutrition_data: bool
    
    model_config = ConfigDict(from_attributes=True)


@router.get("/search", response_model=List[IngredientSearchResponse])
def search_ingredients(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """
    Search ingredients by name (autocomplete)
    Returns ingredients prioritized by relevance:
    1. Exact matches
    2. Matches starting with search term
    3. Matches containing search term
    """
    if not q or len(q.strip()) < 1:
        return []
    
    search_term = q.strip().lower()
    search_pattern = f"%{search_term}%"
    
    # Get all matching ingredients
    all_matches = db.query(IngredientDatabase).filter(
        IngredientDatabase.alim_nom_fr.ilike(search_pattern)
    ).all()
    
    # Score and sort by relevance
    scored_results = []
    for ing in all_matches:
        name_lower = ing.alim_nom_fr.lower()
        score = 0
        
        # Exact match gets highest score
        if name_lower == search_term:
            score = 1000
        # Starts with search term gets high score
        elif name_lower.startswith(search_term):
            score = 500 - len(name_lower)  # Shorter names first
        # Contains search term gets lower score
        elif search_term in name_lower:
            # Penalize longer names and names where search term appears later
            position = name_lower.find(search_term)
            score = 100 - position - (len(name_lower) / 10)
        else:
            continue  # Shouldn't happen, but just in case
        
        scored_results.append({
            "id": str(ing.id),
            "name": ing.alim_nom_fr,
            "has_nutrition_data": ing.nutrition_data is not None and len(ing.nutrition_data) > 0,
            "_score": score
        })
    
    # Sort by score (descending) and take top results
    scored_results.sort(key=lambda x: x["_score"], reverse=True)
    results = [{"id": r["id"], "name": r["name"], "has_nutrition_data": r["has_nutrition_data"]} 
               for r in scored_results[:limit]]
    
    return results


@router.get("/{ingredient_id}")
def get_ingredient(ingredient_id: str, db: Session = Depends(get_db)):
    """Get a single ingredient by ID"""
    from uuid import UUID
    try:
        ingredient = db.query(IngredientDatabase).filter(
            IngredientDatabase.id == UUID(ingredient_id)
        ).first()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ingredient ID format")
    
    if not ingredient:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    
    return {
        "id": str(ingredient.id),
        "name": ingredient.alim_nom_fr,
        "nutrition_data": ingredient.nutrition_data
    }

