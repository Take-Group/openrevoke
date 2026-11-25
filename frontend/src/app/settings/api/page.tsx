import type { Metadata } from "next";

import { ApiTokensView } from "@/components/api-tokens/api-tokens-view";

export const metadata: Metadata = { title: "API and MCP" };

export default function ApiTokensPage() {
  return <ApiTokensView />;
}
