import type { Metadata } from "next";

import { BulkAppsView } from "@/components/apps/bulk-apps-view";

export const metadata: Metadata = { title: "Add several apps" };

export default function BulkAppsPage() {
  return <BulkAppsView />;
}
