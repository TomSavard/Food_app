# 01_embedding_based_ingredient_matching

## Architecture Overview

```
User input: "celemi"
    │
    ▼  Layer 0 — Exact alias match (fast path)
    lookup_exact("celemi") → found? → return canonical row
    │  (user-confirmed synonyms, no change)
    ▼  Layer 1 — Embedding search
    compute embedding(query) → vector_distance with all rows → top-20
    (handles typos, accents, multi-word variants)
    │
    ▼  Layer 2 — BM25 tiebreak
    Score composite: 0.6 * embedding_score + 0.4 * bm25_score
    (substring quality for exact match validation)
    │
    ▼  Layer 3 — LLM re-rank (optional, kept for now)
    Top-5 passed to Gemini for final top-3 with reasons
    │
    ▼  Layer 4 — Alias persistence
    User confirms → create alias → next lookup = instant (layer 0)
```

## Decisions

| Decision | Value | Rationale |
|----------|-------|-----------|
| Embedding model | `google/text-embedding-004` (768-d) | Already using Gemini, small + accurate enough |
| Storage | pgvector `VECTOR(768)` column | ANN search on 84K+ rows; Neon supports pgvector |
| Index | `hnsw` (M=16, ef_construction=64) | Faster query than `ivfflat` at this scale |
| Distance metric | `<=>` (Euclidean) or cosine via pgvector | Built-in, fast |
| Candidate count | 20 (vs 30 trigram) | Tighter pool = fewer irrelevant + less LLM cost |
| Score weights | 0.6 embedding + 0.4 BM25 | Embedding does heavy lifting; BM25 validates substring quality |
| Distance threshold | 0.6 (cosine) | 0 = identical, 2 = opposite. ~0.6 covers typos + accents |

## Current Matching: Pain Points & Weaknesses

### Autocomplete (`/api/ingredients/search`)
- Uses `ILIKE '%needle%'` + heuristic scoring
- **"beurre demi sel" without hyphen** → no match (unless exact alias exists)
- **"celemi"** (typo for "céléri") → no match unless pg_trgm ranks it 30th
- **"pomme de terre"** token conjunction requires ALL tokens to match → misses "patate douce"
- **Accent sensitivity** → "celeri" ≠ "céléri"
- **Generic input** like "a" or "le" returns 30 irrelevant results

### Matching layer (`/api/match/candidates`)
- **30 fixed candidate pool** regardless of query specificity
- **LLM dependency** = cost + latency + silence when API key is missing
- **Exact alias match only** — "beurre demi-sel" (different hyphenation) still misses

### Architectural weaknesses
- Token conjunction is overly restrictive for French multi-word names
- No phonetic or transliteration support
- Seasonality match uses bidirectional substring — "te" matches "Tomate" AND "te" matches "cette"
- 221 lines of hardcoded keyword patterns in categorize.py

## Phases

### Phase 1 — Schema + Batch Embedding (no query changes)

**Files modified:**
- `backend/db/models.py` → add `embedding` column to `IngredientDatabase`
- `scripts/load_ciqual_2025.py` → compute embeddings for new CIQUAL rows during import

**What happens:**
1. New column: `embedding VECTOR(768)` on `ingredient_database` table (nullable)
2. New index: `CREATE INDEX idx_ingredient_embedding ON ingredient_database USING hnsw (embedding vector_l2_ops)`
3. `load_ciqual_2025.py` calls `genai.embed_content(model="text-embedding-004", content=name)` for each row and stores the 768-d array
4. Existing rows have `NULL` embeddings — they get embedded on-demand (lazy compute)

**Cost:** ~0.0002 USD per embedding × 84K rows ≈ $17 one-time

### Phase 2 — Embedding Search Service (drop-in replacement)

**Files modified:**
- `backend/services/ingredient_match.py` → new `embedding_candidates()` function
- `backend/api/match.py` → call `embedding_candidates()` instead of `_trigram_candidates()`
- `backend/api/ingredients.py` → update `search_ingredients()` similarly
- `backend/api/chat.py` → update chat tools

