import type { Metadata } from "next";

import { ResetPasswordView } from "@/components/auth/password-reset-views";

export const metadata: Metadata = { title: "Set a new password" };

/** `?token=` from the reset link (admin or CLI). */
export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const { token } = await searchParams;
  return <ResetPasswordView token={token ?? null} />;
}
