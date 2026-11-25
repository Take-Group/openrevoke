import type { Metadata } from "next";

import { SlackView } from "@/components/slack/slack-view";

export const metadata: Metadata = { title: "Slack" };

export default async function SlackPage({
  searchParams,
}: {
  searchParams: Promise<{ installed?: string; error?: string }>;
}) {
  const { installed, error } = await searchParams;
  return <SlackView installed={installed} error={error} />;
}
