import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import pandas as pd


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


def load_ingredient_db(drive, folder_id, filename="BDD.xlsx"):
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false and title='{filename}'"}).GetList()
    if not file_list:
        return pd.DataFrame()
    file = file_list[0]
    from io import BytesIO
    file_buffer = BytesIO()
    file.GetContentFile(file_buffer)  # Remplit le buffer avec le contenu du fichier
    file_buffer.seek(0)
    return pd.read_excel(file_buffer)

