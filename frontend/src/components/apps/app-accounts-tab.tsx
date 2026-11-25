"use client";

import { useState } from "react";
import { PlusIcon } from "lucide-react";

import { AccountsTable } from "@/components/apps/accounts-table";
import { LinkButton } from "@/components/common/links";
import { QueryState } from "@/components/common/query-state";
import { SearchInput, Toolbar } from "@/components/common/search-input";
import { Segmented } from "@/components/common/segmented";
import { Pager } from "@/components/common/table-shell";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { useAppAccounts, type AccountsParams } from "@/hooks/use-accounts";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import type { AppDetail } from "@/lib/api/types";

export type AccountsFilter = "all" | "unassigned" | "removed";

const PAGE_SIZE = 100;

function filterParams(filter: AccountsFilter): AccountsParams {
  if (filter === "unassigned") return { unassigned: true };
  if (filter === "removed") return { status: "removed" };
  return {};
}

const EMPTY_TEXT: Record<AccountsFilter, string> = {
  all: "No accounts yet",
  unassigned: "Every account has an owner",
  removed: "No removed accounts",
};

export function AppAccountsTab({ app, initialFilter }: { app: AppDetail; initialFilter?: AccountsFilter }) {
  const [filter, setFilter] = useState<AccountsFilter>(initialFilter ?? "all");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const q = useDebouncedValue(search.trim(), 300);
  const query = useAppAccounts(app.id, { ...filterParams(filter), q: q || undefined, limit: PAGE_SIZE, offset });

  return (
    <>
      <Toolbar
        actions={
          app.integration === "manual" && (
            <LinkButton href={`/apps/${app.id}/accounts/new`}>
              <PlusIcon />
              Add account
            </LinkButton>
          )
        }
      >
        <SearchInput
          placeholder="Search accounts"
          value={search}
          onChange={(value) => {
            setSearch(value);
            setOffset(0);
          }}
        />
        <Segmented
          label="Filter accounts"
          value={filter}
          onChange={(value) => {
            setFilter(value);
            setOffset(0);
          }}
          options={[
            { value: "all", label: "All" },
            { value: "unassigned", label: "Without owner", count: app.unassigned_count, attention: true },
            { value: "removed", label: "Removed" },
          ]}
        />
      </Toolbar>
      <QueryState query={query} loading={<TableSkeleton rows={6} />}>
        {(page) => (
          <>
            <AccountsTable accounts={page.items} emptyText={q ? "No matches" : EMPTY_TEXT[filter]} />
            <Pager total={page.total} limit={PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />
          </>
        )}
      </QueryState>
    </>
  );
}
