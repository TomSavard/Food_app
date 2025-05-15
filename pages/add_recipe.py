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


from src.recipe_manager import save_recipes
from src.utils import save_changes
from src.models.recipe import Recipe, Ingredient


def run(drive, folder_id):
    st.title("Add / Edit Recipe")

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
                # st.rerun()
    else:
        st.info("No ingredients added yet.")

    # Add new ingredient using a form
    st.write("Add New Ingredient:")

    # Use a form for adding ingredients
    with st.form(key="ingredient_form"):
        ing_cols = st.columns([3, 1, 1, 2])
        ing_name = ing_cols[0].text_input("Name", key="form_ing_name")
        ing_qty = ing_cols[1].number_input("Qty", min_value=0.0, step=0.1, format="%.1f", key="form_ing_qty")
        ing_unit = ing_cols[2].text_input("Unit", key="form_ing_unit")
        ing_notes = ing_cols[3].text_input("Notes", key="form_ing_notes")
        
        # Submit button inside form
        submitted = st.form_submit_button("Add Ingredient")
        
        if submitted and ing_name:
            # Create a new ingredient
            new_ing = Ingredient(
                name=ing_name,
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
            # st.rerun()

    # Display success message if it exists
    if "add_success" in st.session_state:
        st.success("Ingredient added successfully!")
        del st.session_state.add_success

    # Clear All button outside the form
    if st.button("Clear All Ingredients"):
        st.session_state.ingredients = []
        # st.rerun()


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
                # st.rerun()
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

            # st.rerun()

    # Display success message if it exists
    if "add_instruction_success" in st.session_state:
        st.success("Instruction added successfully!")
        del st.session_state.add_instruction_success

    # Clear All button outside the form
    if st.button("Clear All Instructions"):
        st.session_state.instructions = []
        # st.rerun()

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
        
        # Mark for saving
        st.session_state.need_save = True
        
        # Confirmation and cleanup
        st.success(f"Recipe {'updated' if editing else 'added'} successfully!")
        if editing:
            del st.session_state.edit_recipe
        st.session_state.ingredients = []
        st.session_state.instructions = []
        
        # Save immediately
        save_changes(drive, folder_id, save_recipes)
