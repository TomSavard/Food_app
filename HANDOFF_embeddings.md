# Handoff — ingredient DB cleanup done, embeddings next

## State of the DB (2026-09-13)

`ingredient_database`: **2,840 rows** (was 3,521).

| pass | rows removed | what |
|---|---|---|
| state-variant merge | 281 | `Brocoli, cru` / `cuit` / `surgelé, cru` → one `Brocoli`; old names kept as aliases |
| prepared-dish delete | 400 | CIQUAL group `entrées et plats composés` (stocks/bouillons excluded) |

All 99 recipe→ingredient links preserved; 0 orphans. Aliases: 218 rows carry them.

Backups (restorable, full `nutrition_data`):
- `backups/pre_dedup_20260913_144123.json`
- `backups/pre_dish_delete_20260913_145652.json`

Script: `scripts/dedup_ingredients.py` (dry-run by default, `--apply` to write).
Current export: `data_export_all_ingredients.csv`.

## STOP — read before backfilling embeddings

**All 2,840 rows have `embedding IS NULL`, and backfilling them as the code
stands will make ingredient matching worse, not better.**

Three things are mutually inconsistent:

1. `ingredient_database.embedding` is **`float8[]`**, not a pgvector `vector`.
2. **pgvector is not installed** on this Neon DB (`SELECT count(*) FROM
   pg_extension WHERE extname='vector'` → 0).
3. `backend/services/ingredient_match.py:153` orders by `embedding <-> :vec`.
   The `<->` operator does not exist for `float8[]`, so that query can only throw.

Today nothing breaks because `embedding_candidates()` checks `has_embeddings`
first (line 136); with every row NULL it takes the `_trigram_candidates()`
fallback, which works. **The moment any row has an embedding, that guard passes,
the vector query throws, and the `except Exception: return []` at line 158
swallows it — matching returns zero candidates instead of falling back.**

So the backfill is not step 1. Step 1 is picking one of:
- install pgvector, migrate the column to `vector(N)`, keep the `<->` query; or
- keep `float8[]` and compute cosine distance in SQL or in Python.

Either way, fix `except Exception: return []` to fall back to
`_trigram_candidates()` rather than returning nothing — that silent swallow is
what turns a config error into invisible breakage.

## Model (now resolved)

All code uses **EmbeddingGemma 300M (256-d)** consistently:

| place | model | dim |
|---|---|---|
| `backend/db/models.py` (comment) | gemma-3-300m-it | 256 |
| `ingredient_match.py:80` `_compute_query_embedding` (query side) | gemma-3-300m-it (local fallback) | 256 (Gemini 768 if key set) |
| `scripts/load_ciqual_2025.py` (batch) | gemma-3-300m-it (local) | 256 |
| `scripts/backfill_gemma_embeddings.py` | gemma-3-300m-it (local) | 256 |
| `scripts/backfill_local_embeddings.py` | **DELETED** (was e5-large 1024-d) | — |

Query and corpus vectors are now consistent (256-d).

## Leftovers from the cleanup (optional)

- **18 merge groups skipped**, no keeper rule matched — `égoutté` vs `non
  égoutté` tinned fruit, `déshydraté` vs `reconstitué` stock. Drained-vs-not is a
  real per-100g difference, so they need a human call. Run
  `PYTHONPATH=. .venv/bin/python scripts/dedup_ingredients.py` to list them.
- **Naming is inconsistent.** Merged foods got clean names (`Brocoli`), but
  untouched singletons kept their CIQUAL suffix (`Tomate cerise, crue`,
  `Aubergine, crue`). A rename pass over ~2,800 rows, cosmetic only.
