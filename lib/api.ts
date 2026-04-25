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
  quantity_text?: string;
  source_label?: string;
}) =>
  http<ShoppingItem>(`/shopping-list`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateShoppingItem = (
  id: string,
  data: { name?: string; is_checked?: boolean; category?: string }
) =>
  http<ShoppingItem>(`/shopping-list/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const categorizeShoppingListWithAI = (only_uncertain = true) =>
  http<ShoppingListResponse>(
    `/shopping-list/categorize-with-ai${qs({ only_uncertain })}`,
    { method: "POST" }
  );

export const deleteShoppingItem = (id: string) =>
  http<void>(`/shopping-list/${id}`, { method: "DELETE" });

export const deleteShoppingContribution = (contribution_id: string) =>
  http<void>(`/shopping-list/contributions/${contribution_id}`, {
    method: "DELETE",
  });

export const reorderShoppingList = (
  items: { item_id: string; position: number }[]
) =>
  http<ShoppingListResponse>(`/shopping-list/reorder`, {
    method: "PUT",
    body: JSON.stringify({ items }),
  });

export const clearShoppingList = () =>
  http<void>(`/shopping-list`, { method: "DELETE" });

// ---- Meal plan ----
import type { MealPlanSlot, MealPlanWeek } from "./types";

export const getMealPlan = (weekStart: string) =>
  http<MealPlanWeek>(`/meal-plan${qs({ week_start: weekStart })}`);

export const addMealToDay = (data: {
  slot_date: string;
  recipe_id: string;
  servings: number;
}) =>
  http<MealPlanSlot>(`/meal-plan`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateMealServings = (slot_id: string, servings: number) =>
  http<MealPlanSlot>(`/meal-plan/${slot_id}`, {
    method: "PATCH",
    body: JSON.stringify({ servings }),
  });

export const deleteMeal = (slot_id: string) =>
  http<void>(`/meal-plan/${slot_id}`, { method: "DELETE" });

export const reorderMeals = (
  items: { slot_id: string; slot_date: string; position: number }[]
) =>
  http<MealPlanWeek>(`/meal-plan/reorder`, {
    method: "PUT",
    body: JSON.stringify({ items }),
  });

export const generateMealPlan = (
  weekStart: string,
  mealsPerDay = 3,
  overwrite = false
) =>
  http<MealPlanWeek>(
    `/meal-plan/generate${qs({
      week_start: weekStart,
      meals_per_day: mealsPerDay,
      overwrite,
    })}`,
    { method: "POST" }
  );
