"use client";

import { useState } from "react";
import Link from "next/link";

import { RecordLink } from "@/components/common/links";
import { AppWindowIcon, RefreshCwIcon, ScanSearchIcon, ShieldAlertIcon, UsersIcon } from "lucide-react";

import { PageHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { SearchInput, Toolbar } from "@/components/common/search-input";
import { Segmented } from "@/components/common/segmented";
import { Stat, StatStrip } from "@/components/common/stat";
import { ConnectionBadge } from "@/components/common/status-badge";
import { Pager } from "@/components/common/table-shell";
import { DiscoveredAppsTable } from "@/components/discovery/discovered-apps-table";
import { DiscoverySetup } from "@/components/discovery/discovery-setup";
import { ScanStatus } from "@/components/discovery/scan-status";
import { Button } from "@/components/ui/button";
import { TableSkeleton } from "@/components/common/page-skeletons";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useDiscoveredApps, useDiscovery, useGoogleOAuthResult, useScanNow } from "@/hooks/use-discovery";
import type { DiscoveredAppStatus, DiscoveryOverview } from "@/lib/api/discovery-types";

const PAGE_SIZE = 100;
type Filter = "all" | "at_risk" | DiscoveredAppStatus;

function AppsSection({ overview }: { overview: DiscoveryOverview }) {
  const [filter, setFilter] = useState<Filter>(overview.counts.grants_at_risk > 0 ? "at_risk" : "all");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const q = useDebouncedValue(search.trim(), 300);
  const { counts } = overview;
  const query = useDiscoveredApps({
    q: q || undefined,
    status: filter === "all" || filter === "at_risk" ? undefined : filter,
    at_risk: filter === "at_risk",
    limit: PAGE_SIZE,
    offset,
  });

  return (
    <>
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
          label="Filter"
          value={filter}
          onChange={(value) => {
            setFilter(value);
            setOffset(0);
          }}
          options={[
            { value: "all", label: "All", count: counts.apps },
            { value: "at_risk", label: "Left or removed", count: counts.apps_at_risk, attention: true },
            { value: "new", label: "New", count: counts.apps_new },
            { value: "tracked", label: "Tracked", count: counts.apps_tracked },
            { value: "ignored", label: "Ignored", count: counts.apps_ignored },
          ]}
        />
      </Toolbar>
      <QueryState query={query} loading={<TableSkeleton rows={8} />}>
        {(page) => (
          <>
            <DiscoveredAppsTable apps={page.items} filtered={Boolean(q) || filter !== "all"} />
            <Pager total={page.total} limit={PAGE_SIZE} offset={offset} onOffsetChange={setOffset} />
          </>
        )}
      </QueryState>
    </>
  );
}

function Discovery({ overview, callbackError }: { overview: DiscoveryOverview; callbackError: string | null }) {
  const scan = useScanNow();
  const source = overview.source;
  const { counts } = overview;

  return (
    <>
      <PageHeader
        icon={ScanSearchIcon}
        title="Discovery"
        meta={
          // Only a broken connection matters here; "never synced" is normal right after the setup.
          source &&
          (source.connection_status === "needs_login" || source.connection_status === "error") && (
            <Link href={`/apps/${source.app_id}?tab=connection`}>
              <ConnectionBadge status={source.connection_status} />
            </Link>
          )
        }
        actions={
          source && (
            <Button disabled={scan.isPending || overview.scan_running} onClick={() => scan.mutate()}>
              <RefreshCwIcon className={overview.scan_running ? "animate-spin" : undefined} />
              {overview.scan_running ? "Scanning…" : "Scan now"}
            </Button>
          )
        }
      />
      {!source ? (
        <DiscoverySetup overview={overview} callbackError={callbackError} />
      ) : (
        <>
          <ScanStatus overview={overview} />
          <StatStrip>
            <Stat label="Apps found" icon={AppWindowIcon}>
              {counts.apps}
            </Stat>
            <Stat label="People signing in" icon={UsersIcon}>
              {counts.people}
            </Stat>
            <Stat label="Sign-ins of people who left or were removed" icon={ShieldAlertIcon}>
              {counts.grants_at_risk}
            </Stat>
            <Stat label="Source" icon={ScanSearchIcon}>
              <RecordLink href={`/apps/${source.app_id}`}>
                {source.app_name}
              </RecordLink>
            </Stat>
          </StatStrip>
          <AppsSection overview={overview} key={overview.last_successful_scan?.id ?? "none"} />
        </>
      )}
    </>
  );
}

export function DiscoveryView() {
  const query = useDiscovery();
  const callbackError = useGoogleOAuthResult();
  return (
    <QueryState query={query} rows={6}>
      {(overview) => <Discovery overview={overview} callbackError={callbackError} />}
    </QueryState>
  );
}
