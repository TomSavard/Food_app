import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import pandas as pd
import tempfile

def _on_edit_recipe(recipe):
    st.session_state.edit_recipe = recipe
    st.session_state.view_recipe = False
    st.switch_page("pages/2_ajouter_une_recette.py")

def save_changes(drive, folder_id, save_recipes):
    if st.session_state.get("need_save", False):
        with st.spinner("Saving changes..."):
            if save_recipes(drive, folder_id, st.session_state.recipes):
                st.success("Changes saved successfully!")
                st.session_state.need_save = False
                # Force reload recipes from cache-cleared source
                from src.recipe_manager import cached_load_recipes
                st.session_state.recipes = cached_load_recipes(drive, folder_id)
            else:
                st.error("Failed to save changes")

def ensure_drive_connection():
    if "drive" not in st.session_state or "folder_id" not in st.session_state:
        try:
            credentials = st.secrets["GOOGLE_DRIVE_CREDENTIALS"]
            gauth = GoogleAuth()
            gauth.settings['client_config_backend'] = 'service'
            gauth.settings['service_config'] = {
                'client_json_dict': credentials,
                'client_user_email': credentials.get('client_email')
            }
            gauth.ServiceAuth()
            st.session_state.drive = GoogleDrive(gauth)
            st.session_state.folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
        except Exception as e:
            st.error(f"Google Drive authentication failed: {e}")
            st.stop()

@st.cache_data(show_spinner="Loading ingredient database...")
def load_ingredient_db(_drive, folder_id, filename="BDD.xlsx"):
    """Load ingredient database with caching to avoid repeated downloads"""
    try:
        file_list = _drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false and title='{filename}'"}).GetList()
        if not file_list:
            st.warning(f"File '{filename}' not found in Google Drive folder")
            return pd.DataFrame()
        
        file = file_list[0]
        
        # Get file metadata for debugging
        # file.FetchMetadata()
        # st.write(f"📁 Loading: {file['title']} (Modified: {file.get('modifiedDate', 'Unknown')})")
        
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            file.GetContentFile(tmp_file.name)
            
            # Read the Excel file
            df = pd.read_excel(tmp_file.name, engine='openpyxl')
            
            # Clean up
            import os
            if os.path.exists(tmp_file.name):
                os.remove(tmp_file.name)
            
            # st.write(f"✅ Loaded ingredient database: {df.shape[0]} rows, {df.shape[1]} columns")
            
            # # Show column names for debugging
            # if not df.empty:
            #     st.write(f"📋 Columns: {list(df.columns)}")
            
            return df
            
    except Exception as e:
        st.error(f"Failed to load ingredient database: {e}")
        return pd.DataFrame()

def clear_ingredient_db_cache():
    """Clear the cached ingredient database"""
    load_ingredient_db.clear()
    if "ingredient_db" in st.session_state:
        del st.session_state.ingredient_db

def debug_ingredient_db(drive, folder_id, filename="BDD.xlsx"):
    """Debug function to inspect the ingredient database"""
    st.write("### 🔍 Ingredient Database Debug")
    
    try:
        file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false and title='{filename}'"}).GetList()
        if not file_list:
            st.error(f"❌ File '{filename}' not found in Google Drive")
            return
        
        file = file_list[0]
        file.FetchMetadata()
        
        st.write("**File Information:**")
        st.write(f"- Title: {file['title']}")
        st.write(f"- MIME Type: {file.get('mimeType', 'Unknown')}")
        st.write(f"- Size: {file.get('fileSize', 'Unknown')} bytes")
        st.write(f"- Modified: {file.get('modifiedDate', 'Unknown')}")
        
        # Try to load and show sample data
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
            file.GetContentFile(tmp_file.name)
            
            try:
                df = pd.read_excel(tmp_file.name, engine='openpyxl')
                st.write(f"**Data loaded successfully:** {df.shape[0]} rows, {df.shape[1]} columns")
                
                if not df.empty:
                    st.write("**Columns:**")
                    for i, col in enumerate(df.columns):
                        st.write(f"  {i+1}. {col}")
                    
                    st.write("**Sample data (first 5 rows):**")
                    st.dataframe(df.head())
                    
                    # Check for the ingredient name column
                    if "alim_nom_fr" in df.columns:
                        ingredient_count = df["alim_nom_fr"].dropna().nunique()
                        st.write(f"**Found {ingredient_count} unique ingredients**")
                        
                        st.write("**First 10 ingredients:**")
                        sample_ingredients = df["alim_nom_fr"].dropna().head(10).tolist()
                        for ing in sample_ingredients:
                            st.write(f"- {ing}")
                    else:
                        st.warning("Column 'alim_nom_fr' not found. Available columns:")
                        st.write(list(df.columns))
                        
            except Exception as e:
                st.error(f"Failed to read Excel file: {e}")
            
            finally:
                import os
                if os.path.exists(tmp_file.name):
                    os.remove(tmp_file.name)
                    
    except Exception as e:
        st.error(f"Debug failed: {e}")

