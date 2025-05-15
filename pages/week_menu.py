import streamlit as st

def run(drive, folder_id):
    st.title("Menu de la semaine (libre)")

    # Initialisation de la liste si besoin
    if "week_menu" not in st.session_state:
        st.session_state.week_menu = []

    recipes = st.session_state.recipes
    recipe_names = [r.name for r in recipes]

    # Affichage de chaque ligne du menu
    for idx, entry in enumerate(st.session_state.week_menu):
        cols = st.columns([3, 5, 1])
        # Sélecteur de recette
        selected = cols[0].selectbox(
            f"Recette {idx+1}",
            [""] + recipe_names,
            index=(recipe_names.index(entry["recipe"]) + 1) if entry["recipe"] in recipe_names else 0,
            key=f"menu_recipe_{idx}"
        )
        # Champ texte libre
        note = cols[1].text_input(
            "Infos (jour, moment, invités...)", 
            value=entry["note"], 
            key=f"menu_note_{idx}"
        )
        # Bouton suppression
        if cols[2].button("❌", key=f"del_menu_{idx}"):
            st.session_state.week_menu.pop(idx)
            st.rerun()
        else:
            # Mise à jour de la ligne
            st.session_state.week_menu[idx] = {"recipe": selected, "note": note}

    st.markdown("---")
    # Bouton pour ajouter une ligne
    if st.button("Ajouter une recette"):
        st.session_state.week_menu.append({"recipe": "", "note": ""})
        st.rerun()


    # Résumé de la liste de courses
    st.subheader("🛒 Liste de courses")

    # Dictionnaire pour agréger les ingrédients
    shopping_list = {}

    # On parcourt chaque recette sélectionnée
    for entry in st.session_state.week_menu:
        recipe_name = entry["recipe"]
        if recipe_name:
            # Trouver la recette correspondante
            recipe = next((r for r in recipes if r.name == recipe_name), None)
            if recipe:
                for ing in recipe.ingredients:
                    key = (ing.name.strip().lower(), ing.unit.strip())
                    if key not in shopping_list:
                        shopping_list[key] = 0
                    shopping_list[key] += ing.quantity

    # Affichage de la liste de courses
    if shopping_list:
        for (name, unit), qty in shopping_list.items():
            unit_str = f" {unit}" if unit else ""
            st.write(f"- **{qty:g}{unit_str}** {name.capitalize()}")
    else:
        st.info("Aucune recette sélectionnée pour générer la liste de courses.")