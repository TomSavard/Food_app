"""
Reference data loaders for ANSES daily intakes + Interfel seasonality.

Both datasets live as static JSON in `backend/data/`. Loaded once at import.
The convention: `ciqual_key` strings match the keys in
`ingredient_database.nutrition_data` (see `scripts/load_ciqual_2025.py`),
so the dashboard can map a nutrient → its target without an extra lookup.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

Sex = Literal["male", "female"]


@lru_cache(maxsize=1)
def _rdi_payload() -> dict:
    with (DATA_DIR / "anses_rdi.json").open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def _seasonality_payload() -> dict:
    with (DATA_DIR / "seasonality.json").open(encoding="utf-8") as fh:
        return json.load(fh)


def rdi_payload() -> dict:
    """Full ANSES payload, including sources + every nutrient row."""
    return _rdi_payload()


def rdi_for(sex: Sex) -> dict[str, float]:
    """Daily intake target per CIQUAL key for the given sex."""
    field = "male_adult" if sex == "male" else "female_adult"
    return {n["ciqual_key"]: float(n[field]) for n in _rdi_payload()["nutrients"]}


def lower_is_better_set() -> set[str]:
    return {n["ciqual_key"] for n in _rdi_payload()["nutrients"] if n.get("lower_is_better")}


# Daily macros set for the dashboard's day-by-day breakdown.
# Order = display order on the UI.
DAILY_MACROS: list[str] = [
    "Energie, Règlement UE N° 1169 2011 (kcal 100 g)",
    "Protéines, N x facteur de Jones (g 100 g)",
    "Lipides (g 100 g)",
    "Glucides (g 100 g)",
    "Sucres (g 100 g)",
    "Fibres alimentaires (g 100 g)",
    "Sel chlorure de sodium (g 100 g)",
    "AG saturés (g 100 g)",
]


# ---- Seasonality ----

_LEVEL_RANK = {"coeur": 0, "saison": 1, "disponibilite": 2}


def seasonality_payload() -> dict:
    return _seasonality_payload()


def seasonality_for(month: int) -> list[dict]:
    """Items in season for the given month (1–12). Sorted: coeur > saison > disponibilite."""
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1..12, got {month}")
    key = str(month)
    items = []
    for it in _seasonality_payload()["items"]:
        level = it.get("months", {}).get(key)
        if level:
            items.append({**it, "level": level})
    items.sort(key=lambda i: (_LEVEL_RANK.get(i["level"], 9), i["name"]))
    return items
