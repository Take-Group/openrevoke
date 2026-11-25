"use client";

import { AppWindowIcon, LogInIcon, PanelTopIcon } from "lucide-react";

import { AppAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { Hint } from "@/components/common/info-tip";
import { RecordLink } from "@/components/common/links";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { useOpenInBrowser } from "@/hooks/use-browser";
import type { BrowserApp, BrowserTab, ConnectionStatus } from "@/lib/api/types";

const LOGIN_LABEL: Record<ConnectionStatus, string> = {
  ok: "Logged in",
  needs_login: "Logged out",
  error: "Error",
  never_synced: "Not checked",
};

function loginHint(app: BrowserApp, usable: boolean): string {
  if (!app.login_url) return "No login page: set the admin URL or a browser connector";
  return usable ? `Opens ${app.login_url}` : "The browser is not available";
}

/** Apps that use the shared browser, each with its login state and "Log in". */
export function BrowserAppsList({ apps, tabs, usable }: { apps: BrowserApp[]; tabs: BrowserTab[]; usable: boolean }) {
  const open = useOpenInBrowser();
  const tabApps = new Set(tabs.map((tab) => tab.app_id).filter(Boolean));

  if (apps.length === 0) {
    return <EmptyState icon={AppWindowIcon} title="No apps use the browser yet" className="py-8" />;
  }
  return (
    <ul className="flex flex-col">
      {apps.map((app) => {
        const pending = open.isPending && open.variables?.app_id === app.app_id;
        return (
          <li key={app.app_id} className="flex items-center gap-2.5 px-2 py-2">
            <AppAvatar name={app.name} connectorKey={app.connector_key} size="sm" />
            <div className="min-w-0 flex-1 leading-tight">
              <RecordLink href={`/apps/${app.app_id}?tab=connection`} className="block truncate text-sm font-medium">
                {app.name}
              </RecordLink>
              <span className="mt-1 flex items-center gap-1.5 text-muted-foreground">
                {app.connection_status ? (
                  <StatusBadge status={app.connection_status} label={LOGIN_LABEL[app.connection_status]} />
                ) : (
                  <StatusBadge status="none" label="Not connected" tone="neutral" />
                )}
                {tabApps.has(app.app_id) && (
                  <Hint label="Open in a tab">
                    <PanelTopIcon className="size-3.5" />
                  </Hint>
                )}
              </span>
              {app.last_error && app.connection_status !== "ok" && (
                <Hint label={app.last_error}>
                  <span className="mt-1 block truncate text-xs text-destructive">{app.last_error}</span>
                </Hint>
              )}
            </div>
            <Hint label={loginHint(app, usable)}>
              <span tabIndex={!usable || !app.login_url ? 0 : undefined}>
                <Button
                  size="sm"
                  variant={app.connection_status === "needs_login" ? "default" : "outline"}
                  disabled={!usable || pending || !app.login_url}
                  onClick={() => open.mutate({ app_id: app.app_id })}
                >
                  <LogInIcon />
                  {pending ? "Opening…" : "Log in"}
                </Button>
              </span>
            </Hint>
          </li>
        );
      })}
    </ul>
  );
}
