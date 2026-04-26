"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { Tooltip } from "@/components/ui/tooltip";
import * as api from "@/lib/api";
import type {
  InSeasonResponse,
  RdiReference,
  RdiNutrient,
  SeasonLevel,
  SeasonalityItem,
  SeasonalityReference,
  Sex,
} from "@/lib/types";

const MONTHS_FR = [
  "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
];

export default function ReferencePage() {
  const [tab, setTab] = useState<"rdi" | "season">("rdi");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Références</h1>
        <p className="text-sm text-muted-foreground">
          Sources françaises faisant autorité (ANSES, Interfel).
        </p>
      </div>

      <div className="flex gap-2 border-b">
        <TabButton active={tab === "rdi"} onClick={() => setTab("rdi")}>
          Apports recommandés
        </TabButton>
        <TabButton active={tab === "season"} onClick={() => setTab("season")}>
          Saisonnalité
        </TabButton>
      </div>

      {tab === "rdi" ? <RdiTab /> : <SeasonTab />}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        "px-3 py-2 text-sm transition border-b-2 -mb-px " +
        (active
          ? "border-foreground text-foreground"
          : "border-transparent text-muted-foreground hover:text-foreground")
      }
    >
      {children}
    </button>
  );
}

// ---------------- RDI tab ----------------

const CAT_LABEL: Record<RdiNutrient["category"], string> = {
  macros: "Macronutriments",
  minerals: "Minéraux",
  vitamins: "Vitamines",
};

const TYPE_DEFINITION: Record<RdiNutrient["ref_type"], string> = {
  BNM: "Besoin Nutritionnel Moyen — apport qui couvre les besoins de 50 % de la population (médiane). Indicatif, pas une cible.",
  RNP: "Référence Nutritionnelle pour la Population — apport qui couvre ~97,5 % de la population (BNM + 2 écarts-types). Cible quotidienne à atteindre.",
  AS:  "Apport Satisfaisant — utilisé quand les données ne permettent pas de fixer une RNP. Apport observé chez une population en bonne santé ; cible raisonnable.",
  LSS: "Limite Supérieure de Sécurité — apport maximum considéré comme sûr. Plafond à ne pas dépasser, pas une cible.",
};

