"use client";

import { useRouter } from "next/navigation";
import { ExternalLinkIcon, HistoryIcon, MoreHorizontalIcon, RefreshCwIcon } from "lucide-react";

import { AppAccountsTab, type AccountsFilter } from "@/components/apps/app-accounts-tab";
import { AppSettingsTab } from "@/components/apps/app-settings-tab";
import { ConnectionTab } from "@/components/apps/connection-tab";
import { SyncRunsTab } from "@/components/apps/sync-runs-tab";
import { AppAvatar } from "@/components/common/avatars";
import { TextLink } from "@/components/common/links";
import { IntegrationIcon } from "@/components/common/integration-icon";
import { ConvertedMoney, ConvertedPrice } from "@/components/common/converted-money";
import { DetailHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { RelativeTime } from "@/components/common/relative-time";
import { Stat, StatStrip } from "@/components/common/stat";
import { ConnectionBadge, TONE_TEXT } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DetailPageSkeleton } from "@/components/common/page-skeletons";
import { useApp } from "@/hooks/use-apps";
import { useSyncConnection, useSyncInProgress } from "@/hooks/use-connection";
import { useUrlTab } from "@/hooks/use-url-tab";
import type { AppDetail } from "@/lib/api/types";
import { cn } from "@/lib/utils";

export type AppTab = "accounts" | "connection" | "sync" | "settings";

export interface AppDetailViewProps {
  id: string;
  initialTab?: AppTab;
  initialAccountsFilter?: AccountsFilter;
}

function SyncButton({ app }: { app: AppDetail }) {
  const sync = useSyncConnection(app.id);
  const syncing = useSyncInProgress(app.id) || sync.isPending;
  return (
    <Button variant="outline" disabled={syncing} onClick={() => sync.mutate()}>
      <RefreshCwIcon className={syncing ? "animate-spin" : undefined} />
      {syncing ? "Syncing…" : "Sync now"}
    </Button>
  );
}

function MoreMenu({ app }: { app: AppDetail }) {
  const router = useRouter();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" size="icon" aria-label="More" />}>
        <MoreHorizontalIcon />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-44">
        <DropdownMenuItem onClick={() => router.push(`/audit?app=${app.id}`)}>
          <HistoryIcon />
          History
        </DropdownMenuItem>
        {app.admin_url && (
          <DropdownMenuItem onClick={() => window.open(app.admin_url!, "_blank", "noopener,noreferrer")}>
            <ExternalLinkIcon />
            Admin panel
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function AppPage({ app, initialTab, initialAccountsFilter }: Omit<AppDetailViewProps, "id"> & { app: AppDetail }) {
  const [tab, setTab] = useUrlTab<AppTab>(initialTab, "accounts");
  return (
    <>
      <DetailHeader
        avatar={<AppAvatar name={app.name} slug={app.slug} connectorKey={app.connector_key} logoUrl={app.logo_url} size="lg" />}
        title={app.name}
        badges={
          <>
            <IntegrationIcon integration={app.integration} withLabel />
            {app.connection_status && <ConnectionBadge status={app.connection_status} />}
          </>
        }
        subtitle={
          app.admin_url || app.website ? (
            <TextLink href={(app.admin_url || app.website)!} external>
              {(app.admin_url || app.website)!.replace(/^https?:\/\//, "")}
            </TextLink>
          ) : (
            app.slug
          )
        }
        actions={
          <>
            {app.connection && <SyncButton app={app} />}
            <MoreMenu app={app} />
          </>
        }
      />
      <StatStrip>
        <Stat label="Seats">
          {app.active_seats}
        </Stat>
        <Stat label="Accounts">
          {app.accounts_count}
        </Stat>
        <Stat label="Without owner">
          <span className={cn(app.unassigned_count > 0 && TONE_TEXT.warning)}>{app.unassigned_count}</span>
        </Stat>
        <Stat label="Price">
          {app.pricing_model === "free" ? "Free" : <ConvertedPrice converted={app.price_converted} original={app.price} showOriginal />}
        </Stat>
        <Stat label="Monthly cost">
          <ConvertedMoney converted={app.monthly_cost_converted} original={app.monthly_cost} showOriginal />
        </Stat>
        <Stat label="Last sync">
          <RelativeTime value={app.last_synced_at} className="text-foreground" />
        </Stat>
      </StatStrip>
      <Tabs value={tab} onValueChange={(value) => setTab(value as AppTab)}>
        <TabsList variant="line" className="mb-3">
          <TabsTrigger value="accounts">
            Accounts <span className="text-muted-foreground tabular-nums">{app.accounts_count}</span>
          </TabsTrigger>
          <TabsTrigger value="connection">Connection</TabsTrigger>
          <TabsTrigger value="sync">Sync history</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>
        <TabsContent value="accounts">
          <AppAccountsTab app={app} initialFilter={initialAccountsFilter} />
        </TabsContent>
        <TabsContent value="connection">
          <ConnectionTab app={app} />
        </TabsContent>
        <TabsContent value="sync">
          <SyncRunsTab app={app} />
        </TabsContent>
        <TabsContent value="settings">
          <AppSettingsTab app={app} />
        </TabsContent>
      </Tabs>
    </>
  );
}

export function AppDetailView({ id, ...rest }: AppDetailViewProps) {
  const query = useApp(id);
  return (
    <QueryState query={query} loading={<DetailPageSkeleton stats={6} tabs={4} />}>
      {(app) => <AppPage app={app} {...rest} />}
    </QueryState>
  );
}
