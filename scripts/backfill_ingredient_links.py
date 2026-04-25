"""
Interactive backfill: walk every recipe ingredient + shopping_list item with
NULL ingredient_db_id, run lookup_exact, and prompt the user for confirmation
when the match is ambiguous.

Usage:
  DATABASE_URL=postgresql://... python scripts/backfill_ingredient_links.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re
import time

from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend.db.models import Ingredient, ShoppingList  # noqa: E402
from backend.db.session import get_engine  # noqa: E402
from backend.services import ingredient_match as im  # noqa: E402

SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)


def _llm_candidates_safe(db, name: str):
    """Wraps im.llm_candidates with a 429 retry. On second failure, returns []
    so the user can skip rather than losing the whole session."""
    try:
        return im.llm_candidates(db, name)
    except Exception as e:
        msg = str(e)
        if "429" not in msg and "RESOURCE_EXHAUSTED" not in msg:
            raise
        # Try to extract a retryDelay; fall back to 60s.
        m = re.search(r"'retryDelay':\s*'(\d+)s'", msg)
        delay = int(m.group(1)) + 2 if m else 60
        print(f"  ⏸ rate-limited; sleeping {delay}s …")
        time.sleep(delay)
        try:
            return im.llm_candidates(db, name)
        except Exception:
            print("  ⏸ still rate-limited; returning no candidates (you can (s)kip)")
            return []


def _resolve(db, name: str):
    """Returns ingredient_db_id or None ('s' to skip)."""
    exact = im.lookup_exact(db, name)
    if exact:
        print(f"  ✓ '{name}' → {exact.alim_nom_fr} (exact)")
        return exact.id

    candidates = _llm_candidates_safe(db, name)
    if not candidates:
        choice = input(f"  '{name}': no candidates. (n)ew / (s)kip ? ").strip().lower()
        if choice == "n":
            row = im.create_new(db, name)
            return row.id
        return None

    print(f"  '{name}':")
    for i, c in enumerate(candidates, 1):
        print(f"    {i}. {c['name']} (conf {c['confidence']:.2f}) — {c['reason']}")
    choice = input("    1/2/3 to confirm, (n)ew, (s)kip: ").strip().lower()
    if choice in ("1", "2", "3"):
        idx = int(choice) - 1
        if idx < len(candidates):
            cid = candidates[idx]["ingredient_db_id"]
            row = im.confirm_match(db, name, im.UUID(cid)) if hasattr(im, "UUID") else None
            if row is None:
                from uuid import UUID
                row = im.confirm_match(db, name, UUID(cid))
            return row.id
    if choice == "n":
        row = im.create_new(db, name)
        return row.id
    return None


def main() -> None:
    db = SessionLocal()
    try:
        recipe_ings = (
            db.query(Ingredient).filter(Ingredient.ingredient_db_id.is_(None)).all()
        )
        shop_items = (
            db.query(ShoppingList).filter(ShoppingList.ingredient_db_id.is_(None)).all()
        )
        print(f"Found {len(recipe_ings)} recipe ingredients + {len(shop_items)} shopping items to backfill.")

        # Commit after each row so a crash mid-way doesn't lose work.
        for ing in recipe_ings:
            if not ing.name:
                continue
            ref = _resolve(db, ing.name)
            if ref is not None:
                ing.ingredient_db_id = ref
                db.commit()

        for item in shop_items:
            if not item.name:
                continue
            ref = _resolve(db, item.name)
            if ref is not None:
                item.ingredient_db_id = ref
                db.commit()

        print("✅ Done.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