function RdiTab() {
  const [data, setData] = useState<RdiReference | null>(null);
  const [sex, setSex] = useState<Sex>(() => {
    if (typeof window === "undefined") return "male";
    return (localStorage.getItem("nutrition.sex") as Sex) || "male";
  });

  useEffect(() => {
    api.getRdiReference().then(setData);
  }, []);

  function setSexAndPersist(s: Sex) {
    setSex(s);
    if (typeof window !== "undefined") localStorage.setItem("nutrition.sex", s);
  }

  if (!data) return <p className="text-sm text-muted-foreground">Chargement…</p>;

  const grouped = data.nutrients.reduce<Record<string, RdiNutrient[]>>(
    (acc, n) => {
      (acc[n.category] ??= []).push(n);
      return acc;
    },
    {}
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Référence pour :</span>
        <SexToggle sex={sex} onChange={setSexAndPersist} />
      </div>

      {(["macros", "minerals", "vitamins"] as const).map((cat) => (
        <section key={cat} className="overflow-hidden rounded-md border">
          <div className="bg-muted/50 px-3 py-2 text-xs font-medium">
            {CAT_LABEL[cat]}
          </div>
          <table className="w-full text-sm">
            <thead className="bg-muted/30 text-xs text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left">Nutriment</th>
                <th className="px-3 py-2 text-right">Valeur / jour</th>
                <th className="px-3 py-2 text-left">Type</th>
                <th className="px-3 py-2 text-left">Source</th>
              </tr>
            </thead>
            <tbody>
              {(grouped[cat] || []).map((n) => {
                const value = sex === "male" ? n.male_adult : n.female_adult;
                const src = data.sources[n.source_id];
                return (
                  <tr key={n.ciqual_key} className="border-t align-top">
                    <td className="px-3 py-1.5">{n.label}</td>
                    <td className="px-3 py-1.5 text-right tabular-nums">
                      {value} {n.unit}
                      {n.lower_is_better && (
                        <span className="ml-1 text-xs text-muted-foreground">
                          (max)
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-1.5 text-xs text-muted-foreground">
                      <Tooltip content={TYPE_DEFINITION[n.ref_type]}>
                        <span>{n.ref_type}</span>
                      </Tooltip>
                    </td>
                    <td className="px-3 py-1.5 text-xs">
                      {src ? (
                        <a
                          href={src.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 underline text-muted-foreground hover:text-foreground"
                        >
                          {src.publisher} {src.year}
                          <ExternalLink className="h-3 w-3" />
                          {n.source_page != null && (
                            <span className="ml-1">p. {n.source_page}</span>
                          )}
                        </a>
                      ) : (
                        "—"
                      )}
                      {n.note && (
                        <div className="mt-0.5 text-[10px] italic text-muted-foreground">
                          {n.note}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      ))}
    </div>
  );
}

function SexToggle({ sex, onChange }: { sex: Sex; onChange: (s: Sex) => void }) {
  return (
    <div className="inline-flex overflow-hidden rounded-full border text-xs">
      {(["male", "female"] as const).map((s) => (
        <button
          key={s}
          type="button"
          onClick={() => onChange(s)}
          className={
            "px-3 py-1 transition " +
            (sex === s
              ? "bg-foreground text-background"
              : "text-muted-foreground hover:text-foreground")
          }
        >
          {s === "male" ? "Homme" : "Femme"}
        </button>
      ))}
    </div>
  );
}

// ---------------- Seasonality tab ----------------

const LEVEL_COLOR: Record<SeasonLevel, string> = {
  coeur: "bg-emerald-500",
  saison: "bg-emerald-500/40",
  disponibilite: "bg-muted",
};

const LEVEL_LABEL: Record<SeasonLevel, string> = {
  coeur: "Cœur de saison",
  saison: "Saison",
  disponibilite: "Disponible",
};

function SeasonTab() {
  const [data, setData] = useState<SeasonalityReference | null>(null);
  const [view, setView] = useState<"month" | "grid">("month");
  const [kind, setKind] = useState<"fruit" | "legume">("fruit");
  const [month, setMonth] = useState<number>(() => new Date().getMonth() + 1);
  const [inSeason, setInSeason] = useState<InSeasonResponse | null>(null);

  useEffect(() => {
    api.getSeasonalityReference().then(setData);
  }, []);
  useEffect(() => {
    api.getInSeason(month).then(setInSeason);
  }, [month]);

  if (!data) return <p className="text-sm text-muted-foreground">Chargement…</p>;

  const filtered = data.items.filter((it) => it.kind === kind);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <div className="inline-flex overflow-hidden rounded-full border text-xs">
          {(["fruit", "legume"] as const).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setKind(k)}
              className={
                "px-3 py-1 transition " +
                (kind === k
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:text-foreground")
              }
            >
              {k === "fruit" ? "Fruits" : "Légumes"}
            </button>
          ))}
        </div>
        <div className="inline-flex overflow-hidden rounded-full border text-xs">
          {(["month", "grid"] as const).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              className={
                "px-3 py-1 transition " +
                (view === v
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:text-foreground")
              }
            >
              {v === "month" ? "Ce mois-ci" : "Calendrier"}
            </button>
          ))}
        </div>
        {view === "month" && (
          <select
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
            className="rounded-md border border-input bg-background px-2 text-sm"
          >
            {MONTHS_FR.map((m, i) => (
              <option key={m} value={i + 1}>
                {m}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <Legend />
        <a
          href={data.source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="ml-auto inline-flex items-center gap-1 underline hover:text-foreground"
        >
          Source : {data.source.publisher}
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>

      {view === "month" ? (
        <MonthView items={inSeason?.items.filter((it) => it.kind === kind) ?? []} />
      ) : (
        <GridView items={filtered} />
      )}
    </div>
  );
}

function Legend() {
  return (
    <div className="flex items-center gap-3">
      {(["coeur", "saison", "disponibilite"] as const).map((lv) => (
        <div key={lv} className="inline-flex items-center gap-1">
          <span className={"inline-block h-2.5 w-2.5 rounded-sm " + LEVEL_COLOR[lv]} />
          <span>{LEVEL_LABEL[lv]}</span>
        </div>
      ))}
    </div>
  );
}

function ItemBadges({ it }: { it: SeasonalityItem }) {
  return (
    <span className="ml-2 inline-flex gap-1 text-[10px]">
      {it.exotic && (
        <span className="rounded bg-amber-500/20 px-1 text-amber-600">exotique</span>
      )}
      {it.greenhouse && (
        <span className="rounded bg-blue-500/20 px-1 text-blue-600">serre</span>
      )}
    </span>
  );
}

function MonthView({ items }: { items: SeasonalityItem[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-muted-foreground">Rien ce mois-ci.</p>;
  }
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
      {items.map((it) => (
        <div
          key={it.name}
          className="rounded-md border bg-card p-2 text-sm"
        >
          <div className="flex items-center justify-between">
            <span className="font-medium">{it.name}</span>
            <span
              className={
                "h-2 w-2 rounded-full " +
                (it.level ? LEVEL_COLOR[it.level] : "bg-muted")
              }
              title={it.level ? LEVEL_LABEL[it.level] : ""}
            />
          </div>
          {(it.exotic || it.greenhouse) && (
            <div className="mt-1 text-xs">
              <ItemBadges it={it} />
            </div>
          )}
          {it.notes && (
            <div className="mt-1 text-xs text-muted-foreground">{it.notes}</div>
          )}
        </div>
      ))}
    </div>
  );
}

const MONTHS_HEADER = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

function GridView({ items }: { items: SeasonalityItem[] }) {
  return (
    <div className="overflow-hidden rounded-md border">
      <table className="w-full text-xs">
        <thead className="bg-muted/50">
          <tr>
            <th className="px-3 py-2 text-left">Aliment</th>
            {MONTHS_HEADER.map((m, i) => (
              <th key={i} className="w-6 py-2 text-center">{m}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((it) => (
            <tr key={it.name} className="border-t">
              <td className="px-3 py-1.5 whitespace-nowrap">
                {it.name}
                <ItemBadges it={it} />
              </td>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => {
                const lv = it.months[String(m)] as SeasonLevel | undefined;
                return (
                  <td key={m} className="p-0.5">
                    <div
                      className={
                        "h-4 w-full rounded " + (lv ? LEVEL_COLOR[lv] : "")
                      }
                      title={lv ? LEVEL_LABEL[lv] : "—"}
                    />
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
