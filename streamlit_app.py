import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


from src.utils import _on_edit_recipe, save_changes, ensure_drive_connection
from src.recipe_manager import cached_load_recipes, save_recipes

ensure_drive_connection()
drive = st.session_state.drive
folder_id = st.session_state.folder_id

# Page configuration
st.set_page_config(
    page_title="My Food",
    page_icon="🍲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load recipes data
if "recipes" not in st.session_state:
    with st.spinner("Loading recipes..."):
        st.session_state.recipes = cached_load_recipes(drive, folder_id)
        st.session_state.need_save = False

save_changes(drive, folder_id, save_recipes)

st.title("Welcome to My Food 🍲")
st.markdown("Navigate through the app using the sidebar.")