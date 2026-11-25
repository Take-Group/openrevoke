import type { Metadata } from "next";

import { ImportPeopleView } from "@/components/people/import-people-view";

export const metadata: Metadata = { title: "Import people" };

export default function Page() {
  return <ImportPeopleView />;
}
