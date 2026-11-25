import Link from "next/link";
import { ChevronLeftIcon, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/utils";

interface PageHeaderProps {
  /** Not shown: page titles stand alone. Kept so existing callers compile. */
  icon?: LucideIcon;
  title: React.ReactNode;
  /** A count or badge next to the title (a plain number shows muted). */
  meta?: React.ReactNode;
  /** Buttons on the right; the primary one last. */
  actions?: React.ReactNode;
  /** Link back to the page this one belongs to (form pages: the list or the record). */
  back?: { href: string; label: string };
  className?: string;
}

/**
 * The bar at the top of a page, edge to edge under a hairline (Vercel's dashboard): the title in
 * the middle, actions on the right. The negative margins undo the content padding of `AdminLayout`.
 * Phones already have the mobile bar with the menu, so there it is a plain title row.
 */
const PAGE_BAR = "mb-5 md:-mx-6 md:-mt-6 md:mb-6 md:border-b md:px-6";

/**
 * Short title centred in the bar (left on phones), actions on the right. No icon and no
 * description: tooltips explain.
 */
export function PageHeader({ title, meta, actions, back, className }: PageHeaderProps) {
  return (
    <div
      className={cn(
        PAGE_BAR,
        "flex flex-wrap items-center justify-between gap-x-3 gap-y-2 md:grid md:min-h-14 md:py-2.5 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]",
        className,
      )}
    >
      {back ? (
        <Link
          href={back.href}
          className="flex w-full min-w-0 items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground md:w-auto"
        >
          <ChevronLeftIcon className="size-4 shrink-0" />
          <span className="truncate">{back.label}</span>
        </Link>
      ) : (
        <div aria-hidden className="hidden md:block" />
      )}
      <div className="flex min-w-0 items-baseline gap-2">
        <h1 className="truncate text-xl font-semibold tracking-[-0.02em] md:text-sm md:font-medium">{title}</h1>
        {meta !== undefined && meta !== null && (
          <span className="flex items-center text-sm text-muted-foreground tabular-nums">{meta}</span>
        )}
      </div>
      <div className="flex flex-wrap items-center justify-end gap-2">{actions}</div>
    </div>
  );
}

/** The centred column of a settings page (Vercel's settings: cards 914 px wide in the middle). */
export const SETTINGS_COLUMN = "mx-auto w-full max-w-[57rem]";

interface DetailHeaderProps {
  avatar: React.ReactNode;
  title: React.ReactNode;
  badges?: React.ReactNode;
  /** One muted line under the name (e-mail, admin URL). */
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
}

/** Header of a detail page in the same edge-to-edge bar: avatar, name, status and actions. */
export function DetailHeader({ avatar, title, badges, subtitle, actions }: DetailHeaderProps) {
  return (
    <div className={cn(PAGE_BAR, "flex flex-wrap items-center justify-between gap-4 md:py-4")}>
      <div className="flex min-w-0 items-center gap-3">
        {avatar}
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate text-xl font-semibold tracking-[-0.015em]">{title}</h1>
            {badges}
          </div>
          {subtitle && <div className="mt-0.5 truncate text-sm text-muted-foreground">{subtitle}</div>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/** Heading of a block inside a page. `icon` is accepted but not shown. */
export function SectionHeader({
  title,
  meta,
  actions,
  className,
}: {
  title: React.ReactNode;
  /** Muted text or a count after the title. */
  meta?: React.ReactNode;
  icon?: LucideIcon;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mb-2.5 flex min-h-7 flex-wrap items-center justify-between gap-2", className)}>
      <h2 className="flex items-center gap-1.5 text-sm font-medium">
        {title}
        {meta !== undefined && meta !== null && <span className="font-normal text-muted-foreground tabular-nums">{meta}</span>}
      </h2>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
