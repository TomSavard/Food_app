"""
Manual download helper - creates a simple script to download from Google Drive
without Streamlit dependencies
"""

import json
from pathlib import Path

def create_download_instructions():
    """Create instructions for manual download"""
    instructions = """
# How to Download food_recipes_database.json from Google Drive

## Method 1: Via Google Drive Web Interface (Easiest)

1. Go to: https://drive.google.com
2. Navigate to your Food App folder
3. Find the file: `food_recipes_database.json`
4. Right-click → Download
5. Move the downloaded file to:
   /Users/tom.savard/Desktop/Perso/Food_app/food_recipes_database.json

## Method 2: Via Google Drive API (If you have credentials)

If you have Google Drive API credentials, you can use:
```bash
python scripts/download_from_drive.py
```

## Verify Download

After downloading, verify the file:
```bash
cd /Users/tom.savard/Desktop/Perso/Food_app
python3 -c "
import json
with open('food_recipes_database.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
    print(f'✅ Found {len(data)} recipes')
    if data:
        print(f'First recipe: {data[0].get(\"name\", \"N/A\")}')"
```

## Then Run Migration

```bash
python scripts/migrate_recipes.py
```
"""
    
    output_file = Path(__file__).parent.parent / "DOWNLOAD_INSTRUCTIONS.md"
    with open(output_file, 'w') as f:
        f.write(instructions)
    
    print("✅ Created DOWNLOAD_INSTRUCTIONS.md")
    print(instructions)

if __name__ == "__main__":
    create_download_instructions()

