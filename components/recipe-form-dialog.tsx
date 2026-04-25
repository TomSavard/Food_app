"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import * as api from "@/lib/api";
import type { Recipe } from "@/lib/types";

const UNITS = ["", "g", "kg", "mg", "ml", "cl", "l", "pcs", "c. à café", "c. à soupe"];

interface IngredientRow {
  name: string;
  quantity: number;
  unit: string;
  notes: string;
}

interface InstructionRow {
  instruction_text: string;
}

interface FormState {
  name: string;
  description: string;
  prep_time: number;
  cook_time: number;
  servings: number;
  cuisine_type: string;
  tags: string[];
  ingredients: IngredientRow[];
  instructions: InstructionRow[];
}

const empty: FormState = {
  name: "",
  description: "",
  prep_time: 0,
  cook_time: 0,
  servings: 1,
  cuisine_type: "",
  tags: [],
  ingredients: [{ name: "", quantity: 0, unit: "", notes: "" }],
  instructions: [{ instruction_text: "" }],
};

export function RecipeFormDialog({
  open,
  onOpenChange,
  editing,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  editing: Recipe | null;
  onSaved: (r: Recipe) => void;
}) {
  const [form, setForm] = useState<FormState>(empty);
  const [tagInput, setTagInput] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (editing) {
      setForm({
        name: editing.name,
        description: editing.description || "",
        prep_time: editing.prep_time,
        cook_time: editing.cook_time,
        servings: editing.servings,
        cuisine_type: editing.cuisine_type || "",
        tags: [...(editing.tags || [])],
        ingredients:
          editing.ingredients.length > 0
            ? editing.ingredients.map((i) => ({
                name: i.name,
                quantity: i.quantity || 0,
                unit: i.unit || "",
                notes: i.notes || "",
              }))
            : empty.ingredients,
        instructions:
          editing.instructions.length > 0
            ? editing.instructions.map((s) => ({ instruction_text: s.instruction_text }))
            : empty.instructions,
      });
    } else {
      setForm(empty);
    }
    setTagInput("");
    setError(null);
  }, [open, editing]);

  function addTag() {
    const t = tagInput.trim();
    if (!t || form.tags.includes(t)) return;
    setForm({ ...form, tags: [...form.tags, t] });
    setTagInput("");
  }

  async function submit() {
    if (!form.name.trim()) {
      setError("Le nom est requis");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description || undefined,
        prep_time: form.prep_time,
        cook_time: form.cook_time,
        servings: form.servings,
        cuisine_type: form.cuisine_type || undefined,
        tags: form.tags,
        ingredients: form.ingredients
          .filter((i) => i.name.trim())
          .map((i) => ({
            name: i.name.trim(),
            quantity: Number(i.quantity) || 0,
            unit: i.unit,
            notes: i.notes,
          })),
        instructions: form.instructions
          .filter((s) => s.instruction_text.trim())
          .map((s) => ({ instruction_text: s.instruction_text.trim() })),
      };
      const saved = editing
        ? await api.updateRecipe(editing.recipe_id, payload)
        : await api.createRecipe(payload);
      onSaved(saved);
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur de sauvegarde");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>{editing ? "Modifier la recette" : "Ajouter une recette"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="recipe-name">Nom *</Label>
            <Input
              id="recipe-name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="recipe-desc">Description</Label>
            <Textarea
              id="recipe-desc"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="grid gap-1">
              <Label>Préparation (min)</Label>
              <Input
                type="number"
                min={0}
                value={form.prep_time}
                onChange={(e) => setForm({ ...form, prep_time: Number(e.target.value) })}
              />
            </div>
            <div className="grid gap-1">
              <Label>Cuisson (min)</Label>
              <Input
                type="number"
                min={0}
                value={form.cook_time}
                onChange={(e) => setForm({ ...form, cook_time: Number(e.target.value) })}
              />
            </div>
            <div className="grid gap-1">
              <Label>Portions</Label>
              <Input
                type="number"
                min={1}
                value={form.servings}
                onChange={(e) => setForm({ ...form, servings: Number(e.target.value) })}
              />
            </div>
            <div className="grid gap-1">
              <Label>Cuisine</Label>
              <Input
                value={form.cuisine_type}
                onChange={(e) => setForm({ ...form, cuisine_type: e.target.value })}
              />
            </div>
          </div>

          <div className="grid gap-2">
            <Label>Tags</Label>
            <div className="flex flex-wrap gap-1">
              {form.tags.map((t) => (
                <Badge key={t} variant="secondary" className="cursor-pointer" onClick={() => setForm({ ...form, tags: form.tags.filter((x) => x !== t) })}>
                  {t} ×
                </Badge>
              ))}
            </div>
            <div className="flex gap-2">
              <Input
                placeholder="Ajouter un tag (Entrée pour valider)"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addTag();
                  }
                }}
              />
              <Button type="button" variant="outline" onClick={addTag}>
                Ajouter
              </Button>
            </div>
          </div>

          <section className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Ingrédients</Label>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() =>
                  setForm({
                    ...form,
                    ingredients: [...form.ingredients, { name: "", quantity: 0, unit: "", notes: "" }],
                  })
                }
              >
                <Plus className="h-3 w-3" /> Ligne
              </Button>
            </div>
            <div className="space-y-2">
              {form.ingredients.map((row, idx) => (
                <div key={idx} className="grid grid-cols-12 gap-2">
                  <Input
                    className="col-span-5"
                    placeholder="Nom"
                    value={row.name}
                    onChange={(e) => {
                      const ings = [...form.ingredients];
                      ings[idx] = { ...row, name: e.target.value };
                      setForm({ ...form, ingredients: ings });
                    }}
                  />
                  <Input
                    className="col-span-2"
                    type="number"
                    placeholder="Qté"
                    value={row.quantity || ""}
                    onChange={(e) => {
                      const ings = [...form.ingredients];
                      ings[idx] = { ...row, quantity: Number(e.target.value) };
                      setForm({ ...form, ingredients: ings });
                    }}
                  />
                  <select
                    className="col-span-2 rounded-md border border-input bg-background text-sm"
                    value={row.unit}
                    onChange={(e) => {
                      const ings = [...form.ingredients];
                      ings[idx] = { ...row, unit: e.target.value };
                      setForm({ ...form, ingredients: ings });
                    }}
                  >
                    {UNITS.map((u) => (
                      <option key={u} value={u}>
                        {u || "—"}
                      </option>
                    ))}
                  </select>
                  <Input
                    className="col-span-2"
                    placeholder="Notes"
                    value={row.notes}
                    onChange={(e) => {
                      const ings = [...form.ingredients];
                      ings[idx] = { ...row, notes: e.target.value };
                      setForm({ ...form, ingredients: ings });
                    }}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="col-span-1"
                    onClick={() => {
                      const ings = form.ingredients.filter((_, i) => i !== idx);
                      setForm({ ...form, ingredients: ings.length ? ings : empty.ingredients });
                    }}
                    aria-label="Supprimer"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </section>

          <section className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>Instructions</Label>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() =>
                  setForm({
                    ...form,
                    instructions: [...form.instructions, { instruction_text: "" }],
                  })
                }
              >
                <Plus className="h-3 w-3" /> Étape
              </Button>
            </div>
            <div className="space-y-2">
              {form.instructions.map((row, idx) => (
                <div key={idx} className="flex gap-2">
                  <span className="mt-2 text-sm text-muted-foreground w-6">{idx + 1}.</span>
                  <Textarea
                    rows={2}
                    value={row.instruction_text}
                    onChange={(e) => {
                      const ins = [...form.instructions];
                      ins[idx] = { instruction_text: e.target.value };
                      setForm({ ...form, instructions: ins });
                    }}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      const ins = form.instructions.filter((_, i) => i !== idx);
                      setForm({ ...form, instructions: ins.length ? ins : empty.instructions });
                    }}
                    aria-label="Supprimer"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </section>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            Annuler
          </Button>
          <Button onClick={submit} disabled={submitting}>
            {submitting ? "Sauvegarde…" : editing ? "Mettre à jour" : "Créer"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
