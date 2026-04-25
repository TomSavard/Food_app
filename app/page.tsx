"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Star, StarOff, Clock, Flame, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import * as api from "@/lib/api";
import type { Recipe } from "@/lib/types";
import { RecipeFormDialog } from "@/components/recipe-form-dialog";
import { RecipeDetailDialog } from "@/components/recipe-detail-dialog";

type CategoryFilter = "all" | "plat" | "dessert" | "entrée";

function useDebounced<T>(value: T, delay = 300): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
}

export default function RecipesPage() {
  const [search, setSearch] = useState("");
  const [ingredient, setIngredient] = useState("");
  const [cuisine, setCuisine] = useState("");
  const [tag, setTag] = useState("");
  const [category, setCategory] = useState<CategoryFilter>("all");

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
    if (category === "all") return recipes;
    return recipes.filter((r) => (r.tags || []).map((t) => t.toLowerCase()).includes(category));
  }, [recipes, category]);

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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Mes recettes</h1>
        <Button
          onClick={() => {
            setEditing(null);
            setFormOpen(true);
          }}
        >
          <Plus className="h-4 w-4" /> Ajouter
        </Button>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Input
          placeholder="Rechercher une recette…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <Input
          placeholder="Rechercher par ingrédient (ex: poulet)…"
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

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["all", "Toutes"],
            ["plat", "Plats"],
            ["dessert", "Desserts"],
            ["entrée", "Entrées"],
          ] as [CategoryFilter, string][]
        ).map(([k, label]) => (
          <Button
            key={k}
            size="sm"
            variant={category === k ? "default" : "outline"}
            onClick={() => setCategory(k)}
          >
            {label}
          </Button>
        ))}
      </div>

      {error && <p className="text-destructive">{error}</p>}
      {loading && <p className="text-muted-foreground">Chargement…</p>}
      {!loading && filtered.length === 0 && (
        <p className="text-muted-foreground">Aucune recette.</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((r) => (
          <Card
            key={r.recipe_id}
            className={"surface-interactive " + (r.is_favorite ? "ring-1 ring-primary/40" : "")}
            onClick={() => setDetailId(r.recipe_id)}
          >
            <CardContent className="p-5 space-y-3">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-semibold leading-tight">{r.name}</h3>
                <button
                  className="shrink-0"
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggleFavorite(r);
                  }}
                  aria-label={r.is_favorite ? "Retirer des favoris" : "Ajouter aux favoris"}
                >
                  {r.is_favorite ? (
                    <Star className="h-5 w-5 fill-yellow-400 text-yellow-400" />
                  ) : (
                    <StarOff className="h-5 w-5 text-muted-foreground" />
                  )}
                </button>
              </div>
              {r.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">{r.description}</p>
              )}
              <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
                {r.prep_time > 0 && (
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" /> {r.prep_time} min
                  </span>
                )}
                {r.cook_time > 0 && (
                  <span className="inline-flex items-center gap-1">
                    <Flame className="h-3.5 w-3.5" /> {r.cook_time} min
                  </span>
                )}
                <span className="inline-flex items-center gap-1">
                  <Users className="h-3.5 w-3.5" /> {r.servings}
                </span>
              </div>
              {r.tags && r.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {r.tags.slice(0, 3).map((t) => (
                    <Badge key={t} variant="secondary">
                      {t}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
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

