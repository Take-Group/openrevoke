import type { Metadata } from "next";

import { SetupView } from "@/components/auth/setup-view";

export const metadata: Metadata = { title: "Set up" };

/** `?token=` from the setup link printed on the server (`open-revoke setup-link`). */
export default async function SetupPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token } = await searchParams;
  return <SetupView token={token ?? null} />;
}
