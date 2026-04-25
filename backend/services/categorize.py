"""
Categorisation: every ingredient on the shopping list lands in one of the
ten supermarket sections below. Three layers, in order:

    1. Look up `ingredient_database.category` by case-insensitive name.
    2. Heuristic word-match (mirrors the legacy lib/shopping-categories.ts).
    3. Default to "Autres".

Whenever a category is chosen by the user (drag/drop) or by the LLM, we
upsert the corresponding `ingredient_database` row with source='user' /
'llm', so future occurrences of the same ingredient pre-fill correctly.
"""
from __future__ import annotations

from typing import Iterable, Literal, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.db.models import IngredientDatabase

# Order matches a typical supermarket walk; the frontend renders sections
# in this exact order.
CATEGORIES: list[str] = [
    "Fruits & Légumes",
    "Boulangerie",
    "Viandes & Poissons",
    "Produits Laitiers",
    "Surgelés",
    "Épicerie",
    "Épices & Herbes",
    "Boissons",
    "Sucreries",
    "Autres",
]

# Order matters: first match wins. Earlier patterns are more specific.
_PATTERNS: list[tuple[str, list[str]]] = [
    (
        "Boulangerie",
        ["pain", "baguette", "brioche", "viennoiserie", "croissant", "pain au chocolat"],
    ),
    (
        "Surgelés",
        ["surgelé", "surgelée", "glacé", "glaçon", "glace"],
    ),
    (
        "Viandes & Poissons",
        [
            "poulet", "poularde", "poule", "boeuf", "bœuf", "veau", "porc", "agneau",
            "dinde", "canard", "lapin", "lardon", "jambon", "saucisse", "saucisson",
            "rôti", "steak", "escalope", "bacon", "merguez",
            "saumon", "thon", "merlu", "cabillaud", "sardine", "morue", "truite",
            "crevette", "moule", "huître", "calamar", "calmar", "poisson",
        ],
    ),
    (
        "Produits Laitiers",
        [
            "lait", "yaourt", "yogourt", "fromage", "beurre", "crème fraîche", "crème",
            "mascarpone", "ricotta", "feta", "mozzarella", "parmesan", "comté",
            "gruyère", "emmental", "chèvre", "camembert", "brie", "reblochon",
            "fromage blanc", "skyr", "cancoillotte", "kefir",
        ],
    ),
    (
        "Fruits & Légumes",
        [
            "tomate", "carotte", "oignon", "ail", "echalote", "échalote",
            "pomme", "banane", "orange", "citron", "lime", "mandarine",
            "salade", "laitue", "épinard", "poireau", "courgette", "aubergine",
            "poivron", "concombre", "radis", "betterave", "chou", "brocoli",
            "céleri", "fenouil", "navet", "patate douce", "patate", "pomme de terre",
            "champignon", "fraise", "framboise", "myrtille", "kiwi", "raisin",
            "mangue", "ananas", "pêche", "abricot", "prune", "cerise", "melon",
            "pastèque", "avocat", "courge", "potiron", "potimarron", "haricot vert",
            "petit pois", "endive", "artichaut", "asperge", "blette", "bette",
            "fruit", "légume",
        ],
    ),
    (
        "Épices & Herbes",
        [
            "poivre", "curry", "paprika", "cumin", "cannelle", "muscade",
            "thym", "romarin", "basilic", "persil", "coriandre", "menthe",
            "laurier", "estragon", "ciboulette", "origan", "safran", "gingembre",
            "curcuma", "cardamome", "anis", "vanille",
        ],
    ),
    (
        "Boissons",
        [
            "vin", "bière", "biere", "champagne", "cidre",
            "jus", "eau", "café", "thé", "tisane", "soda", "limonade", "sirop",
        ],
    ),
    (
        "Sucreries",
        ["chocolat", "miel", "confiture", "biscuit", "gâteau", "bonbon", "nutella"],
    ),
    (
        "Épicerie",
        [
            "pâtes", "pates", "spaghetti", "tagliatelles", "lasagne", "ravioli",
            "riz", "farine", "huile", "vinaigre", "sucre", "sel",
            "œuf", "oeuf", "lentille", "pois chiche", "haricot sec", "quinoa",
            "boulgour", "couscous", "céréales", "biscotte",
            "thon en boîte", "tomate concassée", "moutarde", "ketchup", "mayonnaise",
            "sauce soja", "sauce tomate", "pesto", "tapenade", "houmous",
            "olives", "olive", "câpre", "cornichon", "soupe",
        ],
    ),
]


def _heuristic(name: str) -> str:
    n = name.lower()
    for cat, words in _PATTERNS:
        for w in words:
            if w in n:
                return cat
    return "Autres"


def _normalize(name: str) -> str:
    return name.strip().lower()


def lookup_known_category(db: Session, name: str) -> Optional[str]:
    """Look the ingredient up in the knowledge base by case-insensitive name."""
    row = (
        db.query(IngredientDatabase)
        .filter(func.lower(IngredientDatabase.alim_nom_fr) == _normalize(name))
        .first()
    )
    return row.category if row else None


def categorize(db: Session, name: str) -> str:
    """Resolve a category for an ingredient name. Always returns a value
    from CATEGORIES (falls back to 'Autres')."""
    if not name:
        return "Autres"
    known = lookup_known_category(db, name)
    if known and known in CATEGORIES:
        return known
    cat = _heuristic(name)
    return cat if cat in CATEGORIES else "Autres"


def learn_category(
    db: Session,
    name: str,
    category: str,
    source: Literal["user", "llm"] = "user",
) -> None:
    """Persist a category decision. Upserts ingredient_database by name.

    A 'user' decision overrides anything (including a previous 'llm'). An
    'llm' decision is written only if no row exists or the row is currently
    NULL or itself 'llm' / 'ciqual' (so we never silently overwrite a user
    correction)."""
    if category not in CATEGORIES:
        return
    if not name:
        return

    row = (
        db.query(IngredientDatabase)
        .filter(func.lower(IngredientDatabase.alim_nom_fr) == _normalize(name))
        .first()
    )

    if row is None:
        db.add(
            IngredientDatabase(
                alim_nom_fr=name.strip(),
                category=category,
                source=source,
            )
        )
        db.flush()
        return

    if source == "user":
        row.category = category
        row.source = "user"
    elif source == "llm":
        if row.source != "user":
            row.category = category
            row.source = "llm"
    db.flush()


def categorize_many(db: Session, names: Iterable[str]) -> dict[str, str]:
    """Bulk version. Returns {name: category}."""
    return {name: categorize(db, name) for name in names}
