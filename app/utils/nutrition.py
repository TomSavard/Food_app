"""
Nutrition calculation utilities
Ports the logic from Streamlit app to FastAPI
"""
from typing import Optional, Dict, List
from app.db.models import IngredientDatabase, Ingredient
from sqlalchemy.orm import Session
import pandas as pd


def safe_float_conversion(value) -> Optional[float]:
    """
    Safely convert a value to float, handling European decimal format and special cases.
    Ported from Streamlit utils.py
    """
    if value is None:
        return None
    
    import pandas as pd
    if pd.isna(value):
        return None
    
    str_val = str(value).strip().lower()
    
    # Check for invalid values that should return None (no data)
    if str_val in ['-', '', 'nan', 'n/a', 'na']:
        return None
    
    # Check for values that should be treated as 0
    zero_values = ['traces', 'trace', 'tr', '<0.1', '<0,1', '0', '0.0', '0,0']
    if str_val in zero_values:
        return 0.0
    
    # Handle ranges (take the average)
    if '-' in str_val and str_val not in ['-']:
        try:
            parts = str_val.split('-')
            if len(parts) == 2:
                # Convert both parts and take average
                val1 = float(parts[0].strip().replace(',', '.'))
                val2 = float(parts[1].strip().replace(',', '.'))
                return (val1 + val2) / 2
        except:
            pass
    
    # Handle less than values (e.g., "<5" becomes 2.5)
    if str_val.startswith('<'):
        try:
            numeric_part = str_val[1:].strip().replace(',', '.')
            value = float(numeric_part)
            return value / 2  # Take half of the upper limit
        except:
            return 0.0  # If we can't parse it, assume traces
    
    # Handle greater than values (e.g., ">50" becomes 50)
    if str_val.startswith('>'):
        try:
            numeric_part = str_val[1:].strip().replace(',', '.')
            return float(numeric_part)
        except:
            pass
    
    try:
        # Replace comma with dot for European decimal format
        normalized_val = str_val.replace(',', '.')
        return float(normalized_val)
    except (ValueError, TypeError):
        return None


def get_nutrition_value(ingredient_db_row: IngredientDatabase, nutrient_key: str) -> Optional[float]:
    """Get nutrition value from ingredient database row"""
    if not ingredient_db_row.nutrition_data:
        return None
    
    value = ingredient_db_row.nutrition_data.get(nutrient_key)
    return safe_float_conversion(value)


def convert_to_grams(quantity: float, unit: str) -> Optional[float]:
    """
    Convert quantity to grams for nutrition calculation.
    Note: Only weight units (g, kg, mg) are supported for nutrition.
    Volume units (ml, cl, l) are not converted as nutrition data is per 100g.
    """
    unit_lower = unit.lower().strip() if unit else ""
    
    if unit_lower == "g":
        return quantity
    elif unit_lower == "kg":
        return quantity * 1000
    elif unit_lower == "mg":
        return quantity / 1000
    elif unit_lower in ["ml", "cl", "l"]:
        # Volume units - nutrition data is per 100g, so we can't convert volume to weight
        # without density information. Skip for nutrition calculation.
        return None
    else:
        # Unsupported unit for nutrition calculation
        return None


def compute_recipe_nutrition(
    ingredients: List[Ingredient],
    db: Session
) -> Dict[str, float]:
    """
    Compute total nutrition for a recipe from its ingredients.
    Returns dict with: calories, proteins, lipides, glucides
    """
    total_calories = 0.0
    total_proteins = 0.0
    total_lipides = 0.0
    total_glucides = 0.0
    
    # Nutrition column keys (as stored in JSONB)
    NUTRITION_KEYS = {
        "calories": "Energie, Règlement UE N° 1169/2011 (kcal/100 g)",
        "proteins": "Protéines, N x facteur de Jones (g/100 g)",
        "lipides": "Lipides (g/100 g)",
        "glucides": "Glucides (g/100 g)"
    }
    
    for ing in ingredients:
        # Convert quantity to grams
        qty_in_grams = convert_to_grams(ing.quantity, ing.unit)
        if qty_in_grams is None:
            continue  # Skip unsupported units
        
        # Find ingredient in database
        ingredient_db = db.query(IngredientDatabase).filter(
            IngredientDatabase.alim_nom_fr == ing.name
        ).first()
        
        if not ingredient_db:
            continue  # Ingredient not found in database
        
        # Calculate each nutrient
        calories_per_100g = get_nutrition_value(ingredient_db, NUTRITION_KEYS["calories"])
        if calories_per_100g is not None:
            total_calories += (calories_per_100g * qty_in_grams) / 100
        
        proteins_per_100g = get_nutrition_value(ingredient_db, NUTRITION_KEYS["proteins"])
        if proteins_per_100g is not None:
            total_proteins += (proteins_per_100g * qty_in_grams) / 100
        
        lipides_per_100g = get_nutrition_value(ingredient_db, NUTRITION_KEYS["lipides"])
        if lipides_per_100g is not None:
            total_lipides += (lipides_per_100g * qty_in_grams) / 100
        
        glucides_per_100g = get_nutrition_value(ingredient_db, NUTRITION_KEYS["glucides"])
        if glucides_per_100g is not None:
            total_glucides += (glucides_per_100g * qty_in_grams) / 100
    
    return {
        "calories": round(total_calories, 1),
        "proteins": round(total_proteins, 1),
        "lipides": round(total_lipides, 1),
        "glucides": round(total_glucides, 1)
    }

