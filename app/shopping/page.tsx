"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import * as api from "@/lib/api";
import type { Recipe, ShoppingItem } from "@/lib/types";
import { CATEGORIES, type Category, categorize } from "@/lib/shopping-categories";
import { Label } from "@/components/ui/label";

export default function ShoppingPage() {
  const [items, setItems] = useState<ShoppingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getShoppingList();
      setItems(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const grouped = useMemo(() => {
    const map = new Map<Category, ShoppingItem[]>();
    for (const cat of CATEGORIES) map.set(cat, []);
    for (const it of items) map.get(categorize(it.name))!.push(it);
    for (const arr of map.values()) {
      arr.sort((a, b) => Number(a.is_checked) - Number(b.is_checked));
    }
    return map;
  }, [items]);

  async function toggle(item: ShoppingItem) {
    const updated = await api.updateShoppingItem(item.item_id, {
      is_checked: !item.is_checked,
    });
    setItems((xs) => xs.map((x) => (x.item_id === item.item_id ? updated : x)));
  }

  async function remove(item: ShoppingItem) {
    await api.deleteShoppingItem(item.item_id);
    setItems((xs) => xs.filter((x) => x.item_id !== item.item_id));
  }

  async function clearAll() {
    if (!confirm("Vider toute la liste de courses ?")) return;
    await api.clearShoppingList();
    setItems([]);
  }

  function onAdded(item: ShoppingItem) {
    setItems((xs) => [item, ...xs]);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Liste de courses</h1>
        {items.length > 0 && (
          <Button variant="outline" onClick={clearAll}>
            Vider la liste
          </Button>
        )}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <AddRecipeBlock onAdded={load} />
        <AddManualBlock onAdded={onAdded} />
      </div>

      {error && <p className="text-destructive">{error}</p>}
      {loading && <p className="text-muted-foreground">Chargement…</p>}
      {!loading && items.length === 0 && (
        <p className="text-muted-foreground">La liste est vide.</p>
      )}

      <div className="space-y-4">
        {CATEGORIES.map((cat) => {
          const arr = grouped.get(cat) || [];
          if (arr.length === 0) return null;
          return (
            <section key={cat}>
              <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {cat}
              </h3>
              <ul className="divide-y rounded-md border">
                {arr.map((it) => (
                  <li
                    key={it.item_id}
                    className="flex items-center gap-3 px-4 py-2"
                  >
                    <input
                      type="checkbox"
                      checked={it.is_checked}
                      onChange={() => toggle(it)}
                      className="h-4 w-4"
                    />
                    <div className={"flex-1 " + (it.is_checked ? "line-through text-muted-foreground" : "")}>
                      <div className="font-medium">{it.name}</div>
                      <div className="text-xs text-muted-foreground">
                        {it.quantity} {it.source && `· ${it.source}`}
                      </div>
                    </div>
                    <Button size="icon" variant="ghost" onClick={() => remove(it)} aria-label="Supprimer">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </li>
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function AddRecipeBlock({ onAdded }: { onAdded: () => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Recipe[]>([]);
  const [selected, setSelected] = useState<Recipe | null>(null);
  const [servings, setServings] = useState(2);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const res = await api.listRecipes({ search: query, limit: 10 });
        if (!cancelled) setResults(res.recipes);
      } catch {
        /* ignore */
      }
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query]);

  async function add() {
    if (!selected) return;
    setBusy(true);
    try {
      const ratio = servings / Math.max(1, selected.servings);
      for (const ing of selected.ingredients) {
        const qty = ing.quantity ? Math.round(ing.quantity * ratio * 100) / 100 : 0;
        await api.addShoppingItem({
          name: ing.name,
          quantity: qty ? `${qty} ${ing.unit}` : ing.unit,
          source: selected.name,
          is_checked: false,
        });
      }
      setSelected(null);
      setQuery("");
      setResults([]);
      onAdded();
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <Label>Ajouter une recette</Label>
        <Input
          placeholder="Rechercher une recette…"
          value={selected ? selected.name : query}
          onChange={(e) => {
            setSelected(null);
            setQuery(e.target.value);
          }}
        />
        {!selected && results.length > 0 && (
          <ul className="rounded-md border bg-card">
            {results.map((r) => (
              <li
                key={r.recipe_id}
                className="cursor-pointer px-3 py-2 text-sm hover:bg-accent"
                onClick={() => {
                  setSelected(r);
                  setServings(r.servings);
                  setResults([]);
                }}
              >
                {r.name}
              </li>
            ))}
          </ul>
        )}
        {selected && (
          <div className="flex items-center gap-2">
            <Label>Portions:</Label>
            <Input
              type="number"
              min={1}
              value={servings}
              onChange={(e) => setServings(Number(e.target.value))}
              className="w-24"
            />
            <Button onClick={add} disabled={busy}>
              <Plus className="h-4 w-4" /> Ajouter
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function AddManualBlock({ onAdded }: { onAdded: (it: ShoppingItem) => void }) {
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [busy, setBusy] = useState(false);

  async function add() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      const it = await api.addShoppingItem({
        name: name.trim(),
        quantity: quantity.trim(),
        source: "Ajouté manuellement",
        is_checked: false,
      });
      onAdded(it);
      setName("");
      setQuantity("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardContent className="space-y-3 p-4">
        <Label>Ajouter manuellement</Label>
        <Input placeholder="Nom" value={name} onChange={(e) => setName(e.target.value)} />
        <div className="flex gap-2">
          <Input
            placeholder="Quantité (ex: 500g)"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
          <Button onClick={add} disabled={busy || !name.trim()}>
            <Plus className="h-4 w-4" /> Ajouter
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