def compute_recipe_protein(ingredients, ingredient_db):
    total_protein = 0.0
    for ing in ingredients:
        # Check the unit
        unit = ing.unit.lower().strip()
        if unit == "g":
            qty = ing.quantity
        elif unit == "kg":
            qty = ing.quantity * 1000
        else:
            continue
        # Find the ingredient in the DB
        row = ingredient_db[ingredient_db["alim_nom_fr"] == ing.name]
        if not row.empty:
            protein_per_100g = row.iloc[0].get("Protéines, N x facteur de Jones (g/100 g)", 0)
            if pd.notna(protein_per_100g) and str(protein_per_100g).strip() not in ['-', '', 'nan', 'NaN']:
                try:
                    protein_value = float(protein_per_100g)
                    total_protein += (protein_value * qty) / 100
                except (ValueError, TypeError):
                    # Skip if conversion fails
                    continue
    return total_protein

def compute_recipe_calorie(ingredients, ingredient_db):
    total_calorie = 0.0
    for ing in ingredients:
        # Check the unit
        unit = ing.unit.lower().strip()
        if unit == "g":
            qty = ing.quantity
        elif unit == "kg":
            qty = ing.quantity * 1000
        else:
            continue
        # Find the ingredient in the DB
        row = ingredient_db[ingredient_db["alim_nom_fr"] == ing.name]
        if not row.empty:
            calorie_per_100g = row.iloc[0].get("Energie, Règlement UE N° 1169/2011 (kcal/100 g)", 0)
            if pd.notna(calorie_per_100g) and str(calorie_per_100g).strip() not in ['-', '', 'nan', 'NaN']:
                try:
                    calorie_value = float(calorie_per_100g)
                    total_calorie += (calorie_value * qty) / 100
                except (ValueError, TypeError):
                    # Skip if conversion fails
                    continue
    return total_calorie

def compute_recipe_lipide(ingredients, ingredient_db):
    total_lipide = 0.0
    for ing in ingredients:
        # Check the unit
        unit = ing.unit.lower().strip()
        if unit == "g":
            qty = ing.quantity
        elif unit == "kg":
            qty = ing.quantity * 1000
        else:
            continue
        # Find the ingredient in the DB
        row = ingredient_db[ingredient_db["alim_nom_fr"] == ing.name]
        if not row.empty:
            lipide_per_100g = row.iloc[0].get("Lipides (g/100 g)", 0)
            if pd.notna(lipide_per_100g) and str(lipide_per_100g).strip() not in ['-', '', 'nan', 'NaN']:
                try:
                    lipide_value = float(lipide_per_100g)
                    total_lipide += (lipide_value * qty) / 100
                except (ValueError, TypeError):
                    # Skip if conversion fails
                    continue
    return total_lipide

def compute_recipe_glucide(ingredients, ingredient_db):
    total_glucide = 0.0
    for ing in ingredients:
        # Check the unit
        unit = ing.unit.lower().strip()
        if unit == "g":
            qty = ing.quantity
        elif unit == "kg":
            qty = ing.quantity * 1000
        else:
            continue
        # Find the ingredient in the DB
        row = ingredient_db[ingredient_db["alim_nom_fr"] == ing.name]
        if not row.empty:
            glucide_per_100g = row.iloc[0].get("Glucides (g/100 g)", 0)
            if pd.notna(glucide_per_100g) and str(glucide_per_100g).strip() not in ['-', '', 'nan', 'NaN']:
                try:
                    glucide_value = float(glucide_per_100g)
                    total_glucide += (glucide_value * qty) / 100
                except (ValueError, TypeError):
                    # Skip if conversion fails
                    continue
    return total_glucide

