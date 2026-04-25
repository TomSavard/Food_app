"use client";

import { useEffect, useMemo, useState } from "react";
import { Sparkles, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import * as api from "@/lib/api";
import { SHOPPING_CATEGORIES, type ShoppingCategory } from "@/lib/types";
import type { IngredientDetail, IngredientRow } from "@/lib/types";

type Filters = {
  search: string;
  category: ShoppingCategory | "";
  missing: boolean;
  missing_density: boolean;
  modified: boolean;
  source: "" | "ciqual" | "user" | "llm";
};

const NUTRIENT_GROUPS: { title: string; prefix?: string; keys?: string[] }[] = [
  {
    title: "Macros",
    keys: [
      "Energie, Règlement UE N° 1169 2011 (kcal 100 g)",
      "Protéines, N x facteur de Jones (g 100 g)",
      "Lipides (g 100 g)",
      "Glucides (g 100 g)",
      "Sel chlorure de sodium (g 100 g)",
      "AG saturés (g 100 g)",
      "Fibres alimentaires (g 100 g)",
      "Sucres (g 100 g)",
    ],
  },
  { title: "Acides gras", prefix: "AG " },
  {
    title: "Minéraux",
    keys: [
      "Calcium (mg 100 g)",
      "Fer (mg 100 g)",
      "Magnésium (mg 100 g)",
      "Phosphore (mg 100 g)",
      "Potassium (mg 100 g)",
      "Sodium (mg 100 g)",
      "Zinc (mg 100 g)",
      "Iode (µg 100 g)",
      "Sélénium (µg 100 g)",
      "Cuivre (mg 100 g)",
      "Manganèse (mg 100 g)",
      "Chlorure (mg 100 g)",
    ],
  },
  { title: "Vitamines", prefix: "Vitamine " },
];

function valueLabel(v: number | string | null | undefined): string {
  if (v === null || v === undefined || v === "") return "—";
  return String(v);
}

export default function IngredientsPage() {
  const [filters, setFilters] = useState<Filters>({
    search: "",
    category: "",
    missing: false,
    missing_density: false,
    modified: false,
    source: "",
  });
  const [items, setItems] = useState<IngredientRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await api.listIngredients({
          search: filters.search || undefined,
          category: filters.category || undefined,
          missing: filters.missing || undefined,
          missing_density: filters.missing_density || undefined,
          modified: filters.modified || undefined,
          source: filters.source || undefined,
          limit: 50,
        });
        if (cancelled) return;
        setItems(res.items);
        setTotal(res.total);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [filters]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Ingrédients</h1>
        <p className="text-sm text-muted-foreground">
          Base CIQUAL + ingrédients personnels. {total} résultats.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Input
          placeholder="Rechercher (nom ou alias)…"
          value={filters.search}
          onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
          className="max-w-sm"
        />
        <select
          className="rounded-md border border-input bg-background px-2 text-sm"
          value={filters.category}
          onChange={(e) =>
            setFilters((f) => ({ ...f, category: e.target.value as Filters["category"] }))
          }
        >
          <option value="">Toutes catégories</option>
          {SHOPPING_CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          className="rounded-md border border-input bg-background px-2 text-sm"
          value={filters.source}
          onChange={(e) =>
            setFilters((f) => ({ ...f, source: e.target.value as Filters["source"] }))
          }
        >
          <option value="">Toutes sources</option>
          <option value="ciqual">CIQUAL</option>
          <option value="user">Utilisateur</option>
          <option value="llm">IA</option>
        </select>
        <FilterPill
          label="Manque des nutriments"
          on={filters.missing}
          toggle={() => setFilters((f) => ({ ...f, missing: !f.missing }))}
        />
        <FilterPill
          label="Manque la densité"
          on={filters.missing_density}
          toggle={() =>
            setFilters((f) => ({ ...f, missing_density: !f.missing_density }))
          }
        />
        <FilterPill
          label="Modifié"
          on={filters.modified}
          toggle={() => setFilters((f) => ({ ...f, modified: !f.modified }))}
        />
      </div>

      {loading && <p className="text-sm text-muted-foreground">Chargement…</p>}

      <div className="overflow-hidden rounded-md border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-3 py-2 text-left">Nom</th>
              <th className="px-3 py-2 text-left">Catégorie</th>
              <th className="px-3 py-2 text-left">Source</th>
              <th className="px-3 py-2 text-left">Modifié</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {items.map((it) => (
              <tr key={it.id} className="border-t hover:bg-muted/30">
                <td className="px-3 py-2">
                  <div>{it.name}</div>
                  {it.aliases.length > 0 && (
                    <div className="mt-1 flex flex-wrap gap-1">
                      {it.aliases.map((a) => (
                        <Badge key={a.alias_id} variant="outline" className="text-xs">
                          {a.alias_text}
                        </Badge>
                      ))}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2 text-muted-foreground">
                  {it.category || "—"}
                </td>
                <td className="px-3 py-2">
                  <Badge variant={it.source === "ciqual" ? "secondary" : "default"}>
                    {it.source}
                  </Badge>
                </td>
                <td className="px-3 py-2 text-muted-foreground">
                  {it.modified ? (
                    <span title={it.modified_at || undefined}>
                      par {it.modified_by}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-3 py-2 text-right">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setSelectedId(it.id)}
                  >
                    Détails
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <DetailDialog
        id={selectedId}
        onClose={() => setSelectedId(null)}
        onUpdated={() => {
          // Refresh list after edit.
          setFilters((f) => ({ ...f }));
        }}
      />
    </div>
  );
}

function FilterPill({
  label,
  on,
  toggle,
}: {
  label: string;
  on: boolean;
  toggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={toggle}
      className={
        "rounded-full border px-3 py-1 text-xs transition " +
        (on
          ? "border-primary bg-primary text-primary-foreground"
          : "border-input bg-background text-foreground hover:bg-accent")
      }
    >
      {label}
    </button>
  );
}

function DetailDialog({
  id,
  onClose,
  onUpdated,
}: {
  id: string | null;
  onClose: () => void;
  onUpdated: () => void;
}) {
  const [detail, setDetail] = useState<IngredientDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [proposal, setProposal] = useState<Record<string, number | string | null> | null>(
    null
  );
  const [proposedDensity, setProposedDensity] = useState<{ value: number; reason: string } | null>(null);
  const [aliasInput, setAliasInput] = useState("");

  useEffect(() => {
    if (!id) {
      setDetail(null);
      setProposal(null);
      setProposedDensity(null);
      setAliasInput("");
      return;
    }
    setLoading(true);
    api.getIngredientDetail(id).then((d) => {
      setDetail(d);
      setLoading(false);
    });
  }, [id]);

  async function patch(data: Parameters<typeof api.updateIngredient>[1]) {
    if (!detail) return;
    const updated = await api.updateIngredient(detail.id, data);
    setDetail(updated);
    onUpdated();
  }

  async function fillWithAi() {
    if (!detail) return;
    setLoading(true);
    try {
      const res = await api.llmFillProposal(detail.id);
      setProposal(res.proposal);
    } finally {
      setLoading(false);
    }
  }

  async function confirmFill() {
    if (!detail || !proposal) return;
    const updated = await api.llmFillConfirm(detail.id, proposal);
    setDetail(updated);
    setProposal(null);
    onUpdated();
  }

  async function estimateDensity() {
    if (!detail) return;
    setLoading(true);
    try {
      const res = await api.llmDensity(detail.id);
      setProposedDensity(res);
    } finally {
      setLoading(false);
    }
  }

  async function confirmDensity() {
    if (!detail || !proposedDensity) return;
    await patch({ density_g_per_ml: proposedDensity.value });
    setProposedDensity(null);
  }

  const groupedKeys = useMemo(() => {
    if (!detail) return [] as { title: string; entries: [string, number | string | null][] }[];
    const all = Object.entries(detail.nutrition_data || {});
    const used = new Set<string>();
    const result: { title: string; entries: [string, number | string | null][] }[] = [];
    for (const g of NUTRIENT_GROUPS) {
      const matches: [string, number | string | null][] = [];
      for (const [k, v] of all) {
        if (used.has(k)) continue;
        if (g.keys?.includes(k)) {
          matches.push([k, v as number | string | null]);
          used.add(k);
        } else if (g.prefix && k.startsWith(g.prefix)) {
          matches.push([k, v as number | string | null]);
          used.add(k);
        }
      }
      if (matches.length) result.push({ title: g.title, entries: matches });
    }
    const rest = all.filter(([k]) => !used.has(k)) as [string, number | string | null][];
    if (rest.length) result.push({ title: "Autres", entries: rest });
    return result;
  }, [detail]);

  return (
    <Dialog open={!!id} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        {loading && !detail && <p>Chargement…</p>}
        {detail && (
          <>
            <DialogHeader>
              <DialogTitle>{detail.name}</DialogTitle>
            </DialogHeader>

            <div className="space-y-4 text-sm">
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">{detail.source}</Badge>
                {detail.modified && (
                  <Badge variant="outline">Modifié par {detail.modified_by}</Badge>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground">Catégorie</label>
                  <select
                    className="mt-1 w-full rounded-md border border-input bg-background px-2 py-1 text-sm"
                    value={detail.category || ""}
                    onChange={(e) =>
                      patch({ category: e.target.value || undefined })
                    }
                  >
                    <option value="">—</option>
                    {SHOPPING_CATEGORIES.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">
                    Densité (g/ml)
                  </label>
                  <div className="mt-1 flex gap-2">
                    <Input
                      type="number"
                      step="0.01"
                      value={detail.density_g_per_ml ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        if (v === "") return;
                        patch({ density_g_per_ml: Number(v) });
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      onClick={estimateDensity}
                      disabled={loading}
                    >
                      <Sparkles className="h-3 w-3" /> Estimer
                    </Button>
                  </div>
                  {proposedDensity && (
                    <div className="mt-2 rounded-md bg-muted p-2 text-xs">
                      Proposition : <strong>{proposedDensity.value}</strong> g/ml
                      <br />
                      <em>{proposedDensity.reason}</em>
                      <div className="mt-1 flex gap-2">
                        <Button size="sm" onClick={confirmDensity}>
                          Confirmer
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => setProposedDensity(null)}
                        >
                          Rejeter
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <label className="text-xs text-muted-foreground">Alias</label>
                </div>
                <div className="mt-1 flex flex-wrap gap-1">
                  {detail.aliases.map((a) => (
                    <Badge key={a.alias_id} variant="outline" className="gap-1">
                      {a.alias_text}
                      <button
                        type="button"
                        onClick={async () => {
                          await api.deleteIngredientAlias(detail.id, a.alias_id);
                          const fresh = await api.getIngredientDetail(detail.id);
                          setDetail(fresh);
                          onUpdated();
                        }}
                        aria-label="Supprimer l'alias"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
                <div className="mt-2 flex gap-2">
                  <Input
                    placeholder="Ajouter un alias…"
                    value={aliasInput}
                    onChange={(e) => setAliasInput(e.target.value)}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={async () => {
                      if (!aliasInput.trim()) return;
                      await patch({ add_alias: aliasInput.trim() });
                      setAliasInput("");
                    }}
                  >
                    Ajouter
                  </Button>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <h3 className="font-medium">Nutriments</h3>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={fillWithAi}
                    disabled={loading}
                  >
                    <Sparkles className="h-3 w-3" /> Compléter avec l&apos;IA
                  </Button>
                </div>
                {proposal && (
                  <div className="mt-2 rounded-md bg-muted p-3 text-xs space-y-1">
                    <div className="font-medium">Proposition :</div>
                    {Object.entries(proposal).map(([k, v]) => (
                      <div key={k} className="flex justify-between gap-2">
                        <span className="truncate">{k}</span>
                        <span>{valueLabel(v)}</span>
                      </div>
                    ))}
                    <div className="flex gap-2 pt-1">
                      <Button size="sm" onClick={confirmFill}>
                        Confirmer
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setProposal(null)}
                      >
                        Rejeter
                      </Button>
                    </div>
                  </div>
                )}
                <div className="mt-2 space-y-3">
                  {groupedKeys.map((g) => (
                    <details key={g.title} className="rounded-md border">
                      <summary className="cursor-pointer px-3 py-2 text-sm font-medium">
                        {g.title} ({g.entries.length})
                      </summary>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1 p-3 text-xs">
                        {g.entries.map(([k, v]) => (
                          <div key={k} className="flex justify-between gap-2">
                            <span className="truncate text-muted-foreground">{k}</span>
                            <span>{valueLabel(v)}</span>
                          </div>
                        ))}
                      </div>
                    </details>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
