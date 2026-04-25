"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Sparkles, Trash2, X } from "lucide-react";
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
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import * as api from "@/lib/api";
import type {
  ShoppingCategory,
  ShoppingContribution,
  ShoppingItem,
} from "@/lib/types";
import { SHOPPING_CATEGORIES } from "@/lib/types";
import { aggregate } from "@/lib/quantity";

export default function ShoppingPage() {
  const [items, setItems] = useState<ShoppingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [aiBusy, setAiBusy] = useState(false);

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

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const activeItem = useMemo(
    () => items.find((it) => it.item_id === activeId) || null,
    [items, activeId]
  );

  // Group items by category, in the configured supermarket order. Empty
  // categories are skipped — except while a drag is active, when we render
  // every category so the user has an obvious drop target.
  const sections = useMemo(() => {
    const map = new Map<ShoppingCategory, ShoppingItem[]>();
    for (const cat of SHOPPING_CATEGORIES) map.set(cat, []);
    for (const it of items) {
      const cat: ShoppingCategory =
        (it.category as ShoppingCategory) && SHOPPING_CATEGORIES.includes(it.category as ShoppingCategory)
          ? (it.category as ShoppingCategory)
          : "Autres";
      map.get(cat)!.push(it);
    }
    for (const arr of map.values()) {
      arr.sort((a, b) => a.position - b.position);
    }
    return map;
  }, [items]);

  function handleDragStart(e: DragStartEvent) {
    setActiveId(String(e.active.id));
  }

  function handleDragOver(e: DragOverEvent) {
    const { active, over } = e;
    if (!over) return;
    const aId = String(active.id);
    const oId = String(over.id);
    if (aId === oId || oId === "trash") return;

    setItems((prev) => {
      const moving = prev.find((it) => it.item_id === aId);
      if (!moving) return prev;

      // Drop on a category header → move to that category, append to end.
      const overCat = oId.startsWith("cat:") ? (oId.slice(4) as ShoppingCategory) : null;
      const overItem = !overCat ? prev.find((it) => it.item_id === oId) : null;
      if (!overCat && !overItem) return prev;

      const targetCat: ShoppingCategory = overCat ?? (overItem!.category as ShoppingCategory) ?? "Autres";

      // Same-category reorder.
      if ((moving.category ?? "Autres") === targetCat && overItem) {
        const inCat = prev
          .filter((x) => (x.category ?? "Autres") === targetCat)
          .sort((a, b) => a.position - b.position);
        const oldIdx = inCat.findIndex((x) => x.item_id === aId);
        const newIdx = inCat.findIndex((x) => x.item_id === overItem.item_id);
        const reordered = arrayMove(inCat, oldIdx, newIdx).map((x, i) => ({
          ...x,
          position: i,
        }));
        return prev.map((x) => reordered.find((r) => r.item_id === x.item_id) || x);
      }

      // Cross-category move.
      if ((moving.category ?? "Autres") !== targetCat) {
        const sourceCat = moving.category ?? "Autres";
        const stayingInSource = prev
          .filter((x) => (x.category ?? "Autres") === sourceCat && x.item_id !== aId)
          .sort((a, b) => a.position - b.position)
          .map((x, i) => ({ ...x, position: i }));
        const inTarget = prev
          .filter((x) => (x.category ?? "Autres") === targetCat)
          .sort((a, b) => a.position - b.position);
        const insertIdx = overItem
          ? inTarget.findIndex((x) => x.item_id === overItem.item_id)
          : inTarget.length;
        const movedItem: ShoppingItem = { ...moving, category: targetCat };
        inTarget.splice(insertIdx, 0, movedItem);
        const renumberedTarget = inTarget.map((x, i) => ({ ...x, position: i }));
        const untouched = prev.filter(
          (x) =>
            (x.category ?? "Autres") !== sourceCat &&
            (x.category ?? "Autres") !== targetCat
        );
        return [...untouched, ...stayingInSource, ...renumberedTarget];
      }
      return prev;
    });
  }

  async function handleDragEnd(e: DragEndEvent) {
    const overId = e.over?.id;
    const droppedId = String(e.active.id);
    setActiveId(null);

    if (overId === "trash") {
      setItems((prev) => prev.filter((it) => it.item_id !== droppedId));
      try {
        await api.deleteShoppingItem(droppedId);
      } catch {
        load();
      }
      return;
    }

    // Persist: if the dropped item changed category, PATCH it (which also
    // teaches the knowledge base). Then push the global reordering.
    const dropped = items.find((it) => it.item_id === droppedId);
    try {
      if (dropped && dropped.category) {
        // Always send the current category — even if unchanged, it's cheap
        // and idempotent. Backend's learn_category persists user preference.
        await api.updateShoppingItem(droppedId, { category: dropped.category });
      }
      await api.reorderShoppingList(
        items.map((it) => ({ item_id: it.item_id, position: it.position }))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de réorganisation");
      load();
    }
  }

  async function toggleChecked(it: ShoppingItem) {
    const next = !it.is_checked;
    setItems((prev) =>
      prev.map((x) => (x.item_id === it.item_id ? { ...x, is_checked: next } : x))
    );
    try {
      await api.updateShoppingItem(it.item_id, { is_checked: next });
    } catch {
      load();
    }
  }

  async function removeContribution(item_id: string, contribution_id: string) {
    setItems((prev) =>
      prev
        .map((x) =>
          x.item_id === item_id
            ? {
                ...x,
                contributions: x.contributions.filter(
                  (c) => c.contribution_id !== contribution_id
                ),
              }
            : x
        )
        .filter((x) => x.contributions.length > 0)
    );
    try {
      await api.deleteShoppingContribution(contribution_id);
    } catch {
      load();
    }
  }

  async function clearAll() {
    if (!confirm("Vider toute la liste de courses ?")) return;
    await api.clearShoppingList();
    setItems([]);
  }

  async function categorizeWithAI() {
    setAiBusy(true);
    setError(null);
    try {
      const res = await api.categorizeShoppingListWithAI(true);
      setItems(res.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur lors du tri par l'IA");
    } finally {
      setAiBusy(false);
    }
  }

  function onAdded(it: ShoppingItem) {
    setItems((prev) => {
      const idx = prev.findIndex((x) => x.item_id === it.item_id);
      return idx >= 0 ? prev.map((x, i) => (i === idx ? it : x)) : [...prev, it];
    });
  }

  const dragging = activeId !== null;
  const allEmpty = items.length === 0;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Liste de courses</h1>
        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={categorizeWithAI} disabled={aiBusy || allEmpty} variant="outline">
            <Sparkles className="h-4 w-4" /> {aiBusy ? "Analyse…" : "Catégoriser avec l'IA"}
          </Button>
          {items.length > 0 && (
            <Button variant="outline" onClick={clearAll}>
              Vider
            </Button>
          )}
        </div>
      </div>

      <AddManualBlock onAdded={onAdded} />

      {error && <p className="text-destructive">{error}</p>}
      {loading && <p className="text-muted-foreground">Chargement…</p>}
      {!loading && allEmpty && (
        <p className="text-muted-foreground">
          La liste est vide. Ajoute manuellement, ou planifie un repas dans la
          semaine pour la remplir automatiquement.
        </p>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="space-y-4">
          {SHOPPING_CATEGORIES.map((cat) => {
            const inCat = sections.get(cat) || [];
            // Hide empty sections unless the user is dragging — then show
            // them as drop targets.
            if (inCat.length === 0 && !dragging) return null;
            return (
              <CategorySection
                key={cat}
                category={cat}
                items={inCat}
                onToggleChecked={toggleChecked}
                onRemoveContribution={removeContribution}
              />
            );
          })}
        </div>

        <DragOverlay>
          {activeItem && (
            <ItemRow
              item={activeItem}
              onToggleChecked={() => {}}
              onRemoveContribution={() => {}}
              isOverlay
            />
          )}
        </DragOverlay>

        <TrashZone visible={dragging} />
      </DndContext>
    </div>
  );
}

function CategorySection({
  category,
  items,
  onToggleChecked,
  onRemoveContribution,
}: {
  category: ShoppingCategory;
  items: ShoppingItem[];
  onToggleChecked: (it: ShoppingItem) => void;
  onRemoveContribution: (item_id: string, contribution_id: string) => void;
}) {
  const droppableId = `cat:${category}`;
  const { setNodeRef: setHeaderRef, isOver } = useDroppable({ id: droppableId });
  return (
    <section className="space-y-2">
      <div
        ref={setHeaderRef}
        className={
          "flex items-center gap-2 rounded-lg px-2 py-1 text-sm font-semibold tracking-tight transition-colors " +
          (isOver
            ? "bg-primary/15 text-primary"
            : "text-muted-foreground")
        }
      >
        <span>{category}</span>
        {items.length > 0 && (
          <span className="text-xs text-muted-foreground">· {items.length}</span>
        )}
      </div>
      <SortableContext
        items={items.length > 0 ? items.map((it) => it.item_id) : [droppableId]}
        strategy={verticalListSortingStrategy}
      >
        {items.length === 0 && (
          <DroppableEmpty id={droppableId} />
        )}
        <div className="flex flex-col gap-2">
          {items.map((it) => (
            <SortableRow
              key={it.item_id}
              item={it}
              onToggleChecked={onToggleChecked}
              onRemoveContribution={onRemoveContribution}
            />
          ))}
        </div>
      </SortableContext>
    </section>
  );
}

function DroppableEmpty({ id }: { id: string }) {
  const { setNodeRef, isOver } = useDroppable({ id });
  return (
    <div
      ref={setNodeRef}
      className={
        "rounded-xl border border-dashed border-border/60 px-2 py-4 text-center text-xs text-muted-foreground transition-colors " +
        (isOver ? "border-primary/60 bg-primary/10" : "")
      }
    >
      Glisser ici
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
    >
      <Trash2 className="h-4 w-4" />
      <span>{isOver ? "Lâcher pour supprimer" : "Glisser ici pour supprimer"}</span>
    </div>
  );
}

function SortableRow({
  item,
  onToggleChecked,
  onRemoveContribution,
}: {
  item: ShoppingItem;
  onToggleChecked: (it: ShoppingItem) => void;
  onRemoveContribution: (item_id: string, contribution_id: string) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: item.item_id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={isDragging ? "cursor-grabbing" : "cursor-grab"}
      {...attributes}
      {...listeners}
    >
      <ItemRow
        item={item}
        onToggleChecked={onToggleChecked}
        onRemoveContribution={onRemoveContribution}
      />
    </div>
  );
}

function ItemRow({
  item,
  onToggleChecked,
  onRemoveContribution,
  isOverlay,
}: {
  item: ShoppingItem;
  onToggleChecked: (it: ShoppingItem) => void;
  onRemoveContribution: (item_id: string, contribution_id: string) => void;
  isOverlay?: boolean;
}) {
  const total = aggregate(item.contributions);
  return (
    <div
      className={
        "surface select-none p-3 touch-none " +
        (isOverlay ? "scale-[1.02] shadow-2xl ring-1 ring-primary/40 rotate-[0.5deg] " : "") +
        (item.is_checked ? "opacity-60" : "")
      }
    >
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={item.is_checked}
          onChange={() => onToggleChecked(item)}
          onClick={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
          className="mt-1 h-4 w-4 shrink-0 cursor-pointer"
          aria-label={item.is_checked ? "Décocher" : "Cocher"}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0">
            <span
              className={
                "break-words font-medium leading-snug " +
                (item.is_checked ? "line-through" : "")
              }
            >
              {item.name}
            </span>
            {total.display && (
              <span className="text-sm text-muted-foreground">· {total.display}</span>
            )}
          </div>
          {item.contributions.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {item.contributions.map((c) => (
                <ContributionChip
                  key={c.contribution_id}
                  contribution={c}
                  onRemove={() =>
                    onRemoveContribution(item.item_id, c.contribution_id)
                  }
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ContributionChip({
  contribution,
  onRemove,
}: {
  contribution: ShoppingContribution;
  onRemove: () => void;
}) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border bg-background/50 px-2 py-0.5 text-xs text-muted-foreground">
      <span className="font-medium text-foreground/80">
        {contribution.quantity_text || "—"}
      </span>
      <span className="text-muted-foreground">· {contribution.source_label}</span>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onRemove();
        }}
        onPointerDown={(e) => e.stopPropagation()}
        className="text-muted-foreground/60 hover:text-destructive"
        aria-label="Supprimer cette source"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

function AddManualBlock({ onAdded }: { onAdded: (it: ShoppingItem) => void }) {
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState("");
  const [busy, setBusy] = useState(false);

  async function add() {
    const n = name.trim();
    if (!n) return;
    setBusy(true);
    try {
      const it = await api.addShoppingItem({
        name: n,
        quantity_text: quantity.trim(),
        source_label: "Manuel",
      });
      onAdded(it);
      setName("");
      setQuantity("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="p-4">
      <div className="space-y-2">
        <Label>Ajouter un ingrédient</Label>
        <div className="flex flex-wrap gap-2">
          <Input
            placeholder="Nom"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && add()}
            className="min-w-[180px] flex-1"
          />
          <Input
            placeholder="Quantité (ex: 500g, 2)"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && add()}
            className="w-44"
          />
          <Button onClick={add} disabled={busy || !name.trim()}>
            <Plus className="h-4 w-4" /> Ajouter
          </Button>
        </div>
      </div>
    </Card>
  );
}
