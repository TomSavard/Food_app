"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Star, Users, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import * as api from "@/lib/api";
import type { Recipe } from "@/lib/types";
import { RecipeFormDialog } from "@/components/recipe-form-dialog";
import { RecipeDetailDialog } from "@/components/recipe-detail-dialog";

type CategoryFilter = "all" | "plat" | "dessert" | "entrée";

// Fixed sections: entrée, plat, dessert, sauce, autres
const SECTIONS = ["Entrée", "Plat", "Dessert", "Sauce", "Autres"] as const;

const SECTION_META: Record<string, React.ReactNode> = {
  Entrée: <span className="text-lg">🥗</span>,
  Plat: <span className="text-lg">🍽️</span>,
  Dessert: <span className="text-lg">🍰</span>,
  Sauce: <span className="text-lg">🫕</span>,
  Autres: <span className="text-lg">📁</span>,
};

function classifyRecipe(recipe: Recipe): string {
  const tags = (recipe.tags || []).map((t) =>
    t.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "")
  );
  if (tags.some((t) => t.startsWith("entr"))) return "Entrée";
  if (tags.some((t) => t.startsWith("plat"))) return "Plat";
  if (tags.some((t) => t.startsWith("dessert"))) return "Dessert";
  if (tags.some((t) => t.startsWith("sauce"))) return "Sauce";
  return "Autres";
}

