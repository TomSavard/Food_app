import streamlit as st
from src.recipe_manager import load_week_menu

def run(drive, folder_id):
    st.title("🛒 Liste de courses")

    # Charger le menu de la semaine (depuis session ou Drive)
    if "week_menu" not in st.session_state:
        week_menu = load_week_menu(drive, folder_id)
        st.session_state.week_menu = week_menu if week_menu else []

    # Charger les recettes
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

    st.subheader("Ingrédients des recettes de la semaine")
    if shopping_list:
        for (name, unit), qty in shopping_list.items():
            unit_str = f" {unit}" if unit else ""
            st.write(f"- **{qty:g}{unit_str}** {name.capitalize()}")
    else:
        st.info("Aucune recette sélectionnée dans le menu de la semaine.")

    st.divider()

    # Liste libre de produits à ajouter
    st.subheader("Ajouter des produits libres (hors recettes)")
    if "extra_products" not in st.session_state:
        st.session_state.extra_products = []

    # Formulaire d'ajout
    with st.form("add_product_form"):
        new_product = st.text_input("Produit à ajouter (ex: shampoing, lessive...)")
        submitted = st.form_submit_button("Ajouter")
        if submitted and new_product.strip():
            st.session_state.extra_products.append(new_product.strip())
            st.experimental_rerun()

    # Affichage et suppression
    if st.session_state.extra_products:
        st.write("**Produits ajoutés :**")
        for i, prod in enumerate(st.session_state.extra_products):
            cols = st.columns([8, 1])
            cols[0].write(f"- {prod}")
            if cols[1].button("❌", key=f"del_prod_{i}"):
                st.session_state.extra_products.pop(i)
                st.experimental_rerun()
    else:
        st.info("Aucun produit ajouté manuellement.")
