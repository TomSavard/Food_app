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
├── backend/              # FastAPI Python code
│   ├── main.py
│   ├── api/              # Route handlers (recipes, ingredients, shopping_list, chat)
│   ├── db/               # SQLAlchemy models + session
│   ├── schemas.py
│   └── utils/
├── app/                  # Next.js App Router (frontend pages)
├── components/           # React components (incl. shadcn/ui under components/ui/)
├── lib/                  # API client + types
├── public/               # PWA manifest, icons, service worker
├── alembic/              # DB migrations
├── tests/                # pytest suite
├── package.json          # Next.js / React deps
├── tsconfig.json
├── tailwind.config.ts
├── next.config.js
├── vercel.json           # routes /api/* to the Python function; Next.js handles the rest
├── requirements.txt      # runtime deps (installed into the Vercel function)
└── requirements-dev.txt  # local dev + tooling
```

## Local development

```bash
# First-time setup — Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # then paste your Neon DATABASE_URL

# First-time setup — Node
npm install

# Pull Vercel env vars into .env.local (so vercel dev picks up DATABASE_URL)
vercel env pull .env.local

# Run locally — Next.js + the Python function in one process
vercel dev
# → http://localhost:3000
```

## Tests

Tests run against a dedicated Neon test branch (cheap copy-on-write of `main`). Each test wraps work in a transaction that's rolled back on teardown, so no data leaks between runs.

**One-time setup:**
1. Neon Console → your project → **Branches** → "Create branch" → from `main` → name it `test`. Copy the **pooled** connection string.
2. `cp .env.test.example .env.test` and paste it (in `postgresql+psycopg://` form).

**Run:**
```bash
pytest -v
```

CI runs the same tests on every push to `main` and every PR (see [.github/workflows/test.yml](.github/workflows/test.yml)). Set `TEST_DATABASE_URL` as a GitHub Actions secret.

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
