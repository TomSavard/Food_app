Recipe loading optimization — complete.

Changes made (6 phases, 7 files):
1. DB pool: `pool_size=5, max_overflow=10` (was 1/0) → enables concurrent queries
2. N+1 nutrition: batch-load `IngredientDatabase` rows (1 query instead of N)
3. Lightweight list: `/recipes/summary` endpoint — metadata only, no ingredients/instructions
4. Embedded nutrition: `GET /recipes/{id}` now returns nutrition (no separate call)
5. Deferred images: recipe + nutrition in initial call, images loaded async
6. Client cache: 5-min in-memory recipe cache (re-opening same recipe = instant)

Files: `backend/db/session.py`, `backend/utils/nutrition.py`, `backend/api/recipes.py`, `backend/schemas.py`, `lib/types.ts`, `lib/api.ts`, `components/recipe-detail-dialog.tsx`, `components/recipe-form-dialog.tsx`

