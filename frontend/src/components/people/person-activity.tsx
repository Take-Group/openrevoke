"use client";

import Link from "next/link";
import { ArrowRightIcon, HistoryIcon } from "lucide-react";

import { AppAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { Panel } from "@/components/common/panel";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import { buttonVariants } from "@/components/ui/button";
import { useActions } from "@/hooks/use-actions";
import { useAudit } from "@/hooks/use-audit";
import { actionOperation } from "@/lib/format";
import type { ActionStatus } from "@/lib/api/types";
import { cn } from "@/lib/utils";

const OPEN: ActionStatus[] = ["pending_approval", "approved", "running", "verifying", "failed"];

/** A "See all" link in a panel header. */
function SeeAll({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className={cn(buttonVariants({ variant: "ghost", size: "xs" }), "text-muted-foreground")}>
      {children}
      <ArrowRightIcon />
    </Link>
  );
}

/** Actions of the person that still need attention. Hidden when there are none. */
function OpenActions({ personId }: { personId: string }) {
  const actions = useActions({ person_id: personId, status: OPEN, limit: 50 });
  const items = actions.data?.items ?? [];
  if (items.length === 0) return null;

  return (
    <Panel title="Open actions" meta={items.length} actions={<SeeAll href="/actions">Actions</SeeAll>}>
      <ul className="divide-y text-sm">
        {items.map((action) => (
          <li key={action.id} className="flex items-center gap-3 px-4 py-2.5">
            <AppAvatar name={action.app.name} slug={action.app.slug} size="sm" />
            <span className="min-w-0 flex-1 truncate">
              <span className="font-medium">{action.app.name}</span>
              <span className="text-muted-foreground"> · {actionOperation(action)}</span>
            </span>
            <RelativeTime value={action.created_at} className="text-xs" />
            <StatusBadge status={action.status} />
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function RecentEvents({ personId }: { personId: string }) {
  const audit = useAudit({ person_id: personId, limit: 15 });
  const events = audit.data?.items ?? [];
  return (
    <Panel title="History" actions={<SeeAll href={`/audit?person=${personId}`}>All events</SeeAll>}>
      {audit.isSuccess && events.length === 0 ? (
        <EmptyState icon={HistoryIcon} title="No events" />
      ) : (
        <ol className="divide-y text-sm">
          {events.map((event) => (
            <li key={event.id} className="flex items-center gap-3 px-4 py-2">
              <code className="min-w-0 flex-1 truncate font-mono text-xs">{event.event}</code>
              <span className="hidden text-xs text-muted-foreground sm:inline">{event.actor}</span>
              <RelativeTime value={event.at} className="text-xs" />
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}

export function PersonActivity({ personId }: { personId: string }) {
  return (
    <div className="flex flex-col gap-6">
      <OpenActions personId={personId} />
      <RecentEvents personId={personId} />
    </div>
  );
}
