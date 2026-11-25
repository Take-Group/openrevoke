import type { Metadata } from "next";

import { DiscoveryView } from "@/components/discovery/discovery-view";

export const metadata: Metadata = { title: "Discovery" };

export default function DiscoveryPage() {
  return <DiscoveryView />;
}
