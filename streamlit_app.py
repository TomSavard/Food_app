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

# Import custom modules
from src.recipe_manager import (
    load_recipes, save_recipes, recipes_to_dataframe,
    filter_recipes, Recipe, Ingredient
)

# Page configuration
st.set_page_config(
    page_title="Food App",
    page_icon="🍲",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load credentials from Streamlit Secrets
@st.cache_resource
def get_drive():
    try:
        credentials = st.secrets["GOOGLE_DRIVE_CREDENTIALS"]
        
        # Authenticate with Google Drive
        gauth = GoogleAuth()
        gauth.settings['client_config_backend'] = 'service'
        gauth.settings['service_config'] = {
            'client_json_dict': credentials,
            'client_user_email': credentials.get('client_email')
        }
        gauth.ServiceAuth()
        return GoogleDrive(gauth)
    
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        return None

# Get folder ID from secrets
try:
    folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
except KeyError:
    st.error("Missing GOOGLE_DRIVE_FOLDER_ID in Streamlit Secrets")
    st.stop()

# Connect to Google Drive
drive = get_drive()
if not drive:
    st.error("Failed to authenticate with Google Drive.")
    st.stop()

# Sidebar Navigation
st.sidebar.title("Food App 🍲")
page = st.sidebar.radio("Navigate", ["Recipe Browser", "Add Recipe", "Files Manager"])

# Load recipes data
if "recipes" not in st.session_state:
    with st.spinner("Loading recipes..."):
        st.session_state.recipes = load_recipes(drive, folder_id)
        st.session_state.need_save = False

# Function to save changes when needed
def save_changes():
    if st.session_state.need_save:
        with st.spinner("Saving changes..."):
            if save_recipes(drive, folder_id, st.session_state.recipes):
                st.success("Changes saved successfully!")
                st.session_state.need_save = False
            else:
                st.error("Failed to save changes")

# ---------- RECIPE BROWSER PAGE ----------
if page == "Recipe Browser":
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
                    st.write(f"- {ing.quantity} {ing.unit} {ing.name} {ing.notes}")
                
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
            
            if st.button("Close Recipe"):
                st.session_state.view_recipe = False
                st.experimental_rerun()
            
            if st.button("Edit Recipe"):
                st.session_state.edit_recipe = recipe
                st.session_state.view_recipe = False
                st.session_state.page = "Add Recipe"
                st.experimental_rerun()

# ---------- ADD RECIPE PAGE ----------
elif page == "Add Recipe":
    # Check if we're editing an existing recipe
    editing = "edit_recipe" in st.session_state
    
    if editing:
        st.title("Edit Recipe")
        recipe = st.session_state.edit_recipe
    else:
        st.title("Add New Recipe")
        recipe = None
    
    # Recipe form
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
        
        # Ingredients
        st.subheader("Ingredients")
        
        if "ingredients" not in st.session_state or not editing:
            st.session_state.ingredients = recipe.ingredients if editing else []
        
        # Display current ingredients
        for i, ing in enumerate(st.session_state.ingredients):
            cols = st.columns([3, 1, 1, 2, 1])
            cols[0].text(ing.name)
            cols[1].text(str(ing.quantity))
            cols[2].text(ing.unit)
            cols[3].text(ing.notes)
            
        # Add new ingredient inputs
        st.write("Add New Ingredient:")
        ing_cols = st.columns([3, 1, 1, 2])
        ing_name = ing_cols[0].text_input("Name", key="ing_name")
        ing_qty = ing_cols[1].number_input("Qty", min_value=0.0, step=0.1, key="ing_qty")
        ing_unit = ing_cols[2].text_input("Unit", key="ing_unit")
        ing_notes = ing_cols[3].text_input("Notes", key="ing_notes")
        
        # Buttons for ingredients
        ing_btn_cols = st.columns([1, 1])
        add_ingredient = ing_btn_cols[0].form_submit_button("Add Ingredient")
        clear_ingredients = ing_btn_cols[1].form_submit_button("Clear All Ingredients")
        
        # Instructions
        st.subheader("Instructions")
        
        if "instructions" not in st.session_state or not editing:
            st.session_state.instructions = recipe.instructions if editing else []
        
        # Display current instructions
        for i, instruction in enumerate(st.session_state.instructions):
            st.text(f"{i+1}. {instruction}")
        
        # Add new instruction
        new_instruction = st.text_area("New Instruction Step", key="new_instruction")
        
        # Buttons for instructions
        inst_btn_cols = st.columns([1, 1])
        add_instruction = inst_btn_cols[0].form_submit_button("Add Instruction")
        clear_instructions = inst_btn_cols[1].form_submit_button("Clear All Instructions")
        
        # Image upload
        st.subheader("Recipe Image")
        uploaded_image = st.file_uploader("Upload recipe image", type=["jpg", "jpeg", "png"])
        
        # Submit button
        submit = st.form_submit_button("Save Recipe")
    
    # Process ingredient add/clear
    if add_ingredient and ing_name:
        st.session_state.ingredients.append(
            Ingredient(name=ing_name, quantity=ing_qty, unit=ing_unit, notes=ing_notes)
        )
        st.experimental_rerun()
    
    if clear_ingredients:
        st.session_state.ingredients = []
        st.experimental_rerun()
    
    # Process instruction add/clear
    if add_instruction and new_instruction:
        st.session_state.instructions.append(new_instruction)
        st.experimental_rerun()
    
    if clear_instructions:
        st.session_state.instructions = []
        st.experimental_rerun()
    
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
        
        # Create recipe object
        new_recipe = Recipe(
            name=name,
            description=description,
            prep_time=int(prep_time),
            cook_time=int(cook_time),
            servings=int(servings),
            cuisine_type=cuisine_type,
            tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
            ingredients=st.session_state.ingredients,
            instructions=st.session_state.instructions,
            image_file_id=image_file_id
        )
        
        # Save recipe
        if editing:
            # Replace existing recipe
            for i, r in enumerate(st.session_state.recipes):
                if r.name == recipe.name:  # Find by name
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
        save_changes()

# ---------- FILES MANAGER PAGE ----------
elif page == "Files Manager":
    st.title("Google Drive Files Manager")
    
    # --- File Upload Section ---
    uploaded_file = st.file_uploader("Upload file to Google Drive folder", type=None)
    if uploaded_file is not None:
        st.write(f"Uploaded file: {uploaded_file.name}")
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name

        # Upload to Drive
        try:
            with st.spinner(f"Uploading {uploaded_file.name}..."):
                gfile = drive.CreateFile({
                    'title': uploaded_file.name,
                    'parents': [{'id': folder_id}]
                })
                gfile.SetContentFile(tmp_file_path)
                gfile.Upload()
            st.success(f"'{uploaded_file.name}' uploaded successfully!")
            
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
        except Exception as e:
            st.error(f"Upload failed: {e}")
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)
    
    # --- List Files in Google Drive ---
    st.subheader("Files in Google Drive Folder")
    
    if st.button("Refresh Files List"):
        pass  # Just triggers a rerun
    
    try:
        with st.spinner("Fetching files..."):
            file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
        
        if not file_list:
            st.info("No files found in this folder.")
        else:
            # Create DataFrame for display
            file_df = pd.DataFrame([
                {"File Name": file['title'], 
                 "Type": file['mimeType'].split('/')[-1], 
                 "ID": file['id'],
                 "Modified": file.get('modifiedDate', 'Unknown')} 
                for file in file_list
            ])
            st.dataframe(file_df, use_container_width=True)
            
            # Group Excel files for easier access
            excel_files = [file for file in file_list if file['title'].endswith(('.xlsx', '.xls'))]
            if excel_files:
                st.subheader("Excel Files")
                
                selected_excel = st.selectbox(
                    "Select Excel file to view", 
                    [file['title'] for file in excel_files]
                )
                
                if selected_excel:
                    selected_file = next((file for file in excel_files if file['title'] == selected_excel), None)
                    
                    if selected_file and st.button("View Excel Content"):
                        with st.spinner("Loading Excel file..."):
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                                selected_file.GetContentFile(tmp_file.name)
                                tmp_file_path = tmp_file.name
                            
                            try:
                                df = pd.read_excel(tmp_file_path, engine='openpyxl')
                                st.write(f"### Contents of {selected_excel}:")
                                st.dataframe(df, use_container_width=True)
                            except Exception as e:
                                st.error(f"Failed to read Excel file: {e}")
                            finally:
                                # Clean up
                                if os.path.exists(tmp_file_path):
                                    os.remove(tmp_file_path)
    
    except Exception as e:
        st.error(f"Failed to fetch files: {e}")

# Save changes before exiting if needed
save_changes()

