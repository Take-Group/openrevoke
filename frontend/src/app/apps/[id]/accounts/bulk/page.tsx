import type { Metadata } from "next";

import { PasteAccountsView } from "@/components/apps/paste-accounts-view";

export const metadata: Metadata = { title: "Paste e-mails" };

export default async function PasteAccountsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PasteAccountsView appId={id} />;
}
