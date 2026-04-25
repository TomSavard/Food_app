from pydantic import BaseModel, ConfigDict
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
    
    model_config = ConfigDict(from_attributes=True)


# Instruction schemas
class InstructionBase(BaseModel):
    step_number: int
    instruction_text: str


class InstructionCreate(BaseModel):
    instruction_text: str


class InstructionResponse(InstructionBase):
    instruction_id: UUID
    
    model_config = ConfigDict(from_attributes=True)


# Recipe schemas
class RecipeBase(BaseModel):
    name: str
    description: Optional[str] = None
    prep_time: int = 0
    cook_time: int = 0
    servings: int = 1
    cuisine_type: Optional[str] = None
    tags: List[str] = []
    image_url: Optional[str] = None
    is_favorite: bool = False


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
    image_url: Optional[str] = None
    is_favorite: Optional[bool] = None
    ingredients: Optional[List[IngredientCreate]] = None
    instructions: Optional[List[InstructionCreate]] = None


class RecipeResponse(RecipeBase):
    recipe_id: UUID
    created_at: datetime
    updated_at: datetime
    ingredients: List[IngredientResponse] = []
    instructions: List[InstructionResponse] = []
    
    model_config = ConfigDict(from_attributes=True)


class RecipeListResponse(BaseModel):
    recipes: List[RecipeResponse]
    total: int


# Shopping List schemas
class ShoppingListItemBase(BaseModel):
    name: str
    quantity: str = ""
    source: str = ""


class ShoppingListItemCreate(ShoppingListItemBase):
    is_checked: bool = False


class ShoppingListItemUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[str] = None
    source: Optional[str] = None
    is_checked: Optional[bool] = None


class ShoppingListItemResponse(ShoppingListItemBase):
    item_id: UUID
    is_checked: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ShoppingListResponse(BaseModel):
    items: List[ShoppingListItemResponse]
    total: int


# Meal Plan schemas — stack model: each day holds an ordered list of meals.
class MealPlanSlotResponse(BaseModel):
    slot_id: UUID
    slot_date: str  # ISO date YYYY-MM-DD
    position: int   # 0-based, ordering within the day
    recipe_id: UUID
    recipe_name: str
    servings: int

    model_config = ConfigDict(from_attributes=True)


class MealPlanWeekResponse(BaseModel):
    week_start: str  # ISO date (Monday)
    slots: List[MealPlanSlotResponse]


class MealPlanSlotCreate(BaseModel):
    slot_date: str
    recipe_id: UUID
    servings: int = 1
    position: Optional[int] = None  # default = append to end


class MealPlanSlotUpdate(BaseModel):
    servings: Optional[int] = None


class MealPlanReorderItem(BaseModel):
    slot_id: UUID
    slot_date: str
    position: int


class MealPlanReorderRequest(BaseModel):
    items: List[MealPlanReorderItem]

