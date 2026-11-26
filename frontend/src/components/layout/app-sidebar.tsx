"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SearchIcon } from "lucide-react";

import { BrandMark, BrandName } from "@/components/layout/brand-mark";

import { isItemActive, NAV_APPROVALS, NAV_MAIN, NAV_SETTINGS, NAV_TOOLS, NAV_USER, type NavItem } from "@/components/layout/nav-items";
import { NavUser } from "@/components/layout/nav-user";
import { Kbd } from "@/components/ui/kbd";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import { useAuthState } from "@/hooks/use-auth";
import { useDashboard } from "@/hooks/use-dashboard";
import { useMyApprovals } from "@/hooks/use-me";

/** `badges`: count per item href (pending actions, approvals waiting for the user). */
function NavGroup({ label, items, badges = {} }: { label?: string; items: NavItem[]; badges?: Record<string, number> }) {
  const pathname = usePathname();
  const { isMobile, setOpenMobile } = useSidebar();
  return (
    <SidebarGroup>
      {label && <SidebarGroupLabel>{label}</SidebarGroupLabel>}
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            // /me/approvals is not also "My access" (/me): the longer matching item wins.
            const active =
              isItemActive(pathname, item) &&
              !items.some((other) => other.href.length > item.href.length && other.href.startsWith(item.href) && isItemActive(pathname, other));
            return (
              <SidebarMenuItem key={item.href}>
                <SidebarMenuButton
                  render={<Link href={item.href} onClick={() => isMobile && setOpenMobile(false)} />}
                  isActive={active}
                  tooltip={item.title}
                >
                  <item.icon />
                  <span>{item.title}</span>
                </SidebarMenuButton>
                {item.children && active && (
                  <SidebarMenuSub className="mx-0 translate-x-0 gap-0 border-l-0 py-0 pr-0 pl-7">
                    {item.children.map((child) => (
                      <SidebarMenuSubItem key={child.href}>
                        <SidebarMenuSubButton
                          render={<Link href={child.href} onClick={() => isMobile && setOpenMobile(false)} />}
                          isActive={pathname === child.href}
                          className="h-9 rounded-lg px-2.5 text-sm text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground data-active:bg-transparent data-active:font-medium data-active:text-foreground"
                        >
                          {child.title}
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    ))}
                  </SidebarMenuSub>
                )}
                {(badges[item.href] ?? 0) > 0 && (
                  <SidebarMenuBadge
                    aria-label={`${badges[item.href]} waiting for approval`}
                    className="top-2! h-4 min-w-4 rounded-full bg-foreground px-1.5 text-[0.6875rem] leading-none text-background peer-hover/menu-button:text-background peer-data-active/menu-button:text-background"
                  >
                    {badges[item.href]}
                  </SidebarMenuBadge>
                )}
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

/** Logo with the collapse button; collapsed, the button sits under the logo. */
function Brand({ home }: { home: string }) {
  return (
    <div className="flex items-center gap-1 group-data-[collapsible=icon]:flex-col">
      <SidebarMenu className="min-w-0 flex-1">
        <SidebarMenuItem>
          <SidebarMenuButton
            render={<Link href={home} />}
            tooltip="Open Revoke"
            className="h-9 gap-2 px-1.5 text-foreground hover:bg-transparent group-data-[collapsible=icon]:p-1.5!"
          >
            <BrandMark size={20} />
            <BrandName className="group-data-[collapsible=icon]:hidden" />
          </SidebarMenuButton>
        </SidebarMenuItem>
      </SidebarMenu>
      <SidebarTrigger className="shrink-0 text-muted-foreground hover:text-foreground max-md:hidden" />
    </div>
  );
}

function SearchButton({ onSearch }: { onSearch: () => void }) {
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <SidebarMenuButton
          variant="outline"
          tooltip="Search (⌘K)"
          onClick={onSearch}
          className="font-normal text-muted-foreground hover:text-foreground"
        >
          <SearchIcon />
          <span className="flex-1">Search</span>
          <Kbd className="border-0 bg-transparent group-data-[collapsible=icon]:hidden">⌘K</Kbd>
        </SidebarMenuButton>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}

/** The Approvals item with its count, for anyone who manages people or has a request waiting for them. */
function useApprovalsItem(): { items: NavItem[]; badges: Record<string, number> } {
  const approvals = useMyApprovals({ status: ["pending_manager"], limit: 1, offset: 0 });
  const pending = approvals.data?.pending ?? 0;
  const show = Boolean(approvals.data?.has_reports) || pending > 0;
  return { items: show ? [NAV_APPROVALS] : [], badges: { [NAV_APPROVALS.href]: pending } };
}

function AdminNav() {
  const dashboard = useDashboard();
  const approvals = useApprovalsItem();
  const badges = { "/actions": dashboard.data?.counts.actions_pending_approval ?? 0, ...approvals.badges };
  return (
    <>
      <NavGroup items={[...NAV_MAIN, ...approvals.items]} badges={badges} />
      <NavGroup label="Tools" items={NAV_TOOLS} />
      <SidebarSeparator className="mx-2" />
      <NavGroup items={NAV_SETTINGS} />
    </>
  );
}

function UserNav() {
  const approvals = useApprovalsItem();
  const [first, ...rest] = NAV_USER;
  return <NavGroup items={[first, ...approvals.items, ...rest]} badges={approvals.badges} />;
}

/**
 * The only navigation of the panel: logo, search, pages and the signed-in user. A `user` (not admin)
 * gets only My access and Settings, and no search: the API answers them nothing else.
 */
export function AppSidebar({ onSearch }: { onSearch: () => void }) {
  const admin = useAuthState().data?.user?.role === "admin";

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="gap-2.5 px-2 pt-2.5 pb-1">
        <Brand home={admin ? "/" : "/me"} />
        {admin && <SearchButton onSearch={onSearch} />}
      </SidebarHeader>
      <SidebarContent>{admin ? <AdminNav /> : <UserNav />}</SidebarContent>
      <SidebarFooter className="p-2">
        <NavUser />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
