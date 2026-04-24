# Food App

A modern recipe management and meal planning application with shopping list generation.

## 🎯 Project Goals

* Recipe database with ingredient tracking
* Normalize quantities per serving
* Weekly meal planning (manual or random selection)
* Automatic shopping list generation from selected recipes
* Mobile-friendly access (PWA)
* Nutrition tracking (macros and micros)

## 🏗️ Architecture

**Backend**: FastAPI + PostgreSQL (Neon) + Render  
**Frontend**: (To be built - PWA)  
**Legacy**: None (Streamlit app removed)

## 📁 Project Structure

```
Food_app/
├── app/                    # FastAPI backend
│   ├── main.py            # API endpoints
│   └── db/                # Database models & session
├── alembic/               # Database migrations
└── scripts/               # Utility scripts
```

## 🚀 Quick Start

### Local Development

1. **Set up environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements_backend.txt
   ```

2. **Configure database**:
   ```bash
   cp .env.example .env
   # Edit .env and add your Neon DATABASE_URL
   ```

3. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

4. **Start server** (choose one):
   ```bash
   # Option 1: Quick script
   ./start_local.sh
   
   # Option 2: Manual
   uvicorn app.main:app --reload
   ```

5. **Access**:
   - API: http://127.0.0.1:8000
   - Recipes: http://127.0.0.1:8000/api/recipes
   - Health: http://127.0.0.1:8000/health
   - Docs: http://127.0.0.1:8000/docs (interactive API testing)

## 📚 Documentation

- **Next Steps**: See `NEXT_STEPS_PLAN.md` for detailed roadmap
- **Deployment**: See `DEPLOYMENT.md` for Render deployment guide

## 🔄 Migration Status

**Phase 1**: ✅ Infrastructure setup complete  
**Phase 2**: ✅ Deployment & verification complete  
**Phase 3**: ✅ API endpoints implemented  
**Phase 4**: ✅ Data migration complete (102 recipes migrated)  
**Phase 5**: 🚧 Frontend PWA (In Progress)

## 📝 Notes

- Legacy Streamlit app has been removed.
- Database models ready, migrations need to be run
- Backend ready for deployment to Render
