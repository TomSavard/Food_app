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

from src.recipe_manager import save_recipes, cached_load_recipes, clear_recipes_cache
from src.utils import ensure_drive_connection, load_ingredient_db, clear_ingredient_db_cache, debug_ingredient_db, debug_nutrition_columns, debug_recipe_nutrition
from src.models.recipe import Recipe, Ingredient

from src.utils import debug_ingredient_nutrition_matching, debug_database_data_quality, debug_ingredient_search

st.title("Add / Edit Recipe")
ensure_drive_connection()
drive = st.session_state.drive
folder_id = st.session_state.folder_id

if "recipes" not in st.session_state:
    st.session_state.recipes = cached_load_recipes(drive, folder_id)

if "ingredient_db" not in st.session_state:
    st.session_state.ingredient_db = load_ingredient_db(drive, folder_id)

ingredient_db = st.session_state.ingredient_db

# Add these to your sidebar debug section (replace the existing debug buttons)
st.sidebar.write("### 🔄 Database Controls")

if st.sidebar.button("🔄 Refresh Ingredient Database"):
    clear_ingredient_db_cache()
    st.session_state.ingredient_db = load_ingredient_db(drive, folder_id)
    st.sidebar.success("Database refreshed!")
    st.rerun()

if st.sidebar.button("🔍 Debug Database"):
    debug_ingredient_db(drive, folder_id)

if st.sidebar.button("🔍 Debug Nutrition Columns"):
    debug_nutrition_columns(ingredient_db)

if st.sidebar.button("📊 Debug Data Quality"):
    debug_database_data_quality(ingredient_db)

# Add this to test nutrition calculation for an existing recipe
if st.sidebar.button("🧮 Test Nutrition Calculation"):
    if st.session_state.recipes:
        test_recipe = st.session_state.recipes[96]  # Test with first recipe
        debug_ingredient_nutrition_matching(test_recipe, ingredient_db)
    else:
        st.write("No recipes available for testing")

# IMPROVED INGREDIENT PROCESSING
ingredient_names = []
if not ingredient_db.empty and "alim_nom_fr" in ingredient_db.columns:
    # Get unique ingredient names, remove nulls, strip whitespace, and sort
    raw_names = ingredient_db["alim_nom_fr"].dropna().unique()
    ingredient_names = sorted([str(name).strip() for name in raw_names if name and str(name).strip()])
    
    # Remove any empty strings or invalid entries
    ingredient_names = [name for name in ingredient_names if len(name) > 0]

# DEBUG INFO (you can remove this after testing)
if st.checkbox("🔍 Debug Ingredient Database"):
    st.write("### Ingredient Database Debug")
    st.write(f"Database shape: {ingredient_db.shape}")
    st.write(f"Total ingredients found: {len(ingredient_names)}")
    if ingredient_names:
        st.write("First 10 ingredients:")
        for i, ing in enumerate(ingredient_names[:10]):
            st.write(f"{i+1}. '{ing}' (length: {len(ing)})")


editing = "edit_recipe" in st.session_state

if editing:
    st.title("Edit Recipe")
    recipe = st.session_state.edit_recipe
    
    # Initialize ingredients and instructions with the recipe's data
    # Only initialize if we're first loading the edit page
    if "edit_just_loaded" not in st.session_state:
        st.session_state.ingredients = recipe.ingredients.copy() if recipe.ingredients else []
        st.session_state.instructions = recipe.instructions.copy() if recipe.instructions else []
        st.session_state.edit_just_loaded = True
else:
    st.title("Add New Recipe")
    recipe = None
    
    # Initialize empty lists for new recipes
    if "ingredients" not in st.session_state:
        st.session_state.ingredients = []
    
    if "instructions" not in st.session_state:
        st.session_state.instructions = []
    
    # Clear the edit flag if it exists
    if "edit_just_loaded" in st.session_state:
        del st.session_state.edit_just_loaded


