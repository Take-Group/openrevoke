"use client";

import { useState } from "react";

import { AppAvatar } from "@/components/common/avatars";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { InfoTip } from "@/components/common/info-tip";
import { Panel } from "@/components/common/panel";
import { Button } from "@/components/ui/button";
import { useApproveBatch } from "@/hooks/use-actions";
import { fullName, humanize } from "@/lib/format";
import type { ActionOut, ActionReason } from "@/lib/api/types";

interface Batch {
  id: string;
  person: string;
  reason: ActionReason;
  actions: ActionOut[];
}

function groupBatches(actions: ActionOut[]): Batch[] {
  const batches = new Map<string, Batch>();
  for (const action of actions) {
    if (!action.batch_id) continue;
    const batch = batches.get(action.batch_id) ?? {
      id: action.batch_id,
      person: action.person ? fullName(action.person) : "Unknown person",
      reason: action.reason,
      actions: [],
    };
    batch.actions.push(action);
    batches.set(action.batch_id, batch);
  }
  return [...batches.values()];
}

/** One row per onboarding or offboarding batch with pending actions, each with "Approve all". */
export function BatchBar({ actions }: { actions: ActionOut[] }) {
  const [confirming, setConfirming] = useState<Batch | null>(null);
  const approve = useApproveBatch();
  const batches = groupBatches(actions);
  if (batches.length === 0) return null;

  return (
    <>
      <Panel title="Batches" meta={batches.length}>
        <ul className="divide-y">
          {batches.map((batch) => (
            <li key={batch.id} className="flex items-center gap-4 px-4 py-2.5">
              <div className="min-w-0 flex-1 text-sm">
                <span className="font-medium">{batch.person}</span>
                <span className="text-muted-foreground">
                  {" "}
                  · {humanize(batch.reason)} · {batch.actions.length} {batch.actions.length === 1 ? "action" : "actions"}
                </span>
              </div>
              <div className="hidden items-center -space-x-1 sm:flex">
                {batch.actions.slice(0, 6).map((action) => (
                  <AppAvatar
                    key={action.id}
                    name={action.app.name}
                    slug={action.app.slug}
                    size="xs"
                    className="ring-2 ring-card"
                  />
                ))}
              </div>
              <Button size="sm" onClick={() => setConfirming(batch)}>
                Approve all
              </Button>
            </li>
          ))}
        </ul>
      </Panel>
      <ConfirmDialog
        open={confirming !== null}
        onOpenChange={(open) => !open && setConfirming(null)}
        title={`Approve ${confirming?.reason ?? "offboarding"} of ${confirming?.person ?? ""}?`}
        description={
          <span className="inline-flex items-center gap-1.5">
            {confirming?.actions.length ?? 0} action(s) at once.
            <InfoTip>
              Apps with writes on run them now and confirm each by a read. Manual tasks wait until you mark them done.
              Writes for apps with writes off stay pending.
            </InfoTip>
          </span>
        }
        confirmLabel="Approve all"
        pending={approve.isPending}
        onConfirm={() => confirming && approve.mutate(confirming.id, { onSuccess: () => setConfirming(null) })}
      />
    </>
  );
}
