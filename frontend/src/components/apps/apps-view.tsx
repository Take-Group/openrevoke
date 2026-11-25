"use client";

import { useState } from "react";
import { AppWindowIcon, PlusIcon } from "lucide-react";

import { AppsTable } from "@/components/apps/apps-table";
import { EmptyState } from "@/components/common/empty-state";
import { INTEGRATION } from "@/components/common/integration-icon";
import { LinkButton } from "@/components/common/links";
import { PageHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { SearchInput, Toolbar } from "@/components/common/search-input";
import { Segmented } from "@/components/common/segmented";
import { Pager } from "@/components/common/table-shell";
import { OptionSelect } from "@/components/common/option-select";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { useApps } from "@/hooks/use-apps";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { ConnectionStatus, Integration } from "@/lib/api/types";

const PAGE_SIZE = 100;

function AddAppButton() {
  return (
    <LinkButton href="/apps/new">
      <PlusIcon />
      Add app
    </LinkButton>
  );
}

const INTEGRATION_FILTER = [
  { value: "all" as const, label: "All" },
  ...(Object.keys(INTEGRATION) as Integration[]).map((value) => ({ value, label: INTEGRATION[value].label })),
];

const STATUS_FILTER: { value: ConnectionStatus; label: string }[] = [
  { value: "ok", label: "Connected" },
  { value: "needs_login", label: "Needs login" },
  { value: "error", label: "Error" },
  { value: "never_synced", label: "Never synced" },
];

export function AppsView() {
  const [search, setSearch] = useState("");
  const [integration, setIntegration] = useState<Integration | "all">("all");
  const [status, setStatus] = useState<ConnectionStatus | "">("");
  const [offset, setOffset] = useState(0);
  const q = useDebouncedValue(search.trim(), 300);

  const query = useApps({
    q: q || undefined,
    integration: integration === "all" ? undefined : integration,
    status: status || undefined,
    limit: PAGE_SIZE,
    offset,
  });

  return (
    <>
      <PageHeader title="Apps" actions={<AddAppButton />} />
      <Toolbar>
        <SearchInput
          placeholder="Search apps"
          value={search}
          onChange={(value) => {
            setSearch(value);
            setOffset(0);
          }}
        />
        <Segmented
          label="Integration"
          value={integration}
          onChange={(value) => {
            setIntegration(value);
            setOffset(0);
          }}
          options={INTEGRATION_FILTER}
        />
        <OptionSelect
          className="w-40"
          aria-label="Connection status"
          placeholder="Any status"
          options={STATUS_FILTER}
          value={status}
          onChange={(next) => {
            setStatus(next as ConnectionStatus | "");
            setOffset(0);
          }}
        />
      </Toolbar>
      <QueryState query={query} loading={<TableSkeleton rows={8} />}>
        {(page) => (
          <>
            <AppsTable
              apps={page.items}
              filtered={Boolean(q || integration !== "all" || status)}
              empty={<EmptyState icon={AppWindowIcon} title="No apps yet" action={<AddAppButton />} />}
            />
            <Pager total={page.total} limit={PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />
          </>
        )}
      </QueryState>
    </>
  );
}
