"use client";

import { useState } from "react";
import { PlusIcon, XIcon } from "lucide-react";

import { AppLogos } from "@/components/access-profiles/profile-parts";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { LinkButton, RecordLink } from "@/components/common/links";
import { Notice } from "@/components/common/notice";
import { Panel } from "@/components/common/panel";
import { Button } from "@/components/ui/button";
import {
  useCreateRemovals,
  usePersonAccessDrift,
  usePersonAccessProfiles,
  useUnassignPersonProfile,
} from "@/hooks/use-access-profiles";
import type { PersonAccessDrift, PersonAccessProfileOut, ProfileUnassignResult } from "@/lib/api/access-profile-types";
import type { PersonDetail } from "@/lib/api/types";
import { formatWhen } from "@/lib/format";

/** Asks before removing; the mutation lives in the section, because this row disappears when it succeeds. */
function RemoveProfile({
  item,
  pending,
  onConfirm,
}: {
  item: PersonAccessProfileOut;
  pending: boolean;
  onConfirm: () => Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="ghost" size="icon-sm" aria-label={`Remove ${item.profile.name}`} title="Remove profile" onClick={() => setOpen(true)}>
        <XIcon />
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={`Remove ${item.profile.name}?`}
        description="Accounts in apps stay. You can then create removal actions for the apps only this profile gave."
        confirmLabel="Remove profile"
        destructive
        pending={pending}
        onConfirm={() => void onConfirm().then(() => setOpen(false), () => undefined)}
      />
    </>
  );
}

/** Accounts only the removed profile gave: removal is proposed, never automatic. */
function SuggestedRemovals({ result, onDone }: { result: ProfileUnassignResult; onDone: () => void }) {
  const create = useCreateRemovals();
  const items = result.suggested_removals;
  if (items.length === 0) return null;
  return (
    <Notice
      tone="warning"
      title={`${items.length} account(s) came only from ${result.profile.name}`}
      action={
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={onDone}>
            Keep
          </Button>
          <Button size="sm" disabled={create.isPending} onClick={() => create.mutate(items, { onSuccess: onDone })}>
            Create removal actions
          </Button>
        </div>
      }
    >
      {items.map((item) => `${item.app.name} (${item.account.email ?? item.account.username ?? "account"})`).join(", ")}
    </Notice>
  );
}

function DriftLines({ drift }: { drift: PersonAccessDrift }) {
  const lines: [string, string][] = [];
  if (drift.missing.length > 0) {
    lines.push(["Missing", drift.missing.map((item) => `${item.app.name} (${item.profiles.join(", ")})`).join(", ")]);
  }
  if (drift.extra.length > 0) {
    lines.push(["Not in any profile", drift.extra.map((item) => item.app.name).join(", ")]);
  }
  if (drift.role_mismatch.length > 0) {
    lines.push([
      "Other role",
      drift.role_mismatch.map((item) => `${item.app.name}: ${item.role}, profile says ${item.expected_role}`).join("; "),
    ]);
  }
  if (lines.length === 0) return null;
  return (
    <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 border-t px-5 py-3 text-sm">
      {lines.map(([label, value]) => (
        <div key={label} className="contents">
          <dt className="text-muted-foreground">{label}</dt>
          <dd className={label === "Missing" ? "text-warning" : undefined}>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Access profiles of a person on `/people/<id>`: add, remove, what they miss and have outside them. */
export function PersonProfilesSection({ person }: { person: PersonDetail }) {
  const profiles = usePersonAccessProfiles(person.id);
  const drift = usePersonAccessDrift(person.id);
  const unassign = useUnassignPersonProfile(person.id);
  const [removed, setRemoved] = useState<ProfileUnassignResult | null>(null);
  const items = profiles.data?.items ?? [];
  const left = person.status === "left";

  return (
    <div className="mb-6 flex flex-col gap-3">
      {removed && <SuggestedRemovals result={removed} onDone={() => setRemoved(null)} />}
      <Panel
        title="Access profiles"
        meta={profiles.data ? items.length : undefined}
        actions={
          <LinkButton href={`/people/${person.id}/access-profiles/add`} variant="outline" size="sm" disabled={left}>
            <PlusIcon />
            Add profile
          </LinkButton>
        }
        bodyClassName="flex flex-col text-sm"
      >
        {items.length === 0 ? (
          <p className="px-5 py-3 text-muted-foreground">{profiles.isPending ? "Loading…" : "No access profile"}</p>
        ) : (
          <div className="flex flex-col divide-y">
            {items.map((item) => (
              <div key={item.profile.profile_id} className="flex items-center gap-3 px-5 py-2">
                <RecordLink href={`/access-profiles/${item.profile.profile_id}`} className="min-w-0 flex-1 truncate font-medium">
                  {item.profile.name}
                </RecordLink>
                <AppLogos apps={item.apps} max={5} />
                <span className="w-24 text-xs text-muted-foreground max-md:hidden" title={item.assigned_by ?? undefined}>
                  {formatWhen(item.assigned_at).split(",")[0]}
                </span>
                <RemoveProfile
                  item={item}
                  pending={unassign.isPending}
                  onConfirm={() => unassign.mutateAsync(item.profile.profile_id).then(setRemoved)}
                />
              </div>
            ))}
          </div>
        )}
        {drift.data && <DriftLines drift={drift.data} />}
      </Panel>
    </div>
  );
}
