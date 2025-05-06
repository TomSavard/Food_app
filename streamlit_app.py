import streamlit as st
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import pandas as pd
import tempfile

# Load credentials from Streamlit Secrets
try:
    st.write("Loading credentials from Streamlit Secrets...")
    credentials = st.secrets["GOOGLE_DRIVE_CREDENTIALS"]
    folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
    st.write("Credentials and folder ID loaded successfully.")
except KeyError as e:
    st.error(f"Missing secret: {e}")
    st.stop()

def authenticate_drive(credentials):
    try:
        st.write("Authenticating with Google Drive...")
        
        # Ensure that credentials are a plain dictionary
        credentials_dict = dict(credentials)  # Convert the AttrDict to a regular dict
        
        # Initialize GoogleAuth and provide the dictionary directly
        gauth = GoogleAuth()
        gauth.settings['client_config_backend'] = 'service'
        gauth.settings['service_config'] = credentials_dict  # Directly pass the dictionary
        
        # Authenticate using service account
        gauth.ServiceAuth()
        drive = GoogleDrive(gauth)
        
        st.write("Authentication successful.")
        return drive
    except Exception as e:
        st.error(f"Authentication failed: {e}")
        st.stop()

# Streamlit App
st.title("Google Drive Connector")

try:
    # Authenticate and connect to Google Drive
    drive = authenticate_drive(credentials)
    st.success("Connected to Google Drive successfully!")

    # --- File Upload Section ---
    uploaded_file = st.file_uploader("Choose a file to upload to your shared Drive folder", type=None)
    if uploaded_file is not None:
        st.write(f"Uploaded file: {uploaded_file.name}")
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name
        st.write(f"Temporary file path: {tmp_file_path}")

        # Upload to the shared folder (not root)
        try:
            st.write(f"Uploading file '{uploaded_file.name}' to folder ID: {folder_id}")
            gfile = drive.CreateFile({
                'title': uploaded_file.name,
                'parents': [{'id': folder_id}]
            })
            gfile.SetContentFile(tmp_file_path)
            gfile.Upload()
            st.success(f"'{uploaded_file.name}' uploaded to your shared Drive folder!")
        except Exception as e:
            st.error(f"File upload failed: {e}")

    # --- List Files in the Shared Folder ---
    try:
        st.write("Fetching files from the shared Drive folder...")
        file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
        st.write(f"Found {len(file_list)} files in the folder.")
        for file in file_list:
            st.write(f"📄 {file['title']} (ID: {file['id']})")
            if file['title'].endswith('.xlsx'):
                if st.button(f"View {file['title']}"):
                    # Download the file to a temporary location
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                        file.GetContentFile(tmp_file.name)
                        tmp_file_path = tmp_file.name
                    st.write(f"Downloaded file to temporary path: {tmp_file_path}")

                    # Read the Excel file using pandas
                    try:
                        df = pd.read_excel(tmp_file_path, engine='openpyxl')
                        st.write(f"### Contents of {file['title']}:")
                        st.dataframe(df)  # Display the Excel file as a table
                    except Exception as e:
                        st.error(f"Failed to read Excel file: {e}")
    except Exception as e:
        st.error(f"Failed to fetch files from Google Drive: {e}")

except Exception as e:
    st.error(f"Failed to connect to Google Drive: {e}")
    st.write(e)  # Debugging: Print the full error
