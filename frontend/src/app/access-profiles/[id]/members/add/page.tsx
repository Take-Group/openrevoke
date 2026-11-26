import type { Metadata } from "next";

import { AddMembersView } from "@/components/access-profiles/add-members-view";

export const metadata: Metadata = { title: "Add people to profile" };

export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ missing?: string }>;
}) {
  const { id } = await params;
  const { missing } = await searchParams;
  // ?missing=1 preselects the members who miss access ("Create actions for N people").
  return <AddMembersView key={missing ?? ""} id={id} missing={missing === "1"} />;
}
