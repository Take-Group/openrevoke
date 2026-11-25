import type { Metadata } from "next";

import { NewAccountView } from "@/components/apps/new-account-view";

export const metadata: Metadata = { title: "Add account" };

export default async function NewAccountPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <NewAccountView appId={id} />;
}
