"use client";

import { useQuery } from "@tanstack/react-query";

import { useApiMutation } from "@/hooks/use-api-mutation";
import { apiGet, apiSend } from "@/lib/api/client";
import type { OnboardingChoices, OnboardingOut } from "@/lib/api/onboarding-types";

/** The /welcome answers and the setup checklist (worked out by the API from the data). */
export function useOnboarding() {
  return useQuery({ queryKey: ["onboarding"], queryFn: () => apiGet<OnboardingOut>("/api/onboarding") });
}

export function useSaveOnboardingChoices() {
  return useApiMutation({
    mutationFn: (data: OnboardingChoices) => apiSend<OnboardingOut>("PUT", "/api/onboarding/choices", data),
    invalidate: ["onboarding"],
  });
}

export function useDismissOnboarding() {
  return useApiMutation({
    mutationFn: () => apiSend<OnboardingOut>("POST", "/api/onboarding/dismiss"),
    invalidate: ["onboarding"],
  });
}
