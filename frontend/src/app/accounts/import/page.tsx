import type { Metadata } from "next";

import { ImportAccountsView } from "@/components/apps/import-accounts-view";

export const metadata: Metadata = { title: "Import accounts" };

export default function ImportAccountsPage() {
  return <ImportAccountsView />;
}
