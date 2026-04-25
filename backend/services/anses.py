"""
ANSES recommended daily intakes for an adult ~30y, mixed-baseline.

Keys are CIQUAL canonical column names AFTER the load-time normalization
(newlines collapsed to spaces) — they match the keys stored in
`ingredient_database.nutrition_data`.

Sources: ANSES "Apports nutritionnels conseillés" + EFSA dietary reference
values. Values are conservative averages: where ANSES gives sex-specific
ranges, the rounder middle is used. `Sel` and `AG saturés` are upper
bounds (the dashboard inverts the color logic for these two).
"""
from __future__ import annotations

# Daily targets (per day, single adult).
RDI: dict[str, float] = {
    # Énergie + macros
    "Energie, Règlement UE N° 1169 2011 (kcal 100 g)": 2400,
    "Protéines, N x facteur de Jones (g 100 g)": 75,
    "Lipides (g 100 g)": 95,
    "AG saturés (g 100 g)": 32,                # ≤12% energy → upper bound
    "Glucides (g 100 g)": 285,
    "Sucres (g 100 g)": 100,                    # upper bound
    "Fibres alimentaires (g 100 g)": 30,
    "Sel chlorure de sodium (g 100 g)": 6.5,    # upper bound
    # Minéraux
    "Calcium (mg 100 g)": 950,
    "Fer (mg 100 g)": 11,
    "Magnésium (mg 100 g)": 380,
    "Phosphore (mg 100 g)": 550,
    "Potassium (mg 100 g)": 3500,
    "Zinc (mg 100 g)": 11,
    "Iode (µg 100 g)": 150,
    "Sélénium (µg 100 g)": 70,
    "Cuivre (mg 100 g)": 1.3,
    "Manganèse (mg 100 g)": 2.8,
    # Vitamines
    "Vitamine C (mg 100 g)": 110,
    "Vitamine D (µg 100 g)": 15,
    "Vitamine B9 ou Folates totaux (µg 100 g)": 330,
    "Vitamine B12 (µg 100 g)": 4,
    "Activité vitaminique A, équivalents rétinol (µg 100 g)": 750,
    "Vitamine B1 ou Thiamine (mg 100 g)": 1.5,
    "Vitamine B2 ou Riboflavine (mg 100 g)": 1.6,
    "Vitamine B3 ou PP ou Niacine (mg 100 g)": 16,
    "Vitamine B5 ou Acide pantothénique (mg 100 g)": 5,
    "Vitamine B6 (mg 100 g)": 1.7,
    "Vitamine K1 (µg 100 g)": 79,
    "Vitamine E (mg 100 g)": 10.5,
}

# "Lower is better" — % > 100 should warn instead of celebrate.
LOWER_IS_BETTER: set[str] = {
    "Sel chlorure de sodium (g 100 g)",
    "AG saturés (g 100 g)",
    "Sucres (g 100 g)",
}

# Daily macros set rendered on the per-day breakdown.
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
