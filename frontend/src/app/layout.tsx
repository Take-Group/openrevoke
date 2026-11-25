import type { Metadata } from "next";
import { cookies } from "next/headers";
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";

import { AuthGate } from "@/components/auth/auth-gate";
import { Providers } from "@/components/providers";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Open Revoke",
    template: "%s · Open Revoke",
  },
  description: "People, SaaS accounts and costs in one place",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // The sidebar writes its collapsed state to this cookie (components/ui/sidebar.tsx).
  const sidebarOpen = (await cookies()).get("sidebar_state")?.value !== "false";
  return (
    // next-themes sets the theme class on <html> before hydration.
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full">
        <Providers>
          {/* Sign-in pages without the sidebar, the panel only for a signed-in user. */}
          <AuthGate sidebarOpen={sidebarOpen}>{children}</AuthGate>
        </Providers>
      </body>
    </html>
  );
}
