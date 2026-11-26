"use client";

import { InboxIcon } from "lucide-react";
import type { DataColumn } from "@/components/data-table/features";

import { EmptyState } from "@/components/common/empty-state";
import { RecordLink } from "@/components/common/links";
import { RelativeTime } from "@/components/common/relative-time";
import { DataTable } from "@/components/data-table/data-table";
import { RequestStatusBadge, waitingText } from "@/components/requests/request-parts";
import { fullName } from "@/lib/format";
import type { AccessRequestOut } from "@/lib/api/access-request-types";

function columns(showPerson: boolean): DataColumn<AccessRequestOut>[] {
  const all: (DataColumn<AccessRequestOut> | false)[] = [
    showPerson && {
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
      cell: ({ row: { original: request } }) => <span className="whitespace-nowrap">{request.app.name}</span>,
    },
    {
      id: "status",
      header: "Status",
      cell: ({ row: { original: request } }) => <RequestStatusBadge status={request.status} />,
    },
    {
      id: "waiting",
      header: "Waiting for",
      cell: ({ row: { original: request } }) => <span className="whitespace-nowrap text-muted-foreground">{waitingText(request)}</span>,
      meta: { className: "max-md:hidden" },
    },
    {
      id: "why",
      header: "Why",
      cell: ({ row: { original: request } }) => {
        const text = request.justification ?? request.message;
        return (
          <span className="block truncate text-muted-foreground" title={text ?? undefined}>
            {text ?? "—"}
          </span>
        );
      },
      meta: { className: "max-md:hidden w-full max-w-0 min-w-24" },
    },
    {
      id: "asked",
      header: "Asked",
      cell: ({ row }) => <RelativeTime value={row.original.created_at} />,
      meta: { className: "whitespace-nowrap" },
    },
  ];
  return all.filter((column): column is DataColumn<AccessRequestOut> => column !== false);
}

/** Access requests with status, who decides next and age; a row opens `rowHref` (the request's page). */
export function AccessRequestsTable({
  requests,
  rowHref,
  showPerson = true,
  emptyText = "They appear when someone asks on My access, through the API or the Slack bot.",
}: {
  requests: AccessRequestOut[];
  rowHref: (request: AccessRequestOut) => string;
  showPerson?: boolean;
  emptyText?: string;
}) {
  return (
    <DataTable
      columns={columns(showPerson)}
      data={requests}
      getRowId={(request) => request.id}
      rowHref={rowHref}
      empty={<EmptyState icon={InboxIcon} title="No requests" description={emptyText} />}
    />
  );
}
