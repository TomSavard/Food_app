"""
Migration script to import recipes from old format to new database.

Supports:
1. JSON files from Google Drive (food_recipes_database.json)
2. Excel files (recettes.xlsx)
3. Direct Recipe objects from old system
"""

import sys
import os
import json
import pandas as pd
from pathlib import Path
from typing import List, Optional
from uuid import uuid4, UUID

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import get_db, get_engine
from app.db.models import Recipe, Ingredient, Instruction
from sqlalchemy.orm import Session

# Import old models for compatibility
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from models.recipe import Recipe as OldRecipe, Ingredient as OldIngredient


def migrate_from_json(json_file_path: str, db: Session) -> int:
    """Migrate recipes from JSON file (old Google Drive format)"""
    print(f"📖 Reading recipes from JSON: {json_file_path}")
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if not isinstance(data, list):
        print(f"❌ Expected list, got {type(data)}")
        return 0
    
    print(f"✅ Found {len(data)} recipes in JSON file")
    
    migrated_count = 0
    for recipe_data in data:
        try:
            # Convert old Recipe format to new format
            old_recipe = OldRecipe.from_dict(recipe_data)
            new_recipe = convert_old_recipe_to_new(old_recipe, db)
            migrated_count += 1
            print(f"  ✅ Migrated: {old_recipe.name}")
        except Exception as e:
            print(f"  ❌ Failed to migrate recipe: {e}")
            continue
    
    return migrated_count


def migrate_from_excel(excel_file_path: str, db: Session) -> int:
    """Migrate recipes from Excel file"""
    print(f"📖 Reading recipes from Excel: {excel_file_path}")
    
    try:
        df = pd.read_excel(excel_file_path, engine='openpyxl')
        print(f"✅ Found {len(df)} rows in Excel file")
        print(f"   Columns: {list(df.columns)}")
        
        # This is a placeholder - adjust based on Excel structure
        # You'll need to map Excel columns to Recipe fields
        print("⚠️  Excel migration needs custom mapping based on your Excel structure")
        print("   Please check the Excel file structure and update this function")
        
        return 0
    except Exception as e:
        print(f"❌ Error reading Excel: {e}")
        return 0


def convert_old_recipe_to_new(old_recipe: OldRecipe, db: Session) -> Recipe:
    """Convert old Recipe object to new database Recipe"""
    
    # Check if recipe already exists (by name or ID)
    existing = None
    if old_recipe.recipe_id:
        try:
            # Try to convert string UUID to UUID object for comparison
            recipe_uuid = UUID(old_recipe.recipe_id) if isinstance(old_recipe.recipe_id, str) else old_recipe.recipe_id
            existing = db.query(Recipe).filter(Recipe.recipe_id == recipe_uuid).first()
        except (ValueError, AttributeError):
            pass
    
    if not existing:
        existing = db.query(Recipe).filter(Recipe.name == old_recipe.name).first()
    
    if existing:
        print(f"    ⚠️  Recipe '{old_recipe.name}' already exists, skipping...")
        return existing
    
    # Convert recipe_id from string to UUID if needed
    recipe_uuid = None
    if old_recipe.recipe_id:
        try:
            # Try to convert string UUID to UUID object
            if isinstance(old_recipe.recipe_id, str):
                recipe_uuid = UUID(old_recipe.recipe_id)
            else:
                recipe_uuid = old_recipe.recipe_id
        except (ValueError, AttributeError):
            # Invalid UUID format, generate new one
            recipe_uuid = uuid4()
    else:
        recipe_uuid = uuid4()
    
    # Create new recipe
    new_recipe = Recipe(
        recipe_id=recipe_uuid,
        name=old_recipe.name,
        description=old_recipe.description or "",
        prep_time=old_recipe.prep_time or 0,
        cook_time=old_recipe.cook_time or 0,
        servings=old_recipe.servings or 1,
        cuisine_type=old_recipe.cuisine_type or "",
        tags=old_recipe.tags or [],
        utensils=old_recipe.utensils or [],
        image_url=""  # Old system used image_file_id (Google Drive), we'll handle separately
    )
    
    db.add(new_recipe)
    db.flush()  # Get recipe_id
    
    # Migrate ingredients
    for old_ing in old_recipe.ingredients:
        ingredient = Ingredient(
            recipe_id=new_recipe.recipe_id,
            name=old_ing.name,
            quantity=old_ing.quantity or 0.0,
            unit=old_ing.unit or "",
            notes=old_ing.notes or ""
        )
        db.add(ingredient)
    
    # Migrate instructions
    for idx, instruction_text in enumerate(old_recipe.instructions or [], 1):
        instruction = Instruction(
            recipe_id=new_recipe.recipe_id,
            step_number=idx,
            instruction_text=instruction_text
        )
        db.add(instruction)
    
    db.commit()
    db.refresh(new_recipe)
    
    return new_recipe


def main():
    """Main migration function"""
    print("🚀 Starting Recipe Migration\n")
    print("=" * 60)
    
    # Get database session
    db = next(get_db())
    
    migrated_total = 0
    
    # Option 1: Migrate from JSON file (if exists locally)
    json_path = Path(__file__).parent.parent / "food_recipes_database.json"
    if json_path.exists():
        print("\n📁 Found JSON file, migrating...")
        migrated_total += migrate_from_json(str(json_path), db)
    else:
        print("\n📁 No local JSON file found")
        print("   To migrate from Google Drive JSON:")
        print("   1. Download 'food_recipes_database.json' from Google Drive")
        print("   2. Place it in the project root")
        print("   3. Run this script again")
    
    # Option 2: Migrate from Excel
    excel_path = Path(__file__).parent.parent / "recettes.xlsx"
    if excel_path.exists():
        print("\n📁 Found Excel file, checking structure...")
        migrated_total += migrate_from_excel(str(excel_path), db)
    
    print("\n" + "=" * 60)
    print(f"✅ Migration complete! Migrated {migrated_total} recipes")
    
    # Show summary
    total_recipes = db.query(Recipe).count()
    total_ingredients = db.query(Ingredient).count()
    total_instructions = db.query(Instruction).count()
    
    print(f"\n📊 Database Summary:")
    print(f"   Recipes: {total_recipes}")
    print(f"   Ingredients: {total_ingredients}")
    print(f"   Instructions: {total_instructions}")


if __name__ == "__main__":
    main()

