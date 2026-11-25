"use client";

import { useState } from "react";

import { ActionsTable } from "@/components/actions/actions-table";
import { BatchBar } from "@/components/actions/batch-bar";
import { FilterChip } from "@/components/common/links";
import { PageHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { Pager } from "@/components/common/table-shell";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { useActions } from "@/hooks/use-actions";
import { useUrlTab } from "@/hooks/use-url-tab";
import type { ActionStatus } from "@/lib/api/types";

export type ActionsTab = "pending" | "progress" | "done" | "failed" | "cancelled";

const TAB_STATUSES: Record<ActionsTab, ActionStatus[]> = {
  pending: ["pending_approval"],
  progress: ["approved", "running", "verifying"],
  done: ["done"],
  failed: ["failed"],
  cancelled: ["cancelled"],
};

const TAB_LABELS: Record<ActionsTab, string> = {
  pending: "Pending",
  progress: "In progress",
  done: "Done",
  failed: "Failed",
  cancelled: "Cancelled",
};

const EMPTY_TEXT: Record<ActionsTab, string> = {
  pending: "Nothing to approve",
  progress: "Nothing running",
  done: "No finished actions",
  failed: "No failures",
  cancelled: "No cancelled actions",
};

const PAGE_SIZE = 100;

export function ActionsView({ initialTab, batchId }: { initialTab?: ActionsTab; batchId?: string }) {
  const [tab, setTab] = useUrlTab<ActionsTab>(initialTab, "pending");
  const [offset, setOffset] = useState(0);
  const query = useActions({ status: TAB_STATUSES[tab], batch_id: batchId, limit: PAGE_SIZE, offset });
  // Counts per status come with every page (same filters except status).
  const statusCounts = query.data?.counts;
  const tabCount = (key: ActionsTab) =>
    statusCounts ? TAB_STATUSES[key].reduce((sum, status) => sum + (statusCounts[status] ?? 0), 0) : 0;

  return (
    <>
      <PageHeader
        title="Actions"
        meta={
          batchId && (
<FilterChip href="/actions">One batch</FilterChip>
          )
        }
      />
      <Tabs
        value={tab}
        onValueChange={(value) => {
          setTab(value as ActionsTab);
          setOffset(0);
        }}
      >
        <TabsList variant="line" className="mb-3">
          {(Object.keys(TAB_LABELS) as ActionsTab[]).map((key) => {
            const count = tabCount(key);
            return (
              <TabsTrigger key={key} value={key}>
                {TAB_LABELS[key]}
                {count > 0 && <span className="text-muted-foreground tabular-nums">{count}</span>}
              </TabsTrigger>
            );
          })}
        </TabsList>
      </Tabs>
      <QueryState query={query} loading={<TableSkeleton rows={6} />}>
        {(page) => (
          <div className="flex flex-col gap-3">
            {tab === "pending" && <BatchBar actions={page.items} />}
            <div>
              <ActionsTable actions={page.items} emptyText={EMPTY_TEXT[tab]} />
              <Pager total={page.total} limit={PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />
            </div>
          </div>
        )}
      </QueryState>
    </>
  );
}
