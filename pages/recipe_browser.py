import streamlit as st
from io import BytesIO
from PIL import Image
from src.recipe_manager import filter_recipes, save_recipes

from src.utils import _on_edit_recipe, save_changes


# ---------- RECIPE BROWSER PAGE ----------
def run(drive, folder_id):
    st.title("Recipe Browser")

    with st.expander("Debug Information", expanded=False):
        st.write(f"Number of recipes: {len(st.session_state.recipes)}")
        st.write("Recipe IDs:")
        for i, r in enumerate(st.session_state.recipes):
            id_value = r.recipe_id
            id_display = f"'{id_value}'" if id_value else "EMPTY"
            id_type = type(id_value).__name__
            st.write(f"{i}. '{r.name}': {id_display} (type: {id_type}, length: {len(str(id_value))})")

    # Filter/Search controls
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        search = st.text_input("Search recipes", "")
    with col2:
        # Get unique tags
        all_tags = set()
        for recipe in st.session_state.recipes:
            all_tags.update(recipe.tags)
        selected_tags = st.multiselect("Filter by tags", sorted(list(all_tags)))
    with col3:
        # Get unique cuisines
        all_cuisines = sorted(list({r.cuisine_type for r in st.session_state.recipes if r.cuisine_type}))
        cuisine = st.selectbox("Cuisine type", [""] + all_cuisines)
    with col4:
        sort_by = st.selectbox("Sort by", ["Name", "Preparation Time", "Total Time"])

    # Filter recipes
    filtered_recipes = filter_recipes(
        st.session_state.recipes,
        search_term=search,
        tags=selected_tags,
        cuisine=cuisine if cuisine else None
    )

    # Sort recipes
    if sort_by == "Preparation Time":
        filtered_recipes = sorted(filtered_recipes, key=lambda r: r.prep_time)
    elif sort_by == "Total Time":
        filtered_recipes = sorted(filtered_recipes, key=lambda r: r.prep_time + r.cook_time)
    else:  # Default: Name
        filtered_recipes = sorted(filtered_recipes, key=lambda r: r.name)

    # Show recipes
    if not filtered_recipes:
        st.info("No recipes found. Try adjusting your filters or adding new recipes.")
    else:
        st.write(f"Found {len(filtered_recipes)} recipes")

        # Display as grid of cards
        cols = st.columns(3)
        for i, recipe in enumerate(filtered_recipes):
            with cols[i % 3]:
                st.subheader(recipe.name)

                # Display image if available
                if recipe.image_file_id:
                    try:
                        img_file = drive.CreateFile({'id': recipe.image_file_id})
                        img_content = BytesIO(img_file.GetContentString(content_type="image/jpeg").encode())
                        image = Image.open(img_content)
                        st.image(image, use_column_width=True)
                    except:
                        st.warning("Image not available")

                st.write(f"**Cuisine:** {recipe.cuisine_type}")
                st.write(f"**Total time:** {recipe.prep_time + recipe.cook_time} min")
                st.write(f"**Tags:** {', '.join(recipe.tags)}")
                st.write(f"**Ustensils:** {', '.join(recipe.utensils)}")

                # View button
                if st.button(f"View Recipe", key=f"view_{i}"):
                    st.session_state.selected_recipe = recipe
                    st.session_state.view_recipe = True

    # Recipe detail view (when a recipe is selected)
    if "view_recipe" in st.session_state and st.session_state.view_recipe:
        recipe = st.session_state.selected_recipe

        with st.expander(f"Recipe: {recipe.name}", expanded=True):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(recipe.name)
                st.write(recipe.description)

                st.write("### Ingredients")
                for ing in recipe.ingredients:
                    st.write(f"- {ing.formatted_quantity()} {ing.unit} {ing.name} {ing.notes}")

                st.write("### Instructions")
                for i, step in enumerate(recipe.instructions, 1):
                    st.write(f"{i}. {step}")

            with col2:
                # Display image if available
                if recipe.image_file_id:
                    try:
                        img_file = drive.CreateFile({'id': recipe.image_file_id})
                        img_content = BytesIO(img_file.GetContentString(content_type="image/jpeg").encode())
                        image = Image.open(img_content)
                        st.image(image, use_column_width=True)
                    except:
                        st.warning("Image not available")

                st.write(f"**Preparation Time:** {recipe.prep_time} min")
                st.write(f"**Cooking Time:** {recipe.cook_time} min")
                st.write(f"**Total Time:** {recipe.prep_time + recipe.cook_time} min")
                st.write(f"**Servings:** {recipe.servings}")
                st.write(f"**Cuisine:** {recipe.cuisine_type}")
                st.write(f"**Tags:** {', '.join(recipe.tags)}")
                st.write(f"**Ustensils:** {', '.join(recipe.utensils)}")


        # Ajouter des boutons d'action en bas de la recette
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            if st.button("Close Recipe"):
                st.session_state.view_recipe = False
                st.rerun()
        with col2:
            st.button(
                "Edit Recipe",
                key=f"edit_{i}",
                on_click=_on_edit_recipe,
                args=(recipe,)
            )
        with col3:
            # Show ID for debugging
            #st.write(f"Recipe ID: {recipe.recipe_id}")

            if st.button("Delete Recipe", type="primary", use_container_width=True):
                # Store a reference to the specific recipe index to delete
                recipe_index = next((i for i, r in enumerate(st.session_state.recipes) 
                                    if r.recipe_id == recipe.recipe_id), None)

                if recipe_index is not None:
                    st.session_state.confirm_delete = True
                    st.session_state.recipe_to_delete = recipe
                    st.session_state.recipe_index_to_delete = recipe_index
                else:
                    st.error("Recipe not found in the list.")

        # Update the delete confirmation handler
        if "confirm_delete" in st.session_state and st.session_state.confirm_delete:
            st.warning(f"Are you sure you want to delete '{st.session_state.recipe_to_delete.name}'?")
            col1, col2 = st.columns([1, 1])

            with col1:
                if st.button("Yes, Delete", type="primary", use_container_width=True):
                    if "recipe_index_to_delete" in st.session_state:
                        # Delete by index instead of filtering by ID
                        st.session_state.recipes.pop(st.session_state.recipe_index_to_delete)
                        st.session_state.need_save = True
                        st.session_state.view_recipe = False
                        del st.session_state.confirm_delete
                        del st.session_state.recipe_to_delete
                        del st.session_state.recipe_index_to_delete
                        save_changes(drive, folder_id, save_recipes)
                        st.success("Recipe deleted successfully!")
                        rerun

            with col2:
                if st.button("Cancel", use_container_width=True):
                    del st.session_state.confirm_delete
                    if "recipe_to_delete" in st.session_state:
                        del st.session_state.recipe_to_delete
                    st.rerun()
