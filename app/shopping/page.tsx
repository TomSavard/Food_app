"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Trash2, X } from "lucide-react";
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
import type { ShoppingContribution, ShoppingItem } from "@/lib/types";
import { aggregate } from "@/lib/quantity";

export default function ShoppingPage() {
  const [items, setItems] = useState<ShoppingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);

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
      const oldIdx = prev.findIndex((it) => it.item_id === aId);
      const newIdx = prev.findIndex((it) => it.item_id === oId);
      if (oldIdx < 0 || newIdx < 0) return prev;
      return arrayMove(prev, oldIdx, newIdx).map((it, i) => ({ ...it, position: i }));
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
    try {
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

  function onAdded(it: ShoppingItem) {
    setItems((prev) => {
      const idx = prev.findIndex((x) => x.item_id === it.item_id);
      return idx >= 0 ? prev.map((x, i) => (i === idx ? it : x)) : [it, ...prev];
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-2xl font-semibold tracking-tight">Liste de courses</h1>
        {items.length > 0 && (
          <Button variant="outline" onClick={clearAll}>
            Vider la liste
          </Button>
        )}
      </div>

      <AddManualBlock onAdded={onAdded} />

      {error && <p className="text-destructive">{error}</p>}
      {loading && <p className="text-muted-foreground">Chargement…</p>}
      {!loading && items.length === 0 && (
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
        <SortableContext
          items={items.map((it) => it.item_id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="flex flex-col gap-2">
            {items.map((it) => (
              <SortableRow
                key={it.item_id}
                item={it}
                onToggleChecked={toggleChecked}
                onRemoveContribution={removeContribution}
              />
            ))}
          </div>
        </SortableContext>

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

        <TrashZone visible={activeId !== null} />
      </DndContext>
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
