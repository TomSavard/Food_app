#!/bin/bash
# Start the FastAPI backend locally

# Ensure we're in the project root
cd "$(dirname "$0")"

# Check if .venv exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements_backend.txt
else
    source .venv/bin/activate
fi

# Run the server
echo "Starting FastAPI server..."
echo "API: http://127.0.0.1:8000"
echo "Docs: http://127.0.0.1:8000/docs"
uvicorn app.main:app --reload
