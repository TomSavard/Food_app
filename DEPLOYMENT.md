# Deployment Guide: FastAPI Backend on Render + Neon

This guide walks you through deploying the Food App backend to Render with a Neon PostgreSQL database.

## Prerequisites

- GitHub account
- Neon.tech account (free tier)
- Render.com account (free tier)

## Step 0: Create Neon Database

### Quick Setup (Recommended)

1. Sign up at [neon.tech](https://neon.tech)
2. Create a new project
3. Create a database (accept defaults)
4. Go to **Connection Details** in the Neon dashboard
5. Copy the connection string (it will look like `postgresql://user:pass@host/dbname`)
6. **Convert it for SQLAlchemy**:
   - Add `+psycopg` after `postgresql`: `postgresql+psycopg://...`
   - Add `?sslmode=require` at the end: `postgresql+psycopg://...?sslmode=require`
7. Your final DATABASE_URL should be: `postgresql+psycopg://USER:PASSWORD@HOST/DBNAME?sslmode=require`

**Note**: You don't need the Neon CLI (`npx neonctl`) for Python apps. Just get the connection string from the Neon dashboard.

### Alternative: Using Neon CLI (Optional)

If you prefer using the CLI (requires Node.js):
```bash
npx neonctl@latest init
npx neonctl@latest connection-string --format sqlalchemy
```
Then add `?sslmode=require` to the connection string.

## Step 1: Local Setup

1. Clone this repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements_backend.txt
   ```

4. Create `.env` file (copy from `.env.example`):
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` and add your Neon DATABASE_URL

6. Test locally:
   ```bash
   uvicorn app.main:app --reload
   ```

7. Visit `http://127.0.0.1:8000/health` - should return `{"status": "ok", "database": "connected"}`

## Step 2: Initialize Database Schema

1. Create initial migration:
   ```bash
   alembic revision --autogenerate -m "init"
   ```

2. Review the migration file in `alembic/versions/` - ensure it looks correct

3. Apply migration:
   ```bash
   alembic upgrade head
   ```

4. Verify tables were created in Neon dashboard (SQL Editor)

## Step 3: Deploy to Render

### Option A: Using render.yaml (Recommended)

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New** → **Blueprint**
4. Connect your GitHub repository
5. Render will detect `render.yaml` and configure automatically
6. Add environment variable `DATABASE_URL` in Render dashboard (Settings → Environment)
7. Deploy!

### Option B: Manual Setup

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click **New** → **Web Service**
4. Connect your GitHub repository
5. Configure:
   - **Name**: `food-app-backend` (or your choice)
   - **Region**: Choose nearest to you
   - **Branch**: `main` (or your default branch)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements_backend.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
6. Add environment variable:
   - **Key**: `DATABASE_URL`
   - **Value**: Your Neon connection string (with `sslmode=require`)
7. Click **Create Web Service**

## Step 4: Run Migrations on Render

After deployment, you need to run migrations on Render:

1. Go to Render dashboard → Your service → **Shell**
2. Run:
   ```bash
   alembic upgrade head
   ```

Alternatively, you can run migrations locally pointing to the production database (not recommended for production).

## Step 5: Verify Deployment

1. Visit your Render URL: `https://your-app-name.onrender.com`
2. Check health endpoint: `https://your-app-name.onrender.com/health`
3. Should return: `{"status": "ok", "database": "connected"}`

## Step 6: Test from Phone

Open your Render URL on your phone:
- `https://your-app-name.onrender.com`
- `https://your-app-name.onrender.com/health`

You should see JSON responses confirming the backend is accessible.

## Troubleshooting

### Health check fails
- Verify `DATABASE_URL` is set correctly in Render dashboard
- Check Render logs for connection errors
- Ensure Neon project allows connections (check Neon dashboard)

### Migration errors
- Ensure `DATABASE_URL` includes `sslmode=require`
- Check Alembic version table exists: `SELECT * FROM alembic_version;`
- Review migration files in `alembic/versions/`

### Slow first request
- Free tier on Render spins down after inactivity
- First request after idle period can take 30-60 seconds
- This is normal for free tier

## Next Steps

After infrastructure is set up:
1. Add API endpoints for recipes (GET, POST, PUT, DELETE)
2. Add endpoints for weekly menu
3. Add endpoints for shopping list
4. Build frontend (PWA) that consumes these APIs
5. Add authentication if needed

## Notes

- Free tier on Render may spin down after 15 minutes of inactivity
- Free tier on Neon has some limitations (check Neon docs)
- For production, consider upgrading to paid tiers for better performance
- Keep `.env` file local only - never commit secrets to Git