function useDebounced<T>(value: T, delay = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

// ---------------------------------------------------------------------------
// Grouped recipe list (CookBooker-inspired)
// ---------------------------------------------------------------------------

function CategoryGroup({
  category,
  recipes: grouped,
  onOpen,
  onToggleFavorite,
  onAdd,
}: {
  category: string;
  recipes: Recipe[];
  onOpen: (id: string) => void;
  onToggleFavorite: (r: Recipe) => void;
  onAdd?: () => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const meta = SECTION_META[category] ?? SECTION_META["Autres"];

  return (
    <div className="rounded-lg border border-border/50 bg-card overflow-hidden">
      <div
        className="flex w-full cursor-pointer items-center gap-3 px-4 py-2.5 text-left hover:bg-accent/50 transition-colors"
        onClick={() => setCollapsed((c) => !c)}
      >
        <ChevronDown
          className={`h-4 w-4 shrink-0 transition-transform ${collapsed ? "" : "rotate-180"}`}
        />
        {meta}
        <span className="font-semibold text-sm">{category}</span>
        <span className="ml-auto text-xs text-muted-foreground tabular-nums">{grouped.length}</span>
      </div>

      {!collapsed && (
        <div className="divide-y divide-border/50">
          {grouped.map((r) => (
            <RecipeRow
              key={r.recipe_id}
              recipe={r}
              onOpen={onOpen}
              onToggleFavorite={onToggleFavorite}
            />
          ))}
          {onAdd && (
            <div
              className="flex w-full cursor-pointer items-center gap-3 px-4 py-2.5 text-left text-muted-foreground hover:bg-accent/50 transition-colors"
              onClick={onAdd}
            >
              <Plus className="h-4 w-4" />
              <span className="text-sm">Nouvelle recette</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RecipeRow({
  recipe,
  onOpen,
  onToggleFavorite,
}: {
  recipe: Recipe;
  onOpen: (id: string) => void;
  onToggleFavorite: (r: Recipe) => void;
}) {
  return (
    <div
      className={`flex w-full cursor-pointer items-center gap-3 px-4 py-2.5 text-left hover:bg-accent/50 transition-colors ${recipe.is_favorite ? "bg-yellow-50/10" : ""}`}
      onClick={() => onOpen(recipe.recipe_id)}
    >
      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-md bg-secondary/60 text-xs text-muted-foreground overflow-hidden">
        {recipe.image_url ? (
          <img src={recipe.image_url} alt={recipe.name} className="h-full w-full object-cover" />
        ) : (
          <span>{recipe.name.charAt(0).toUpperCase()}</span>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium">{recipe.name}</div>
      </div>

      <button
        className="shrink-0"
        onClick={(e) => {
          e.stopPropagation();
          onToggleFavorite(recipe);
        }}
        aria-label={recipe.is_favorite ? "Retirer des favoris" : "Ajouter aux favoris"}
      >
        <Star className={`h-4 w-4 ${recipe.is_favorite ? "fill-yellow-400 text-yellow-400" : "text-muted-foreground/50"}`} />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Full-page search/filter bar (collapsible)
// ---------------------------------------------------------------------------

function FilterBar({
  search,
  setSearch,
  ingredient,
  setIngredient,
  cuisine,
  setCuisine,
  tag,
  setTag,
}: {
  search: string;
  setSearch: (v: string) => void;
  ingredient: string;
  setIngredient: (v: string) => void;
  cuisine: string;
  setCuisine: (v: string) => void;
  tag: string;
  setTag: (v: string) => void;
}) {
  return (
    <div className="space-y-3 rounded-lg border border-border/50 bg-card p-4">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Input
          placeholder="Rechercher une recette…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Input
          placeholder="Ingrédient (ex: poulet)…"
          value={ingredient}
          onChange={(e) => setIngredient(e.target.value)}
        />
        <Input
          placeholder="Type de cuisine"
          value={cuisine}
          onChange={(e) => setCuisine(e.target.value)}
        />
        <Input placeholder="Tag" value={tag} onChange={(e) => setTag(e.target.value)} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function RecipesPage() {
  const [search, setSearch] = useState("");
  const [ingredient, setIngredient] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [tag, setTag] = useState("");
  const [category, setCategory] = useState<CategoryFilter>("all");
  const [showFilters, setShowFilters] = useState(false);

  const dSearch = useDebounced(search);
  const dIngredient = useDebounced(ingredient);
  const dCuisine = useDebounced(cuisine);
  const dTag = useDebounced(tag);

  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [detailId, setDetailId] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Recipe | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.listRecipes({
        search: dSearch || undefined,
        ingredient: dIngredient || undefined,
        cuisine: dCuisine || undefined,
        tag: dTag || undefined,
        limit: 200,
      });
      setRecipes(res.recipes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, [dSearch, dIngredient, dCuisine, dTag]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    let list = recipes;
    if (category !== "all") {
      list = list.filter((r) => (r.tags || []).map((t) => t.toLowerCase()).includes(category));
    }
    return list;
  }, [recipes, category]);

  // Group recipes into fixed sections
  const groups = useMemo(() => {
    const map = new Map<string, Recipe[]>();
    for (const s of SECTIONS) map.set(s, []);
    for (const r of filtered) {
      const section = classifyRecipe(r);
      map.get(section)!.push(r);
    }
    return map;
  }, [filtered]);

  async function onToggleFavorite(r: Recipe) {
    try {
      const updated = await api.toggleFavorite(r.recipe_id, !r.is_favorite);
      setRecipes((rs) => rs.map((x) => (x.recipe_id === r.recipe_id ? updated : x)));
    } catch (e) {
      console.error(e);
    }
  }

  async function onDelete(r: Recipe) {
    if (!confirm(`Supprimer "${r.name}" ?`)) return;
    await api.deleteRecipe(r.recipe_id);
    setRecipes((rs) => rs.filter((x) => x.recipe_id !== r.recipe_id));
    setDetailId(null);
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Mes recettes</h1>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={() => setShowFilters((f) => !f)}>
            {showFilters ? "Masquer filtres" : "Filtres"}
          </Button>
          <Button
            onClick={() => {
              setEditing(null);
              setFormOpen(true);
            }}
          >
            <Plus className="h-4 w-4" /> Ajouter
          </Button>
        </div>
      </div>

      {/* Category filter pills */}
      <div className="flex flex-wrap gap-2">
        {["all", "entrée", "plat", "dessert"].map((k) => (
          <Button
            key={k}
            size="sm"
            variant={category === k ? "default" : "outline"}
            onClick={() => setCategory(k as CategoryFilter)}
          >
            {k === "all" ? "Toutes" : k.charAt(0).toUpperCase() + k.slice(1)}
          </Button>
        ))}
      </div>

      {showFilters && (
        <FilterBar
          search={search}
          setSearch={setSearch}
          ingredient={ingredient}
          setIngredient={setIngredient}
          cuisine={cuisine}
          setCuisine={setCuisine}
          tag={tag}
          setTag={setTag}
        />
      )}

      {error && <p className="text-destructive">{error}</p>}
      {loading && <p className="text-muted-foreground">Chargement…</p>}
      {!loading && filtered.length === 0 && (
        <p className="text-muted-foreground">Aucune recette.</p>
      )}

      {/* Category groups */}
      <div className="space-y-3">
        {SECTIONS.map((section) => {
          const recs = groups.get(section) ?? [];
          if (recs.length === 0) return null;
          return (
            <CategoryGroup
              key={section}
              category={section}
              recipes={recs}
              onOpen={(id) => setDetailId(id)}
              onToggleFavorite={onToggleFavorite}
            />
          );
        })}
      </div>

      <RecipeDetailDialog
        recipeId={detailId}
        onClose={() => setDetailId(null)}
        onEdit={(r) => {
          setEditing(r);
          setDetailId(null);
          setFormOpen(true);
        }}
        onDelete={onDelete}
      />

      <RecipeFormDialog
        open={formOpen}
        onOpenChange={setFormOpen}
        editing={editing}
        onSaved={(r) => {
          setRecipes((rs) => {
            const idx = rs.findIndex((x) => x.recipe_id === r.recipe_id);
            return idx >= 0 ? rs.map((x, i) => (i === idx ? r : x)) : [r, ...rs];
          });
        }}
      />
    </div>
  );
}

