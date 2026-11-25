import type { Metadata } from "next";

import { NewPersonView } from "@/components/people/new-person-view";

export const metadata: Metadata = { title: "Add person" };

export default function Page() {
  return <NewPersonView />;
}
