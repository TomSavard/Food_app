"""
Helper script to download food_recipes_database.json from Google Drive
"""

import sys
import json
import tempfile
from pathlib import Path
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# Constants from old system
RECIPES_FILE_NAME = "food_recipes_database.json"

def download_recipes_json():
    """Download recipes JSON file from Google Drive"""
    print("🔐 Authenticating with Google Drive...")
    
    try:
        # Try to use Streamlit secrets (if available)
        import streamlit as st
        credentials = st.secrets["GOOGLE_DRIVE_CREDENTIALS"]
        folder_id = st.secrets["GOOGLE_DRIVE_FOLDER_ID"]
        
        gauth = GoogleAuth()
        gauth.settings['client_config_backend'] = 'service'
        gauth.settings['service_config'] = {
            'client_json_dict': credentials,
            'client_user_email': credentials.get('client_email')
        }
        gauth.ServiceAuth()
        drive = GoogleDrive(gauth)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n📝 Alternative: Manual Download")
        print("   1. Go to https://drive.google.com")
        print("   2. Navigate to your Food App folder")
        print("   3. Download 'food_recipes_database.json'")
        print("   4. Place it in the project root")
        return False
    
    print("📁 Searching for recipes file...")
    
    # Find the recipes file
    file_list = drive.ListFile({
        'q': f"'{folder_id}' in parents and title='{RECIPES_FILE_NAME}' and trashed=false"
    }).GetList()
    
    if not file_list:
        print(f"❌ File '{RECIPES_FILE_NAME}' not found in Google Drive")
        return False
    
    recipes_file = file_list[0]
    print(f"✅ Found file: {recipes_file['title']}")
    
    # Download to project root
    output_path = Path(__file__).parent.parent / RECIPES_FILE_NAME
    
    print(f"📥 Downloading to: {output_path}")
    recipes_file.GetContentFile(str(output_path))
    
    # Verify download
    if output_path.exists():
        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Download successful! Found {len(data)} recipes")
        return True
    else:
        print("❌ Download failed")
        return False


if __name__ == "__main__":
    success = download_recipes_json()
    if success:
        print("\n✅ Ready to migrate! Run: python scripts/migrate_recipes.py")
    else:
        print("\n⚠️  Please download the file manually and place it in the project root")

