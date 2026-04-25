"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  GripVertical,
  Plus,
  Sparkles,
  Trash2,
} from "lucide-react";
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  DragOverlay,
  DragStartEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import * as api from "@/lib/api";
import type { MealPlanSlot, MealPlanWeek, Recipe } from "@/lib/types";
import { addDays, dayLabelFR, isoDate, mondayOf, shortDateFR } from "@/lib/dates";
import { RecipePickerDialog } from "@/components/recipe-picker-dialog";

export default function MealPlanPage() {
  const [weekStartDate, setWeekStartDate] = useState<Date>(() => mondayOf(new Date()));
  const weekStart = useMemo(() => isoDate(weekStartDate), [weekStartDate]);
  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(weekStartDate, i)),
    [weekStartDate]
  );

  const [slots, setSlots] = useState<MealPlanSlot[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pickerDate, setPickerDate] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const week = await api.getMealPlan(weekStart);
      setSlots(week.slots);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de chargement");
    } finally {
      setLoading(false);
    }
  }, [weekStart]);

  useEffect(() => {
    load();
  }, [load]);

  const byDay = useMemo(() => {
    const map = new Map<string, MealPlanSlot[]>();
    for (const d of days) map.set(isoDate(d), []);
    for (const s of slots) map.get(s.slot_date)?.push(s);
    return map;
  }, [slots, days]);

  const activeSlot = useMemo(
    () => slots.find((s) => s.slot_id === activeId) || null,
    [slots, activeId]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  // ----- DnD: optimistic local update + server sync -----
  function handleDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }

  function handleDragOver(e: DragOverEvent) {
    const { active, over } = e;
    if (!over) return;
    const activeIdStr = String(active.id);
    const overIdStr = String(over.id);
    if (activeIdStr === overIdStr) return;
    // Trash drop is handled in handleDragEnd; don't reorder while hovering it.
    if (overIdStr === "trash") return;

    setSlots((prev) => {
      const activeSlot = prev.find((s) => s.slot_id === activeIdStr);
      if (!activeSlot) return prev;

      // Dropping on a day container directly → move to end of that day.
      const overDay = overIdStr.startsWith("day:") ? overIdStr.slice(4) : null;
      const overSlot = !overDay ? prev.find((s) => s.slot_id === overIdStr) : null;
      if (!overDay && !overSlot) return prev;

      const targetDate = overDay ?? overSlot!.slot_date;
      if (activeSlot.slot_date === targetDate && overSlot && activeSlot.slot_id !== overSlot.slot_id) {
        // Reorder within same day.
        const dayItems = prev
          .filter((s) => s.slot_date === targetDate)
          .sort((a, b) => a.position - b.position);
        const oldIdx = dayItems.findIndex((s) => s.slot_id === activeIdStr);
        const newIdx = dayItems.findIndex((s) => s.slot_id === overSlot.slot_id);
        const reordered = arrayMove(dayItems, oldIdx, newIdx);
        const repositioned = reordered.map((s, i) => ({ ...s, position: i }));
        return prev.map((s) => repositioned.find((r) => r.slot_id === s.slot_id) || s);
      }

      if (activeSlot.slot_date !== targetDate) {
        // Cross-day move: snip from source day and insert in target.
        const sourceDay = prev
          .filter((s) => s.slot_date === activeSlot.slot_date && s.slot_id !== activeIdStr)
          .sort((a, b) => a.position - b.position)
          .map((s, i) => ({ ...s, position: i }));
        const targetDayItems = prev
          .filter((s) => s.slot_date === targetDate)
          .sort((a, b) => a.position - b.position);
        const insertIdx = overSlot
          ? targetDayItems.findIndex((s) => s.slot_id === overSlot.slot_id)
          : targetDayItems.length;
        const moved = { ...activeSlot, slot_date: targetDate };
        targetDayItems.splice(insertIdx, 0, moved);
        const repositioned = targetDayItems.map((s, i) => ({ ...s, position: i }));
        const untouched = prev.filter(
          (s) => s.slot_date !== activeSlot.slot_date && s.slot_date !== targetDate
        );
        return [...untouched, ...sourceDay, ...repositioned];
      }
      return prev;
    });
  }

  async function handleDragEnd(e: DragEndEvent) {
    const overId = e.over?.id;
    const droppedId = String(e.active.id);
    setActiveId(null);

    if (overId === "trash") {
      // Optimistic delete; revert by reload on error.
      setSlots((prev) => prev.filter((s) => s.slot_id !== droppedId));
      try {
        await api.deleteMeal(droppedId);
      } catch {
        load();
      }
      return;
    }

    // Push the entire current ordering of all 7 days. Cheap; small payload.
    const items = slots.map((s) => ({
      slot_id: s.slot_id,
      slot_date: s.slot_date,
      position: s.position,
    }));
    try {
      await api.reorderMeals(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de réorganisation");
      load();
    }
  }

  async function pickRecipe(recipe: Recipe) {
    if (!pickerDate) return;
    try {
      await api.addMealToDay({
        slot_date: pickerDate,
        recipe_id: recipe.recipe_id,
        servings: recipe.servings || 1,
      });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  async function changeServings(slot_id: string, servings: number) {
    if (servings < 1) return;
    setSlots((prev) =>
      prev.map((s) => (s.slot_id === slot_id ? { ...s, servings } : s))
    );
    try {
      await api.updateMealServings(slot_id, servings);
    } catch {
      load();
    }
  }

  async function generateWeek() {
    if (!confirm("Générer 3 repas pour les jours encore vides ?")) return;
    try {
      await api.generateMealPlan(weekStart, 3, false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Semaine</h1>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setWeekStartDate((d) => addDays(d, -7))}
            aria-label="Semaine précédente"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="outline" onClick={() => setWeekStartDate(mondayOf(new Date()))}>
            Cette semaine
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setWeekStartDate((d) => addDays(d, 7))}
            aria-label="Semaine suivante"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button onClick={generateWeek}>
            <Sparkles className="h-4 w-4" /> Générer
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground">
        {shortDateFR(days[0])} → {shortDateFR(days[6])}
      </p>

      {error && <p className="text-destructive">{error}</p>}
      {loading && <p className="text-muted-foreground">Chargement…</p>}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="grid gap-3 md:grid-cols-7">
          {days.map((d) => {
            const date = isoDate(d);
            const dayItems = (byDay.get(date) || []).sort(
              (a, b) => a.position - b.position
            );
            return (
              <DayColumn
                key={date}
                date={date}
                title={dayLabelFR(d)}
                subtitle={shortDateFR(d)}
                items={dayItems}
                onAdd={() => setPickerDate(date)}
                onServings={changeServings}
              />
            );
          })}
        </div>

        <DragOverlay>
          {activeSlot && (
            <MealCard slot={activeSlot} onServings={() => {}} isOverlay />
          )}
        </DragOverlay>

        <TrashZone visible={activeId !== null} />
      </DndContext>

      <RecipePickerDialog
        open={pickerDate !== null}
        onOpenChange={(v) => !v && setPickerDate(null)}
        onPick={pickRecipe}
        title={pickerDate ? `Ajouter au ${pickerDate}` : ""}
      />
    </div>
  );
}

function DayColumn({
  date,
  title,
  subtitle,
  items,
  onAdd,
  onServings,
}: {
  date: string;
  title: string;
  subtitle: string;
  items: MealPlanSlot[];
  onAdd: () => void;
  onServings: (id: string, n: number) => void;
}) {
  return (
    <div className="surface flex min-h-[200px] flex-col gap-2 p-3" data-day-id={date}>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-semibold">{title}</span>
        <span className="text-xs text-muted-foreground">{subtitle}</span>
      </div>
      <SortableContext
        items={items.length > 0 ? items.map((s) => s.slot_id) : [`day:${date}`]}
        strategy={verticalListSortingStrategy}
      >
        <DroppableEmpty id={`day:${date}`} hidden={items.length > 0} />
        <div className="flex flex-col gap-2">
          {items.map((s) => (
            <SortableMeal key={s.slot_id} slot={s} onServings={onServings} />
          ))}
        </div>
      </SortableContext>
      <Button
        variant="ghost"
        size="sm"
        className="mt-auto w-full justify-center text-muted-foreground hover:text-foreground"
        onClick={onAdd}
      >
        <Plus className="h-4 w-4" /> Ajouter
      </Button>
    </div>
  );
}

function TrashZone({ visible }: { visible: boolean }) {
  const { setNodeRef, isOver } = useDroppable({ id: "trash" });
  return (
    <div
      ref={setNodeRef}
      className={
        "fixed bottom-6 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-full px-5 py-3 text-sm font-medium shadow-2xl transition-all duration-200 " +
        (visible
          ? "translate-y-0 opacity-100"
          : "pointer-events-none translate-y-24 opacity-0") +
        (isOver
          ? " scale-110 bg-destructive text-destructive-foreground ring-2 ring-destructive/40"
          : " glass text-foreground")
      }
      aria-label="Glisser pour supprimer"
    >
      <Trash2 className="h-4 w-4" />
      <span>{isOver ? "Lâcher pour supprimer" : "Glisser ici pour supprimer"}</span>
    </div>
  );
}

function DroppableEmpty({ id, hidden }: { id: string; hidden: boolean }) {
  const { setNodeRef, isOver } = useSortable({ id });
  if (hidden) return null;
  return (
    <div
      ref={setNodeRef}
      className={
        "rounded-xl border border-dashed border-border/60 px-2 py-6 text-center text-xs text-muted-foreground transition-colors " +
        (isOver ? "border-primary/60 bg-primary/10" : "")
      }
    >
      Glisser ici
    </div>
  );
}

function SortableMeal({
  slot,
  onServings,
}: {
  slot: MealPlanSlot;
  onServings: (id: string, n: number) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: slot.slot_id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div ref={setNodeRef} style={style} {...attributes}>
      <MealCard slot={slot} onServings={onServings} dragHandleListeners={listeners} />
    </div>
  );
}

function MealCard({
  slot,
  onServings,
  dragHandleListeners,
  isOverlay,
}: {
  slot: MealPlanSlot;
  onServings: (id: string, n: number) => void;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  dragHandleListeners?: any;
  isOverlay?: boolean;
}) {
  return (
    <div
      className={
        "group relative rounded-xl border bg-card px-2.5 py-2 text-sm shadow-sm " +
        (isOverlay ? "scale-[1.04] shadow-2xl ring-1 ring-primary/40 rotate-[1deg]" : "")
      }
    >
      {/* Top row: recipe name (full width) + tiny drag handle. */}
      <div className="flex items-start gap-1.5">
        <div className="min-w-0 flex-1 line-clamp-2 font-medium leading-snug">
          {slot.recipe_name}
        </div>
        <button
          className="mt-0.5 shrink-0 cursor-grab touch-none text-muted-foreground/60 hover:text-foreground"
          aria-label="Réorganiser"
          {...(dragHandleListeners || {})}
        >
          <GripVertical className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Bottom row: compact servings pill, right-aligned. */}
      <div className="mt-1.5 flex items-center justify-end gap-1 text-[11px] text-muted-foreground">
        <Input
          type="number"
          min={1}
          value={slot.servings}
          onChange={(e) => onServings(slot.slot_id, Number(e.target.value))}
          onPointerDown={(e) => e.stopPropagation()}
          className="h-5 w-8 rounded-full px-0 text-center text-[11px]"
          aria-label="Portions"
        />
        <span>pers.</span>
      </div>
    </div>
  );
}
