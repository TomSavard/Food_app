"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import * as api from "@/lib/api";
import type { Recipe } from "@/lib/types";

export function RecipePickerDialog({
  open,
  onOpenChange,
  onPick,
  title = "Choisir une recette",
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  onPick: (recipe: Recipe) => void;
  title?: string;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setResults([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const res = await api.listRecipes({ search: query || undefined, limit: 30 });
        if (!cancelled) setResults(res.recipes);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 200);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [open, query]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <Input
          autoFocus
          placeholder="Rechercher…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="max-h-[60vh] space-y-1 overflow-y-auto">
          {loading && <p className="text-sm text-muted-foreground">Chargement…</p>}
          {!loading && results.length === 0 && (
            <p className="text-sm text-muted-foreground">Aucune recette.</p>
          )}
          {results.map((r) => (
            <Button
              key={r.recipe_id}
              variant="ghost"
              className="h-auto w-full justify-start py-2 text-left"
              onClick={() => {
                onPick(r);
                onOpenChange(false);
              }}
            >
              <div className="flex-1">
                <div className="font-medium">{r.name}</div>
                {r.cuisine_type && (
                  <div className="text-xs text-muted-foreground">{r.cuisine_type}</div>
                )}
              </div>
            </Button>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
