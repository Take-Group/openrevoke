import type { Metadata } from "next";

import { RegisterView } from "@/components/auth/register-view";

export const metadata: Metadata = { title: "Create account" };

/** `?token=` from the invite link the admin passed on. */
export default async function RegisterPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token } = await searchParams;
  return <RegisterView token={token ?? null} />;
}
