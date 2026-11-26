"use client";

import { useState } from "react";

import { PageHeader } from "@/components/common/page-header";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { QueryState } from "@/components/common/query-state";
import { Segmented } from "@/components/common/segmented";
import { Pager } from "@/components/common/table-shell";
import { AccessRequestsTable } from "@/components/requests/access-requests-table";
import { useMyApprovals } from "@/hooks/use-me";
import type { AccessRequestStatus } from "@/lib/api/access-request-types";

const LIMIT = 50;
type View = "pending" | "decided" | "all";

const VIEW_STATUSES: Record<View, AccessRequestStatus[] | undefined> = {
  pending: ["pending_manager"],
  decided: ["pending_admin", "approved", "done", "failed", "rejected", "cancelled"],
  all: undefined,
};

/** `/me/approvals`: requests of the user's reports that wait (or waited) for the user as their manager. */
export function ApprovalsView() {
  const [view, setView] = useState<View>("pending");
  const [offset, setOffset] = useState(0);
  const approvals = useMyApprovals({ status: VIEW_STATUSES[view], limit: LIMIT, offset });
  const pending = approvals.data?.pending;
  return (
    <>
      <PageHeader title="Approvals" />
      <div className="flex flex-col gap-4">
        <Segmented
          label="Requests"
          value={view}
          onChange={(next) => {
            setView(next);
            setOffset(0);
          }}
          options={[
            { value: "pending", label: "Waiting for you", count: pending, attention: (pending ?? 0) > 0 },
            { value: "decided", label: "Decided" },
            { value: "all", label: "All" },
          ]}
        />
        <QueryState query={approvals} feature="Approvals" loading={<TableSkeleton rows={4} />}>
          {(data) => (
            <>
              <AccessRequestsTable
                requests={data.items}
                rowHref={(request) => `/me/approvals/${request.id}`}
                emptyText={
                  view === "pending"
                    ? "Nothing waits for you. Requests of the people you manage show up here."
                    : "No requests from the people you manage yet."
                }
              />
              {data.total > 0 && <Pager total={data.total} limit={LIMIT} offset={offset} onOffsetChange={setOffset} />}
            </>
          )}
        </QueryState>
      </div>
    </>
  );
}
