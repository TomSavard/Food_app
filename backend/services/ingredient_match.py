"""
Free-text ingredient name → IngredientDatabase row.

Three resolution layers, cheapest first:

  1. lookup_exact(name)    — case-insensitive match on alim_nom_fr OR alias_text.
  2. embedding_candidates() — pgvector nearest-neighbor, optional Gemini re-rank.
  3. confirm_match()       — user-chosen winner; persists an alias for next time.
  4. create_new()          — user rejected all; mints a new IngredientDatabase row
                             (source='user', modified=true) plus an alias.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from backend.db.models import IngredientAlias, IngredientDatabase

CANDIDATE_PREFILTER_LIMIT = 30
EMBEDDING_CANDIDATE_LIMIT = 20
LLM_TOP_K = 3
EMBEDDING_DIM = 256  # EmbeddingGemma 300M
EMBEDDING_MODEL = "google/embeddinggemma-300m"


def _normalize(name: str) -> str:
    return name.strip().lower()


def lookup_exact(db: Session, name: str) -> Optional[IngredientDatabase]:
    """Case-insensitive match on canonical name OR any alias."""
    if not name or not name.strip():
        return None
    n = _normalize(name)

    row = (
        db.query(IngredientDatabase)
        .filter(func.lower(IngredientDatabase.alim_nom_fr) == n)
        .first()
    )
    if row:
        return row

    alias = (
        db.query(IngredientAlias)
        .filter(func.lower(IngredientAlias.alias_text) == n)
        .first()
    )
    if alias:
        return db.get(IngredientDatabase, alias.ingredient_db_id)
    return None


def _trigram_candidates(db: Session, name: str, limit: int) -> list[IngredientDatabase]:
    """Substring match on ingredient name and aliases (used as embedding fallback)."""
    tokens = [t for t in name.split() if len(t) >= 3]
    if not tokens:
        return []

    # Build a subquery of ingredient_db_ids that match via their alias text.
    alias_subq = (
        db.query(IngredientAlias.ingredient_db_id)
        .filter(IngredientAlias.alias_text.ilike(f"%{name}%"))
        .subquery()
    )
    q = db.query(IngredientDatabase).filter(
        func.lower(IngredientDatabase.alim_nom_fr).ilike(f"%{name}%")
        | IngredientDatabase.id.in_(alias_subq.select())
    )
    return q.limit(limit).all()


def _compute_query_embedding(name: str) -> Optional[list[float]]:
    """Compute a 256-d text embedding via Gemma 300M (local, open source)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        # Legacy path: Gemini text-embedding-004 (768-d).
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=[name],
            )
            return response.embeddings[0].values  # type: ignore[union-attr]
        except Exception:
            pass
    # Open-source local fallback: EmbeddingGemma 300M (256-d).
    try:
        import numpy as np
        import torch
        from transformers import AutoModel, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL, trust_remote_code=True)
        model = AutoModel.from_pretrained(
            EMBEDDING_MODEL, trust_remote_code=True, dtype=torch.float16
        ).to("cpu")
        inputs = tokenizer([name], padding=True, truncation=True, return_tensors="pt")
        with torch.no_grad():
            outputs = model(**inputs)
        emb = outputs.last_hidden_state.mean(dim=1).numpy()
        # Replace NaN with 0 (can happen for short/special-char names).
        emb = np.nan_to_num(emb, nan=0.0).tolist()[0]
        return emb[:EMBEDDING_DIM]
    except Exception:
        return None


def _bm25_score(text: str, query: str) -> float:
    """Simple BM25-inspired score: token overlap weighted by query frequency."""
    query_tokens = [t for t in query.lower().split() if len(t) >= 3]
    if not query_tokens:
        return 0.0
    text_lower = text.lower()
    score = 0.0
    for token in query_tokens:
        count = text_lower.count(token)
        if count:
            score += (count / len(query_tokens)) * math.log(1 + 1 / (1 + count / 100))
    return score


