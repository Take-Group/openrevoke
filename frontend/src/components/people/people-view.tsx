"use client";

import { useState } from "react";
import { PlusIcon, UploadIcon } from "lucide-react";

import { LinkButton } from "@/components/common/links";
import { PageHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { SearchInput, Toolbar } from "@/components/common/search-input";
import { Segmented } from "@/components/common/segmented";
import { Pager } from "@/components/common/table-shell";
import { PeopleTable } from "@/components/people/people-table";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { usePeople } from "@/hooks/use-people";
import type { PersonKind, PersonStatus } from "@/lib/api/types";

const PAGE_SIZE = 100;

type StatusFilter = PersonStatus | "all";

type ManagerFilter = "all" | "none";

export function PeopleView({ initialStatus, initialNoManager }: { initialStatus?: PersonStatus; initialNoManager?: boolean }) {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<StatusFilter>(initialStatus ?? "all");
  const [manager, setManager] = useState<ManagerFilter>(initialNoManager ? "none" : "all");
  // Service accounts (shared mailboxes, technical accounts) have their own tab: they do not leave.
  const [kind, setKind] = useState<PersonKind>("human");
  const [offset, setOffset] = useState(0);
  const q = useDebouncedValue(search.trim(), 300);

  const query = usePeople({
    q: q || undefined,
    status: status === "all" ? undefined : status,
    kind,
    no_manager: manager === "none" || undefined,
    limit: PAGE_SIZE,
    offset,
  });

  return (
    <>
      <PageHeader
        title="People"
        actions={
          <>
            <LinkButton href="/people/import" variant="outline">
              <UploadIcon />
              Import
            </LinkButton>
            <LinkButton href="/people/new">
              <PlusIcon />
              Add person
            </LinkButton>
          </>
        }
      />
      <Toolbar>
        <SearchInput
          placeholder="Search people"
          value={search}
          onChange={(value) => {
            setSearch(value);
            setOffset(0);
          }}
        />
        <Segmented
          label="Kind"
          value={kind}
          onChange={(value) => {
            setKind(value);
            setOffset(0);
          }}
          options={[
            { value: "human", label: "People", count: query.data?.kind_counts.human },
            { value: "service", label: "Service accounts", count: query.data?.kind_counts.service },
          ]}
        />
        <Segmented
          label="Status"
          value={status}
          onChange={(value) => {
            setStatus(value);
            setOffset(0);
          }}
          options={[
            { value: "all", label: "All" },
            { value: "active", label: "Active" },
            { value: "left", label: "Left" },
          ]}
        />
        <Segmented
          label="Manager"
          value={manager}
          onChange={(value) => {
            setManager(value);
            setOffset(0);
          }}
          options={[
            { value: "all", label: "Any manager" },
            { value: "none", label: "No manager" },
          ]}
        />
      </Toolbar>
      <QueryState query={query} loading={<TableSkeleton rows={8} />}>
        {(page) => (
          <>
            <PeopleTable people={page.items} filtered={Boolean(q || status !== "all" || manager !== "all")} />
            <Pager total={page.total} limit={PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />
          </>
        )}
      </QueryState>
    </>
  );
}
