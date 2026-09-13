# Food App

A personal recipe management and meal planning app. Plan weekly meals, auto-generate shopping lists with quantities fused by ingredient, grouped by supermarket aisle, and track real nutrition (kcal, macros, micros) using the CIQUAL database — with LLM fallback for unmatched ingredients.

Built as a Next.js PWA with a FastAPI backend, hosted on Vercel with a Neon Postgres database.

See [NORTH_STAR.md](NORTH_STAR.md) for product direction and [INFRASTRUCTURE.md](INFRASTRUCTURE.md) for stack rationale.

---

## Quick start

Install dependencies:

```bash
# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env  # then paste your Neon DATABASE_URL

# Node
npm install
```

Choose how to run:

**Single process (recommended):**
```bash
vercel dev
# → http://localhost:3000
```

**Separate servers (uvicorn + Next.js):**
```bash
# Terminal 1 — Python API
uvicorn backend.main:app --port 8000

# Terminal 2 — Next.js frontend
npm run dev
# → http://localhost:3000 (proxies /api/* to the Python server)
```

## Project structure

```
Food_app/
├── api/index.py          # Vercel entry point (re-exports FastAPI)
├── backend/              # FastAPI API + business logic
│   ├── api/              # Route handlers (recipes, ingredients, chat, meal plan, shopping list)
│   ├── db/               # SQLAlchemy models + session
│   ├── services/         # Business logic (CIQUAL matching, seasonality, categorize)
│   ├── schemas.py        # Pydantic types
│   └── main.py
├── app/                  # Next.js pages (reference, meal-plan, shopping, ingredients)
├── components/           # React components (shadcn/ui under components/ui/)
├── lib/                  # API client + types + utilities
├── public/               # PWA manifest, icons, service worker
    ├── config/               # postcss.config.js
├── tests/                # pytest suite
└── scripts/              # utility scripts
```

## Tests

Tests run against a dedicated Neon test branch. Each test wraps work in a transaction that rolls back, so no data leaks between runs.

**One-time setup:** create a `test` branch in Neon from `main`, copy its pooled connection string into `.env.test`.

```bash
pytest -v
```

## Deployment

Pushes to `main` auto-deploy on Vercel. Manual:

```bash
vercel --prod
```
