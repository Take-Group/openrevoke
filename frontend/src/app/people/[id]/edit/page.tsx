import type { Metadata } from "next";

import { EditPersonView } from "@/components/people/edit-person-view";

export const metadata: Metadata = { title: "Edit person" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <EditPersonView id={id} />;
}
