"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { AddressWarning } from "@/components/layout/address-warning";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { BrandWordmark } from "@/components/layout/brand-mark";
import { CommandMenu } from "@/components/layout/command-menu";
import { PageTransition } from "@/components/layout/page-transition";
import { UpdateNotice } from "@/components/layout/update-notice";
import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { useAuthState } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

/**
 * Phones only: the sidebar is a sheet there, so something has to open it.
 * Desktop has no top bar; everything lives in the sidebar.
 */
function MobileBar() {
  return (
    <div className="sticky top-0 z-20 flex h-12 items-center gap-2 border-b bg-page/85 px-3 backdrop-blur md:hidden">
      <SidebarTrigger className="text-muted-foreground" />
      <Link href="/">
        <BrandWordmark />
      </Link>
    </div>
  );
}

/** Pages that use the whole width: the live view of the shared browser. */
const FULL_WIDTH_PAGES = new Set(["/browser"]);

/** Sidebar and content frame shared by every page (used in the root layout). */
export function AdminLayout({ children, defaultOpen }: { children: React.ReactNode; defaultOpen: boolean }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const fullWidth = FULL_WIDTH_PAGES.has(usePathname());
  const admin = useAuthState().data?.user?.role === "admin";
  return (
    <SidebarProvider defaultOpen={defaultOpen}>
      <AppSidebar onSearch={() => setSearchOpen(true)} />
      <SidebarInset className="min-w-0">
        <MobileBar />
        <AddressWarning className="mx-4 mt-4 md:mx-6" />
        <UpdateNotice className="mx-4 mt-4 md:mx-6" />
        {/* Padding matches the page bar of `PageHeader`, which bleeds to the edges (PAGE_BAR). */}
        <div className={cn("flex w-full flex-1 flex-col px-4 pt-5 pb-10 md:px-6 md:pt-6", fullWidth && "pb-5")}>
          <PageTransition>{children}</PageTransition>
        </div>
      </SidebarInset>
      {/* Search reads people and apps: admins only. */}
      {admin && <CommandMenu open={searchOpen} onOpenChange={setSearchOpen} />}
    </SidebarProvider>
  );
}
