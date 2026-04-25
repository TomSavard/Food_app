"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, ChevronDown, ChevronRight } from "lucide-react";
import * as api from "@/lib/api";
import type { UntrackedItem, WeeklyNutrition } from "@/lib/types";

// CIQUAL canonical keys (post-normalization), mirrored from backend/services/anses.py.
const K = {
  cal: "Energie, Règlement UE N° 1169 2011 (kcal 100 g)",
  prot: "Protéines, N x facteur de Jones (g 100 g)",
  lip: "Lipides (g 100 g)",
  agSat: "AG saturés (g 100 g)",
  gluc: "Glucides (g 100 g)",
  sucres: "Sucres (g 100 g)",
  fibres: "Fibres alimentaires (g 100 g)",
  sel: "Sel chlorure de sodium (g 100 g)",
} as const;

const DAILY_ROWS: { key: string; label: string; unit: string }[] = [
  { key: K.cal, label: "Calories", unit: "kcal" },
  { key: K.prot, label: "Protéines", unit: "g" },
  { key: K.lip, label: "Lipides", unit: "g" },
  { key: K.gluc, label: "Glucides", unit: "g" },
  { key: K.sucres, label: "Sucres", unit: "g" },
  { key: K.fibres, label: "Fibres", unit: "g" },
  { key: K.sel, label: "Sel", unit: "g" },
  { key: K.agSat, label: "AG saturés", unit: "g" },
];

const LOWER_IS_BETTER = new Set<string>([K.sel, K.agSat, K.sucres]);

const MICRO_GROUPS: { title: string; rows: { key: string; label: string; unit: string }[] }[] = [
  {
    title: "Minéraux",
    rows: [
      { key: "Calcium (mg 100 g)", label: "Calcium", unit: "mg" },
      { key: "Fer (mg 100 g)", label: "Fer", unit: "mg" },
      { key: "Magnésium (mg 100 g)", label: "Magnésium", unit: "mg" },
      { key: "Phosphore (mg 100 g)", label: "Phosphore", unit: "mg" },
      { key: "Potassium (mg 100 g)", label: "Potassium", unit: "mg" },
      { key: "Zinc (mg 100 g)", label: "Zinc", unit: "mg" },
      { key: "Iode (µg 100 g)", label: "Iode", unit: "µg" },
      { key: "Sélénium (µg 100 g)", label: "Sélénium", unit: "µg" },
      { key: "Cuivre (mg 100 g)", label: "Cuivre", unit: "mg" },
      { key: "Manganèse (mg 100 g)", label: "Manganèse", unit: "mg" },
    ],
  },
  {
    title: "Vitamines",
    rows: [
      { key: "Vitamine C (mg 100 g)", label: "Vitamine C", unit: "mg" },
      { key: "Vitamine D (µg 100 g)", label: "Vitamine D", unit: "µg" },
      { key: "Activité vitaminique A, équivalents rétinol (µg 100 g)", label: "Vitamine A", unit: "µg" },
      { key: "Vitamine E (mg 100 g)", label: "Vitamine E", unit: "mg" },
      { key: "Vitamine K1 (µg 100 g)", label: "Vitamine K1", unit: "µg" },
      { key: "Vitamine B1 ou Thiamine (mg 100 g)", label: "B1 (Thiamine)", unit: "mg" },
      { key: "Vitamine B2 ou Riboflavine (mg 100 g)", label: "B2 (Riboflavine)", unit: "mg" },
      { key: "Vitamine B3 ou PP ou Niacine (mg 100 g)", label: "B3 (Niacine)", unit: "mg" },
      { key: "Vitamine B5 ou Acide pantothénique (mg 100 g)", label: "B5", unit: "mg" },
      { key: "Vitamine B6 (mg 100 g)", label: "B6", unit: "mg" },
      { key: "Vitamine B9 ou Folates totaux (µg 100 g)", label: "B9 (Folates)", unit: "µg" },
      { key: "Vitamine B12 (µg 100 g)", label: "B12", unit: "µg" },
    ],
  },
];

