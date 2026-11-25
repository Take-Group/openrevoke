import type { Metadata } from "next";

import { RequestsView } from "@/components/requests/requests-view";

export const metadata: Metadata = { title: "Access requests" };

export default function RequestsPage() {
  return <RequestsView />;
}
