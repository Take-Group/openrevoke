import type { Metadata } from "next";

import { AccessProfileDetailView } from "@/components/access-profiles/access-profile-detail-view";

export const metadata: Metadata = { title: "Access profile" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AccessProfileDetailView id={id} />;
}
