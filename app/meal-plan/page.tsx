"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Plus, Sparkles, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import * as api from "@/lib/api";
import type { MealPlanWeek, MealSlot, Recipe } from "@/lib/types";
import { MEAL_SLOTS } from "@/lib/types";
import { addDays, dayLabelFR, isoDate, mondayOf, shortDateFR } from "@/lib/dates";
import { RecipePickerDialog } from "@/components/recipe-picker-dialog";

const SLOT_LABEL_FR: Record<MealSlot, string> = {
  breakfast: "Petit-déj",
  lunch: "Déjeuner",
  dinner: "Dîner",
  extra: "Extra",
};

interface PickerTarget {
  date: string;
  slot: MealSlot;
}

export default function MealPlanPage() {
  const [weekStartDate, setWeekStartDate] = useState<Date>(() => mondayOf(new Date()));
  const weekStart = useMemo(() => isoDate(weekStartDate), [weekStartDate]);
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStartDate, i)), [weekStartDate]);

  const [plan, setPlan] = useState<MealPlanWeek | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [picker, setPicker] = useState<PickerTarget | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setPlan(await api.getMealPlan(weekStart));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, [weekStart]);

  useEffect(() => {
    load();
  }, [load]);

  const slotMap = useMemo(() => {
    const m = new Map<string, MealPlanWeek["slots"][number]>();
    for (const s of plan?.slots || []) m.set(`${s.slot_date}|${s.slot}`, s);
    return m;
  }, [plan]);

  async function pick(recipe: Recipe) {
    if (!picker) return;
    setBusy(true);
    try {
      await api.setMealPlanSlot({
        slot_date: picker.date,
        slot: picker.slot,
        recipe_id: recipe.recipe_id,
        servings: recipe.servings || 1,
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    } finally {
      setBusy(false);
    }
  }

  async function changeServings(date: string, slot: MealSlot, recipe_id: string, servings: number) {
    if (servings < 1) return;
    setBusy(true);
    try {
      await api.setMealPlanSlot({ slot_date: date, slot, recipe_id, servings });
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function clearSlot(date: string, slot: MealSlot) {
    setBusy(true);
    try {
      await api.clearMealPlanSlot(date, slot);
      await load();
    } finally {
      setBusy(false);
    }
  }

  async function generateWeek() {
    if (!confirm("Remplir les créneaux vides avec des recettes au hasard ?")) return;
    setBusy(true);
    try {
      await api.generateMealPlan(weekStart, false);
      await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold">Semaine</h1>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => setWeekStartDate((d) => addDays(d, -7))} aria-label="Semaine précédente">
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={() => setWeekStartDate(mondayOf(new Date()))}>
            Cette semaine
          </Button>
          <Button variant="outline" size="icon" onClick={() => setWeekStartDate((d) => addDays(d, 7))} aria-label="Semaine suivante">
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button onClick={generateWeek} disabled={busy}>
            <Sparkles className="h-4 w-4" /> Générer
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">
        {shortDateFR(days[0])} → {shortDateFR(days[6])}
      </p>

      {error && <p className="text-destructive">{error}</p>}
      {loading && <p className="text-muted-foreground">Chargement…</p>}

      {/* Desktop: 7-col grid by slot row. Mobile: stacked by day. */}
      <div className="hidden md:block">
        <div className="grid grid-cols-[120px_repeat(7,1fr)] gap-2">
          <div />
          {days.map((d) => (
            <div key={isoDate(d)} className="text-center text-sm font-medium">
              <div>{dayLabelFR(d)}</div>
              <div className="text-xs text-muted-foreground">{shortDateFR(d)}</div>
            </div>
          ))}
          {MEAL_SLOTS.map((slot) => (
            <SlotRow
              key={slot}
              slot={slot}
              days={days}
              slotMap={slotMap}
              onAdd={(date) => setPicker({ date, slot })}
              onClear={clearSlot}
              onServings={changeServings}
              disabled={busy}
            />
          ))}
        </div>
      </div>

      <div className="space-y-4 md:hidden">
        {days.map((d) => {
          const date = isoDate(d);
          return (
            <Card key={date} className="p-3">
              <div className="mb-2 flex items-baseline justify-between">
                <span className="font-medium">{dayLabelFR(d)}</span>
                <span className="text-xs text-muted-foreground">{shortDateFR(d)}</span>
              </div>
              <div className="space-y-2">
                {MEAL_SLOTS.map((slot) => {
                  const filled = slotMap.get(`${date}|${slot}`);
                  return (
                    <SlotCell
                      key={slot}
                      label={SLOT_LABEL_FR[slot]}
                      filled={filled}
                      onAdd={() => setPicker({ date, slot })}
                      onClear={() => clearSlot(date, slot)}
                      onServings={(n) => filled && changeServings(date, slot, filled.recipe_id, n)}
                      disabled={busy}
                    />
                  );
                })}
              </div>
            </Card>
          );
        })}
      </div>

      <RecipePickerDialog
        open={picker !== null}
        onOpenChange={(v) => !v && setPicker(null)}
        onPick={pick}
        title={picker ? `${SLOT_LABEL_FR[picker.slot]} — ${picker.date}` : ""}
      />
    </div>
  );
}

function SlotRow({
  slot,
  days,
  slotMap,
  onAdd,
  onClear,
  onServings,
  disabled,
}: {
  slot: MealSlot;
  days: Date[];
  slotMap: Map<string, ReturnType<MealPlanWeek["slots"]["at"]>>;
  onAdd: (date: string) => void;
  onClear: (date: string, slot: MealSlot) => void;
  onServings: (date: string, slot: MealSlot, recipe_id: string, n: number) => void;
  disabled: boolean;
}) {
  return (
    <>
      <div className="flex items-center text-sm font-medium text-muted-foreground">
        {SLOT_LABEL_FR[slot]}
      </div>
      {days.map((d) => {
        const date = isoDate(d);
        const filled = slotMap.get(`${date}|${slot}`);
        return (
          <SlotCell
            key={date}
            filled={filled}
            onAdd={() => onAdd(date)}
            onClear={() => onClear(date, slot)}
            onServings={(n) => filled && onServings(date, slot, filled.recipe_id, n)}
            disabled={disabled}
            compact
          />
        );
      })}
    </>
  );
}

function SlotCell({
  label,
  filled,
  onAdd,
  onClear,
  onServings,
  disabled,
  compact,
}: {
  label?: string;
  filled?: ReturnType<MealPlanWeek["slots"]["at"]>;
  onAdd: () => void;
  onClear: () => void;
  onServings: (n: number) => void;
  disabled: boolean;
  compact?: boolean;
}) {
  return (
    <div
      className={
        "rounded-md border bg-card p-2 text-sm " +
        (compact ? "min-h-[68px]" : "")
      }
    >
      {label && <div className="mb-1 text-xs text-muted-foreground">{label}</div>}
      {filled ? (
        <div className="space-y-1">
          <div className="line-clamp-2 text-sm font-medium">{filled.recipe_name}</div>
          <div className="flex items-center gap-1">
            <Input
              type="number"
              min={1}
              value={filled.servings}
              onChange={(e) => onServings(Number(e.target.value))}
              className="h-7 w-14 px-2 text-xs"
              disabled={disabled}
              aria-label="Portions"
            />
            <span className="text-xs text-muted-foreground">pers.</span>
            <button
              className="ml-auto text-muted-foreground hover:text-destructive"
              onClick={onClear}
              disabled={disabled}
              aria-label="Supprimer"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      ) : (
        <button
          onClick={onAdd}
          disabled={disabled}
          className="flex h-full min-h-[40px] w-full items-center justify-center text-muted-foreground hover:text-foreground"
          aria-label="Ajouter"
        >
          <Plus className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