def _lazy_compute_embedding(db: Session, row: IngredientDatabase):
    """Compute and store the embedding for a row (if no embeddings exist yet).

    Gracefully skips when pgvector isn't available (e.g. CI test env).
    """
    try:
        has_embeddings = db.execute(text('''
            SELECT count(*) FROM ingredient_database WHERE embedding IS NOT NULL
        ''')).scalar()
        if has_embeddings > 0:
            return
        vec = _compute_query_embedding(row.alim_nom_fr)
        if vec is not None:
            db.execute(text('''
                UPDATE ingredient_database SET embedding = :vec WHERE id = :id
            '''), {'vec': json.dumps(vec), 'id': str(row.id)})
            db.flush()
    except Exception:
        pass  # pgvector not available — silently skip.


def embedding_candidates(
    db: Session, name: str, limit: int = EMBEDDING_CANDIDATE_LIMIT
) -> list[IngredientDatabase]:
    """Embedding-based nearest-neighbor search with BM25 re-ranking.

    Falls back to trigram when pgvector is unavailable.
    """
    if not os.getenv("GEMINI_API_KEY"):
        return _trigram_candidates(db, name, limit)

    query_vec = _compute_query_embedding(name)
    if query_vec is None:
        return []

    # Check if any rows have embeddings (coarse existence check via raw SQL).
    try:
        has_embeddings = db.execute(text('''
            SELECT count(*) FROM ingredient_database WHERE embedding IS NOT NULL
        ''')).scalar() > 0
    except Exception:
        return _trigram_candidates(db, name, limit)

    if not has_embeddings:
        return _trigram_candidates(db, name, limit)

    # Vector distance query (pgvector).
    try:
        rows = db.execute(
            text(
                f"""
                SELECT id, alim_nom_fr
                FROM ingredient_database
                WHERE embedding IS NOT NULL
                ORDER BY embedding <-> :vec
                LIMIT :top_n
                """
            ),
            {"vec": json.dumps(query_vec), "top_n": EMBEDDING_CANDIDATE_LIMIT * 2},
        ).all()
    except Exception:
        return _trigram_candidates(db, name, limit)

    if not rows:
        return _trigram_candidates(db, name, limit)

    ids = [r.id for r in rows]
    candidates = (
        db.query(IngredientDatabase)
        .filter(IngredientDatabase.id.in_(ids))
        .all()
    )

    if len(candidates) <= limit:
        return candidates

    # Composite scoring: 0.6 * embedding + 0.4 * BM25.
    try:
        scored: list[tuple[float, IngredientDatabase]] = []
        for c in candidates:
            # Read embedding via raw SQL (ORM doesn't handle pgvector).
            emb_row = db.execute(
                text('SELECT embedding FROM ingredient_database WHERE id = :id'),
                {'id': str(c.id)},
            ).fetchone()
            name_vec = emb_row.embedding if emb_row else None
            if name_vec is None:
                continue
            dot = sum(a * b for a, b in zip(query_vec, name_vec))
            q_norm = math.sqrt(sum(v * v for v in query_vec))
            c_norm = math.sqrt(sum(v * v for v in name_vec))
            if q_norm == 0 or c_norm == 0:
                emb_score = 0.0
            else:
                cos_sim = dot / (q_norm * c_norm)
                emb_score = max(0.0, cos_sim)

            bm25 = _bm25_score(c.alim_nom_fr, name)
            bm25_norm = min(1.0, bm25)

            composite = 0.6 * emb_score + 0.4 * bm25_norm
            scored.append((composite, c))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:limit]]
    except Exception:
        return _trigram_candidates(db, name, limit)


