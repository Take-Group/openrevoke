"use client";

import {
  BellIcon,
  Building2Icon,
  ChevronsUpDownIcon,
  KeyRoundIcon,
  LogOutIcon,
  UserIcon,
  UsersIcon,
  type LucideIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { PersonAvatar } from "@/components/common/avatars";
import { ThemeSubmenu } from "@/components/layout/theme-toggle";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SidebarMenu, SidebarMenuButton, SidebarMenuItem, useSidebar } from "@/components/ui/sidebar";
import { useAuthState, useLogout } from "@/hooks/use-auth";
import { useSystemVersion } from "@/hooks/use-system";
import type { UserOut } from "@/lib/api/auth-types";

// Items without `href` are not built yet and show a toast. `adminOnly`: hidden for a `user`.
const ACCOUNT_ITEMS: { label: string; icon: LucideIcon; href?: string; adminOnly?: boolean }[] = [
  { label: "Account", icon: UserIcon, href: "/settings" },
  { label: "Organization", icon: Building2Icon, href: "/settings", adminOnly: true },
  { label: "Users", icon: UsersIcon, href: "/settings/users", adminOnly: true },
  { label: "Notifications", icon: BellIcon, adminOnly: true },
  { label: "API tokens", icon: KeyRoundIcon, adminOnly: true },
];

function notAvailable(label: string) {
  toast.info(`${label}: not available yet`);
}

function UserLine({ user }: { user: UserOut }) {
  const [firstName, ...rest] = user.name.split(" ");
  return (
    <>
      <PersonAvatar firstName={firstName} lastName={rest.join(" ")} email={user.email} size="sm" />
      <div className="grid min-w-0 flex-1 text-left leading-tight">
        <span className="truncate text-[0.8125rem] font-medium text-foreground">{user.name}</span>
        <span className="truncate text-xs font-normal text-muted-foreground">{user.email}</span>
      </div>
    </>
  );
}

/** Signed-in user at the bottom of the sidebar: account pages, theme and sign-out. */
export function NavUser() {
  const { isMobile, state } = useSidebar();
  const router = useRouter();
  const auth = useAuthState().data;
  const logout = useLogout();
  const version = useSystemVersion().data?.version;
  const user = auth?.user;
  if (!user) return null; // the auth gate shows the panel only to a signed-in user
  return (
    <SidebarMenu>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger
            render={
              <SidebarMenuButton
                size="lg"
                className="h-10 gap-2 px-1.5 data-popup-open:bg-sidebar-accent data-popup-open:text-sidebar-accent-foreground group-data-[collapsible=icon]:p-1!"
              />
            }
          >
            <UserLine user={user} />
            <ChevronsUpDownIcon className="ml-auto size-3.5! text-muted-foreground" />
          </DropdownMenuTrigger>
          <DropdownMenuContent
            side={isMobile ? "top" : state === "collapsed" ? "right" : "top"}
            align="end"
            sideOffset={6}
            className="w-60"
          >
            <div className="flex items-center gap-2 px-2 py-1.5">
              <UserLine user={user} />
            </div>
            {auth.organization && (
              <div className="px-2 pb-1.5 text-xs text-muted-foreground">{auth.organization.name}</div>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              {ACCOUNT_ITEMS.filter((item) => user.role === "admin" || !item.adminOnly).map(({ label, icon: Icon, href }) => (
                <DropdownMenuItem key={label} onClick={() => (href ? router.push(href) : notAvailable(label))}>
                  <Icon />
                  {label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <ThemeSubmenu />
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled={logout.isPending} onClick={() => logout.mutate()}>
              <LogOutIcon />
              Sign out
            </DropdownMenuItem>
            {version && <div className="px-2 pt-1 pb-1.5 text-xs text-muted-foreground">Open Revoke {version}</div>}
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
