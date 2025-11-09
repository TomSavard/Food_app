#!/bin/bash
# Quick start script for local development

echo "🚀 Starting Food App Backend..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements_backend.txt

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Copying .env.example to .env..."
    cp .env.example .env
    echo "✏️  Please edit .env and add your DATABASE_URL from Neon"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL not set in .env file"
    exit 1
fi

# Run migrations (optional - comment out if you want to run manually)
# echo "🗄️  Running database migrations..."
# alembic upgrade head

# Start server
echo "✅ Starting FastAPI server..."
echo "📍 API available at: http://127.0.0.1:8000"
echo "📍 Health check: http://127.0.0.1:8000/health"
echo "📍 API docs: http://127.0.0.1:8000/docs"
echo ""
uvicorn app.main:app --reload

