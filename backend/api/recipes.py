import dataclasses
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import StreamingResponse
import io
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import desc, String, func
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
import os, uuid

from backend.db.session import get_db
from backend.db.models import Recipe, Ingredient, Instruction, RecipeImage
from backend.schemas import (
    RecipeCreate,
    RecipeSummary,
    RecipeUpdate,
    RecipeResponse,
    RecipeListResponse,
    RecipeWithNutritionResponse,
)
from backend.utils.nutrition import compute_recipe_nutrition
from backend.storage import get_storage_service, PresignedUrlResponse

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
    """List all recipes with optional filtering (full data with ingredients/instructions)
    
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


@router.get("/summary", response_model=RecipeListResponse)
def list_recipes_summary(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    cuisine: Optional[str] = None,
    ingredient: Optional[str] = None,
    tag: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lightweight list: recipe metadata only, NO ingredients/instructions.
    
    Use this for the list/grid view. Open individual recipes for full detail.
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

    base_query = apply_filters(db.query(Recipe))
    total = base_query.count()

    recipes = base_query.order_by(
        desc(Recipe.is_favorite), desc(Recipe.created_at)
    ).offset(skip).limit(limit).all()

    return RecipeListResponse(recipes=recipes, total=total)


@router.get("/{recipe_id}", response_model=RecipeWithNutritionResponse)
def get_recipe(recipe_id: UUID, db: Session = Depends(get_db)):
    """Get a single recipe by ID (includes pre-computed nutrition)"""
    recipe = db.query(Recipe).options(
        selectinload(Recipe.ingredients),
        selectinload(Recipe.instructions)
    ).filter(Recipe.recipe_id == recipe_id).first()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found"
        )

    nutrition = compute_recipe_nutrition(recipe.ingredients, db)
    servings = recipe.servings if recipe.servings > 0 else 1
    nutrition["per_serving"] = {
        k: round(v / servings, 1) for k, v in nutrition.items()
    }
    nutrition["servings"] = servings

    recipe_dict = RecipeResponse.model_validate(recipe).model_dump()
    recipe_dict["nutrition"] = nutrition
    return RecipeWithNutritionResponse(**recipe_dict)


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
        k: round(v / servings, 1) for k, v in nutrition.items()
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
            notes=ing_data.notes,
            ingredient_db_id=ing_data.ingredient_db_id,
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
                notes=ing_data.notes,
                ingredient_db_id=ing_data.ingredient_db_id,
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


# ===========================================================================
# Image management (Neon Object Storage)
# ===========================================================================


class ImageUploadRequest(BaseModel):
    content_type: str = "image/jpeg"
    size_bytes: int
    original_filename: Optional[str] = None


@router.post("/{recipe_id}/images/presigned-url")
async def get_presigned_upload_url(
    recipe_id: UUID,
    body: ImageUploadRequest,
    db: Session = Depends(get_db),
):
    """Return a presigned URL for direct upload to Neon Object Storage."""
    recipe = db.query(Recipe).filter(Recipe.recipe_id == recipe_id).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found",
        )

    storage = get_storage_service()
    valid, error = storage.validate_upload(body.content_type, body.size_bytes)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    ext = os.path.splitext(body.original_filename or "")[1].lower() or ".jpg"
    object_key = f"recipes/{recipe_id}/{uuid.uuid4().hex}{ext}"
    result = storage.generate_presigned_put_url(object_key, body.content_type, body.size_bytes)

    return dataclasses.asdict(result)


@router.post("/{recipe_id}/images/upload", response_model=dict)
async def upload_recipe_image(
    recipe_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload an image file directly to S3 via the backend."""
    recipe = db.query(Recipe).filter(Recipe.recipe_id == recipe_id).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found",
        )

    storage = get_storage_service()
    valid, error = storage.validate_upload(file.content_type, file.size)
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    object_key = f"recipes/{recipe_id}/{uuid.uuid4().hex}{ext}"
    await storage.upload_file(file.file, object_key, file.content_type)

    image = RecipeImage(
        recipe_id=recipe_id,
        object_key=object_key,
        original_filename=file.filename,
        content_type=file.content_type,
        size_bytes=file.size,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return {"image_id": str(image.image_id), "object_key": image.object_key}


@router.patch("/{recipe_id}/images/complete", response_model=dict)
async def complete_image_upload(
    recipe_id: UUID,
    object_key: str,
    db: Session = Depends(get_db),
):
    """Register an uploaded image in the database."""
    recipe = db.query(Recipe).filter(Recipe.recipe_id == recipe_id).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found",
        )

    existing = db.query(RecipeImage).filter(
        RecipeImage.recipe_id == recipe_id,
        RecipeImage.object_key == object_key,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Image already registered")

    image = RecipeImage(
        recipe_id=recipe_id,
        object_key=object_key,
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    return {"image_id": str(image.image_id), "object_key": image.object_key}


@router.get("/{recipe_id}/images", response_model=list[dict])
def list_recipe_images(
    recipe_id: UUID,
    db: Session = Depends(get_db),
):
    """List all images for a recipe."""
    images = db.query(RecipeImage).filter(
        RecipeImage.recipe_id == recipe_id
    ).order_by(RecipeImage.sort_order).all()

    return [
        {
            "image_id": str(img.image_id),
            "object_key": img.object_key,
            "original_filename": img.original_filename,
            "content_type": img.content_type,
            "size_bytes": img.size_bytes,
            "sort_order": img.sort_order,
            "created_at": img.created_at.isoformat(),
        }
        for img in images
    ]


@router.get("/{recipe_id}/images/{object_key:path}")
async def get_recipe_image(
    recipe_id: UUID,
    object_key: str,
    db: Session = Depends(get_db),
):
    """Proxy an image from S3 to the frontend."""
    recipe = db.query(Recipe).filter(Recipe.recipe_id == recipe_id).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with id {recipe_id} not found",
        )

    # Verify the object_key belongs to this recipe
    if f"recipes/{recipe_id}/" not in object_key:
        raise HTTPException(status_code=403, detail="Unauthorized")

    storage = get_storage_service()
    obj = storage._client.get_object(Bucket=storage.bucket, Key=object_key)
    return StreamingResponse(
        io.BytesIO(obj["Body"].read()),
        media_type=obj.get("ContentType", "application/octet-stream"),
    )


@router.delete("/{recipe_id}/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recipe_image(
    recipe_id: UUID,
    image_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete an image from both Neon Object Storage and the database."""
    image = db.query(RecipeImage).filter(
        RecipeImage.image_id == image_id,
        RecipeImage.recipe_id == recipe_id,
    ).first()
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found",
        )

    storage = get_storage_service()
    result = storage.delete_object(image.object_key)
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)

    db.delete(image)
    db.commit()

    return None

