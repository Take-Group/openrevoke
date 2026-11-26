import type { Metadata } from "next";

import { AssignProfilesView } from "@/components/access-profiles/assign-profiles-view";

export const metadata: Metadata = { title: "Add access profiles" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AssignProfilesView id={id} />;
}
