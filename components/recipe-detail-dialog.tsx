"use client";

import { useEffect, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import * as api from "@/lib/api";
import type { Recipe, RecipeNutrition } from "@/lib/types";

export function RecipeDetailDialog({
  recipeId,
  onClose,
  onEdit,
  onDelete,
}: {
  recipeId: string | null;
  onClose: () => void;
  onEdit?: (r: Recipe) => void;
  onDelete?: (r: Recipe) => void;
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
    Promise.all([
      api.getRecipe(recipeId),
      api.getRecipeNutrition(recipeId).catch(() => null),
    ])
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
                {(onEdit || onDelete) && (
                  <div className="flex gap-1">
                    {onEdit && (
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => onEdit(recipe)}
                        aria-label="Modifier"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                    )}
                    {onDelete && (
                      <Button
                        size="icon"
                        variant="ghost"
                        onClick={() => onDelete(recipe)}
                        aria-label="Supprimer"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </DialogHeader>

            {recipe.description && (
              <p className="text-sm whitespace-pre-wrap">{recipe.description}</p>
            )}

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
                <NutritionGrid
                  label={`Par portion (${nutrition.servings})`}
                  data={nutrition}
                  totalKey="per_serving"
                />
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
                    <li
                      key={s.instruction_id || idx}
                      className="whitespace-pre-wrap"
                    >
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
