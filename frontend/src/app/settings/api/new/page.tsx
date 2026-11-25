import type { Metadata } from "next";

import { NewApiTokenView } from "@/components/api-tokens/new-api-token-view";

export const metadata: Metadata = { title: "Create API token" };

export default function NewApiTokenPage() {
  return <NewApiTokenView />;
}