# Main recipe form
st.subheader("1. Recipe Details")
with st.form("recipe_form"):
    # Basic info
    name = st.text_input("Recipe Name", recipe.name if editing else "")
    description = st.text_area("Description", recipe.description if editing else "")

    col1, col2, col3 = st.columns(3)
    with col1:
        prep_time = st.number_input("Preparation Time (minutes)", min_value=0, value=recipe.prep_time if editing else 0)
    with col2:
        cook_time = st.number_input("Cooking Time (minutes)", min_value=0, value=recipe.cook_time if editing else 0)
    with col3:
        servings = st.number_input("Servings", min_value=1, value=recipe.servings if editing else 1)

    cuisine_type = st.text_input("Cuisine Type", recipe.cuisine_type if editing else "")
    tags = st.text_input("Tags (comma separated)", ", ".join(recipe.tags) if editing else "")
    utensils = st.text_input(
        "Ustensils (comma separated)",
        ", ".join(recipe.utensils) if editing and hasattr(recipe, "utensils") else ""
    )
    # Image upload
    st.subheader("Recipe Image")
    uploaded_image = st.file_uploader("Upload recipe image", type=["jpg", "jpeg", "png"])

    # Submit button
    submit = st.form_submit_button("Save Recipe")


st.divider()


# Ingredients section
st.subheader("2. Ingredients")

# Display current ingredients
if st.session_state.ingredients:
    st.write("Current ingredients:")
    for i, ing in enumerate(st.session_state.ingredients):
        cols = st.columns([3, 1, 1, 2, 1])
        cols[0].text(ing.name)
        cols[1].text(ing.formatted_quantity())
        cols[2].text(ing.unit)
        cols[3].text(ing.notes)
        if cols[4].button("❌", key=f"del_ing_{i}"):
            st.session_state.ingredients.pop(i)
            st.rerun()
else:
    st.info("No ingredients added yet.")

# Add new ingredient using a form
st.write("Add New Ingredient:")

# IMPROVED INGREDIENT SELECTION WITH SEARCH
with st.form(key="ingredient_form"):
    ing_cols = st.columns([3, 1, 1, 2])
    
    # Method 1: Selectbox with search (improved)
    ing_name_select = ing_cols[0].selectbox(
        "Select Ingredient",
        options=[""] + ingredient_names,  # Add empty option at the beginning
        index=0,  # Start with empty selection
        help="Start typing to search for ingredients",
        key="form_ing_name_select"
    )
    
    # Method 2: Text input for manual entry or custom ingredients
    ing_name_text = ing_cols[0].text_input(
        "Or type ingredient name",
        placeholder="Type custom ingredient...",
        key="form_ing_name_text",
        help="Use this if ingredient not found in list above"
    )
    
    # Use selectbox value if selected, otherwise use text input
    ing_name = ing_name_select if ing_name_select else ing_name_text
    
    # Show suggestions if user is typing in text field
    if ing_name_text and len(ing_name_text) > 2:
        matches = [name for name in ingredient_names if ing_name_text.lower() in name.lower()]
        if matches:
            ing_cols[0].caption(f"💡 Suggestions: {', '.join(matches[:3])}{'...' if len(matches) > 3 else ''}")
    
    ing_qty = ing_cols[1].number_input("Qty", min_value=0.0, step=0.1, format="%.1f", key="form_ing_qty")
    ing_unit = ing_cols[2].text_input("Unit", key="form_ing_unit")
    ing_notes = ing_cols[3].text_input("Notes", key="form_ing_notes")
    
    # Submit button inside form
    submitted = st.form_submit_button("Add Ingredient")
    
    if submitted and ing_name and ing_name.strip():
        # Create a new ingredient
        new_ing = Ingredient(
            name=ing_name.strip(),
            quantity=ing_qty,
            unit=ing_unit,
            notes=ing_notes
        )
        
        # Add to session state ingredients list
        if "ingredients" not in st.session_state:
            st.session_state.ingredients = []
        st.session_state.ingredients.append(new_ing)
        
        # Set success flag (will be displayed on next run)
        st.session_state.add_success = True
        st.rerun()

# Display success message if it exists
if "add_success" in st.session_state:
    st.success("Ingredient added successfully!")
    del st.session_state.add_success

