"""
Load CIQUAL 2025 (Table Ciqual 2025_FR_2025_11_03.xls) into ingredient_database.

- Drops every ingredient_database row where source='ciqual' AND modified=false.
- Preserves rows with modified=true (user/llm curation) and rows with non-ciqual source.
- Loads all 84 columns of the file into JSONB. Newlines in column headers
  are normalized to spaces and runs of whitespace collapsed.
- Asserts the 6 promoted nutrients exist before writing anything.

Usage:
  DATABASE_URL=postgresql://... python scripts/load_ciqual_2025.py [path/to/Table.xls]
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pandas as pd

# Ensure backend imports work when run from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import sessionmaker  # noqa: E402

from backend.db.models import IngredientDatabase  # noqa: E402
from backend.db.session import get_engine  # noqa: E402

SessionLocal = sessionmaker(bind=get_engine(), autocommit=False, autoflush=False)

DEFAULT_XLS = Path(__file__).resolve().parent.parent / "Table Ciqual 2025_FR_2025_11_03.xls"

# Promoted (assert they exist; surfaced as first-class nutrients).
# Names below are POST-normalization (newlines → spaces, collapsed).
PROMOTED_KEYS = [
    "Energie, Règlement UE N° 1169 2011 (kcal 100 g)",
    "Protéines, N x facteur de Jones (g 100 g)",
    "Lipides (g 100 g)",
    "Glucides (g 100 g)",
    "Sel chlorure de sodium (g 100 g)",
    "AG saturés (g 100 g)",
]


def normalize_col(name: str) -> str:
    """Collapse newlines + whitespace runs to single spaces."""
    return re.sub(r"\s+", " ", name.replace("\n", " ")).strip()


def main(xls_path: Path) -> None:
    if not xls_path.exists():
        print(f"❌ File not found: {xls_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {xls_path} ...")
    df = pd.read_excel(xls_path)
    df.columns = [normalize_col(c) for c in df.columns]
    print(f"  {len(df)} rows × {len(df.columns)} columns")

    if "alim_nom_fr" not in df.columns:
        print("❌ alim_nom_fr column missing", file=sys.stderr)
        sys.exit(1)

    missing_promoted = [k for k in PROMOTED_KEYS if k not in df.columns]
    if missing_promoted:
        print("❌ Promoted nutrient columns missing — aborting:", file=sys.stderr)
        for k in missing_promoted:
            print(f"   - {k}", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        # Wipe untouched ciqual rows. Preserve curated ones.
        deleted = (
            db.query(IngredientDatabase)
            .filter(
                IngredientDatabase.source == "ciqual",
                IngredientDatabase.modified.is_(False),
            )
            .delete(synchronize_session=False)
        )
        print(f"  deleted {deleted} untouched ciqual rows")

        # Index curated rows by lowercased name to skip them on insert.
        curated_names = {
            r.alim_nom_fr.strip().lower()
            for r in db.query(IngredientDatabase.alim_nom_fr)
            .filter(IngredientDatabase.modified.is_(True))
            .all()
        }
        print(f"  preserving {len(curated_names)} curated rows")

        inserted = 0
        skipped_curated = 0
        for _, row in df.iterrows():
            name = row.get("alim_nom_fr")
            if not isinstance(name, str) or not name.strip():
                continue
            if name.strip().lower() in curated_names:
                skipped_curated += 1
                continue

            nutrition_data: dict = {}
            for col in df.columns:
                if col.startswith("alim_"):
                    continue
                val = row[col]
                if pd.isna(val):
                    nutrition_data[col] = None
                else:
                    nutrition_data[col] = (
                        float(val) if isinstance(val, (int, float)) else str(val)
                    )

            db.add(
                IngredientDatabase(
                    alim_nom_fr=name.strip(),
                    nutrition_data=nutrition_data,
                    source="ciqual",
                    modified=False,
                )
            )
            inserted += 1

        db.commit()
        print(f"✅ inserted {inserted} rows (skipped {skipped_curated} curated)")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLS
    main(path)