def llm_candidates(db: Session, name: str, k: int = LLM_TOP_K) -> list[dict]:
    """Returns up to k candidates: [{ingredient_db_id, name, reason, confidence}]."""
    pool = embedding_candidates(db, name, EMBEDDING_CANDIDATE_LIMIT)
    if not pool:
        return []
    if len(pool) <= k:
        return [
            {
                "ingredient_db_id": str(r.id),
                "name": r.alim_nom_fr,
                "reason": "Requête trouvée par similarité vectorielle.",
                "confidence": 0.5,
            }
            for r in pool
        ]

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        # Without an LLM, return the top-k by embedding order.
        return [
            {
                "ingredient_db_id": str(r.id),
                "name": r.alim_nom_fr,
                "reason": "Similarité vectorielle.",
                "confidence": 0.4,
            }
            for r in pool[:k]
        ]

    from google import genai
    from google.genai import types

    catalog = [{"id": str(r.id), "name": r.alim_nom_fr} for r in pool]
    prompt = (
        f"L'utilisateur a saisi l'ingrédient « {name} ». "
        f"Choisis dans la liste ci-dessous les {k} meilleurs candidats CIQUAL "
        "qui correspondent à cet ingrédient. Réponds UNIQUEMENT avec un JSON de la forme "
        '{"candidates": [{"id": "...", "reason": "...", "confidence": 0-1}]}.\n\n'
        f"Liste: {json.dumps(catalog, ensure_ascii=False)}"
    )
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    try:
        parsed = json.loads(response.text or "{}")
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=502, detail=f"Bad LLM response: {e}")

    by_id = {str(r.id): r for r in pool}
    out: list[dict] = []
    for c in (parsed.get("candidates") or [])[:k]:
        cid = str(c.get("id") or "")
        if cid in by_id:
            out.append(
                {
                    "ingredient_db_id": cid,
                    "name": by_id[cid].alim_nom_fr,
                    "reason": str(c.get("reason") or ""),
                    "confidence": float(c.get("confidence") or 0.0),
                }
            )
    return out


def confirm_match(
    db: Session, free_text: str, ingredient_db_id: UUID, *, created_by: str = "user"
) -> IngredientDatabase:
    """Persist `free_text` → `ingredient_db_id` as an alias. Idempotent."""
    if not free_text or not free_text.strip():
        raise HTTPException(status_code=400, detail="free_text is required")

    canonical = db.get(IngredientDatabase, ingredient_db_id)
    if canonical is None:
        raise HTTPException(status_code=404, detail="ingredient_db_id not found")

    n = _normalize(free_text)
    if n == canonical.alim_nom_fr.strip().lower():
        return canonical  # alias would duplicate the canonical name

    existing = (
        db.query(IngredientAlias)
        .filter(func.lower(IngredientAlias.alias_text) == n)
        .first()
    )
    if existing:
        if existing.ingredient_db_id != ingredient_db_id:
            existing.ingredient_db_id = ingredient_db_id
            existing.created_by = created_by
            db.flush()
        return canonical

    db.add(
        IngredientAlias(
            ingredient_db_id=ingredient_db_id,
            alias_text=free_text.strip(),
            created_by=created_by,
        )
    )

    # Lazy-compute embedding on the canonical row (if no embeddings exist yet).
    try:
        has_embeddings = db.execute(text('''
            SELECT count(*) FROM ingredient_database WHERE embedding IS NOT NULL
        ''')).scalar()
        if has_embeddings == 0:
            _lazy_compute_embedding(db, canonical)
    except Exception:
        pass  # pgvector not available — silently skip.

    db.flush()
    return canonical


def create_new(
    db: Session,
    name: str,
    *,
    category: Optional[str] = None,
    created_by: str = "user",
) -> IngredientDatabase:
    """Create a new IngredientDatabase row + alias for the given free-text."""
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="name is required")

    # If exact already exists, just return it.
    existing = lookup_exact(db, name)
    if existing:
        return existing

    row = IngredientDatabase(
        alim_nom_fr=name.strip(),
        nutrition_data={},
        category=category,
        source=created_by if created_by in ("user", "llm") else "user",
        modified=True,
        modified_by=created_by,
        modified_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    # Always anchor an alias for the typed form so casing variants resolve.
    db.add(
        IngredientAlias(
            ingredient_db_id=row.id,
            alias_text=name.strip(),
            created_by=created_by,
        )
    )
    db.flush()
    # Compute embedding for the new row (idempotent, stored once).
    _lazy_compute_embedding(db, row)
    return row
