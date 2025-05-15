import streamlit as st
import pandas as pd
import tempfile
import os
import json
from io import BytesIO
from PIL import Image

# Import modules
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# Import custom modules
from src.recipe_manager import (
    load_recipes, save_recipes, recipes_to_dataframe,
    filter_recipes, Recipe, Ingredient
)
from pages import recipe_browser, add_recipe, files_manager, week_menu



# Page configuration
st.set_page_config(
    page_title="Food App",
    page_icon="🍲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load credentials from Streamlit Secrets
@st.cache_resource
def get_drive() -> GoogleDrive | None:
    try:
        credentials = st.secrets["GOOGLE_DRIVE_CREDENTIALS"]
        
        # Authenticate with Google Drive
        gauth = GoogleAuth()
        gauth.settings['client_config_backend'] = 'service'
        gauth.settings['service_config'] = {
            'client_json_dict': credentials,
            'client_user_email': credentials.get('client_email')
        }
        gauth.ServiceAuth()
        return GoogleDrive(gauth)
    
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None

# Get folder ID from secrets
try:
    folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
except KeyError:
    st.error("Missing GOOGLE_DRIVE_FOLDER_ID in Streamlit Secrets")
    st.stop()

# Connect to Google Drive
drive = get_drive()
if not drive:
    st.error("Failed to authenticate with Google Drive.")
    st.stop()

# Sidebar Navigation
st.sidebar.title("Food App 🍲")
if "page" not in st.session_state:
    st.session_state.page = "Recipe Browser"
st.sidebar.radio(
    "Navigate",
    ["Recipe Browser", "Add Recipe", "Files Manager"],
    index=["Recipe Browser", "Add Recipe", "Files Manager"].index(st.session_state.page),
    key="page"
)

# Load recipes data
if "recipes" not in st.session_state:
    with st.spinner("Loading recipes..."):
        st.session_state.recipes = load_recipes(drive, folder_id)
        st.session_state.need_save = False

# Function to save changes when needed
def save_changes():
    if st.session_state.need_save:
        with st.spinner("Saving changes..."):
            if save_recipes(drive, folder_id, st.session_state.recipes):
                st.success("Changes saved successfully!")
                st.session_state.need_save = False
            else:
                st.error("Failed to save changes")

def _on_edit_recipe(recipe):
    st.session_state.edit_recipe = recipe
    st.session_state.view_recipe = False
    st.session_state.page = "Add Recipe"


PAGES = {
    "Recipe Browser": recipe_browser.run,
    "Add Recipe": add_recipe.run,
    "Files Manager": files_manager.run,
    "Week Menu": week_menu.run,
}

page = st.sidebar.radio(
    "Navigate",
    list(PAGES.keys()),
    index=list(PAGES.keys()).index(st.session_state.get("page", "Recipe Browser")),
    key="page",
)

PAGES[page](drive, folder_id)

save_changes()