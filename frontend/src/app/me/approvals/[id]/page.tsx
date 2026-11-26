import type { Metadata } from "next";

import { ApprovalDetailView } from "@/components/me/approval-detail-view";

export const metadata: Metadata = { title: "Access request" };

export default async function ApprovalPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ApprovalDetailView id={id} />;
}