**New function in `ingredient_match.py`:**

```python
def embedding_candidates(db: Session, name: str, limit: int = 20) -> list[IngredientDatabase]:
    """Embedding-based nearest-neighbor search with BM25 score re-ranking."""
    # 1. Compute embedding for query string
    # 2. Vector distance query: ORDER BY alim_embedding <=> query_embedding LIMIT 50
    # 3. BM25 scoring on the result set
    # 4. Composite scoring: 0.6 * embedding_score + 0.4 * bm25_score
    # 5. Return top-{limit}
```

**Key implementation notes:**
- Retrieve the 768-d array as Python list from pgvector
- Compute cosine similarity: `1 - (dot(a, b) / (||a|| * ||b||))` in SQL via pgvector
- BM25: simple token-based term frequency for the 50 candidates (no full-text index needed)

### Phase 3 — On-Demand Embedding for User-Created Ingredients

**Files modified:**
- `backend/services/ingredient_match.py` → `create_new()` computes embedding
- `backend/services/ingredient_match.py` → `confirm_match()` computes embedding on the canonical row (if NULL)
- `backend/api/ingredients.py` → PATCH endpoint triggers embedding

**What happens:**
- When a user creates a new ingredient or confirms an alias, the canonical row's embedding is computed automatically (lazy compute, stored in DB)
- No manual embedding step needed

### Phase 4 — Clean Up Old Matching

**Files removed/deactivated:**
- `_trigram_candidates()` → replaced by `embedding_candidates()`
- `pg_trgm` extension → no longer needed (remove from DB setup if it exists)
- LLM fallback for trigram (now LLM gets tighter 5-pool, not 30)
- `"Similarité trigramme"` fallback responses

## Files That Change

| File | Change |
|------|--------|
| `backend/db/models.py` | Add `embedding Column(ARRAY(Float))` to `IngredientDatabase` |
| `scripts/load_ciqual_2025.py` | Compute + store embeddings for each row during import |
| `backend/services/ingredient_match.py` | Add `embedding_candidates()`, update `llm_candidates()` to call it |
| `backend/api/match.py` | Call `embedding_candidates()` instead of `_trigram_candidates()` |
| `backend/api/ingredients.py` | Update `search_ingredients()` similarly |
| `backend/api/chat.py` | Update chat tools to use embedding search |
| `backend/api/reference.py` | (optional) Seasonality matching → embedding-based |
| `backend/services/shopping_list_sync.py` | (optional) `_find_or_create_item` → embedding |
| `backend/services/categorize.py` | (optional) Embedding-based categorization |

## Backward Compatibility

- **Aliases remain exact-match** — no change, works with or without embeddings
- **`lookup_exact()` unchanged** — exact match still fast-paths first
- **LLM re-ranking still exists** — gets tighter 5-pool, fewer tokens
- **Existing API responses** — `CandidatesResponse` schema unchanged

## Testing Strategy

- Add tests for `embedding_candidates()` with known queries: typos, accents, plurals, multi-word
- Ensure existing 159 tests still pass (they test the API layer, which routes through the same endpoints)
- Test embedding-based autocomplete for edge cases that ILIKE misses

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Neon/pgvector not available in project's Neon | Verify extension is enabled; fallback to JSONB + Python distance computation |
| Embedding API cost for 84K rows | ~$17 one-time; negligible for project scale |
| Latency of embedding at query time | Store embeddings in DB; only new/updated rows incur API cost |
| Embedding for very short queries ("a") | Distance threshold filters out weak matches; return empty |
| Multi-language inputs ("onion" vs "oignon") | Same embedding model — cross-lingual is partial; can add language hints if needed |

## Proposed Implementation Order

```
1. Phase 1 (schema + batch)    → verify: all CIQUAL rows have embeddings
2. Phase 2 (search service)    → verify: new search handles typos better than ILIKE
3. Phase 3 (lazy compute)       → verify: user-created ingredients get embeddings
4. Phase 4 (cleanup)            → verify: 159 tests still pass, CI workflow clean
```
