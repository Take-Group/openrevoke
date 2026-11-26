"use client";

import { useState } from "react";
import { InboxIcon } from "lucide-react";
import type { DataColumn } from "@/components/data-table/features";

import { EmptyState } from "@/components/common/empty-state";
import { RecordLink } from "@/components/common/links";
import { QueryState } from "@/components/common/query-state";
import { RelativeTime } from "@/components/common/relative-time";
import { StatusBadge } from "@/components/common/status-badge";
import { Pager } from "@/components/common/table-shell";
import { DataTable } from "@/components/data-table/data-table";
import { useAccessRequests } from "@/hooks/use-access-requests";
import { fullName } from "@/lib/format";
import type { AccessRequestOut } from "@/lib/api/access-request-types";

const LIMIT = 20;

const columns: DataColumn<AccessRequestOut>[] = [
  {
    id: "person",
    header: "Person",
    cell: ({ row: { original: request } }) => (
      <RecordLink href={`/people/${request.person.person_id}`} className="font-medium">
        {fullName(request.person)}
      </RecordLink>
    ),
    meta: { className: "whitespace-nowrap" },
  },
  {
    id: "app",
    header: "App",
    cell: ({ row: { original: request } }) => (
      <RecordLink href={`/apps/${request.app.app_id}`}>
        {request.app.name}
      </RecordLink>
    ),
    meta: { className: "whitespace-nowrap" },
  },
  {
    id: "status",
    header: "Status",
    cell: ({ row: { original: request } }) => (
      <StatusBadge status={request.status === "pending_admin" || request.status === "approved" ? request.action_status : request.status} />
    ),
  },
  {
    id: "message",
    header: "Message",
    cell: ({ row: { original: request } }) => (
      <span className="block truncate text-muted-foreground" title={request.message ?? undefined}>
        {request.message}
      </span>
    ),
    meta: { className: "max-md:hidden w-full max-w-0 min-w-24" },
  },
  {
    id: "asked",
    header: "Asked",
    cell: ({ row }) => <RelativeTime value={row.original.created_at} />,
    meta: { className: "whitespace-nowrap" },
  },
];

/** Requests people sent to the Slack agent, newest first. */
export function AccessRequestsTable() {
  const [offset, setOffset] = useState(0);
  const requests = useAccessRequests({ limit: LIMIT, offset });
  return (
    <QueryState query={requests} feature="Access requests" rows={3}>
      {(data) => (
        <>
          <DataTable
            columns={columns}
            data={data.items}
            getRowId={(request) => request.id}
            empty={
              <EmptyState
                icon={InboxIcon}
                title="No requests yet"
                description="They appear when someone asks the Slack bot or uses My access."
              />
            }
          />
          {data.total > 0 && <Pager total={data.total} limit={LIMIT} offset={offset} onOffsetChange={setOffset} />}
        </>
      )}
    </QueryState>
  );
}
