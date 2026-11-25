"use client";

import { CalendarIcon, KeyRoundIcon, ShieldAlertIcon, UsersIcon } from "lucide-react";

import { AppAvatar } from "@/components/common/avatars";
import { InfoTip } from "@/components/common/info-tip";
import { TextLink } from "@/components/common/links";
import { Notice } from "@/components/common/notice";
import { DetailHeader, SectionHeader } from "@/components/common/page-header";
import { QueryState } from "@/components/common/query-state";
import { Stat, StatStrip } from "@/components/common/stat";
import { StatusBadge, TagBadge } from "@/components/common/status-badge";
import { GrantsTable } from "@/components/discovery/grants-table";
import { ReviewActions } from "@/components/discovery/review-actions";
import { DetailPageSkeleton } from "@/components/common/page-skeletons";
import { useDiscoveredApp } from "@/hooks/use-discovery";
import { formatWhen } from "@/lib/format";
import type { DiscoveredAppDetail } from "@/lib/api/discovery-types";

const STATUS_LABEL = { new: "New", tracked: "Tracked", ignored: "Ignored" } as const;
const STATUS_TONE = { new: "info", tracked: "success", ignored: "neutral" } as const;

function hostOf(url: string): string {
  try {
    return new URL(url).host.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/** Website from the catalog, the name Google shows, and whether the app is tracked. */
function Subtitle({ app }: { app: DiscoveredAppDetail }) {
  const { catalog } = app;
  const parts: React.ReactNode[] = [];
  if (catalog) {
    parts.push(
      <span key="site" className="inline-flex items-center gap-1">
        <TextLink href={catalog.website} external className="font-normal">
          {hostOf(catalog.website)}
        </TextLink>
        {catalog.matched_by === "name" && (
          <InfoTip>
            Open Revoke knows this app by its name, not by its Google OAuth client, so any app can show this name.
            If nobody in the company uses {catalog.name}, check who published it before trusting it.
          </InfoTip>
        )}
      </span>,
    );
    if (catalog.name !== app.name) parts.push(<span key="google">In Google as “{app.name}”</span>);
  }
  parts.push(<span key="state">{app.app ? `Tracked as ${app.app.name}` : "Found in Google sign-ins"}</span>);
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2">
      {parts.map((part, index) => (
        <span key={index} className="inline-flex items-center gap-2">
          {index > 0 && <span aria-hidden>·</span>}
          {part}
        </span>
      ))}
    </span>
  );
}

function DiscoveredApp({ app }: { app: DiscoveredAppDetail }) {
  const name = app.catalog?.name ?? app.name;
  return (
    <>
      <DetailHeader
        avatar={<AppAvatar name={name} catalogSlug={app.catalog?.slug} size="lg" />}
        title={name}
        badges={<StatusBadge status={app.status} label={STATUS_LABEL[app.status]} tone={STATUS_TONE[app.status]} />}
        subtitle={<Subtitle app={app} />}
        actions={<ReviewActions app={app} size="default" />}
      />
      <StatStrip>
        <Stat label="People" icon={UsersIcon}>
          {app.users}
        </Stat>
        <Stat label="Left or removed" icon={ShieldAlertIcon}>
          {app.users_at_risk}
        </Stat>
        <Stat label="Live tokens" icon={KeyRoundIcon}>
          {app.active_tokens ?? "—"}
        </Stat>
        <Stat label="First sign-in" icon={CalendarIcon}>
          {app.first_seen_at ? formatWhen(app.first_seen_at).split(",")[0] : "—"}
        </Stat>
      </StatStrip>
      {app.users_at_risk > 0 && app.status !== "tracked" && (
        <Notice tone="warning" className="mb-4">
          {app.users_at_risk} {app.users_at_risk === 1 ? "person" : "people"} who left or were removed signed in
          here. A sign-in shows they used the app, not that they still hold a paid seat. Track the app and connect
          it to see its real accounts, or check its admin panel.
        </Notice>
      )}
      <GrantsTable grants={app.grants} />
      {app.scopes.length > 0 && (
        <section className="mt-6">
          <SectionHeader title="Access people granted" />
          <div className="flex flex-wrap gap-1.5">
            {app.scopes.map((scope) => (
              <TagBadge key={scope} className="font-mono text-xs">
                {scope.replace("https://www.googleapis.com/auth/", "")}
              </TagBadge>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

export function DiscoveredAppView({ id }: { id: string }) {
  const query = useDiscoveredApp(id);
  return (
    <QueryState query={query} loading={<DetailPageSkeleton stats={4} tabs={0} />}>
      {(app) => <DiscoveredApp app={app} />}
    </QueryState>
  );
}
