import streamlit as st
from io import BytesIO
from PIL import Image
from src.recipe_manager import filter_recipes, save_recipes, cached_load_recipes
from src.utils import _on_edit_recipe, save_changes, ensure_drive_connection, load_ingredient_db, compute_recipe_protein, compute_recipe_glucide, compute_recipe_lipide, compute_recipe_calorie

# ---------- RECIPE BROWSER PAGE ----------

ensure_drive_connection()
drive = st.session_state.drive
folder_id = st.session_state.folder_id

if "recipes" not in st.session_state:
    st.session_state.recipes = cached_load_recipes(drive, folder_id)

if "ingredient_db" not in st.session_state:
    st.session_state.ingredient_db = load_ingredient_db(drive, folder_id)

ingredient_db = st.session_state.ingredient_db

st.title("Recipe Browser")

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

    # Initialize selected recipe state
    if "selected_recipe" not in st.session_state:
        st.session_state.selected_recipe = None

    # Display recipes in 3 columns for better density
    cols_per_row = 3
    for row in range(0, len(filtered_recipes), cols_per_row):
        columns = st.columns(cols_per_row)
        
        for col_idx in range(cols_per_row):
            recipe_idx = row + col_idx
            if recipe_idx < len(filtered_recipes):
                recipe = filtered_recipes[recipe_idx]
                
                with columns[col_idx]:
                    # Check if this recipe is currently selected
                    is_selected = st.session_state.selected_recipe == recipe.recipe_id

                    # Recipe card with more compact styling
                    card_color = "#26272F"
                    border_color = "#d1d8e0"
                    
                    st.markdown(
                        f"""
                        <div style="
                            background: {card_color};
                            border-radius: 12px;
                            border: 1px solid {border_color};
                            padding: 1em;
                            margin-bottom: 0.5em;
                            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
                            min-height: 180px;
                            color:#fff;
                            position: relative;
                        ">
                            <h5 style="margin-top:0;margin-bottom:0.4em;font-size:20px;">{recipe.name}</h5>
                            <p style="margin-bottom:0.3em;font-size:12px;"><b>Cuisine:</b> {recipe.cuisine_type}</p>
                            <p style="margin-bottom:0.3em;font-size:12px;"><b>Total:</b> {recipe.prep_time + recipe.cook_time} min</p>
                            <p style="margin-bottom:0.3em;font-size:12px;"><b>Tags:</b> {', '.join(recipe.tags[:2])}{'...' if len(recipe.tags) > 2 else ''}</p>
                            <p style="margin-bottom:0.8em;font-size:12px;"><b>Servings:</b> {recipe.servings}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # View/Hide button
                    if is_selected:
                        if st.button("Hide Details", key=f"hide_{recipe_idx}", use_container_width=True):
                            st.session_state.selected_recipe = None
                            st.rerun()
                    else:
                        if st.button("View Recipe", key=f"view_{recipe_idx}", use_container_width=True):
                            st.session_state.selected_recipe = recipe.recipe_id
                            st.rerun()

        # Check if any recipe in this row is selected and display details
        for col_idx in range(cols_per_row):
            recipe_idx = row + col_idx
            if recipe_idx < len(filtered_recipes):
                recipe = filtered_recipes[recipe_idx]

                # If this recipe is selected, display its details below the row
                if st.session_state.selected_recipe == recipe.recipe_id:
                    st.markdown("---")

                    # Create a bordered container for the expanded view
                    st.markdown(
                        """
                        <style>
                        .info-box {
                            border: 2px solid #4A90E2;
                            border-radius: 15px;
                            padding: 20px;
                            margin: 15px 0;
                            background: #1E1E1E;
                            box-shadow: 0 4px 12px rgba(74, 144, 226, 0.4);
                            color: #FFFFFF;
                            height: fit-content;
                        }
                        .nutrition-box {
                            border: 2px solid #28a745;
                            border-radius: 15px;
                            padding: 20px;
                            margin: 15px 0;
                            background: #1E1E1E;
                            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
                            color: #FFFFFF;
                            height: fit-content;
                        }
                        .column-container {
                            display: flex;
                            flex-direction: column;
                            justify-content: flex-end;
                            height: 100%;
                        }
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    st.markdown(f"## 🍽️ {recipe.name}")
                    
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.write(recipe.description)

                        st.write("### 🥘 Ingredients")
                        for ing in recipe.ingredients:
                            st.write(f"- {ing.formatted_quantity()} {ing.unit} {ing.name} {ing.notes}")

                        st.write("### 📝 Instructions")
                        for j, step in enumerate(recipe.instructions, 1):
                            st.write(f"{j}. {step}")

                        # Add some space before nutrition box to push it down
                        st.write("")
                        st.write("")
                        
                        # Nutritional information in the left column, positioned at bottom
                        calorie_total = compute_recipe_calorie(recipe.ingredients, ingredient_db)
                        protein_total = compute_recipe_protein(recipe.ingredients, ingredient_db)
                        lipide_total = compute_recipe_lipide(recipe.ingredients, ingredient_db)
                        glucide_total = compute_recipe_glucide(recipe.ingredients, ingredient_db)
                        
                        st.markdown(
                            f"""
                            <div class="nutrition-box">
                                <h4 style="margin-top: 0; color: #28a745;">Nutrition Facts</h4>
                                <p style="color: #E0E0E0; margin-bottom: 8px;">
                                    <strong>Calories:</strong> {calorie_total:.1f} kcal &nbsp;&nbsp;&nbsp;&nbsp;
                                    <strong>Protéines:</strong> {protein_total:.1f} g
                                </p>
                                <p style="color: #E0E0E0; margin-bottom: 0;">
                                    <strong>Lipides:</strong> {lipide_total:.1f} g &nbsp;&nbsp;&nbsp;&nbsp;
                                    <strong>Glucides:</strong> {glucide_total:.1f} g
                                </p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    with col2:
                        if recipe.image_file_id:
                            try:
                                img_file = drive.CreateFile({'id': recipe.image_file_id})
                                img_content = BytesIO(img_file.GetContentString(content_type="image/jpeg").encode())
                                image = Image.open(img_content)
                                st.image(image, use_column_width=True, caption="Recipe Image")
                            except:
                                st.warning("Image not available")
                        
                        # Add space to push info box to bottom (align with nutrition box)
                        st.write("")
                        st.write("")
                        
                        # Recipe info in a dark-themed info box
                        st.markdown(
                            f"""
                            <div class="info-box">
                                <h4 style="margin-top: 0; color: #4A90E2;">Timing & Info</h4>
                                <p style="color: #E0E0E0;"><strong>Preparation:</strong> {recipe.prep_time} min</p>
                                <p style="color: #E0E0E0;"><strong>Cooking:</strong> {recipe.cook_time} min</p>
                                <p style="color: #E0E0E0;"><strong>Total:</strong> {recipe.prep_time + recipe.cook_time} min</p>
                                <p style="color: #E0E0E0;"><strong>Servings:</strong> {recipe.servings}</p>
                                <p style="color: #E0E0E0;"><strong>Cuisine:</strong> {recipe.cuisine_type}</p>
                                <p style="color: #E0E0E0;"><strong>Tags:</strong> {', '.join(recipe.tags)}</p>
                                <p style="color: #E0E0E0;"><strong>Ustensils:</strong> {', '.join(recipe.utensils)}</p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    # Action buttons
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col1:
                        if st.button("❌ Close Recipe", key=f"close_{recipe_idx}", use_container_width=True):
                            st.session_state.selected_recipe = None
                            st.rerun()
                    with col2:
                        if st.button("✏️ Edit Recipe", key=f"edit_{recipe_idx}", use_container_width=True):
                            _on_edit_recipe(recipe)
                    with col3:
                        if st.button("🗑️ Delete Recipe", key=f"delete_{recipe_idx}", type="primary", use_container_width=True):
                            # Store a reference to the specific recipe index to delete
                            recipe_index = next((idx for idx, r in enumerate(st.session_state.recipes)
                                                if r.recipe_id == recipe.recipe_id), None)

                            if recipe_index is not None:
                                st.session_state.confirm_delete = True
                                st.session_state.recipe_to_delete = recipe
                                st.session_state.recipe_index_to_delete = recipe_index
                            else:
                                st.error("Recipe not found in the list.")

                    # Delete confirmation with dark-themed warning
                    if ("confirm_delete" in st.session_state and st.session_state.confirm_delete and 
                        st.session_state.recipe_to_delete.recipe_id == recipe.recipe_id):

                        st.markdown(
                            f"""
                            <div style="
                                background: #3D2914;
                                border: 1px solid #D4A574;
                                border-radius: 8px;
                                padding: 15px;
                                margin: 15px 0;
                                border-left: 4px solid #e17055;
                            ">
                                <h4 style="margin-top: 0; color: #D4A574;">⚠️ Confirm Deletion</h4>
                                <p style="margin-bottom: 0; color: #D4A574;">
                                    Are you sure you want to delete '<strong>{st.session_state.recipe_to_delete.name}</strong>'? 
                                    This action cannot be undone.
                                </p>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        col1, col2 = st.columns([1, 1])

                        with col1:
                            if st.button("✅ Yes, Delete", key=f"confirm_delete_{recipe_idx}", type="primary", use_container_width=True):
                                if "recipe_index_to_delete" in st.session_state:
                                    # Delete by index instead of filtering by ID
                                    st.session_state.recipes.pop(st.session_state.recipe_index_to_delete)
                                    st.session_state.need_save = True
                                    st.session_state.selected_recipe = None
                                    del st.session_state.confirm_delete
                                    del st.session_state.recipe_to_delete
                                    del st.session_state.recipe_index_to_delete
                                    save_changes(drive, folder_id, save_recipes)
                                    st.success("Recipe deleted successfully!")
                                    st.rerun()

                        with col2:
                            if st.button("❌ Cancel", key=f"cancel_delete_{recipe_idx}", use_container_width=True):
                                del st.session_state.confirm_delete
                                if "recipe_to_delete" in st.session_state:
                                    del st.session_state.recipe_to_delete
                                st.rerun()
                    
                    st.markdown("---")
                    break  # Only show one expanded recipe at a time