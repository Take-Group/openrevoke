"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SearchIcon } from "lucide-react";

import { BrandMark, BrandName } from "@/components/layout/brand-mark";

import { isItemActive, NAV_MAIN, NAV_SETTINGS, NAV_TOOLS, NAV_USER, type NavItem } from "@/components/layout/nav-items";
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

function NavGroup({ label, items, pending }: { label?: string; items: NavItem[]; pending: number }) {
  const pathname = usePathname();
  const { isMobile, setOpenMobile } = useSidebar();
  return (
    <SidebarGroup>
      {label && <SidebarGroupLabel>{label}</SidebarGroupLabel>}
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            const active = isItemActive(pathname, item);
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
                {item.href === "/actions" && pending > 0 && (
                  <SidebarMenuBadge
                    aria-label={`${pending} waiting for approval`}
                    className="top-2! h-4 min-w-4 rounded-full bg-foreground px-1.5 text-[0.6875rem] leading-none text-background peer-hover/menu-button:text-background peer-data-active/menu-button:text-background"
                  >
                    {pending}
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

function AdminNav() {
  const dashboard = useDashboard();
  const pending = dashboard.data?.counts.actions_pending_approval ?? 0;
  return (
    <>
      <NavGroup items={NAV_MAIN} pending={pending} />
      <NavGroup label="Tools" items={NAV_TOOLS} pending={pending} />
      <SidebarSeparator className="mx-2" />
      <NavGroup items={NAV_SETTINGS} pending={pending} />
    </>
  );
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
      <SidebarContent>{admin ? <AdminNav /> : <NavGroup items={NAV_USER} pending={0} />}</SidebarContent>
      <SidebarFooter className="p-2">
        <NavUser />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
