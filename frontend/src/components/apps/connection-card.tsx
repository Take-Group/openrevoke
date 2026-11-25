"use client";

import { useState } from "react";
import Link from "next/link";
import { LogInIcon, PencilIcon, StethoscopeIcon } from "lucide-react";

import { AppAvatar } from "@/components/common/avatars";
import { LinkButton } from "@/components/common/links";
import { InlineError, Notice } from "@/components/common/notice";
import { Panel } from "@/components/common/panel";
import { RelativeTime } from "@/components/common/relative-time";
import { Stat } from "@/components/common/stat";
import { ConnectionBadge, StatusBadge } from "@/components/common/status-badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { useCheckConnection } from "@/hooks/use-connection";
import { authKindLabel, humanize } from "@/lib/format";
import type { AppDetail, ConnectionCheckResult, ConnectionOut, ConnectorOut } from "@/lib/api/types";

function OnOff({ on }: { on: boolean }) {
  return <StatusBadge status={on ? "on" : "off"} label={on ? "On" : "Off"} tone={on ? "success" : "neutral"} />;
}

function CheckResult({ result }: { result: ConnectionCheckResult }) {
  if (!result.ok) return <InlineError message={result.message || "Check failed"} />;
  return <Notice tone="success">{result.message || "Connection works"}</Notice>;
}

interface ConnectionCardProps {
  app: AppDetail;
  connection: ConnectionOut;
  connector: ConnectorOut | undefined;
  /** The connection form page. */
  editHref: string;
}

/** The saved connection: state, facts, Check, Sync now and Edit. */
export function ConnectionCard({ app, connection, connector, editHref }: ConnectionCardProps) {
  const check = useCheckConnection(app.id);
  const [result, setResult] = useState<ConnectionCheckResult | null>(null);
  const name = connector?.display_name ?? connection.connector_key;

  return (
    <Panel
      className="max-w-3xl"
      title={
        <>
          <AppAvatar name={name} connectorKey={connection.connector_key} size="sm" className="mr-1" />
          <span className="truncate">{name}</span>
          <ConnectionBadge status={connection.status} className="ml-1" />
        </>
      }
      meta={connector ? authKindLabel(connector.auth_kind) : undefined}
      actions={
        <>
          <Button
            variant="ghost"
            size="sm"
            disabled={check.isPending}
            onClick={() => check.mutate(undefined, { onSuccess: setResult })}
          >
            <StethoscopeIcon />
            {check.isPending ? "Checking…" : "Check"}
          </Button>
          <LinkButton href={editHref} variant="outline" size="sm">
            <PencilIcon />
            Edit
          </LinkButton>
        </>
      }
    >
      <dl className="grid grid-cols-2 sm:grid-cols-4 sm:divide-x">
        <Stat label="Last sync">
          <RelativeTime value={connection.last_synced_at} className="text-foreground" />
        </Stat>
        <Stat label="Writes" info="With writes on, approved actions create and remove real accounts.">
          <OnOff on={connection.writes_enabled} />
        </Stat>
        <Stat label="People source" info="New users of this app become people in Open Revoke.">
          <OnOff on={connection.is_people_source} />
        </Stat>
        <Stat label="Secrets">
          {connection.secret_fields_set.length > 0 ? `${connection.secret_fields_set.length} set` : "None"}
        </Stat>
      </dl>
      {connector && connector.capabilities.length > 0 && (
        <p className="border-t px-4 py-2.5 text-xs text-muted-foreground">
          {connector.capabilities.map((capability) => humanize(capability)).join(" · ")}
        </p>
      )}
      {(result || connection.status === "needs_login" || connection.last_error) && (
        <div className="flex flex-col gap-3 border-t px-4 py-3">
          {result && <CheckResult result={result} />}
          {connection.status === "needs_login" && (
            <Notice
              tone="warning"
              action={
                <Link href="/browser" className={buttonVariants({ size: "sm", variant: "outline" })}>
                  <LogInIcon />
                  Browser
                </Link>
              }
            >
              Session expired. Log in again, then sync.
            </Notice>
          )}
          {connection.last_error && <InlineError message={connection.last_error} />}
        </div>
      )}
    </Panel>
  );
}
