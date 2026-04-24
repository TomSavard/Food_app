"""
Migration script to import BDD.xlsx nutrition database into PostgreSQL
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from sqlalchemy.orm import Session
from app.db.session import get_db, get_engine, Base
from app.db.models import IngredientDatabase
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Path to BDD.xlsx (relative to project root)
BDD_XLSX_PATH = project_root / "BDD.xlsx"

# Nutrition columns to extract
NUTRITION_COLUMNS = {
    "Energie, Règlement UE N° 1169/2011 (kcal/100 g)": "Energie, Règlement UE N° 1169/2011 (kcal/100 g)",
    "Protéines, N x facteur de Jones (g/100 g)": "Protéines, N x facteur de Jones (g/100 g)",
    "Lipides (g/100 g)": "Lipides (g/100 g)",
    "Glucides (g/100 g)": "Glucides (g/100 g)"
}


def migrate_nutrition_database(db: Session):
    """Migrate BDD.xlsx to IngredientDatabase table"""
    if not os.path.exists(BDD_XLSX_PATH):
        print(f"Error: BDD.xlsx not found at {BDD_XLSX_PATH}")
        print("Please place BDD.xlsx in the project root directory.")
        return
    
    print(f"Loading {BDD_XLSX_PATH}...")
    try:
        df = pd.read_excel(BDD_XLSX_PATH, engine='openpyxl')
        print(f"✅ Loaded {len(df)} rows from Excel file")
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return
    
    # Check required columns
    if "alim_nom_fr" not in df.columns:
        print("❌ Error: 'alim_nom_fr' column not found in Excel file")
        print(f"Available columns: {list(df.columns)}")
        return
    
    # Get all nutrition columns that exist in the dataframe
    available_nutrition_cols = {}
    for key, col_name in NUTRITION_COLUMNS.items():
        if col_name in df.columns:
            available_nutrition_cols[col_name] = col_name
        else:
            print(f"⚠️  Warning: Nutrition column '{col_name}' not found in Excel")
    
    if not available_nutrition_cols:
        print("❌ Error: No nutrition columns found in Excel file")
        return
    
    print(f"✅ Found {len(available_nutrition_cols)} nutrition columns")
    
    migrated_count = 0
    skipped_count = 0
    updated_count = 0
    duplicate_count = 0
    error_count = 0
    
    # Track processed names to avoid duplicates within the same batch
    processed_names = set()
    
    for idx, row in df.iterrows():
        ingredient_name = row.get("alim_nom_fr")
        
        if pd.isna(ingredient_name) or not str(ingredient_name).strip():
            skipped_count += 1
            continue
        
        ingredient_name = str(ingredient_name).strip()
        
        # Skip if we've already processed this name in this run (duplicate in Excel)
        if ingredient_name in processed_names:
            duplicate_count += 1
            continue
        
        processed_names.add(ingredient_name)
        
        # Build nutrition data JSON
        nutrition_data = {}
        for col_name in available_nutrition_cols.keys():
            value = row.get(col_name)
            # Store raw value (will be converted when calculating)
            nutrition_data[col_name] = value if pd.notna(value) else None
        
        try:
            # Check if ingredient already exists
            existing = db.query(IngredientDatabase).filter(
                IngredientDatabase.alim_nom_fr == ingredient_name
            ).first()
            
            if existing:
                # Update existing record
                existing.nutrition_data = nutrition_data
                updated_count += 1
            else:
                # Create new record
                new_ingredient = IngredientDatabase(
                    alim_nom_fr=ingredient_name,
                    nutrition_data=nutrition_data
                )
                db.add(new_ingredient)
                migrated_count += 1
            
            # Commit in smaller batches to avoid large rollbacks
            if (migrated_count + updated_count) % 50 == 0:
                db.commit()
                print(f"  Processed {migrated_count + updated_count} ingredients...")
                
        except Exception as e:
            db.rollback()
            error_count += 1
            print(f"  ⚠️  Error processing '{ingredient_name}': {e}")
            continue
    
    # Final commit
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  ⚠️  Error on final commit: {e}")
        print(f"  Rolling back last batch...")
    
    print(f"\n✅ Migration complete!")
    print(f"   - New ingredients: {migrated_count}")
    print(f"   - Updated ingredients: {updated_count}")
    print(f"   - Skipped (empty names): {skipped_count}")
    print(f"   - Duplicates in Excel (skipped): {duplicate_count}")
    print(f"   - Errors: {error_count}")
    print(f"   - Total processed: {migrated_count + updated_count + skipped_count + duplicate_count}")


if __name__ == "__main__":
    print("Starting nutrition database migration...")
    
    # Get database session
    for db_session in get_db():
        migrate_nutrition_database(db_session)
    
    print("Nutrition database migration script finished.")

