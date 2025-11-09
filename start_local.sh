#!/bin/bash
# Quick script to start the FastAPI server locally

cd "$(dirname "$0")"
source .venv/bin/activate

echo "🚀 Starting FastAPI server locally..."
echo "📡 API will be available at: http://127.0.0.1:8000"
echo "📚 API docs: http://127.0.0.1:8000/docs"
echo "🍽️  Recipes: http://127.0.0.1:8000/api/recipes"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

