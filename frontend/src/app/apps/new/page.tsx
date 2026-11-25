import type { Metadata } from "next";

import { NewAppView } from "@/components/apps/new-app-view";

export const metadata: Metadata = { title: "Add app" };

export default function NewAppPage() {
  return <NewAppView />;
}
