"use client";

import { PenLineIcon, PlugIcon, PlugZapIcon } from "lucide-react";

import { ConnectionCard } from "@/components/apps/connection-card";
import { EmptyState } from "@/components/common/empty-state";
import { LinkButton } from "@/components/common/links";
import { Panel } from "@/components/common/panel";
import { QueryState } from "@/components/common/query-state";
import { useConnectors } from "@/hooks/use-connectors";
import type { AppDetail } from "@/lib/api/types";

export function ConnectionTab({ app }: { app: AppDetail }) {
  const connectors = useConnectors();
  const editHref = `/apps/${app.id}/connection/edit`;

  if (app.integration === "manual" && !app.connection) {
    return (
      <Panel className="max-w-3xl">
        <EmptyState icon={PenLineIcon} title="Manual app" description="To connect it, change the integration in Settings." />
      </Panel>
    );
  }

  return (
    <QueryState query={connectors} feature="The connector catalog" rows={3}>
      {(page) => {
        if (page.items.length === 0) {
          return (
            <Panel className="max-w-3xl">
              <EmptyState icon={PlugZapIcon} title="No connectors available" />
            </Panel>
          );
        }
        return app.connection ? (
          <ConnectionCard
            app={app}
            connection={app.connection}
            connector={page.items.find((c) => c.key === app.connection!.connector_key)}
            editHref={editHref}
          />
        ) : (
          <Panel className="max-w-3xl">
            <EmptyState icon={PlugIcon} title="Not connected" action={<LinkButton href={editHref}>Connect</LinkButton>} />
          </Panel>
        );
      }}
    </QueryState>
  );
}
