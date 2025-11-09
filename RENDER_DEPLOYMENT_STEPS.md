# Step-by-Step Render Deployment Guide

## Prerequisites Check ✅
- [x] GitHub repository exists: `https://github.com/TomSavard/Food_app.git`
- [x] Branch: `feat/new_infra`
- [x] Code ready for deployment

## Step 1: Commit and Push Code to GitHub

```bash
# Add all new files
git add .

# Commit changes
git commit -m "Add FastAPI backend infrastructure with Neon database"

# Push to GitHub
git push origin feat/new_infra
```

## Step 2: Deploy to Render

### Option A: Using render.yaml (Recommended - Automatic)

1. Go to https://dashboard.render.com
2. Sign up/Login (use GitHub to connect)
3. Click **"New"** → **"Blueprint"**
4. Connect your GitHub repository: `TomSavard/Food_app`
5. Render will detect `render.yaml` automatically
6. **IMPORTANT**: Before deploying, add environment variable:
   - Go to your service → **"Environment"** tab
   - Add: `DATABASE_URL` = your Neon connection string
   - Format: `postgresql+psycopg://neondb_owner:password@host.neon.tech/dbname?sslmode=require&channel_binding=require`
7. Click **"Apply"** to deploy

### Option B: Manual Setup

1. Go to https://dashboard.render.com
2. Click **"New"** → **"Web Service"**
3. Connect GitHub repository: `TomSavard/Food_app`
4. Configure:
   - **Name**: `food-app-backend`
   - **Region**: Choose nearest (e.g., Frankfurt, Oregon)
   - **Branch**: `feat/new_infra` (or `main` if you merge)
   - **Root Directory**: (leave empty)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements_backend.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Environment Variables**:
   - Click **"Add Environment Variable"**
   - Key: `DATABASE_URL`
   - Value: Your Neon connection string (from `.env` file)
6. Click **"Create Web Service"**

## Step 3: Wait for Deployment

- First deployment takes 3-5 minutes
- Watch the logs in Render dashboard
- Look for: "Your service is live at https://your-app.onrender.com"

## Step 4: Run Migrations on Render

After deployment succeeds:

1. Go to Render dashboard → Your service
2. Click **"Shell"** tab (or **"Logs"** → **"Shell"**)
3. Run:
   ```bash
   alembic upgrade head
   ```
4. You should see: "Running upgrade -> 94784dba1688, init"

## Step 5: Verify Deployment

1. Visit your Render URL: `https://your-app-name.onrender.com`
2. Test endpoints:
   - `https://your-app-name.onrender.com/` → Should show `{"message": "Backend is running", "status": "ok"}`
   - `https://your-app-name.onrender.com/health` → Should show `{"status": "ok", "database": "connected"}`
   - `https://your-app-name.onrender.com/docs` → Should show API documentation

## Troubleshooting

### Build fails
- Check `requirements_backend.txt` exists
- Verify Python version in Render (should be 3.x)
- Check build logs for errors

### Health check shows "disconnected"
- Verify `DATABASE_URL` is set correctly in Render environment variables
- Check Neon project is active
- Ensure connection string includes `sslmode=require`

### Migration fails
- Make sure you're in the correct directory in Shell
- Verify `DATABASE_URL` is accessible from Render
- Check Alembic can find migration files

### Service won't start
- Check start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Verify `app.main:app` path is correct
- Check logs for Python errors

