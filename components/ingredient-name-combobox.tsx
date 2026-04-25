"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Plus } from "lucide-react";
import { Input } from "@/components/ui/input";
import * as api from "@/lib/api";
import type { IngredientDb } from "@/lib/types";

/**
 * Name input with live autocomplete against /api/ingredients/search.
 *
 * - Typing fires a debounced search (matches canonical name + aliases).
 * - Picking a result writes the canonical name and stores its FK in the form.
 * - "Créer « X »" creates a new ingredient_database row when nothing fits.
 * - Manually editing the name after a link clears the FK (force a re-pick).
 */
export function IngredientNameCombobox({
  name,
  ingredient_db_id,
  onChange,
  placeholder,
  className,
}: {
  name: string;
  ingredient_db_id: string | null | undefined;
  onChange: (name: string, ingredient_db_id: string | null) => void;
  placeholder?: string;
  className?: string;
}) {
  const [query, setQuery] = useState(name);
  const [results, setResults] = useState<IngredientDb[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const wrapRef = useRef<HTMLDivElement | null>(null);

  // Sync external name prop into local input.
  useEffect(() => {
    setQuery(name);
  }, [name]);

  // Debounced search.
  useEffect(() => {
    if (!open) return;
    const q = query.trim();
    if (q.length < 1) {
      setResults([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const res = await api.searchIngredients(q, 8);
        if (!cancelled) setResults(res);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 150);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query, open]);

  // Close on click outside.
  useEffect(() => {
    function onDoc(e: MouseEvent) {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  function pick(r: IngredientDb) {
    onChange(r.name, r.id);
    setQuery(r.name);
    setOpen(false);
  }

  async function createNew() {
    const q = query.trim();
    if (!q) return;
    setCreating(true);
    try {
      const row = await api.createIngredient(q);
      onChange(row.name, row.id);
      setQuery(row.name);
      setOpen(false);
    } finally {
      setCreating(false);
    }
  }

  const exactExists = results.some(
    (r) => r.name.trim().toLowerCase() === query.trim().toLowerCase()
  );

  return (
    <div ref={wrapRef} className={"relative " + (className || "")}>
      <Input
        placeholder={placeholder || "Nom"}
        value={query}
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          const v = e.target.value;
          setQuery(v);
          // Editing after a link drops the link.
          onChange(v, null);
          setOpen(true);
        }}
      />
      {ingredient_db_id && query.trim() === name && (
        <Check className="pointer-events-none absolute right-2 top-1/2 h-4 w-4 -translate-y-1/2 text-emerald-500" />
      )}
      {open && query.trim().length > 0 && (
        <div className="absolute z-20 mt-1 w-full rounded-md border bg-popover shadow-lg">
          {loading && (
            <div className="px-3 py-2 text-xs text-muted-foreground">
              Recherche…
            </div>
          )}
          {!loading && results.length === 0 && (
            <div className="px-3 py-2 text-xs text-muted-foreground">
              Aucun résultat.
            </div>
          )}
          {results.map((r) => (
            <button
              key={r.id}
              type="button"
              onClick={() => pick(r)}
              className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-accent"
            >
              <span className="truncate">{r.name}</span>
              {!r.has_nutrition_data && (
                <span className="text-xs text-muted-foreground">sans données</span>
              )}
            </button>
          ))}
          {!exactExists && query.trim().length >= 2 && (
            <button
              type="button"
              onClick={createNew}
              disabled={creating}
              className="flex w-full items-center gap-2 border-t px-3 py-2 text-left text-sm text-muted-foreground hover:bg-accent"
            >
              <Plus className="h-3 w-3" />
              Créer « {query.trim()} »
            </button>
          )}
        </div>
      )}
    </div>
  );
}
