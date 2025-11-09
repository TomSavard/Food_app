# Nutrition Database Setup

## 🎯 Overview

The nutrition calculation feature has been implemented, porting the logic from the Streamlit app to FastAPI. This allows automatic calculation of calories, proteins, lipides, and glucides for recipes based on their ingredients.

## 📋 What's Been Implemented

### 1. Dark Theme ✅
- Complete dark theme CSS applied
- Modern dark color scheme (#121212 background)
- All UI elements updated for dark mode

### 2. Nutrition Calculation Logic ✅
- `safe_float_conversion()` - Handles European decimal format and special cases
- `compute_recipe_nutrition()` - Calculates total nutrition from ingredients
- Supports g, kg, mg units
- Matches ingredients by name (`alim_nom_fr`)

### 3. Database Migration Script ✅
- `scripts/migrate_nutrition_db.py` - Imports BDD.xlsx to PostgreSQL
- Stores nutrition data as JSONB in `ingredient_database` table

### 4. API Endpoint ✅
- `GET /api/recipes/{recipe_id}/nutrition` - Returns nutrition info
- Includes total and per-serving values

### 5. Frontend Display ✅
- Nutrition section in recipe detail modal
- Shows calories, proteins, lipides, glucides
- Displays both total and per-serving values

## 🚀 Setup Instructions

### Step 1: Install Dependencies

```bash
pip install -r requirements_backend.txt
```

This will install `pandas` and `openpyxl` needed for reading Excel files.

### Step 2: Migrate Nutrition Database

1. **Place BDD.xlsx in project root**:
   ```bash
   # Make sure BDD.xlsx is in the same directory as this script
   ls BDD.xlsx
   ```

2. **Run migration script**:
   ```bash
   source .venv/bin/activate
   python scripts/migrate_nutrition_db.py
   ```

   The script will:
   - Load BDD.xlsx
   - Extract nutrition columns
   - Store in `ingredient_database` table
   - Show progress and summary

### Step 3: Verify Migration

Check that ingredients were imported:

```bash
# Using psql or any PostgreSQL client
psql $DATABASE_URL -c "SELECT COUNT(*) FROM ingredient_database;"
```

Or test via API (if you have a test endpoint):

```python
from app.db.session import get_db
from app.db.models import IngredientDatabase

for db in get_db():
    count = db.query(IngredientDatabase).count()
    print(f"Total ingredients in database: {count}")
```

### Step 4: Test Nutrition Calculation

1. **Start the server**:
   ```bash
   ./start_local.sh
   ```

2. **Test with a recipe that has ingredients**:
   ```bash
   # Get a recipe ID first
   curl http://127.0.0.1:8000/api/recipes | python3 -m json.tool | grep recipe_id | head -1
   
   # Then get nutrition (replace {recipe_id} with actual ID)
   curl http://127.0.0.1:8000/api/recipes/{recipe_id}/nutrition | python3 -m json.tool
   ```

3. **Check in frontend**:
   - Open http://127.0.0.1:8000
   - Click on a recipe with ingredients
   - You should see "📊 Valeurs Nutritionnelles" section

## 📊 Nutrition Columns

The system looks for these columns in BDD.xlsx:

- **Calories**: `Energie, Règlement UE N° 1169/2011 (kcal/100 g)`
- **Proteins**: `Protéines, N x facteur de Jones (g/100 g)`
- **Lipides**: `Lipides (g/100 g)`
- **Glucides**: `Glucides (g/100 g)`

## 🔧 How It Works

1. **Ingredient Matching**: Ingredients are matched by exact name (`alim_nom_fr`)
2. **Unit Conversion**: Quantities are converted to grams (g, kg, mg supported)
3. **Calculation**: `(nutrition_per_100g * quantity_in_grams) / 100`
4. **Aggregation**: Sum all ingredients to get recipe totals
5. **Per Serving**: Divide totals by number of servings

## 🐛 Troubleshooting

### No nutrition data showing?

1. **Check if ingredients are in database**:
   ```python
   from app.db.session import get_db
   from app.db.models import IngredientDatabase
   
   for db in get_db():
       # Check if ingredient exists
       ing = db.query(IngredientDatabase).filter(
           IngredientDatabase.alim_nom_fr == "Your Ingredient Name"
       ).first()
       print(ing.nutrition_data if ing else "Not found")
   ```

2. **Check ingredient name matching**:
   - Names must match exactly (case-sensitive)
   - Check for extra spaces or special characters

3. **Check units**:
   - Only g, kg, mg are supported
   - Other units are skipped

### Migration fails?

1. **Check Excel file path**: Make sure `BDD.xlsx` is in project root
2. **Check columns**: Verify `alim_nom_fr` column exists
3. **Check database connection**: Ensure `DATABASE_URL` is set correctly

## 📝 Notes

- Nutrition calculation is optional - recipes without matching ingredients will simply not show nutrition data
- The system gracefully handles missing nutrition data
- European decimal format (comma) is automatically converted
- Special values like "traces", "<5", ranges are handled correctly

## 🎨 Dark Theme

The dark theme is now active by default. To switch back to light theme, edit `frontend/css/styles.css` and uncomment the light theme variables in `:root`.

