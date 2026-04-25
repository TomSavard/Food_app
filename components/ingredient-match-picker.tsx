"use client";

import { useState } from "react";
import { Check, Link as LinkIcon, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import * as api from "@/lib/api";
import type { MatchCandidate } from "@/lib/types";

/**
 * Inline match status for one recipe ingredient.
 *
 * `name` is the free-text the user typed; `ingredient_db_id` is the
 * resolved FK (or null/undefined if unresolved). On "Lier" we hit the
 * /candidates endpoint and let the user confirm one of the top matches
 * (or create a brand-new row).
 */
export function IngredientMatchPicker({
  name,
  ingredient_db_id,
  onChange,
}: {
  name: string;
  ingredient_db_id: string | null | undefined;
  onChange: (id: string | null) => void;
}) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exact, setExact] = useState<{ id: string; name: string } | null>(null);
  const [candidates, setCandidates] = useState<MatchCandidate[]>([]);

  if (!name.trim()) return null;

  if (ingredient_db_id) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Check className="h-3 w-3 text-emerald-500" />
        Lié
        <button
          type="button"
          className="text-xs underline hover:text-foreground"
          onClick={() => onChange(null)}
        >
          délier
        </button>
      </div>
    );
  }

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getMatchCandidates(name);
      if (res.exact) {
        // Auto-link: same name (case-insensitive) or known alias.
        onChange(res.exact.id);
        return;
      }
      setExact(null);
      setCandidates(res.llm_candidates);
      setOpen(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }

  async function confirm(c: MatchCandidate) {
    setLoading(true);
    try {
      await api.confirmMatch(name, c.ingredient_db_id);
      onChange(c.ingredient_db_id);
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }

  async function createNew() {
    setLoading(true);
    try {
      const row = await api.createIngredient(name);
      onChange(row.id);
      setOpen(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {error ? (
          <span className="text-destructive">{error}</span>
        ) : (
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="inline-flex items-center gap-1 underline hover:text-foreground"
          >
            <LinkIcon className="h-3 w-3" />
            {loading ? "…" : "Lier à un ingrédient"}
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-md border bg-muted/40 p-2 text-xs space-y-1">
      <div className="flex items-center justify-between">
        <span className="font-medium">Choisir une correspondance pour « {name} »</span>
        <button type="button" onClick={() => setOpen(false)}>
          <X className="h-3 w-3" />
        </button>
      </div>
      {candidates.length === 0 && (
        <div className="text-muted-foreground">Aucun candidat trouvé.</div>
      )}
      {candidates.map((c) => (
        <button
          key={c.ingredient_db_id}
          type="button"
          disabled={loading}
          onClick={() => confirm(c)}
          className="flex w-full items-start gap-2 rounded px-2 py-1 text-left hover:bg-accent"
        >
          <span className="font-medium">{c.name}</span>
          <span className="ml-auto text-muted-foreground">
            {Math.round(c.confidence * 100)}%
          </span>
        </button>
      ))}
      <Button
        type="button"
        size="sm"
        variant="outline"
        disabled={loading}
        onClick={createNew}
        className="w-full"
      >
        <Sparkles className="h-3 w-3" /> Créer un nouvel ingrédient « {name} »
      </Button>
    </div>
  );
}
