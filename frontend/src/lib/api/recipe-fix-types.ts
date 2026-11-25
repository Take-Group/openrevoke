import type { DateTimeString, Uuid } from "@/lib/api/types";

/** `active` fixes run before the recipe's own locators; `proposed` (irreversible click) waits for an admin. */
export type RecipeFixStatus = "proposed" | "active" | "rejected";

/** A local fix of one click recipe step, made by AI repair (GET /api/recipe-fixes, ActionOut.recipe_fixes). */
export interface RecipeFixOut {
  id: Uuid;
  /** Connector key of the recipe, e.g. slack. */
  recipe_app: string;
  recipe_action: string;
  step_id: string;
  step_goal: string;
  irreversible: boolean;
  /** The element the fix finds, readable: role, name, container. */
  locator: string;
  status: RecipeFixStatus;
  /** "ai:<model>" or "admin". */
  author: string;
  /** What was wrong and what the fix picks instead. */
  note: string;
  action_id: Uuid | null;
  created_at: DateTimeString;
  decided_at: DateTimeString | null;
}

export interface RecipeFixList {
  items: RecipeFixOut[];
  total: number;
}
