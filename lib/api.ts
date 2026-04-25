// Typed API client. Same-origin (Vercel routes /api/* to the Python function).

import type {
  IngredientDb,
  Recipe,
  RecipeCreate,
  RecipeListResponse,
  RecipeNutrition,
  RecipeUpdate,
  ShoppingItem,
  ShoppingListResponse,
} from "./types";

const BASE = "/api";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${detail || res.statusText}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface RecipeFilters {
  search?: string;
  cuisine?: string;
  ingredient?: string;
  tag?: string;
  skip?: number;
  limit?: number;
}

function qs(params: Record<string, unknown> | object): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    sp.append(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

// ---- Recipes ----
export const listRecipes = (filters: RecipeFilters = {}) =>
  http<RecipeListResponse>(`/recipes${qs(filters)}`);

export const getRecipe = (id: string) => http<Recipe>(`/recipes/${id}`);

export const createRecipe = (data: RecipeCreate) =>
  http<Recipe>(`/recipes`, { method: "POST", body: JSON.stringify(data) });

export const updateRecipe = (id: string, data: RecipeUpdate) =>
  http<Recipe>(`/recipes/${id}`, { method: "PUT", body: JSON.stringify(data) });

export const deleteRecipe = (id: string) =>
  http<void>(`/recipes/${id}`, { method: "DELETE" });

export const toggleFavorite = (id: string, is_favorite: boolean) =>
  http<Recipe>(`/recipes/${id}/favorite${qs({ is_favorite })}`, {
    method: "PATCH",
  });

export const getRecipeNutrition = (id: string) =>
  http<RecipeNutrition>(`/recipes/${id}/nutrition`);

// ---- Ingredient DB ----
export const searchIngredients = (q: string, limit = 10) =>
  http<IngredientDb[]>(`/ingredients/search${qs({ q, limit })}`);

export const getIngredientDb = (id: string) =>
  http<IngredientDb>(`/ingredients/${id}`);

// ---- Shopping list ----
export const getShoppingList = (include_checked = true) =>
  http<ShoppingListResponse>(`/shopping-list${qs({ include_checked })}`);

export const addShoppingItem = (data: {
  name: string;
  quantity?: string;
  source?: string;
  is_checked?: boolean;
}) => http<ShoppingItem>(`/shopping-list`, { method: "POST", body: JSON.stringify(data) });

export const updateShoppingItem = (id: string, data: { is_checked?: boolean }) =>
  http<ShoppingItem>(`/shopping-list/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const deleteShoppingItem = (id: string) =>
  http<void>(`/shopping-list/${id}`, { method: "DELETE" });

export const clearShoppingList = () =>
  http<void>(`/shopping-list`, { method: "DELETE" });

// ---- Meal plan ----
import type { MealPlanSlot, MealPlanWeek, MealSlot } from "./types";

export const getMealPlan = (weekStart: string) =>
  http<MealPlanWeek>(`/meal-plan${qs({ week_start: weekStart })}`);

export const setMealPlanSlot = (data: {
  slot_date: string;
  slot: MealSlot;
  recipe_id: string;
  servings: number;
}) =>
  http<MealPlanSlot>(`/meal-plan/slot`, {
    method: "PUT",
    body: JSON.stringify(data),
  });

export const clearMealPlanSlot = (slot_date: string, slot: MealSlot) =>
  http<void>(`/meal-plan/slot${qs({ slot_date, slot })}`, { method: "DELETE" });

export const generateMealPlan = (weekStart: string, overwrite = false) =>
  http<MealPlanWeek>(
    `/meal-plan/generate${qs({ week_start: weekStart, overwrite })}`,
    { method: "POST" }
  );
