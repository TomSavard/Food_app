import streamlit as st
import json
import pandas as pd
import tempfile
from typing import List, Optional, Dict
from pydrive2.drive import GoogleDrive

from src.models.recipe import Recipe, Ingredient

# Constants
RECIPES_FILE_NAME = "food_recipes_database.json"
WEEK_MENU_FILE_NAME = "week_menu.json"
EXTRA_PRODUCTS_FILE_NAME = "extra_products.json"



@st.cache_data(show_spinner="Chargement du menu de la semaine...")
def cached_load_week_menu(_drive, folder_id):
    return load_week_menu(_drive, folder_id)



def find_recipes_file(drive: GoogleDrive, folder_id: str) -> Optional[Dict]:
    """Find or create the recipes database file in Google Drive"""
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and title='{RECIPES_FILE_NAME}' and trashed=false"}).GetList()
    
    if file_list:
        # Database file exists
        return file_list[0]
    else:
        # Create a new database file
        st.info(f"Creating new recipes database file '{RECIPES_FILE_NAME}'")
        
        # Create empty recipes file
        empty_db = []
        
        # Create a temporary file with empty database
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json") as tmp_file:
            json.dump(empty_db, tmp_file)
            tmp_file_path = tmp_file.name
        
        # Upload to Google Drive
        gfile = drive.CreateFile({
            'title': RECIPES_FILE_NAME,
            'parents': [{'id': folder_id}]
        })
        gfile.SetContentFile(tmp_file_path)
        gfile.Upload()
        
        # Clean up temporary file
        import os
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
            
        return gfile


def load_recipes(drive: GoogleDrive, folder_id: str) -> List[Recipe]:
    """Load all recipes from the database file in Google Drive"""
    recipes_file = find_recipes_file(drive, folder_id)
    
    if not recipes_file:
        return []
    
    # Download the recipes file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_file:
        recipes_file.GetContentFile(tmp_file.name)
        tmp_file_path = tmp_file.name
        
    # Read recipes
    try:
        with open(tmp_file_path, 'r') as f:
            data = json.load(f)
        
        # Convert to Recipe objects
        recipes = [Recipe.from_dict(recipe_data) for recipe_data in data]
        
        # Clean up
        import os
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
            
        return recipes
    
    except Exception as e:
        st.error(f"Failed to load recipes: {e}")
        
        # Clean up in case of error
        import os
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
            
        return []
    
@st.cache_data(show_spinner="Chargement des recettes...")
def cached_load_recipes(_drive, folder_id):
    """Cached version of load_recipes to avoid repeated downloads"""
    return load_recipes(_drive, folder_id)

def clear_recipes_cache():
    """Clear the cached recipes data"""
    cached_load_recipes.clear()

def save_recipes(drive: GoogleDrive, folder_id: str, recipes: List[Recipe]) -> bool:
    """Save all recipes to the database file in Google Drive"""
    recipes_file = find_recipes_file(drive, folder_id)
    
    if not recipes_file:
        st.error("Failed to find or create recipes database file")
        return False
    
    # Convert recipes to dict format
    recipes_data = [recipe.to_dict() for recipe in recipes]
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".json") as tmp_file:
        json.dump(recipes_data, tmp_file, ensure_ascii=False, indent=2)
        tmp_file_path = tmp_file.name
    
    # Upload to Google Drive (overwrite existing file)
    try:
        # Update existing file
        recipes_file.SetContentFile(tmp_file_path)
        recipes_file.Upload()
        
        # Clear cache to force reload on next access
        clear_recipes_cache()
        
        # Clean up
        import os
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
            
        return True
    
    except Exception as e:
        st.error(f"Failed to save recipes: {e}")
        
        # Clean up in case of error
        import os
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
            
        return False

def recipes_to_dataframe(recipes: List[Recipe]) -> pd.DataFrame:
    """Convert a list of recipes to a pandas DataFrame"""
    if not recipes:
        return pd.DataFrame()
    
    # Convert each recipe to a row
    recipe_rows = [recipe.to_dataframe_row() for recipe in recipes]
    
    # Create DataFrame
    df = pd.DataFrame(recipe_rows)
    
    return df

def filter_recipes(recipes: List[Recipe], search_term: str = "", tags: List[str] = None, cuisine: str = None) -> List[Recipe]:
    """Filter recipes based on search criteria"""
    filtered_recipes = recipes
    
    # Filter by search term
    if search_term:
        search_lower = search_term.lower()
        filtered_recipes = [
            r for r in filtered_recipes if 
            search_lower in r.name.lower() or
            search_lower in r.description.lower() or
            any(search_lower in ingredient.name.lower() for ingredient in r.ingredients)
        ]
    
    # Filter by tags
    if tags:
        filtered_recipes = [
            r for r in filtered_recipes if
            any(tag in r.tags for tag in tags)
        ]
    
    # Filter by cuisine type
    if cuisine:
        filtered_recipes = [
            r for r in filtered_recipes if
            cuisine.lower() == r.cuisine_type.lower()
        ]
    
    return filtered_recipes




def load_week_menu(drive, folder_id):
    """Charge le menu de la semaine depuis Google Drive"""
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false and title='{WEEK_MENU_FILE_NAME}'"}).GetList()
    if file_list:
        file = file_list[0]
        content = file.GetContentString()
        return json.loads(content)
    return []





def save_week_menu(drive, folder_id, week_menu):
    """Sauvegarde le menu de la semaine sur Google Drive"""
    # Cherche si le fichier existe déjà
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false and title='{WEEK_MENU_FILE_NAME}'"}).GetList()
    content = json.dumps(week_menu, ensure_ascii=False, indent=2)
    if file_list:
        file = file_list[0]
        file.SetContentString(content)
        file.Upload()
    else:
        file = drive.CreateFile({'title': WEEK_MENU_FILE_NAME, 'parents': [{'id': folder_id}]})
        file.SetContentString(content)
        file.Upload()




def load_extra_products(drive, folder_id):
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false and title='{EXTRA_PRODUCTS_FILE_NAME}'"}).GetList()
    if file_list:
        file = file_list[0]
        content = file.GetContentString()
        return json.loads(content)
    return []

def save_extra_products(drive, folder_id, extra_products):
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false and title='{EXTRA_PRODUCTS_FILE_NAME}'"}).GetList()
    content = json.dumps(extra_products, ensure_ascii=False, indent=2)
    if file_list:
        file = file_list[0]
        file.SetContentString(content)
        file.Upload()
    else:
        file = drive.CreateFile({'title': EXTRA_PRODUCTS_FILE_NAME, 'parents': [{'id': folder_id}]})
        file.SetContentString(content)
        file.Upload()