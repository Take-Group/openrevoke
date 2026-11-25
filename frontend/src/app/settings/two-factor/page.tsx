import type { Metadata } from "next";

import { TwoFactorView } from "@/components/settings/two-factor-view";

export const metadata: Metadata = { title: "Two-factor authentication" };

export default function TwoFactorPage() {
  return <TwoFactorView />;
}
