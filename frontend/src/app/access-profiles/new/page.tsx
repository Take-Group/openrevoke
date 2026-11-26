import type { Metadata } from "next";

import { NewAccessProfileView } from "@/components/access-profiles/new-access-profile-view";

export const metadata: Metadata = { title: "New access profile" };

export default function NewAccessProfilePage() {
  return <NewAccessProfileView />;
}