def debug_nutrition_columns(ingredient_db):
    """Debug function to show nutrition-related columns and their sample values"""
    if ingredient_db.empty:
        st.write("❌ Ingredient database is empty")
        return
    
    st.write("### 🔍 Nutrition Columns Debug")
    
    # Define the exact columns we're looking for
    nutrition_columns = {
        "Calories": "Energie, Règlement UE N° 1169/2011 (kcal/100 g)",
        "Proteins": "Protéines, N x facteur de Jones (g/100 g)",
        "Lipides": "Lipides (g/100 g)",
        "Glucides": "Glucides (g/100 g)"
    }
    
    st.write("**Nutrition columns status:**")
    for nutrient, column_name in nutrition_columns.items():
        if column_name in ingredient_db.columns:
            st.write(f"✅ **{nutrient}**: `{column_name}` - Found")
            
            # Show sample values (excluding '-' and empty values)
            sample_data = ingredient_db[column_name].dropna()
            valid_samples = []
            for val in sample_data.head(10):
                if str(val).strip() not in ['-', '', 'nan', 'NaN']:
                    try:
                        float_val = float(val)
                        valid_samples.append(str(val))
                    except:
                        pass
            
            if valid_samples:
                st.write(f"   Sample values: {valid_samples[:5]}")
            else:
                st.write("   ⚠️ No valid numeric values found")
        else:
            st.write(f"❌ **{nutrient}**: `{column_name}` - Not found")
    
    # Show ingredient matching test
    st.write("**Ingredient matching test:**")
    if "alim_nom_fr" in ingredient_db.columns:
        sample_ingredients = ingredient_db["alim_nom_fr"].dropna().head(3).tolist()
        for ing_name in sample_ingredients:
            st.write(f"Testing ingredient: `{ing_name}`")
            row = ingredient_db[ingredient_db["alim_nom_fr"] == ing_name]
            if not row.empty:
                for nutrient, column_name in nutrition_columns.items():
                    if column_name in ingredient_db.columns:
                        value = row.iloc[0].get(column_name, "N/A")
                        st.write(f"  - {nutrient}: {value}")
            st.write("---")

def debug_recipe_nutrition(recipe, ingredient_db):
    """Debug function to show nutrition calculation for a specific recipe"""
    st.write(f"### 🧮 Nutrition Debug for: {recipe.name}")
    
    total_calories = 0
    total_proteins = 0
    total_lipides = 0
    total_glucides = 0
    
    st.write("**Ingredient breakdown:**")
    
    for ing in recipe.ingredients:
        st.write(f"**{ing.name}** - {ing.formatted_quantity()} {ing.unit}")
        
        # Convert to grams
        unit = ing.unit.lower().strip()
        if unit == "g":
            qty_in_grams = ing.quantity
        elif unit == "kg":
            qty_in_grams = ing.quantity * 1000
        else:
            st.write(f"  ⚠️ Unit '{ing.unit}' not supported for nutrition calculation")
            continue
        
        st.write(f"  Quantity in grams: {qty_in_grams}g")
        
        # Find in database
        row = ingredient_db[ingredient_db["alim_nom_fr"] == ing.name]
        if not row.empty:
            st.write(f"  ✅ Found in database")
            
            # Check each nutrient
            nutrients = {
                "Calories": "Energie, Règlement UE N° 1169/2011 (kcal/100 g)",
                "Proteins": "Protéines, N x facteur de Jones (g/100 g)",
                "Lipides": "Lipides (g/100 g)",
                "Glucides": "Glucides (g/100 g)"
            }
            
            for nutrient_name, column_name in nutrients.items():
                if column_name in ingredient_db.columns:
                    value_per_100g = row.iloc[0].get(column_name, 0)
                    st.write(f"    {nutrient_name} per 100g: {value_per_100g}")
                    
                    if pd.notna(value_per_100g) and str(value_per_100g).strip() not in ['-', '', 'nan', 'NaN']:
                        try:
                            numeric_value = float(value_per_100g)
                            total_for_ingredient = (numeric_value * qty_in_grams) / 100
                            st.write(f"    {nutrient_name} total: {total_for_ingredient:.2f}")
                            
                            # Add to totals
                            if nutrient_name == "Calories":
                                total_calories += total_for_ingredient
                            elif nutrient_name == "Proteins":
                                total_proteins += total_for_ingredient
                            elif nutrient_name == "Lipides":
                                total_lipides += total_for_ingredient
                            elif nutrient_name == "Glucides":
                                total_glucides += total_for_ingredient
                                
                        except (ValueError, TypeError):
                            st.write(f"    ❌ Cannot convert '{value_per_100g}' to number")
                    else:
                        st.write(f"    ⚠️ No valid data for {nutrient_name}")
        else:
            st.write(f"  ❌ Not found in database")
        
        st.write("---")
    
    st.write("**Recipe Totals:**")
    st.write(f"- **Calories**: {total_calories:.1f} kcal")
    st.write(f"- **Proteins**: {total_proteins:.1f} g")
    st.write(f"- **Lipides**: {total_lipides:.1f} g")
    st.write(f"- **Glucides**: {total_glucides:.1f} g")