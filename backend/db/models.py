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
    ingredient_db_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingredient_database.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationship
    recipe = relationship("Recipe", back_populates="ingredients")
    ingredient_db = relationship("IngredientDatabase")
    
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


from sqlalchemy import Date, UniqueConstraint


class MealPlanSlot(Base):
    """One meal in the day's stack. Ordered by `position`; days hold any
    number of meals. Reordering = updating positions, including across days."""
    __tablename__ = "meal_plan_slots"
    __table_args__ = (
        UniqueConstraint("slot_date", "position", name="uq_meal_plan_slot_date_position"),
    )

    slot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slot_date = Column(Date, nullable=False, index=True)
    position = Column(Integer, nullable=False)
    recipe_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recipes.recipe_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    servings = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    recipe = relationship("Recipe")

    def __repr__(self):
        return f"<MealPlanSlot({self.slot_date} #{self.position} -> {self.recipe_id})>"


class ShoppingList(Base):
    """One ingredient on the shopping list. Quantity & sources live in
    ShoppingListContribution rows (one ingredient may have several)."""
    __tablename__ = "shopping_list"

    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    position = Column(Integer, nullable=False, default=0)
    is_checked = Column(Boolean, default=False, index=True)
    category = Column(String(50), nullable=True, index=True)
    ingredient_db_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingredient_database.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    contributions = relationship(
        "ShoppingListContribution",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="ShoppingListContribution.created_at",
    )

    def __repr__(self):
        return f"<ShoppingList(name='{self.name}', checked={self.is_checked})>"


class ShoppingListContribution(Base):
    """One source contributing to a shopping-list item: a manual add,
    or an ingredient pulled in from a meal-plan slot's recipe."""
    __tablename__ = "shopping_list_contributions"

    contribution_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("shopping_list.item_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity_text = Column(String(100), nullable=False, default="")
    source_label = Column(String(255), nullable=False, default="Manuel")
    recipe_id = Column(
        UUID(as_uuid=True),
        ForeignKey("recipes.recipe_id", ondelete="SET NULL"),
        nullable=True,
    )
    slot_id = Column(
        UUID(as_uuid=True),
        ForeignKey("meal_plan_slots.slot_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    item = relationship("ShoppingList", back_populates="contributions")


class IngredientDatabase(Base):
    """Ingredient knowledge base. Started as CIQUAL nutrition; we layer
    learned categorisation on top — corrected by users + the LLM."""
    __tablename__ = "ingredient_database"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alim_nom_fr = Column(String(255), nullable=False, unique=True, index=True)
    nutrition_data = Column(JSONB)
    category = Column(String(50), nullable=True, index=True)
    source = Column(String(20), nullable=False, default="ciqual")  # 'ciqual' | 'user' | 'llm'

    # Curation tracking: shielded from CIQUAL re-imports.
    modified = Column(Boolean, nullable=False, default=False)
    modified_by = Column(String(20), nullable=True)  # 'user' | 'llm'
    modified_at = Column(DateTime, nullable=True)

    # Volume → mass conversion (per ingredient).
    density_g_per_ml = Column(Float, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    aliases = relationship(
        "IngredientAlias",
        back_populates="ingredient_db",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<IngredientDatabase(name='{self.alim_nom_fr}')>"


class IngredientAlias(Base):
    """Free-text → CIQUAL canonical match, persisted so we don't re-LLM
    every time. `created_by` tracks who confirmed the alias."""
    __tablename__ = "ingredient_aliases"

    alias_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingredient_db_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ingredient_database.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias_text = Column(String(255), nullable=False)
    created_by = Column(String(20), nullable=False)  # 'user' | 'llm'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    ingredient_db = relationship("IngredientDatabase", back_populates="aliases")