# Clear All button outside the form
if st.button("Clear All Ingredients"):
    st.session_state.ingredients = []
    st.rerun()


# Gardez seulement une section pour ajouter des instructions
st.divider()

# Instructions section
st.subheader("3. Instructions")

# Display current instructions
if st.session_state.instructions:
    st.write("Current instructions:")
    for i, instruction in enumerate(st.session_state.instructions):
        cols = st.columns([10, 1])
        cols[0].text(f"{i+1}. {instruction}")
        # Add a delete button per instruction
        if cols[1].button("❌", key=f"del_instr_{i}"):
            st.session_state.instructions.pop(i)
            st.rerun()
else:
    st.info("No instructions added yet.")

# Add new instruction using a form
st.write("Add New Instruction:")

# Use a form for adding instructions
with st.form(key="instruction_form"):
    new_instruction = st.text_area("Instruction step", key="form_new_instruction")

    # Submit button inside form
    submitted = st.form_submit_button("Add Instruction")

    if submitted and new_instruction:
        # Add to session state instructions list
        if "instructions" not in st.session_state:
            st.session_state.instructions = []
        st.session_state.instructions.append(new_instruction)

        # Set success flag (will be displayed on next run)
        st.session_state.add_instruction_success = True

        st.rerun()

# Display success message if it exists
if "add_instruction_success" in st.session_state:
    st.success("Instruction added successfully!")
    del st.session_state.add_instruction_success

# Clear All button outside the form
if st.button("Clear All Instructions"):
    st.session_state.instructions = []
    st.rerun()

# Process form submission
if submit and name:  # Basic validation
    # Upload image if provided
    image_file_id = ""
    if uploaded_image:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_image.type.split('/')[1]}") as tmp_file:
            tmp_file.write(uploaded_image.read())
            tmp_file_path = tmp_file.name

        try:
            gfile = drive.CreateFile({
                'title': f"recipe_img_{name.replace(' ', '_')}",
                'parents': [{'id': folder_id}]
            })
            gfile.SetContentFile(tmp_file_path)
            gfile.Upload()
            image_file_id = gfile['id']

            # Clean up
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
        except Exception as e:
            st.error(f"Failed to upload image: {e}")
    elif editing and recipe.image_file_id:
        # Keep existing image
        image_file_id = recipe.image_file_id

    utensils_list = [u.strip() for u in utensils.split(",") if u.strip()]

    # Create recipe object
    new_recipe = Recipe(
        name=name,
        description=description,
        prep_time=int(prep_time),
        cook_time=int(cook_time),
        servings=int(servings),
        cuisine_type=cuisine_type,
        tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
        utensils=utensils_list,
        ingredients=st.session_state.ingredients.copy(),
        instructions=st.session_state.instructions.copy(),
        image_file_id=image_file_id,
        **({} if not editing else {"recipe_id": recipe.recipe_id})
    )

    # Save recipe
    if editing:
        # Replace existing recipe by ID
        for i, r in enumerate(st.session_state.recipes):
            if r.recipe_id == recipe.recipe_id:  # Find by ID instead of name
                st.session_state.recipes[i] = new_recipe
                break
    else:
        # Add new recipe
        st.session_state.recipes.append(new_recipe)

   # IMPROVED SAVE PROCESS
    with st.spinner("Saving recipe..."):
        success = save_recipes(drive, folder_id, st.session_state.recipes)
    
    if success:
        st.success(f"Recipe {'updated' if editing else 'added'} successfully!")
        st.session_state.need_save = False
        
        # Clear cache and reload to ensure consistency
        clear_recipes_cache()
        st.session_state.recipes = cached_load_recipes(drive, folder_id)
        
        # Clean up form state
        if editing:
            del st.session_state.edit_recipe
        st.session_state.ingredients = []
        st.session_state.instructions = []
        
        # Small delay then rerun to show updated state
        import time
        time.sleep(1)
        st.rerun()
    else:
        st.error(f"Failed to {'update' if editing else 'add'} recipe. Please try again.")
