# Food App

A personal recipe management and meal planning app with shopping list generation and nutrition tracking.

Product direction: [NORTH_STAR.md](NORTH_STAR.md). Stack rationale: [INFRASTRUCTURE.md](INFRASTRUCTURE.md).

## Stack

- **Frontend + API hosting:** Vercel (serverless)
- **Backend:** FastAPI (runs as a single Vercel Python function via [api/index.py](api/index.py))
- **Database:** Neon Postgres (pooled endpoint)
- **Frontend:** vanilla HTML/JS PWA in [frontend/](frontend/)

Live: https://food-app-bice-alpha.vercel.app

## Project layout

```
Food_app/
├── api/index.py          # Vercel entry point (re-exports FastAPI app)
├── app/                  # FastAPI backend
│   ├── main.py           # App setup, routers, /health
│   ├── api/              # Route handlers (recipes, ingredients, shopping_list)
│   ├── db/               # SQLAlchemy models + session
│   ├── schemas/          # Pydantic schemas
│   └── utils/            # Nutrition calc, etc.
├── alembic/              # DB migrations
├── frontend/             # Static HTML/JS/CSS served by Vercel CDN
├── vercel.json           # Vercel routing + Python runtime config
├── requirements.txt      # Runtime deps (installed into the Vercel function)
└── requirements-dev.txt  # Local dev + tooling (uvicorn, alembic, ruff)
```

## Local development

```bash
# First-time setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then paste your Neon DATABASE_URL

# Pull Vercel env vars into .env.local (so vercel dev picks up DATABASE_URL)
vercel env pull .env.local

# Run locally (mirrors prod: static frontend + /api function)
vercel dev
# → http://localhost:3000
```

## Database migrations

Alembic runs locally against Neon — it is **not** wired into the Vercel deploy.

```bash
# Apply pending migrations
alembic upgrade head

# Create a new migration after editing app/db/models.py
alembic revision --autogenerate -m "describe the change"
```

## Deployment

Pushes to `main` auto-deploy on Vercel (GitHub integration). Manual:

```bash
vercel --prod
```

Env var to set in Vercel project settings (Production + Development):
- `DATABASE_URL` — Neon **pooled** connection string (hostname contains `-pooler`).
