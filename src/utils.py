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
    import pandas as pd
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=True) as tmp_file:
        file.GetContentFile(tmp_file.name)
        return pd.read_excel(tmp_file.name)


def compute_recipe_protein(ingredients, ingredient_db):
    total_protein = 0.0
    for ing in ingredients:
        st.write(f"Ingredient: {ing.name}, unit: '{unit}', quantity: {ing.quantity}")
        # on check l'unité
        unit = ing.unit.lower()
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
            total_protein += (protein_per_100g * qty) / 100
    return total_protein

def compute_recipe_lipide(ingredients, ingredient_db):
    total_lipide = 0.0
    for ing in ingredients:
        # on check l'unité
        unit = ing.unit.lower()
        if unit == "g":
            qty = ing.quantity
        elif unit == "kg":
            qty = ing.quantity * 1000
        else:
            continue
        # Find the ingredient in the DB
        row = ingredient_db[ingredient_db["alim_nom_fr"] == ing.name]
        if not row.empty:
            lipide_per_100g = row.iloc[0].get("Lipides (g/100 g)",0)
            total_lipide += (lipide_per_100g * qty) / 100
    return total_lipide


def compute_recipe_glucide(ingredients, ingredient_db):
    total_glucide = 0.0
    for ing in ingredients:
        # on check l'unité
        unit = ing.unit.lower()
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
            total_glucide += (glucide_per_100g * qty) / 100
    return total_glucide



def compute_recipe_calorie(ingredients, ingredient_db):
    total_calorie = 0.0
    for ing in ingredients:
        # on check l'unité
        unit = ing.unit.lower()
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
            total_calorie += (calorie_per_100g * qty) / 100
    return total_calorie