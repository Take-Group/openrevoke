import type { Metadata } from "next";

import { ActionsView, type ActionsTab } from "@/components/actions/actions-view";

export const metadata: Metadata = { title: "Actions" };

const TABS: ActionsTab[] = ["pending", "progress", "done", "failed", "cancelled"];
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function ActionsPage({ searchParams }: { searchParams: Promise<{ tab?: string; batch?: string }> }) {
  const { tab, batch } = await searchParams;
  return (
    <ActionsView
      key={`${tab}-${batch}`}
      initialTab={TABS.find((value) => value === tab)}
      batchId={batch && UUID.test(batch) ? batch : undefined}
    />
  );
}
