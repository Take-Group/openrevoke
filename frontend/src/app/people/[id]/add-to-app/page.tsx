import type { Metadata } from "next";

import { AddToAppView } from "@/components/people/add-to-app-view";

export const metadata: Metadata = { title: "Add to app" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AddToAppView id={id} />;
}
