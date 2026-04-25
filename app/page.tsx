"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Star, StarOff, Pencil, Trash2, Clock, Flame, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import * as api from "@/lib/api";
import type { Recipe, RecipeNutrition, IngredientDb } from "@/lib/types";
import { RecipeFormDialog } from "@/components/recipe-form-dialog";

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
            className={
              "cursor-pointer transition-colors hover:border-primary/60 " +
              (r.is_favorite ? "border-primary/50" : "")
            }
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

function RecipeDetailDialog({
  recipeId,
  onClose,
  onEdit,
  onDelete,
}: {
  recipeId: string | null;
  onClose: () => void;
  onEdit: (r: Recipe) => void;
  onDelete: (r: Recipe) => void;
}) {
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [nutrition, setNutrition] = useState<RecipeNutrition | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!recipeId) {
      setRecipe(null);
      setNutrition(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    Promise.all([api.getRecipe(recipeId), api.getRecipeNutrition(recipeId).catch(() => null)])
      .then(([r, n]) => {
        if (cancelled) return;
        setRecipe(r);
        setNutrition(n);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [recipeId]);

  return (
    <Dialog open={!!recipeId} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        {loading && <p className="text-muted-foreground">Chargement…</p>}
        {recipe && (
          <>
            <DialogHeader>
              <div className="flex items-start justify-between gap-3 pr-8">
                <DialogTitle>{recipe.name}</DialogTitle>
                <div className="flex gap-1">
                  <Button size="icon" variant="ghost" onClick={() => onEdit(recipe)} aria-label="Modifier">
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button size="icon" variant="ghost" onClick={() => onDelete(recipe)} aria-label="Supprimer">
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </DialogHeader>

            {recipe.description && <p className="text-sm whitespace-pre-wrap">{recipe.description}</p>}

            <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
              {recipe.prep_time > 0 && <span>⏱ {recipe.prep_time} min</span>}
              {recipe.cook_time > 0 && <span>🔥 {recipe.cook_time} min</span>}
              <span>👥 {recipe.servings}</span>
              {recipe.cuisine_type && <span>🍽 {recipe.cuisine_type}</span>}
            </div>

            {recipe.tags?.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {recipe.tags.map((t) => (
                  <Badge key={t} variant="secondary">{t}</Badge>
                ))}
              </div>
            )}

            {nutrition && (
              <section className="space-y-2 rounded-md border bg-card p-4">
                <h4 className="font-semibold">Nutrition</h4>
                <NutritionGrid label="Total" data={nutrition} totalKey="total" />
                <NutritionGrid label={`Par portion (${nutrition.servings})`} data={nutrition} totalKey="per_serving" />
              </section>
            )}

            {recipe.ingredients?.length > 0 && (
              <section className="space-y-1">
                <h4 className="font-semibold">Ingrédients</h4>
                <ul className="list-disc pl-5 text-sm space-y-0.5">
                  {recipe.ingredients.map((i, idx) => (
                    <li key={i.ingredient_id || idx}>
                      {i.quantity ? `${i.quantity} ${i.unit} ` : ""}
                      {i.name}
                      {i.notes ? ` (${i.notes})` : ""}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {recipe.instructions?.length > 0 && (
              <section className="space-y-1">
                <h4 className="font-semibold">Instructions</h4>
                <ol className="list-decimal pl-5 text-sm space-y-1">
                  {recipe.instructions.map((s, idx) => (
                    <li key={s.instruction_id || idx} className="whitespace-pre-wrap">
                      {s.instruction_text}
                    </li>
                  ))}
                </ol>
              </section>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function NutritionGrid({
  label,
  data,
  totalKey,
}: {
  label: string;
  data: RecipeNutrition;
  totalKey: "total" | "per_serving";
}) {
  const v = totalKey === "per_serving" ? data.per_serving : data;
  return (
    <div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className="mt-1 grid grid-cols-4 gap-2 text-sm">
        <Stat n="kcal" v={Math.round(v.calories)} />
        <Stat n="protéines" v={Math.round(v.proteins)} u="g" />
        <Stat n="lipides" v={Math.round(v.lipides)} u="g" />
        <Stat n="glucides" v={Math.round(v.glucides)} u="g" />
      </div>
    </div>
  );
}

function Stat({ n, v, u }: { n: string; v: number; u?: string }) {
  return (
    <div className="rounded bg-secondary p-2 text-center">
      <div className="font-semibold">
        {v}
        {u || ""}
      </div>
      <div className="text-xs text-muted-foreground">{n}</div>
    </div>
  );
}