const DAY_LABELS = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"];

const REASON_LABEL: Record<UntrackedItem["reason"], string> = {
  missing_fk: "Non lié à un ingrédient connu",
  missing_density: "Densité manquante (volume non convertible)",
  no_data: "Aucune donnée nutritionnelle",
  unknown_unit: "Unité non reconnue",
};

function fmt(value: number, unit: string): string {
  if (value === 0) return `0 ${unit}`;
  if (value < 1) return `${value.toFixed(2)} ${unit}`;
  if (value < 10) return `${value.toFixed(1)} ${unit}`;
  return `${Math.round(value)} ${unit}`;
}

function pctColor(pct: number, lowerIsBetter: boolean): string {
  if (lowerIsBetter) {
    if (pct <= 80) return "bg-emerald-500";
    if (pct <= 110) return "bg-amber-500";
    return "bg-rose-500";
  }
  if (pct < 50) return "bg-slate-400";
  if (pct < 90) return "bg-amber-500";
  if (pct <= 120) return "bg-emerald-500";
  return "bg-rose-500";
}

export function NutritionSection({
  weekStart,
  refreshKey = "",
}: {
  weekStart: string;
  refreshKey?: string;
}) {
  const [data, setData] = useState<WeeklyNutrition | null>(null);
  const [loading, setLoading] = useState(false);
  const [showUntracked, setShowUntracked] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .getWeeklyNutrition(weekStart)
      .then((d) => !cancelled && setData(d))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [weekStart, refreshKey]);

  if (loading && !data) {
    return <div className="text-sm text-muted-foreground">Chargement…</div>;
  }
  if (!data) return null;

  const hasAny = Object.values(data.week).some((v) => v > 0);

  return (
    <section className="space-y-6">
      <h2 className="text-xl font-semibold">Nutrition</h2>

      {data.untracked.length > 0 && (
        <UntrackedBanner
          items={data.untracked}
          open={showUntracked}
          onToggle={() => setShowUntracked((s) => !s)}
        />
      )}

      {!hasAny ? (
        <p className="text-sm text-muted-foreground">
          Pas encore de données nutritionnelles pour cette semaine. Ajoute des
          repas et lie leurs ingrédients à la base CIQUAL pour voir le bilan.
        </p>
      ) : (
        <>
          <WeekOverview data={data} />
          <DailyBreakdown data={data} />
          <WeekMicros data={data} />
        </>
      )}
    </section>
  );
}

