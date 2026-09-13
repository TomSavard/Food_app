# North Star — Food_app

> Living document. Captures the "why" and the ideal end-state for the Food_app project.

---

## Vision

A unified, intelligent, and frictionless recipe management and meal planning app that reduces mental load and eliminates wasted time. One app on your phone and computer: plan weekly meals, generate shopping lists, and track real nutrition — with LLM assistance that anticipates what you need.

**Current stack:** Next.js PWA + FastAPI backend + Neon Postgres, hosted on Vercel.

See [README.md](README.md) for setup, [INFRASTRUCTURE.md](INFRASTRUCTURE.md) for stack rationale.

---

## Product Pillars

### 1. Solve real pain points, not build cool toys
- **Meal planning:** Plan the week, one shopping trip
- **Shopping lists:** Auto-derived, quantities fused by ingredient, grouped by aisle
- **Nutrition tracking:** Real kcal/macros/micros per meal using CIQUAL data + LLM fallback

### 2. Deterministic UI, LLM-assisted filling
- Calendar, shopping list, nutrition views are hand-coded and deterministic
- The LLM *fills* them via documented "skills" (step-by-step procedures) — does not replace them

### 3. Industrialize weekly rhythm
- 1 shop/week, full visibility on the week ahead
- Low operational overhead: if I can't keep it running without pain, it fails

---

## Ideal End-State

A responsive web app (phone + laptop) where I can:

- **Recipe base** — browse, search, edit recipes. LLM proposes new ones, I validate.
- **Weekly meal plan** — 7-day calendar. Fill by hand or ask the assistant ("plan me a week, high protein, seasonal").
- **Shopping list** — auto-derived from the week, deduped, grouped by aisle, usable at the supermarket (checkboxes).
- **Nutrition tracking** — every ingredient matched to CIQUAL. LLM fills gaps tagged `source: llm` for audit.
- **In-app chat** — Gemini-powered sidebar: read/write recipes, manage meal plan, trigger shopping-list regeneration, query nutrition, propose recipes.
- **Seasonality hint** — soft nudge, not hard filter.

---

## Settled Decisions

- **Interface:** responsive web app (URL), not Obsidian, not markdown
- **Nutrition:** full tracking is required. CIQUAL is the backbone; LLM fills gaps with a provenance flag
- **LLM provider:** Gemini 2.5 Flash via Google AI Studio (free tier). Not local vLLM for v1
- **LLM role:** in-app chat assistant with tools. Does not replace deterministic UI — it fills it
- **Success metric:** continuous, unbroken usage for at least one month. Frictionless UX is first-class

---

## Working Principle: Build Assistant-First

When designing a feature (meal plan, shopping list, nutrition view, etc.), think about how the assistant interacts with it *first*, then build the deterministic UI/data layer second.

- Every domain entity should eventually be readable by the assistant via a tool
- Every action the user can take in the UI should eventually be callable by the assistant via a tool
- This guides DB schema and API design — if a tool would need it, model it cleanly now

---

## Tech Strategy (Forward-Looking)

- **Embeddings & Vector Search:** semantic intent capture beyond keyword matching
- **Hybrid Search:** combine vector scoring (semantics) with lexical search (exact filters)
- **Modularity & Scalability:** decouple components for rapid evolution and new models/services
- **Performance:** minimize latency in queries and data processing for a frictionless front-end experience

---

## Backlog: Assistant Context Expansion

Current chat (v1) only sees recipe summaries via `list_recipes`. Future expansions:

- **`get_recipe(recipe_id)`** — full instructions, ingredients with quantities + units, nutrition (per-recipe + per-serving)
- **`recipe_overview`** — index + count of recipes so the assistant knows the collection shape without listing all every turn
- **`weekly_intake`** — query daily/weekly nutrition after tracking lands
