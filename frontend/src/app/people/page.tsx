import type { Metadata } from "next";

import { PeopleView } from "@/components/people/people-view";
import type { PersonStatus } from "@/lib/api/types";

export const metadata: Metadata = { title: "People" };

export default async function PeoplePage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; no_manager?: string }>;
}) {
  const { status, no_manager } = await searchParams;
  const initialStatus: PersonStatus | undefined = status === "active" || status === "left" ? status : undefined;
  const initialNoManager = no_manager === "true";
  return (
    <PeopleView key={`${status}-${no_manager}`} initialStatus={initialStatus} initialNoManager={initialNoManager} />
  );
}
