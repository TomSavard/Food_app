from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import desc, String, func
from typing import Optional
from uuid import UUID

from app.db.session import get_db
from app.db.models import Recipe, Ingredient, Instruction
from app.schemas import (
    RecipeCreate,
    RecipeUpdate,
    RecipeResponse,
    RecipeListResponse
)
from app.utils.nutrition import compute_recipe_nutrition

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


@router.get("", response_model=RecipeListResponse)
def list_recipes(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    cuisine: Optional[str] = None,
    ingredient: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all recipes with optional filtering
    
    - search: Search in recipe name and description
    - cuisine: Filter by cuisine type
    - ingredient: Filter by ingredient name (partial match, e.g., "poulet" matches "poulet cru")
    - tag: Filter by tag
    """
    
    def apply_filters(q):
        if search:
            q = q.filter(
                Recipe.name.ilike(f"%{search}%") |
                Recipe.description.ilike(f"%{search}%")
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
        return q

    query = apply_filters(
        db.query(Recipe).options(
            selectinload(Recipe.ingredients),
            selectinload(Recipe.instructions),
        )
    )
    total = apply_filters(db.query(Recipe)).count()

    # Favorites first, then newest
    recipes = query.order_by(desc(Recipe.is_favorite), desc(Recipe.created_at)).offset(skip).limit(limit).all()
    
    return RecipeListResponse(recipes=recipes, total=total)


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(recipe_id: UUID, db: Session = Depends(get_db)):
    """Get a single recipe by ID"""
    # Eagerly load ingredients and instructions
    recipe = db.query(Recipe).options(
        selectinload(Recipe.ingredients),
        selectinload(Recipe.instructions)
    ).filter(Recipe.recipe_id == recipe_id).first()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found"
        )
    
    return recipe


@router.get("/{recipe_id}/nutrition")
def get_recipe_nutrition(recipe_id: UUID, db: Session = Depends(get_db)):
    """Get nutrition information for a recipe"""
    recipe = db.query(Recipe).options(
        selectinload(Recipe.ingredients)
    ).filter(Recipe.recipe_id == recipe_id).first()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found"
        )
    
    # Calculate nutrition
    nutrition = compute_recipe_nutrition(recipe.ingredients, db)
    
    # Add per-serving values
    servings = recipe.servings if recipe.servings > 0 else 1
    nutrition["per_serving"] = {
        "calories": round(nutrition["calories"] / servings, 1),
        "proteins": round(nutrition["proteins"] / servings, 1),
        "lipides": round(nutrition["lipides"] / servings, 1),
        "glucides": round(nutrition["glucides"] / servings, 1)
    }
    nutrition["servings"] = servings
    
    return nutrition


@router.post("", response_model=RecipeResponse, status_code=status.HTTP_201_CREATED)
def create_recipe(recipe_data: RecipeCreate, db: Session = Depends(get_db)):
    """Create a new recipe"""
    # Create recipe
    recipe = Recipe(
        name=recipe_data.name,
        description=recipe_data.description,
        prep_time=recipe_data.prep_time,
        cook_time=recipe_data.cook_time,
        servings=recipe_data.servings,
        cuisine_type=recipe_data.cuisine_type,
        tags=recipe_data.tags,
        image_url=recipe_data.image_url,
        is_favorite=recipe_data.is_favorite
    )
    
    db.add(recipe)
    db.flush()  # Flush to get recipe_id
    
    # Add ingredients
    for idx, ing_data in enumerate(recipe_data.ingredients):
        ingredient = Ingredient(
            recipe_id=recipe.recipe_id,
            name=ing_data.name,
            quantity=ing_data.quantity,
            unit=ing_data.unit,
            notes=ing_data.notes
        )
        db.add(ingredient)
    
    # Add instructions
    for idx, instr_data in enumerate(recipe_data.instructions):
        instruction = Instruction(
            recipe_id=recipe.recipe_id,
            step_number=idx + 1,
            instruction_text=instr_data.instruction_text
        )
        db.add(instruction)
    
    db.commit()
    # Eagerly load relationships for response
    db.refresh(recipe)
    # Explicitly load relationships
    recipe.ingredients  # Trigger lazy load if not already loaded
    recipe.instructions  # Trigger lazy load if not already loaded
    
    return recipe


@router.put("/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: UUID,
    recipe_data: RecipeUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing recipe"""
    recipe = db.query(Recipe).filter(Recipe.recipe_id == recipe_id).first()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found"
        )
    
    # Update recipe fields
    update_data = recipe_data.dict(exclude_unset=True, exclude={"ingredients", "instructions"})
    for field, value in update_data.items():
        setattr(recipe, field, value)
    
    # Update ingredients if provided
    if recipe_data.ingredients is not None:
        # Delete existing ingredients
        db.query(Ingredient).filter(Ingredient.recipe_id == recipe_id).delete()
        # Add new ingredients
        for ing_data in recipe_data.ingredients:
            ingredient = Ingredient(
                recipe_id=recipe.recipe_id,
                name=ing_data.name,
                quantity=ing_data.quantity,
                unit=ing_data.unit,
                notes=ing_data.notes
            )
            db.add(ingredient)
    
    # Update instructions if provided
    if recipe_data.instructions is not None:
        # Delete existing instructions
        db.query(Instruction).filter(Instruction.recipe_id == recipe_id).delete()
        # Add new instructions
        for idx, instr_data in enumerate(recipe_data.instructions):
            instruction = Instruction(
                recipe_id=recipe.recipe_id,
                step_number=idx + 1,
                instruction_text=instr_data.instruction_text
            )
            db.add(instruction)
    
    db.commit()
    # Eagerly load relationships for response
    db.refresh(recipe)
    # Explicitly load relationships
    recipe.ingredients  # Trigger lazy load if not already loaded
    recipe.instructions  # Trigger lazy load if not already loaded
    
    return recipe


@router.delete("/{recipe_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe(recipe_id: UUID, db: Session = Depends(get_db)):
    """Delete a recipe"""
    recipe = db.query(Recipe).filter(Recipe.recipe_id == recipe_id).first()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found"
        )
    
    # Cascade delete will handle ingredients and instructions
    db.delete(recipe)
    db.commit()
    
    return None


@router.patch("/{recipe_id}/favorite", response_model=RecipeResponse)
def toggle_recipe_favorite(
    recipe_id: UUID,
    is_favorite: bool,
    db: Session = Depends(get_db)
):
    """Toggle favorite status of a recipe"""
    recipe = db.query(Recipe).options(
        selectinload(Recipe.ingredients),
        selectinload(Recipe.instructions)
    ).filter(Recipe.recipe_id == recipe_id).first()
    
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found"
        )
    
    # Update favorite status
    recipe.is_favorite = is_favorite
    db.commit()
    db.refresh(recipe)
    
    return recipe

