"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import * as api from "@/lib/api";
import type { IngredientDb } from "@/lib/types";

export default function IngredientsPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<IngredientDb[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<IngredientDb | null>(null);

  useEffect(() => {
    if (query.trim().length < 1) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const res = await api.searchIngredients(query, 25);
        if (!cancelled) setResults(res);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query]);

  async function view(ing: IngredientDb) {
    const full = await api.getIngredientDb(ing.id);
    setSelected(full);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Ingrédients</h1>
      <Input
        placeholder="Rechercher un ingrédient…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {loading && <p className="text-muted-foreground">Recherche…</p>}
      {!loading && query && results.length === 0 && (
        <p className="text-muted-foreground">Aucun résultat.</p>
      )}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {results.map((ing) => (
          <Card key={ing.id}>
            <CardContent className="space-y-2 p-4">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-medium leading-tight">{ing.name}</h3>
                {ing.has_nutrition_data ? (
                  <Badge variant="secondary">Données disponibles</Badge>
                ) : (
                  <Badge variant="outline">Sans données</Badge>
                )}
              </div>
              <Button size="sm" variant="outline" onClick={() => view(ing)}>
                Voir
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Dialog open={!!selected} onOpenChange={(v) => !v && setSelected(null)}>
        <DialogContent>
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle>{selected.name}</DialogTitle>
              </DialogHeader>
              {selected.nutrition_data ? (
                <pre className="max-h-[60vh] overflow-y-auto rounded-md bg-secondary p-3 text-xs">
                  {JSON.stringify(selected.nutrition_data, null, 2)}
                </pre>
              ) : (
                <p className="text-muted-foreground">Aucune donnée nutritionnelle.</p>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
