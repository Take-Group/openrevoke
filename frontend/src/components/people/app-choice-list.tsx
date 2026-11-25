"use client";

import { AppWindowIcon } from "lucide-react";

import { AppAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { Panel } from "@/components/common/panel";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

/** The scrolling list of apps in the Onboard and Offboard dialogs. */
export function AppChoiceList({ emptyTitle, children }: { emptyTitle: string; children: React.ReactNode[] }) {
  return (
    <Panel bodyClassName="flex max-h-72 flex-col divide-y overflow-y-auto text-sm">
      {children.length === 0 ? <EmptyState icon={AppWindowIcon} title={emptyTitle} className="py-6" /> : children}
    </Panel>
  );
}

interface AppChoiceRowProps {
  app: { name: string; slug?: string | null; connectorKey?: string | null };
  /** Muted line under the app name (the account). */
  detail?: React.ReactNode;
  /** What happens to the app, on the right. */
  aside: React.ReactNode;
  /** With a checkbox: the row toggles the choice. */
  choice?: { checked: boolean; disabled: boolean; onToggle: () => void };
}

/** One app: avatar, name, an optional account line and the outcome on the right. */
export function AppChoiceRow({ app, detail, aside, choice }: AppChoiceRowProps) {
  const body = (
    <>
      {choice && <Checkbox disabled={choice.disabled} checked={choice.checked} onCheckedChange={choice.onToggle} />}
      <AppAvatar name={app.name} slug={app.slug} connectorKey={app.connectorKey} size="sm" />
      <span className="min-w-0 flex-1 leading-tight">
        <span className="block truncate font-medium">{app.name}</span>
        {detail && <span className="block truncate text-xs text-muted-foreground">{detail}</span>}
      </span>
      {aside}
    </>
  );
  if (!choice) return <div className="flex items-center gap-3 px-3 py-2">{body}</div>;
  return (
    <label
      className={cn(
        "flex items-center gap-3 px-3 py-2",
        choice.disabled ? "opacity-60" : "cursor-pointer hover:bg-subtle",
      )}
    >
      {body}
    </label>
  );
}
