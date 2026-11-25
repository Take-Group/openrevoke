import type { Metadata } from "next";

import { MyAccessView } from "@/components/me/my-access-view";

export const metadata: Metadata = { title: "My access" };

export default function MyAccessPage() {
  return <MyAccessView />;
}
