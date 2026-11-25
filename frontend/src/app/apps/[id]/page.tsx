import type { Metadata } from "next";

import type { AccountsFilter } from "@/components/apps/app-accounts-tab";
import { AppDetailView, type AppTab } from "@/components/apps/app-detail-view";

export const metadata: Metadata = { title: "App" };

const TABS: AppTab[] = ["accounts", "connection", "sync", "settings"];
const FILTERS: AccountsFilter[] = ["all", "unassigned", "removed"];

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string; accounts?: string }>;
}

export default async function AppPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { tab, accounts } = await searchParams;
  return (
    <AppDetailView
      key={`${id}-${tab}-${accounts}`}
      id={id}
      initialTab={TABS.find((value) => value === tab)}
      initialAccountsFilter={FILTERS.find((value) => value === accounts)}
    />
  );
}
