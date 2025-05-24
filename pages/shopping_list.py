import streamlit as st
from src.recipe_manager import load_week_menu, load_extra_products, save_extra_products
from src.utils import ensure_drive_connection


st.title("🛒 Liste de courses")

ensure_drive_connection()
drive = st.session_state.drive
folder_id = st.session_state.folder_id

if drive is None or folder_id is None:
    st.error("Google Drive connection not available. Please reload the app.")
    st.stop()

if "week_menu" not in st.session_state:
    st.session_state.week_menu = load_week_menu(drive, folder_id)

if "extra_products" not in st.session_state:
    st.session_state.extra_products = load_extra_products(drive, folder_id)

if "recipes" not in st.session_state:
    st.session_state.recipes = []

# Retrieve data from session state
week_menu = st.session_state.week_menu
extra_products = st.session_state.extra_products
recipes = st.session_state.recipes

# Générer la liste de courses à partir des recettes du menu
shopping_list = {}
for entry in st.session_state.week_menu:
    recipe_name = entry["recipe"]
    if recipe_name:
        recipe = next((r for r in recipes if r.name == recipe_name), None)
        if recipe:
            for ing in recipe.ingredients:
                key = (ing.name.strip().lower(), ing.unit.strip())
                if key not in shopping_list:
                    shopping_list[key] = 0
                shopping_list[key] += ing.quantity

# Liste libre de produits à ajouter
st.subheader("Ajouter un produit manuellement")

# Formulaire d'ajout
with st.form("add_product_form"):
    new_product = st.text_input("Produit à ajouter (ex: shampoing, lessive...)")
    submitted = st.form_submit_button("Ajouter")
    if submitted and new_product.strip():
        st.session_state.extra_products.append(new_product.strip())
        save_extra_products(drive, folder_id, st.session_state.extra_products)
        st.rerun()

# Debug info
with st.expander("Debug Info"):
    st.write("Week menu:", week_menu)
    st.write("Recipes:", [getattr(r, "name", None) for r in recipes])
    st.write("Extra products:", extra_products)
    st.write("Shopping list:", shopping_list)

if shopping_list:
    for (name, unit), qty in shopping_list.items():
        unit_str = f" {unit}" if unit else ""
        st.write(f"- **{qty:g}{unit_str}** {name.capitalize()}")

    for i, prod in enumerate(st.session_state.extra_products):
        cols = st.columns([8, 1])
        cols[0].write(f"- {prod}")
        if cols[1].button("❌", key=f"del_prod_{i}"):
            st.session_state.extra_products.pop(i)
            save_extra_products(drive, folder_id, st.session_state.extra_products)
            st.rerun()
