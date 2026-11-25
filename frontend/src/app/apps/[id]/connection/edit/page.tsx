import type { Metadata } from "next";

import { ConnectionFormView } from "@/components/apps/connection-form-view";

export const metadata: Metadata = { title: "Connection" };

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ connector?: string }>;
}

export default async function ConnectionEditPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { connector } = await searchParams;
  return <ConnectionFormView key={`${id}-${connector}`} appId={id} initialConnector={connector} />;
}
