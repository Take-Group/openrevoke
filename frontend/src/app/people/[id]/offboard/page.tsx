import type { Metadata } from "next";

import { OffboardView } from "@/components/people/offboard-view";

export const metadata: Metadata = { title: "Offboard" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <OffboardView id={id} />;
}
