"use client";

import { useState } from "react";
import { DownloadIcon } from "lucide-react";

import { OptionSelect } from "@/components/common/option-select";
import { PageHeader } from "@/components/common/page-header";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { PersonPicker } from "@/components/common/person-picker";
import { QueryState } from "@/components/common/query-state";
import { Toolbar } from "@/components/common/search-input";
import { Segmented } from "@/components/common/segmented";
import { Pager } from "@/components/common/table-shell";
import { AccessRequestsTable } from "@/components/requests/access-requests-table";
import { buttonVariants } from "@/components/ui/button";
import { accessRequestsExportUrl, useAccessRequests } from "@/hooks/use-access-requests";
import { useApps } from "@/hooks/use-apps";
import type { AccessRequestFilters, AccessRequestStatus } from "@/lib/api/access-request-types";
import type { PersonRef } from "@/lib/api/types";

const LIMIT = 50;

type View = "all" | "manager" | "admin" | "approved" | "done" | "rejected" | "failed";

const VIEWS: { value: View; label: string }[] = [
  { value: "all", label: "All" },
  { value: "manager", label: "Waiting for manager" },
  { value: "admin", label: "Waiting for admin" },
  { value: "approved", label: "In progress" },
  { value: "done", label: "Done" },
  { value: "rejected", label: "Rejected" },
  { value: "failed", label: "Failed or cancelled" },
];

const VIEW_STATUSES: Record<View, AccessRequestStatus[] | undefined> = {
  all: undefined,
  manager: ["pending_manager"],
  admin: ["pending_admin"],
  approved: ["approved"],
  done: ["done"],
  rejected: ["rejected"],
  failed: ["failed", "cancelled"],
};

/** `/requests`: every access request with filters, who it waits for, and the CSV export of the same filter. */
export function RequestsView() {
  const [view, setView] = useState<View>("all");
  const [appId, setAppId] = useState("");
  const [person, setPerson] = useState<Pick<PersonRef, "person_id" | "first_name" | "last_name" | "primary_email"> | null>(null);
  const [offset, setOffset] = useState(0);
  const apps = useApps({ limit: 500 });
  const filters: AccessRequestFilters = {
    status: VIEW_STATUSES[view],
    app_id: appId || undefined,
    person_id: person?.person_id,
  };
  const requests = useAccessRequests({ ...filters, limit: LIMIT, offset });
  const reset = () => setOffset(0);

  return (
    <>
      <PageHeader
        title="Access requests"
        actions={
          <a href={accessRequestsExportUrl(filters)} download className={buttonVariants({ variant: "outline", size: "sm" })}>
            <DownloadIcon />
            <span className="max-md:sr-only">Export CSV</span>
          </a>
        }
      />
      <div className="flex flex-col gap-4">
        <Segmented
          label="Status"
          value={view}
          onChange={(next) => {
            setView(next);
            reset();
          }}
          options={VIEWS}
        />
        <Toolbar>
          <OptionSelect
            aria-label="App"
            className="w-56"
            value={appId}
            onChange={(next) => {
              setAppId(next);
              reset();
            }}
            placeholder="All apps"
            options={(apps.data?.items ?? []).map((app) => ({ value: app.id, label: app.name }))}
          />
          <PersonPicker
            className="w-64"
            value={person}
            allowClear
            placeholder="All people"
            onChange={(next) => {
              setPerson(next ? { person_id: next.id, first_name: next.first_name, last_name: next.last_name, primary_email: next.primary_email } : null);
              reset();
            }}
          />
        </Toolbar>
        <QueryState query={requests} feature="Access requests" loading={<TableSkeleton rows={6} />}>
          {(data) => (
            <>
              <AccessRequestsTable requests={data.items} rowHref={(request) => `/requests/${request.id}`} />
              {data.total > 0 && <Pager total={data.total} limit={LIMIT} offset={offset} onOffsetChange={setOffset} />}
            </>
          )}
        </QueryState>
      </div>
    </>
  );
}
