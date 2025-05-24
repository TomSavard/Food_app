import streamlit as st
import pandas as pd
import tempfile
import os
import json
from io import BytesIO
from PIL import Image
from src.utils import ensure_drive_connection


# ---------- FILES MANAGER PAGE ----------

ensure_drive_connection()
drive = st.session_state.drive
folder_id = st.session_state.folder_id

if drive is None or folder_id is None:
    st.error("Google Drive connection not available. Please reload the app.")
    st.stop()

st.title("Files Manager")

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



