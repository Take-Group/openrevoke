import type { Metadata } from "next";

import { DiscoveredAppView } from "@/components/discovery/discovered-app-view";

export const metadata: Metadata = { title: "Discovered app" };

interface Props {
  params: Promise<{ id: string }>;
}

export default async function DiscoveredAppPage({ params }: Props) {
  const { id } = await params;
  return <DiscoveredAppView key={id} id={id} />;
}
