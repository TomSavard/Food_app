from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from datetime import datetime, timezone
import uuid
from backend.db.session import Base


class Recipe(Base):
    """Recipe model"""
    __tablename__ = "recipes"
    
    recipe_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    prep_time = Column(Integer, default=0)  # minutes
    cook_time = Column(Integer, default=0)  # minutes
    servings = Column(Integer, default=1)
    cuisine_type = Column(String(100), index=True)
    tags = Column(ARRAY(String), default=[])
    image_url = Column(String(500))  # URL or path to image (replacing Google Drive file ID)
    is_favorite = Column(Boolean, default=False, index=True)  # Star/favorite flag
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    ingredients = relationship("Ingredient", back_populates="recipe", cascade="all, delete-orphan")
    instructions = relationship("Instruction", back_populates="recipe", cascade="all, delete-orphan", order_by="Instruction.step_number")
    
    def __repr__(self):
        return f"<Recipe(name='{self.name}', recipe_id='{self.recipe_id}')>"


class Ingredient(Base):
    """Ingredient model - belongs to a recipe"""
    __tablename__ = "ingredients"
    
    ingredient_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.recipe_id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    quantity = Column(Float, default=0.0)
    unit = Column(String(50), default="")
    notes = Column(String(500), default="")
    
    # Relationship
    recipe = relationship("Recipe", back_populates="ingredients")
    
    def __repr__(self):
        return f"<Ingredient(name='{self.name}', quantity={self.quantity} {self.unit})>"


class Instruction(Base):
    """Cooking instruction step - belongs to a recipe"""
    __tablename__ = "instructions"
    
    instruction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.recipe_id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    instruction_text = Column(Text, nullable=False)
    
    # Relationship
    recipe = relationship("Recipe", back_populates="instructions")
    
    def __repr__(self):
        return f"<Instruction(step={self.step_number}, recipe_id='{self.recipe_id}')>"


class WeekMenu(Base):
    """Weekly menu planning"""
    __tablename__ = "week_menus"
    
    menu_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id = Column(UUID(as_uuid=True), ForeignKey("recipes.recipe_id", ondelete="SET NULL"), nullable=True, index=True)
    recipe_name = Column(String(255))  # Denormalized for easier queries and in case recipe is deleted
    note = Column(Text)  # Day, time, guests info, etc.
    menu_date = Column(DateTime)  # Optional: specific date for this menu item
    position = Column(Integer, default=0)  # Order in the menu
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship
    recipe = relationship("Recipe")
    
    def __repr__(self):
        return f"<WeekMenu(recipe_name='{self.recipe_name}', note='{self.note}')>"


class ShoppingList(Base):
    """Shopping list items"""
    __tablename__ = "shopping_list"
    
    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    quantity = Column(String(100), default="")  # Store as string to support "500g", "2 cups", etc.
    is_checked = Column(Boolean, default=False, index=True)
    source = Column(String(500), default="")  # Source: recipe name or "Ajouté manuellement"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<ShoppingList(name='{self.name}', quantity={self.quantity}, checked={self.is_checked})>"


class IngredientDatabase(Base):
    """Ingredient nutrition database (from Excel)"""
    __tablename__ = "ingredient_database"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alim_nom_fr = Column(String(255), nullable=False, unique=True, index=True)
    # Nutrition columns - stored as JSONB for flexibility
    nutrition_data = Column(JSONB)  # Stores all nutrition info as JSON
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<IngredientDatabase(name='{self.alim_nom_fr}')>"

