"use client";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiSend } from "@/lib/api/client";
import type { RecipeFixOut } from "@/lib/api/recipe-fix-types";

export type RecipeFixDecision = "approve" | "reject";

const DECISION_TEXT: Record<RecipeFixDecision, () => string> = {
  approve: () => "Fix approved. Retry the action to use it.",
  reject: () => "Fix rejected. Runs use the recipe's own steps again.",
};

/** Approve a proposed click recipe fix, or reject / revert one. Shown on the actions that made them. */
export function useRecipeFixDecision(decision: RecipeFixDecision) {
  return useApiMutation({
    mutationFn: (id: string) => apiSend<RecipeFixOut>("POST", `/api/recipe-fixes/${id}/${decision}`),
    invalidate: ["actions"],
    success: DECISION_TEXT[decision],
  });
}
