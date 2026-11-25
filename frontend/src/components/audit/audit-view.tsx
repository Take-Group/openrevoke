"use client";

import { useState } from "react";

import { AuditTable } from "@/components/audit/audit-table";
import { InfoTip } from "@/components/common/info-tip";
import { FilterChip } from "@/components/common/links";
import { PageHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { SearchInput, Toolbar } from "@/components/common/search-input";
import { Pager } from "@/components/common/table-shell";
import { OptionSelect } from "@/components/common/option-select";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { useAudit } from "@/hooks/use-audit";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

const PAGE_SIZE = 100;

// Entity types the backend writes today; the API accepts any string.
const ENTITY_OPTIONS = [
  { value: "person", label: "Person" },
  { value: "people_source", label: "People source" },
  { value: "app", label: "App" },
  { value: "account", label: "Account" },
  { value: "connection", label: "Connection" },
  { value: "action", label: "Action" },
];

interface AuditViewProps {
  initialEntityType?: string;
  entityId?: string;
  /** Everything about one app (its accounts, connection and actions too). */
  appId?: string;
  /** Everything about one person (their accounts and actions too). */
  personId?: string;
}

function scopeText({ initialEntityType, entityId, appId, personId }: AuditViewProps): string | null {
  if (appId) return "One app";
  if (personId) return "One person";
  if (entityId) return `One ${initialEntityType ?? "entity"}`;
  return null;
}

export function AuditView(props: AuditViewProps) {
  const { initialEntityType, entityId, appId, personId } = props;
  const [entityType, setEntityType] = useState(initialEntityType ?? "");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const q = useDebouncedValue(search.trim(), 300);
  const query = useAudit({
    entity_type: entityType || undefined,
    entity_id: entityId,
    app_id: appId,
    person_id: personId,
    q: q || undefined,
    limit: PAGE_SIZE,
    offset,
  });
  const scope = scopeText(props);

  return (
    <>
      <PageHeader
        title="Audit"
        meta={
          <>
            <InfoTip>Every change in Open Revoke, newest first. Entries are never edited or deleted.</InfoTip>
            {scope && (
<FilterChip href="/audit">{scope}</FilterChip>
            )}
          </>
        }
      />
      <Toolbar>
        <SearchInput
          placeholder="Search events"
          value={search}
          onChange={(value) => {
            setSearch(value);
            setOffset(0);
          }}
        />
        <OptionSelect
          className="w-40"
          aria-label="Entity"
          placeholder="All entities"
          options={ENTITY_OPTIONS}
          value={entityType}
          onChange={(next) => {
            setEntityType(next);
            setOffset(0);
          }}
        />
      </Toolbar>
      <QueryState query={query} loading={<TableSkeleton rows={10} />}>
        {(page) => (
          <>
            <AuditTable events={page.items} />
            <Pager total={page.total} limit={PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />
          </>
        )}
      </QueryState>
    </>
  );
}
