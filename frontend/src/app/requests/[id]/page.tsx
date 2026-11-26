import type { Metadata } from "next";

import { RequestDetailView } from "@/components/requests/request-detail-view";

export const metadata: Metadata = { title: "Access request" };

export default async function AccessRequestPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <RequestDetailView id={id} />;
}
