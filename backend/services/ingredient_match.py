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
EMBEDDING_MODEL = "text-embedding-004"


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
    """pg_trgm-based pre-filter. Falls back to ILIKE if pg_trgm unavailable."""
    try:
        rows = db.execute(
            text(
                """
                SELECT id, alim_nom_fr, similarity(alim_nom_fr, :q) AS sim
                FROM ingredient_database
                WHERE alim_nom_fr % :q
                ORDER BY sim DESC
                LIMIT :lim
                """
            ),
            {"q": name, "lim": limit},
        ).all()
        if rows:
            ids = [r.id for r in rows]
            return (
                db.query(IngredientDatabase)
                .filter(IngredientDatabase.id.in_(ids))
                .all()
            )
    except Exception:
        pass

    # Fallback: substring match on each token (name + alias text).
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
    """Compute a 768-d text embedding via Gemini text-embedding-004."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=[name],
        )
        return response.embeddings[0].values  # type: ignore[union-attr]
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


def embedding_candidates(
    db: Session, name: str, limit: int = EMBEDDING_CANDIDATE_LIMIT
) -> list[IngredientDatabase]:
    """Embedding-based nearest-neighbor search with BM25 re-ranking.

    If GEMINI_API_KEY is not set, falls back to _trigram_candidates().
    """
    # Fast path: no embedding config → use trigram.
    if not os.getenv("GEMINI_API_KEY"):
        return _trigram_candidates(db, name, limit)

    query_vec = _compute_query_embedding(name)
    if query_vec is None:
        return _trigram_candidates(db, name, limit)

    # Check if any rows have embeddings (coarse existence check).
    has_embeddings = db.query(
        func.count(IngredientDatabase.embedding).filter(
            IngredientDatabase.embedding.isnot(None)
        )
    ).scalar() > 0

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
        return []

    ids = [r.id for r in rows]
    candidates = (
        db.query(IngredientDatabase)
        .filter(IngredientDatabase.id.in_(ids))
        .all()
    )

    if len(candidates) <= limit:
        return candidates

    # Composite scoring: 0.6 * embedding + 0.4 * BM25.
    scored: list[tuple[float, IngredientDatabase]] = []
    for c in candidates:
        # Get distance from the pgvector result by finding position.
        # Compute cosine similarity from distance (distance ranges 0-2 for L2).
        name_vec = c.embedding
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
        # Normalize BM25 to [0, 1] range (heuristic cap at 1.0).
        bm25_norm = min(1.0, bm25)

        composite = 0.6 * emb_score + 0.4 * bm25_norm
        scored.append((composite, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]


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
    return row
