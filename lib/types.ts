// Mirrors backend/schemas.py.

export interface Ingredient {
  ingredient_id?: string;
  name: string;
  quantity: number;
  unit: string;
  notes: string;
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

export interface ShoppingItem {
  item_id: string;
  name: string;
  quantity: string;
  source: string;
  is_checked: boolean;
  created_at: string;
  updated_at: string;
}

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

export interface RecipeNutrition {
  calories: number;
  proteins: number;
  lipides: number;
  glucides: number;
  servings: number;
  per_serving: {
    calories: number;
    proteins: number;
    lipides: number;
    glucides: number;
  };
}

export interface ChatMessage {
  role: "user" | "model";
  text: string;
}
