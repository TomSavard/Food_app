// Categorize a shopping-list item name into one of the 8 buckets.
// Ported from the previous frontend's heuristic regex matching.

export const CATEGORIES = [
  "Fruits & Légumes",
  "Viandes & Poissons",
  "Produits Laitiers",
  "Épicerie",
  "Épices & Herbes",
  "Boissons",
  "Sucreries",
  "Autres",
] as const;
export type Category = (typeof CATEGORIES)[number];

const PATTERNS: { cat: Category; words: string[] }[] = [
  {
    cat: "Fruits & Légumes",
    words: [
      "tomate", "carotte", "oignon", "ail", "pomme", "banane", "orange", "citron",
      "salade", "épinard", "poireau", "courgette", "aubergine", "poivron", "concombre",
      "radis", "betterave", "chou", "brocoli", "céleri", "fenouil", "navet", "patate",
      "champignon", "fraise", "framboise", "myrtille", "kiwi", "raisin", "mangue",
      "ananas", "pêche", "abricot", "prune", "cerise", "melon", "pastèque", "avocat",
      "courge", "haricot", "petit pois", "radis", "endive", "artichaut", "asperge",
    ],
  },
  {
    cat: "Viandes & Poissons",
    words: [
      "poulet", "boeuf", "veau", "porc", "agneau", "dinde", "canard", "saumon", "thon",
      "merlu", "cabillaud", "sardine", "crevette", "moule", "poisson", "viande", "lardon",
      "jambon", "saucisse", "rôti", "steak", "escalope",
    ],
  },
  {
    cat: "Produits Laitiers",
    words: [
      "lait", "yaourt", "fromage", "beurre", "crème", "mascarpone", "ricotta", "feta",
      "mozzarella", "parmesan", "comté", "gruyère", "chèvre", "camembert", "brie",
    ],
  },
  {
    cat: "Épicerie",
    words: [
      "pâtes", "riz", "farine", "huile", "vinaigre", "sucre", "sel", "œuf", "oeuf",
      "lentille", "pois chiche", "haricot sec", "quinoa", "boulgour", "couscous",
      "céréales", "biscotte", "pain", "thon en boîte", "tomate concassée", "moutarde",
      "ketchup", "mayonnaise", "sauce soja",
    ],
  },
  {
    cat: "Épices & Herbes",
    words: [
      "poivre", "curry", "paprika", "cumin", "cannelle", "muscade", "thym", "romarin",
      "basilic", "persil", "coriandre", "menthe", "laurier", "estragon", "ciboulette",
      "origan", "safran", "gingembre",
    ],
  },
  {
    cat: "Boissons",
    words: ["vin", "bière", "jus", "eau", "café", "thé", "tisane", "soda", "limonade"],
  },
  {
    cat: "Sucreries",
    words: ["chocolat", "miel", "confiture", "sirop", "biscuit", "gâteau", "bonbon"],
  },
];

export function categorize(name: string): Category {
  const n = name.toLowerCase();
  for (const { cat, words } of PATTERNS) {
    if (words.some((w) => n.includes(w))) return cat;
  }
  return "Autres";
}
