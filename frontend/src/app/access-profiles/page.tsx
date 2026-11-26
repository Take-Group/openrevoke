import type { Metadata } from "next";

import { AccessProfilesView } from "@/components/access-profiles/access-profiles-view";

export const metadata: Metadata = { title: "Access profiles" };

export default function AccessProfilesPage() {
  return <AccessProfilesView />;
}