function UntrackedBanner({
  items,
  open,
  onToggle,
}: {
  items: UntrackedItem[];
  open: boolean;
  onToggle: () => void;
}) {
  const grouped = items.reduce<Record<UntrackedItem["reason"], UntrackedItem[]>>(
    (acc, it) => {
      (acc[it.reason] ??= []).push(it);
      return acc;
    },
    {} as Record<UntrackedItem["reason"], UntrackedItem[]>
  );

  return (
    <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-2 text-left"
      >
        {open ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        <AlertTriangle className="h-4 w-4 text-amber-600" />
        <span>
          <strong>{items.length}</strong> élément{items.length > 1 ? "s" : ""} non
          suivi{items.length > 1 ? "s" : ""} cette semaine —{" "}
          <Link href="/ingredients" className="underline">
            corriger dans /ingredients
          </Link>
        </span>
      </button>
      {open && (
        <div className="mt-3 space-y-2">
          {(Object.keys(grouped) as UntrackedItem["reason"][]).map((reason) => (
            <div key={reason}>
              <div className="text-xs font-medium text-muted-foreground">
                {REASON_LABEL[reason]} ({grouped[reason].length})
              </div>
              <ul className="mt-1 space-y-0.5 text-xs">
                {grouped[reason].map((it, i) => (
                  <li key={`${reason}-${i}`} className="flex justify-between gap-3">
                    <span className="truncate">
                      <span className="font-medium">{it.ingredient_name}</span>
                      <span className="text-muted-foreground">
                        {" — "}
                        {it.recipe_name}
                      </span>
                    </span>
                    <span className="text-muted-foreground">{it.slot_date}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function WeekOverview({ data }: { data: WeeklyNutrition }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-muted-foreground">
        Vue d&apos;ensemble (semaine)
      </h3>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {DAILY_ROWS.map((row) => {
          const total = data.week[row.key] || 0;
          const target = (data.rdi[row.key] || 0) * 7;
          const pct = target > 0 ? (total / target) * 100 : 0;
          const lower = LOWER_IS_BETTER.has(row.key);
          const color = pctColor(pct, lower);
          return (
            <div key={row.key} className="rounded-lg border bg-card p-3">
              <div className="text-xs text-muted-foreground">{row.label}</div>
              <div className="mt-1 text-lg font-semibold">{fmt(total, row.unit)}</div>
              <div className="text-xs text-muted-foreground">
                {target > 0 ? `${Math.round(pct)} % de l'apport hebdo` : "—"}
              </div>
              {target > 0 && (
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted">
                  <div
                    className={"h-full " + color}
                    style={{ width: `${Math.min(pct, 100)}%` }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DailyBreakdown({ data }: { data: WeeklyNutrition }) {
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-muted-foreground">
        Décomposition jour par jour (macros)
      </h3>
      <div className="space-y-1">
        {DAILY_ROWS.map((row) => {
          const target = data.rdi[row.key] || 0;
          const lower = LOWER_IS_BETTER.has(row.key);
          const weekTotal = data.week[row.key] || 0;
          return (
            <div
              key={row.key}
              className="grid grid-cols-12 items-center gap-2 rounded border bg-card p-2 text-xs"
            >
              <div className="col-span-3 sm:col-span-2 font-medium">{row.label}</div>
              <div className="col-span-7 sm:col-span-8 grid grid-cols-7 gap-1">
                {data.days.map((d, i) => {
                  const v = d.macros[row.key] || 0;
                  const pct = target > 0 ? (v / target) * 100 : 0;
                  return (
                    <div
                      key={d.date}
                      title={`${DAY_LABELS[i]} — ${fmt(v, row.unit)}${
                        target ? ` (${Math.round(pct)}%)` : ""
                      }`}
                      className="relative h-5 overflow-hidden rounded-sm bg-muted"
                    >
                      <div
                        className={"h-full " + pctColor(pct, lower)}
                        style={{ width: `${Math.min(pct, 100)}%` }}
                      />
                      <div className="absolute inset-0 flex items-center justify-center text-[9px] font-semibold leading-none text-foreground/80">
                        {DAY_LABELS[i]}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div className="col-span-2 text-right text-muted-foreground tabular-nums">
                {fmt(weekTotal, row.unit)}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function WeekMicros({ data }: { data: WeeklyNutrition }) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium text-muted-foreground">
        Micro-nutriments (semaine)
      </h3>
      {MICRO_GROUPS.map((g) => (
        <div key={g.title} className="overflow-hidden rounded-md border">
          <div className="bg-muted/50 px-3 py-1.5 text-xs font-medium">{g.title}</div>
          <table className="w-full text-xs">
            <tbody>
              {g.rows.map((row) => {
                const total = data.week[row.key] || 0;
                const target = (data.rdi[row.key] || 0) * 7;
                const pct = target > 0 ? (total / target) * 100 : 0;
                return (
                  <tr key={row.key} className="border-t">
                    <td className="px-3 py-1.5">{row.label}</td>
                    <td className="px-3 py-1.5 tabular-nums">
                      {total > 0 ? fmt(total, row.unit) : "—"}
                    </td>
                    <td className="px-3 py-1.5 text-muted-foreground">
                      {target > 0 && total > 0 ? `${Math.round(pct)} %` : "—"}
                    </td>
                    <td className="px-3 py-1.5 w-1/3">
                      {target > 0 && total > 0 && (
                        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                          <div
                            className={"h-full " + pctColor(pct, false)}
                            style={{ width: `${Math.min(pct, 100)}%` }}
                          />
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
