import type { Metadata } from "next";

import { PeopleView } from "@/components/people/people-view";
import type { PersonStatus } from "@/lib/api/types";

export const metadata: Metadata = { title: "People" };

export default async function PeoplePage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const { status } = await searchParams;
  const initialStatus: PersonStatus | undefined = status === "active" || status === "left" ? status : undefined;
  return <PeopleView key={status} initialStatus={initialStatus} />;
}
