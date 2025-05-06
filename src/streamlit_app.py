import streamlit as st
import tempfile
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import pandas as pd


# Path to your service account key file
json_keyfile = "streamlit_drive_connector.json"
folder_id = '1IB8TbwUYMqu3JElebpg0ctpPcQ4IfSBe'



def authenticate_drive(json_keyfile):
    gauth = GoogleAuth()
    # Configure GoogleAuth to use the service account JSON file
    gauth.settings['client_config_backend'] = 'service'
    gauth.settings['service_config'] = {
        "client_json_file_path": json_keyfile,
        "client_user_email": "food-app@my-food-459018.iam.gserviceaccount.com"  # Replace with your service account email
    }
    gauth.ServiceAuth()  # Authenticate using the service account
    drive = GoogleDrive(gauth)
    return drive




# Streamlit App
st.title("Google Drive Connector")

try:
    # Authenticate and connect to Google Drive
    drive = authenticate_drive(json_keyfile)
    st.success("Connected to Google Drive successfully!")

    # --- File Upload Section ---
    uploaded_file = st.file_uploader("Choose a file to upload to your shared Drive folder", type=None)
    if uploaded_file is not None:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name

        # Upload to the shared folder (not root)
        gfile = drive.CreateFile({
            'title': uploaded_file.name,
            'parents': [{'id': folder_id}]
        })
        gfile.SetContentFile(tmp_file_path)
        gfile.Upload()
        st.success(f"'{uploaded_file.name}' uploaded to your shared Drive folder!")

    # --- List Files in the Shared Folder ---
    st.write("### Files in your shared Drive folder:")
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()
    for file in file_list:
        st.write(f"📄 {file['title']} (ID: {file['id']})")
        if file['title'].endswith('.xlsx'):
            if st.button(f"View {file['title']}"):
                # Download the file to a temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
                    file.GetContentFile(tmp_file.name)
                    tmp_file_path = tmp_file.name

                # Read the Excel file using pandas
                df = pd.read_excel(tmp_file_path, engine='openpyxl')
                st.write(f"### Contents of {file['title']}:")
                st.dataframe(df)  # Display the Excel file as a table

except Exception as e:
    st.error(f"Failed to connect to Google Drive: {e}")

