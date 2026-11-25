import type { Metadata } from "next";

import { PersonDetailView, type PersonTab } from "@/components/people/person-detail-view";

export const metadata: Metadata = { title: "Person" };

const TABS: PersonTab[] = ["accounts", "sign-ins", "activity", "sources", "details"];

interface Props {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ tab?: string }>;
}

export default async function PersonPage({ params, searchParams }: Props) {
  const { id } = await params;
  const { tab } = await searchParams;
  return <PersonDetailView id={id} initialTab={TABS.find((value) => value === tab)} />;
}
