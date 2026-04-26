"""
Rank recipes by how well their ingredients match what's in season for a
given month. Pure function over the Interfel data + a list of recipes.

Scoring: each recipe ingredient matches a seasonality item if the item's
canonical name appears (lowercase substring) in the ingredient name.
A `coeur` (cœur de saison) match counts 2; a `saison` match counts 1;
`disponibilite` counts 0.5; no match counts 0. The recipe score is the
sum of per-ingredient scores divided by the number of ingredients
(so big recipes don't beat small ones automatically), then top-k.
"""
from __future__ import annotations

from typing import Iterable

from backend.db.models import Recipe
from backend.services.reference import seasonality_for

_LEVEL_WEIGHT = {"coeur": 2.0, "saison": 1.0, "disponibilite": 0.5}


def _ingredient_score(name: str, in_season: list[dict]) -> tuple[float, str | None]:
    """Returns (score, matched_item_name)."""
    needle = (name or "").lower()
    if not needle:
        return 0.0, None
    best = 0.0
    matched: str | None = None
    for item in in_season:
        anchor = item["name"].lower()
        # Substring match in either direction (e.g. "tomate" matches "tomate"
        # in the recipe ingredient "Tomate, crue" and vice-versa).
        if anchor in needle or needle in anchor:
            score = _LEVEL_WEIGHT.get(item.get("level", ""), 0.0)
            if score > best:
                best = score
                matched = item["name"]
    return best, matched


def rank_recipes(recipes: Iterable[Recipe], month: int, k: int = 5) -> list[dict]:
    """Returns up to k recipes ranked by their seasonal alignment for `month`.

    Each result: {recipe_id, recipe_name, score, matched_ingredients[]}.
    Recipes with no in-season match are excluded.
    """
    items = seasonality_for(month)
    out: list[dict] = []
    for r in recipes:
        ings = list(r.ingredients or [])
        if not ings:
            continue
        total = 0.0
        matches: list[dict] = []
        for ing in ings:
            score, matched = _ingredient_score(ing.name or "", items)
            if score > 0 and matched:
                matches.append({"ingredient": ing.name, "matched": matched, "score": score})
                total += score
        if not matches:
            continue
        avg = total / len(ings)
        out.append({
            "recipe_id": str(r.recipe_id),
            "recipe_name": r.name,
            "score": round(avg, 3),
            "n_in_season": len(matches),
            "matched_ingredients": matches[:6],
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:k]
