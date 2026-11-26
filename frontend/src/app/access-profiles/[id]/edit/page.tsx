import type { Metadata } from "next";

import { EditAccessProfileView } from "@/components/access-profiles/edit-access-profile-view";

export const metadata: Metadata = { title: "Edit access profile" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <EditAccessProfileView id={id} />;
}
