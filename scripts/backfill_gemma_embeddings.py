"""
Backfill NULL embeddings using EmbeddingGemma 300M (Google, open-source).

Runs locally on your Mac via HuggingFace transformers — no API key, no cost.

EmbeddingGemma 300M is Google's open-source embedding model, specifically
trained for retrieval. 256-d embeddings, high quality on French/English
multilingual retrieval.

Usage:
  DATABASE_URL=$(cat .env | grep DATABASE_URL | cut -d= -f2) \
    python scripts/backfill_gemma_embeddings.py

Check progress anytime:
  python scripts/load_ciqual_2025.py --status
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import torch
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.models import IngredientDatabase
from backend.db.session import get_engine

EMBEDDING_DIM = 256  # EmbeddingGemma 300M outputs 256-d
MODEL_NAME = "google/embeddinggemma-300m"

SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


def load_model():
    """Load EmbeddingGemma 300M once (cached after first run)."""
    from transformers import AutoModel, AutoTokenizer
    print("  Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME, trust_remote_code=True
    )
    print("  Loading model (~600 MB)...")
    model = AutoModel.from_pretrained(
        MODEL_NAME, trust_remote_code=True, torch_dtype=torch.float16
    ).to("cpu")  # CPU on Mac, no GPU needed
    return model, tokenizer


def compute_embeddings(tokenizer, model, texts: list[str]) -> list[list[float]]:
    """Compute 256-d mean-pooled embeddings, replacing NaN with 0."""
    import numpy as np
    inputs = tokenizer(
        texts, padding=True, truncation=True, return_tensors="pt"
    )
    with torch.no_grad():
        outputs = model(**inputs)
    # Mean pooling across sequence dimension.
    embeddings = outputs.last_hidden_state.mean(dim=1).numpy()
    # Replace NaN with 0 (can happen for short/special-char names).
    embeddings = np.nan_to_num(embeddings, nan=0.0)
    return embeddings.tolist()


def main() -> None:
    print(f"Model: {MODEL_NAME}  →  {EMBEDDING_DIM}-d embeddings\n")
    model, tokenizer = load_model()
    print("Ready.\n")

    db = SessionLocal()
    try:
        # Count rows that need embeddings (raw SQL avoids pgvector type casting).
        total = db.execute(text('SELECT count(*) FROM ingredient_database WHERE embedding IS NULL')).scalar()
        print(f"Rows to embed: {total}\n")

        if total == 0:
            print("Nothing to do — all rows already have embeddings.")
            return

        batch_size = 500  # fits in RAM comfortably
        offset = 0
        inserted = 0

        for batch_start in range(0, total, batch_size):
            rows = db.execute(text('''
                SELECT id::text, alim_nom_fr
                FROM ingredient_database
                WHERE embedding IS NULL
                ORDER BY id
                LIMIT :batch_size OFFSET :offset
            '''), {'batch_size': batch_size, 'offset': offset}).fetchall()
            if not rows:
                break

            names = [r[1] for r in rows]
            embeddings = compute_embeddings(tokenizer, model, names)

            for row, emb in zip(rows, embeddings):
                ing_id = row[0]
                db.execute(text('''
                    UPDATE ingredient_database SET embedding = :vec
                    WHERE id = :id AND embedding IS NULL
                '''), {'vec': json.dumps(emb[:EMBEDDING_DIM]), 'id': ing_id})
                inserted += 1

            db.commit()
            offset += batch_size

            elapsed = time.time() - getattr(main, "_start", time.time())
            pct = 100 * inserted / max(total, 1)
            print(f"  {inserted}/{total} ({pct:.1f}%) — {elapsed:.0f}s elapsed")

        print(f"\n✅ Done. {inserted} rows embedded with EmbeddingGemma 300M.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main._start = time.time()  # track elapsed across batches
    main()
