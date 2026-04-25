// Mirrors backend/schemas.py.

export interface Ingredient {
  ingredient_id?: string;
  name: string;
  quantity: number;
  unit: string;
  notes: string;
  ingredient_db_id?: string | null;
}

export interface Instruction {
  instruction_id?: string;
  step_number?: number;
  instruction_text: string;
}

export interface Recipe {
  recipe_id: string;
  name: string;
  description: string | null;
  prep_time: number;
  cook_time: number;
  servings: number;
  cuisine_type: string | null;
  tags: string[];
  image_url: string | null;
  is_favorite: boolean;
  created_at: string;
  updated_at: string;
  ingredients: Ingredient[];
  instructions: Instruction[];
}

export interface RecipeListResponse {
  recipes: Recipe[];
  total: number;
}

export interface RecipeCreate {
  name: string;
  description?: string;
  prep_time?: number;
  cook_time?: number;
  servings?: number;
  cuisine_type?: string;
  tags?: string[];
  image_url?: string;
  is_favorite?: boolean;
  ingredients: Omit<Ingredient, "ingredient_id">[];
  instructions: Pick<Instruction, "instruction_text">[];
}

export type RecipeUpdate = Partial<RecipeCreate>;

export interface ShoppingContribution {
  contribution_id: string;
  quantity_text: string;
  source_label: string;
  recipe_id: string | null;
  slot_id: string | null;
}

export interface ShoppingItem {
  item_id: string;
  name: string;
  position: number;
  is_checked: boolean;
  category: string | null;
  contributions: ShoppingContribution[];
}

// Order matches the supermarket-walking flow defined in
// backend/services/categorize.py CATEGORIES.
export const SHOPPING_CATEGORIES = [
  "Fruits & Légumes",
  "Boulangerie",
  "Viandes & Poissons",
  "Produits Laitiers",
  "Surgelés",
  "Épicerie",
  "Épices & Herbes",
  "Boissons",
  "Sucreries",
  "Autres",
] as const;
export type ShoppingCategory = (typeof SHOPPING_CATEGORIES)[number];

export interface ShoppingListResponse {
  items: ShoppingItem[];
  total: number;
}

export interface IngredientDb {
  id: string;
  name: string;
  has_nutrition_data: boolean;
  nutrition_data?: Record<string, unknown>;
}

export interface IngredientAlias {
  alias_id: string;
  alias_text: string;
  created_by: "user" | "llm";
}

export interface IngredientRow {
  id: string;
  name: string;
  category: ShoppingCategory | null;
  source: "ciqual" | "user" | "llm";
  modified: boolean;
  modified_by: "user" | "llm" | null;
  modified_at: string | null;
  density_g_per_ml: number | null;
  aliases: IngredientAlias[];
}

export interface IngredientDetail extends IngredientRow {
  nutrition_data: Record<string, number | string | null>;
}

export interface IngredientListResponse {
  items: IngredientRow[];
  total: number;
}

export interface MatchCandidate {
  ingredient_db_id: string;
  name: string;
  reason: string;
  confidence: number;
}

export interface CanonicalRow {
  id: string;
  name: string;
  category: ShoppingCategory | null;
  source: "ciqual" | "user" | "llm";
}

export interface MatchCandidatesResponse {
  exact: CanonicalRow | null;
  llm_candidates: MatchCandidate[];
}

export interface NutritionMacros {
  calories: number;
  proteins: number;
  lipides: number;
  glucides: number;
  salt: number;
  saturated_fats: number;
}

export interface RecipeNutrition extends NutritionMacros {
  servings: number;
  per_serving: NutritionMacros;
}

export interface ChatMessage {
  role: "user" | "model";
  text: string;
}

export interface MealPlanSlot {
  slot_id: string;
  slot_date: string; // YYYY-MM-DD
  position: number;  // 0-based ordering within the day
  recipe_id: string;
  recipe_name: string;
  servings: number;
}

export interface MealPlanWeek {
  week_start: string;
  slots: MealPlanSlot[];
}

export interface NutritionDay {
  date: string;
  macros: Record<string, number>;
}

export type UntrackedReason =
  | "missing_fk"
  | "missing_density"
  | "no_data"
  | "unknown_unit";

export interface UntrackedItem {
  slot_date: string;
  recipe_name: string;
  ingredient_name: string;
  reason: UntrackedReason;
}

export interface WeeklyNutrition {
  week_start: string;
  days: NutritionDay[];
  week: Record<string, number>;
  rdi: Record<string, number>;
  untracked: UntrackedItem[];
}
