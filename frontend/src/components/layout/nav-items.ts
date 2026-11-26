import {
  AppWindowIcon,
  GlobeIcon,
  HistoryIcon,
  InboxIcon,
  KeyRoundIcon,
  LayoutDashboardIcon,
  ListChecksIcon,
  PlugIcon,
  ShieldCheckIcon,
  ScanSearchIcon,
  SettingsIcon,
  UsersIcon,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  title: string;
  href: string;
  icon: LucideIcon;
  /** Sub-pages shown under the item while one of them is open (Vercel's settings). */
  children?: { title: string; href: string }[];
}

/** Pages of the panel, in sidebar order. The command palette uses the same list. */
export const NAV_MAIN: NavItem[] = [
  { title: "Dashboard", href: "/", icon: LayoutDashboardIcon },
  { title: "People", href: "/people", icon: UsersIcon },
  { title: "Apps", href: "/apps", icon: AppWindowIcon },
  { title: "Access profiles", href: "/access-profiles", icon: ShieldCheckIcon },
  { title: "Discovery", href: "/discovery", icon: ScanSearchIcon },
  { title: "Actions", href: "/actions", icon: ListChecksIcon },
  { title: "Requests", href: "/requests", icon: InboxIcon },
];

export const NAV_TOOLS: NavItem[] = [
  { title: "Browser", href: "/browser", icon: GlobeIcon },
  { title: "Audit", href: "/audit", icon: HistoryIcon },
];

/** Below a hairline at the end of the sidebar. */
export const NAV_SETTINGS: NavItem[] = [
  {
    title: "Settings",
    href: "/settings",
    icon: SettingsIcon,
    children: [
      { title: "General", href: "/settings" },
      { title: "Users", href: "/settings/users" },
      { title: "AI model", href: "/settings/ai" },
      { title: "Slack", href: "/settings/slack" },
      { title: "API and MCP", href: "/settings/api" },
    ],
  },
];

export const NAV_ALL = [...NAV_MAIN, ...NAV_TOOLS, ...NAV_SETTINGS];

/** Every page for the command palette: the items plus their sub-pages ("Settings: AI model"). */
export const NAV_PAGES: NavItem[] = NAV_ALL.flatMap((item) => [
  item,
  ...(item.children ?? [])
    .filter((child) => child.href !== item.href)
    .map((child) => ({ title: `${item.title}: ${child.title}`, href: child.href, icon: item.icon })),
]);

/** The whole sidebar of a `user` (not admin): their own access and their account. */
export const NAV_USER: NavItem[] = [
  { title: "My access", href: "/me", icon: KeyRoundIcon },
  { title: "Settings", href: "/settings", icon: SettingsIcon },
  { title: "API and MCP", href: "/settings/api", icon: PlugIcon },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

/** An item with sub-pages is active on those pages only (not on /settings/two-factor). */
export function isItemActive(pathname: string, item: NavItem): boolean {
  return item.children ? item.children.some((child) => pathname === child.href) : isActive(pathname, item.href);
}

