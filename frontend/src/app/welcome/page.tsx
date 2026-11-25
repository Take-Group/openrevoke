import type { Metadata } from "next";

import { WelcomeView, type WelcomeStep } from "@/components/onboarding/welcome-view";

export const metadata: Metadata = { title: "Welcome" };

const STEPS: WelcomeStep[] = ["people", "chat", "manager"];

export default async function WelcomePage({ searchParams }: { searchParams: Promise<{ step?: string }> }) {
  const { step } = await searchParams;
  return <WelcomeView initialStep={STEPS.find((value) => value === step)} />;
}
