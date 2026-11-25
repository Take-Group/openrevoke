import type { Metadata } from "next";

import { RequestAccessView } from "@/components/me/request-access-view";

export const metadata: Metadata = { title: "Request access" };

/** `?app=` preselects an app. */
export default async function RequestAccessPage({ searchParams }: { searchParams: Promise<{ app?: string }> }) {
  const { app } = await searchParams;
  return <RequestAccessView appId={app ?? null} />;
}
