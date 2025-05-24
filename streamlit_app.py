import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive


from src.utils import _on_edit_recipe, save_changes, ensure_drive_connection
from src.recipe_manager import load_recipes, save_recipes



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

# # Load credentials from Streamlit Secrets
# @st.cache_resource
# def get_drive() -> GoogleDrive | None:
#     try:
#         credentials = st.secrets["GOOGLE_DRIVE_CREDENTIALS"]

#         # Authenticate with Google Drive
#         gauth = GoogleAuth()
#         gauth.settings['client_config_backend'] = 'service'
#         gauth.settings['service_config'] = {
#             'client_json_dict': credentials,
#             'client_user_email': credentials.get('client_email')
#         }
#         gauth.ServiceAuth()
#         return GoogleDrive(gauth)

#     except Exception as e:
#         st.error(f"Authentication failed: {e}")
#         return None

# # Get folder ID from secrets
# try:
#     folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
# except KeyError:
#     st.error("Missing GOOGLE_DRIVE_FOLDER_ID in Streamlit Secrets")
#     st.stop()

# # Connect to Google Drive
# drive = get_drive()
# if not drive:
#     st.error("Failed to authenticate with Google Drive.")
#     st.stop()

# st.session_state.drive = drive
# st.session_state.folder_id = folder_id

# Load recipes data
if "recipes" not in st.session_state:
    with st.spinner("Loading recipes..."):
        st.session_state.recipes = load_recipes(drive, folder_id)
        st.session_state.need_save = False

save_changes(drive, folder_id, save_recipes)

st.title("Welcome to My Food 🍲")
st.markdown("Navigate through the app using the sidebar.")