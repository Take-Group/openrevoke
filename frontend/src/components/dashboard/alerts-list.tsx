import Link from "next/link";
import { ChevronRightIcon, CircleCheckIcon } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { Panel } from "@/components/common/panel";
import { StatusDot } from "@/components/common/status-badge";
import { ROW_HOVER } from "@/components/dashboard/row-hover";
import type { Alert } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/** Where the operator fixes the alert. */
export function alertHref(alert: Alert): string {
  switch (alert.kind) {
    case "unassigned_accounts":
      return alert.app_id ? `/apps/${alert.app_id}?accounts=unassigned` : "/apps";
    case "connection_needs_login":
    case "connection_error":
      return alert.app_id ? `/apps/${alert.app_id}?tab=connection` : "/apps";
    case "action_failed":
      return "/actions?tab=failed";
    case "left_person_active_account":
    case "person_inactive_in_source":
      if (alert.person_id) return `/people/${alert.person_id}`;
      return alert.app_id ? `/apps/${alert.app_id}` : "/people";
    case "discovered_sign_ins_at_risk":
      return `/discovery/${alert.entity_id}`;
    case "profile_access_missing":
      return `/access-profiles/${alert.entity_id}`;
  }
}

const SEVERITY_ORDER = { critical: 0, warning: 1 } as const;

export function AlertsList({ alerts }: { alerts: Alert[] }) {
  const sorted = [...alerts].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
  return (
    <div id="alerts" className="h-full min-w-0 scroll-mt-6">
      <Panel title="Alerts" meta={sorted.length || undefined} className="h-full">
        {sorted.length === 0 ? (
          <EmptyState icon={CircleCheckIcon} title="All clear" />
        ) : (
          <ul className="divide-y">
            {sorted.map((alert, index) => (
              <li key={`${alert.kind}-${alert.entity_id}-${index}`}>
                <Link
                  href={alertHref(alert)}
                  className={cn("group flex h-11 items-center gap-3 px-4 text-sm", ROW_HOVER)}
                >
                  <StatusDot tone={alert.severity === "critical" ? "danger" : "warning"} className="size-2" />
                  <span className="min-w-0 flex-1 truncate">{alert.message}</span>
                  {alert.count !== null && alert.count > 1 && (
                    <span className="text-xs text-muted-foreground tabular-nums">{alert.count}</span>
                  )}
                  <ChevronRightIcon className="size-4 shrink-0 text-muted-foreground/0 transition-colors group-hover:text-muted-foreground" />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
