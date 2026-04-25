"""
Nutrition calculation utilities.

Resolution path: each `Ingredient` carries an `ingredient_db_id` FK set by
the match flow. NULL FK → silently untracked.

Quantity → grams in two layers:
  1. Spoon/cup table: cuillère à soupe / cuillère à café / verre / tasse / pincée.
     These are conventional volumes (or, for pincée, mass).
  2. Per-ingredient density (g/ml) for any ml/cl/l, after spoon conversion.
"""
from __future__ import annotations

import math
import re
import unicodedata
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from backend.db.models import Ingredient, IngredientDatabase

# CIQUAL column names AFTER load-time normalization (newlines → spaces).
NUTRITION_KEYS = {
    "calories": "Energie, Règlement UE N° 1169 2011 (kcal 100 g)",
    "proteins": "Protéines, N x facteur de Jones (g 100 g)",
    "lipides": "Lipides (g 100 g)",
    "glucides": "Glucides (g 100 g)",
    "salt": "Sel chlorure de sodium (g 100 g)",
    "saturated_fats": "AG saturés (g 100 g)",
}


def safe_float(value) -> Optional[float]:
    """Tolerant float parser for CIQUAL cells (handles 'traces', '<0.1',
    '1,5', ranges 'a-b'). Returns None when unparseable."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    if s in ("", "-", "nan", "n/a", "na"):
        return None
    if s in ("traces", "trace", "tr", "<0.1", "<0,1", "0", "0.0", "0,0"):
        return 0.0
    if s.startswith("<"):
        try:
            return float(s[1:].replace(",", ".")) / 2
        except ValueError:
            return 0.0
    if s.startswith(">"):
        try:
            return float(s[1:].replace(",", "."))
        except ValueError:
            return None
    if "-" in s:
        try:
            a, b = s.split("-", 1)
            return (float(a.replace(",", ".")) + float(b.replace(",", "."))) / 2
        except ValueError:
            pass
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def _normalize_unit(unit: str) -> str:
    """Lowercase + strip accents + collapse whitespace + strip dots."""
    if not unit:
        return ""
    n = _strip_accents(unit).lower()
    n = re.sub(r"[.\s]+", " ", n).strip()
    return n


# Conventional cooking volumes / masses, keyed by normalized unit.
# Values: ("ml", float)  → ml; ("g", float) → grams (skips density step).
_SPOON_TABLE: dict[str, tuple[str, float]] = {
    "cuillere a soupe": ("ml", 15.0),
    "cuilleres a soupe": ("ml", 15.0),
    "cas": ("ml", 15.0),
    "c a s": ("ml", 15.0),
    "c s": ("ml", 15.0),
    "cuillere a cafe": ("ml", 5.0),
    "cuilleres a cafe": ("ml", 5.0),
    "cac": ("ml", 5.0),
    "c a c": ("ml", 5.0),
    "c c": ("ml", 5.0),
    "verre": ("ml", 200.0),
    "verres": ("ml", 200.0),
    "tasse": ("ml", 240.0),
    "tasses": ("ml", 240.0),
    "pincee": ("g", 0.5),
    "pincees": ("g", 0.5),
}


def convert_to_grams(
    quantity: float, unit: str, density_g_per_ml: Optional[float] = None
) -> Optional[float]:
    """quantity × unit → grams. Returns None when conversion is impossible."""
    if quantity is None:
        return None
    n = _normalize_unit(unit)

    # Direct mass.
    if n in ("g", ""):
        return float(quantity) if n == "g" else None
    if n == "kg":
        return float(quantity) * 1000
    if n == "mg":
        return float(quantity) / 1000

    # Direct volume.
    ml: Optional[float] = None
    if n == "ml":
        ml = float(quantity)
    elif n == "cl":
        ml = float(quantity) * 10
    elif n == "l":
        ml = float(quantity) * 1000
    elif n in _SPOON_TABLE:
        kind, factor = _SPOON_TABLE[n]
        if kind == "g":
            return float(quantity) * factor
        ml = float(quantity) * factor

    if ml is None:
        return None
    if density_g_per_ml is None:
        return None
    return ml * float(density_g_per_ml)


def _per_100g(row: IngredientDatabase, key: str) -> Optional[float]:
    if not row.nutrition_data:
        return None
    return safe_float(row.nutrition_data.get(key))


def compute_recipe_nutrition(
    ingredients: List[Ingredient], db: Session
) -> Dict[str, float]:
    totals = {k: 0.0 for k in NUTRITION_KEYS}
    for ing in ingredients:
        if ing.ingredient_db_id is None:
            continue
        row = db.get(IngredientDatabase, ing.ingredient_db_id)
        if row is None:
            continue
        grams = convert_to_grams(ing.quantity, ing.unit, row.density_g_per_ml)
        if grams is None:
            continue
        for nutrient, key in NUTRITION_KEYS.items():
            per100 = _per_100g(row, key)
            if per100 is not None:
                totals[nutrient] += per100 * grams / 100

    return {k: round(v, 1) for k, v in totals.items()}
