"use client";

import Link from "next/link";
import {
  AppWindowIcon,
  BracesIcon,
  DatabaseIcon,
  HistoryIcon,
  KeyRoundIcon,
  ListChecksIcon,
  PlugIcon,
  UserCogIcon,
  UserIcon,
  type LucideIcon,
} from "lucide-react";
import type { DataColumn } from "@/components/data-table/features";

import { EmptyState } from "@/components/common/empty-state";
import { Hint } from "@/components/common/info-tip";
import { RelativeTime } from "@/components/common/relative-time";
import { DataTable } from "@/components/data-table/data-table";
import { Button, buttonVariants } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { humanize } from "@/lib/format";
import type { AuditEventOut } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const GONE = new Set(["app.deleted", "person.deleted"]);

const ENTITY_ICON: Record<string, LucideIcon> = {
  person: UserIcon,
  people_source: DatabaseIcon,
  app: AppWindowIcon,
  account: KeyRoundIcon,
  connection: PlugIcon,
  action: ListChecksIcon,
  user: UserCogIcon,
};

/** Links of an event: the person and the app it is about (columns app_id, person_id). */
function subjectLinks(event: AuditEventOut): { href: string; label: string; icon: LucideIcon }[] {
  const links: { href: string; label: string; icon: LucideIcon }[] = [];
  const gone = GONE.has(event.event);
  if (event.person_id && !(gone && event.entity_type === "person")) {
    links.push({ href: `/people/${event.person_id}`, label: "Person", icon: UserIcon });
  }
  if (event.app_id && !(gone && event.entity_type === "app")) {
    links.push({ href: `/apps/${event.app_id}`, label: "App", icon: AppWindowIcon });
  }
  if (event.entity_type === "action") links.push({ href: "/actions", label: "Actions", icon: ListChecksIcon });
  return links;
}

function Data({ data }: { data: AuditEventOut["data"] }) {
  if (!data || Object.keys(data).length === 0) return <span className="text-muted-foreground">—</span>;
  const text = JSON.stringify(data);
  return (
    <Popover>
      <PopoverTrigger
        render={
          <Button variant="ghost" size="xs" className="-mx-2 max-w-full min-w-0 justify-start font-normal text-muted-foreground" />
        }
      >
        <BracesIcon className="size-3.5 shrink-0" />
        <code className="min-w-0 truncate font-mono text-xs">{text}</code>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-[28rem] max-w-[90vw] p-0">
        <pre className="max-h-80 overflow-auto p-3 font-mono text-xs">{JSON.stringify(data, null, 2)}</pre>
      </PopoverContent>
    </Popover>
  );
}

const columns: DataColumn<AuditEventOut>[] = [
  {
    accessorKey: "at",
    header: "When",
    cell: ({ row }) => <RelativeTime value={row.original.at} className="whitespace-nowrap tabular-nums" />,
    meta: { className: "w-28" },
  },
  {
    accessorKey: "event",
    header: "Event",
    cell: ({ row: { original: event } }) => {
      const Icon = ENTITY_ICON[event.entity_type] ?? HistoryIcon;
      return (
        <span className="inline-flex items-center gap-2">
          <Hint label={humanize(event.entity_type)}>
            <Icon className="size-3.5 shrink-0 text-muted-foreground" />
          </Hint>
          <code className="font-mono text-xs">{event.event}</code>
        </span>
      );
    },
  },
  {
    id: "links",
    header: "Open",
    cell: ({ row }) => (
      <span className="flex items-center gap-1">
        {subjectLinks(row.original).map((link) => (
          <Hint key={link.href} label={link.label}>
            <Link
              href={link.href}
              aria-label={link.label}
              className={cn(buttonVariants({ variant: "ghost", size: "icon-xs" }), "text-muted-foreground")}
            >
              <link.icon className="size-3.5" />
            </Link>
          </Hint>
        ))}
      </span>
    ),
    meta: { className: "max-md:hidden w-24" },
  },
  {
    accessorKey: "actor",
    header: "Actor",
    cell: ({ row }) => <span className="text-muted-foreground">{row.original.actor}</span>,
    meta: { className: "max-md:hidden" },
  },
  {
    id: "data",
    header: "Data",
    cell: ({ row }) => <Data data={row.original.data} />,
    meta: { className: "max-md:hidden w-full max-w-0 min-w-40" },
  },
];

export function AuditTable({ events }: { events: AuditEventOut[] }) {
  return (
    <DataTable
      columns={columns}
      data={events}
      getRowId={(event) => event.id}
      empty={<EmptyState icon={HistoryIcon} title="No events" />}
    />
  );
}
