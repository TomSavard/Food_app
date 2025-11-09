from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime


# Ingredient schemas
class IngredientBase(BaseModel):
    name: str
    quantity: float = 0.0
    unit: str = ""
    notes: str = ""


class IngredientCreate(IngredientBase):
    pass


class IngredientResponse(IngredientBase):
    ingredient_id: UUID
    
    class Config:
        from_attributes = True


# Instruction schemas
class InstructionBase(BaseModel):
    step_number: int
    instruction_text: str


class InstructionCreate(BaseModel):
    instruction_text: str


class InstructionResponse(InstructionBase):
    instruction_id: UUID
    
    class Config:
        from_attributes = True


# Recipe schemas
class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    prep_time: int = 0
    cook_time: int = 0
    servings: int = 1
    cuisine_type: Optional[str] = None
    tags: List[str] = []
    utensils: List[str] = []
    image_url: Optional[str] = None


class RecipeCreate(RecipeBase):
    ingredients: List[IngredientCreate] = []
    instructions: List[InstructionCreate] = []


class RecipeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    prep_time: Optional[int] = None
    cook_time: Optional[int] = None
    servings: Optional[int] = None
    cuisine_type: Optional[str] = None
    tags: Optional[List[str]] = None
    utensils: Optional[List[str]] = None
    image_url: Optional[str] = None
    ingredients: Optional[List[IngredientCreate]] = None
    instructions: Optional[List[InstructionCreate]] = None


class RecipeResponse(RecipeBase):
    recipe_id: UUID
    created_at: datetime
    updated_at: datetime
    ingredients: List[IngredientResponse] = []
    instructions: List[InstructionResponse] = []
    
    class Config:
        from_attributes = True


class RecipeListResponse(BaseModel):
    recipes: List[RecipeResponse]
    total: int

