"use client";

import { InlineError, Notice } from "@/components/common/notice";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import { formatWhen } from "@/lib/format";
import type { DiscoveryOverview } from "@/lib/api/discovery-types";

/** One line about the last scan, its window, and anything the admin should fix. */
export function ScanStatus({ overview }: { overview: DiscoveryOverview }) {
  const last = overview.last_scan;
  const ok = overview.last_successful_scan;
  if (!last) return null;
  return (
    <div className="mb-4 flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
        <StatusBadge status={overview.scan_running ? "running" : last.status} />
        {overview.scan_running ? (
          <span>Scanning {overview.source?.app_name ?? "the directory"}…</span>
        ) : (
          <span>
            Last scan <RelativeTime value={last.finished_at ?? last.started_at} />
          </span>
        )}
        {ok?.events_from && ok.events_until && (
          <span>
            Sign-ins read from {formatWhen(ok.events_from).split(",")[0]} to {formatWhen(ok.events_until).split(",")[0]}
          </span>
        )}
        {ok && <span>{ok.users_scanned} people in the directory</span>}
      </div>
      {last.status === "failed" && last.error && !overview.scan_running && <InlineError message={last.error} />}
      {ok?.notes
        ?.filter((note) => note.startsWith("Token inventory skipped"))
        .map((note) => (
          <Notice key={note} tone="info">
            {note}
          </Notice>
        ))}
    </div>
  );
}
