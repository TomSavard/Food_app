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
**Legacy**: Streamlit app (being migrated)

## 📁 Project Structure

```
Food_app/
├── app/                    # FastAPI backend
│   ├── main.py            # API endpoints
│   └── db/                # Database models & session
├── alembic/               # Database migrations
├── pages/                 # Legacy Streamlit pages
└── src/                   # Legacy Streamlit code
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

4. **Start server**:
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Access**:
   - API: http://127.0.0.1:8000
   - Health: http://127.0.0.1:8000/health
   - Docs: http://127.0.0.1:8000/docs

## 📚 Documentation

- **Next Steps**: See `NEXT_STEPS_PLAN.md` for detailed roadmap
- **Deployment**: See `DEPLOYMENT.md` for Render deployment guide

## 🔄 Migration Status

**Phase 1**: ✅ Infrastructure setup complete  
**Phase 2**: ⏳ Deployment & verification (in progress)  
**Phase 3**: ⏳ API endpoints (pending)  
**Phase 4**: ⏳ Frontend PWA (pending)

## 📝 Notes

- Legacy Streamlit app still exists in `pages/` and `src/` (will be replaced)
- Database models ready, migrations need to be run
- Backend ready for deployment to Render
