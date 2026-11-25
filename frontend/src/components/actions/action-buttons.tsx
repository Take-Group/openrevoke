"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  CheckIcon,
  HandIcon,
  RotateCcwIcon,
  SparklesIcon,
  SquareArrowOutUpRightIcon,
  UndoIcon,
  UserIcon,
  XIcon,
} from "lucide-react";

import { RevealSecretButton } from "@/components/actions/reveal-secret-dialog";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { TextLink } from "@/components/common/links";
import { RowActions } from "@/components/data-table/row-actions";
import { Button } from "@/components/ui/button";
import { DropdownMenuItem, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { useActionTransition } from "@/hooks/use-actions";
import { useRecipeFixDecision } from "@/hooks/use-recipe-fixes";
import { ApiError, errorMessage } from "@/lib/api/client";
import { accountLabel, actionOperation } from "@/lib/format";
import type { ActionOut } from "@/lib/api/types";

// Allowed moves, as the backend checks them (services/actions.py TRANSITIONS).
function canApprove(action: ActionOut) {
  return action.status === "pending_approval";
}
function canComplete(action: ActionOut) {
  return action.kind === "manual_task" && (action.status === "pending_approval" || action.status === "approved");
}
function canCancel(action: ActionOut) {
  return ["pending_approval", "approved", "failed"].includes(action.status);
}
/** A failed connector write: retry (reads first) or hand it to a person. */
function canRetry(action: ActionOut) {
  return action.status === "failed" && action.kind !== "manual_task";
}

function target(action: ActionOut): string {
  const who = action.account ? accountLabel(action.account) : (action.payload.email ?? "the account");
  const operation = action.payload.operation ?? action.kind;
  if (operation === "create_account") return `You created or invited ${who} in ${action.app.name}.`;
  if (operation === "delete_account") return `You removed ${who} from ${action.app.name}.`;
  return `You did “${actionOperation(action)}” in ${action.app.name}.`;
}

export function ActionButtons({ action }: { action: ActionOut }) {
  const router = useRouter();
  const approve = useActionTransition("approve");
  const cancel = useActionTransition("cancel");
  const complete = useActionTransition("complete");
  const retry = useActionTransition("retry");
  const byHand = useActionTransition("by-hand");
  const approveFix = useRecipeFixDecision("approve");
  const rejectFix = useRecipeFixDecision("reject");
  const [confirmDone, setConfirmDone] = useState(false);
  const [confirmFix, setConfirmFix] = useState(false);
  const busy =
    approve.isPending ||
    cancel.isPending ||
    complete.isPending ||
    retry.isPending ||
    byHand.isPending ||
    approveFix.isPending ||
    rejectFix.isPending;
  // An irreversible click the AI wants to change: nothing uses it until an admin approves.
  const proposedFix = action.status === "failed" ? action.recipe_fixes.find((fix) => fix.status === "proposed") : undefined;
  const activeFixes = action.recipe_fixes.filter((fix) => fix.status === "active");
  const inlineError = canApprove(action) ? approve.error : canRetry(action) ? retry.error : null;
  // A refused connector write (400) is usually "writes are disabled": point to the switch.
  const refused = inlineError instanceof ApiError && inlineError.status === 400 && action.kind !== "manual_task";

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center justify-end gap-1">
        {/* Mounted for every create, so a refetch that clears has_secret_result keeps the open dialog. */}
        {action.kind === "create_account" && <RevealSecretButton action={action} />}
        {canApprove(action) && (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => approve.mutate(action.id)}>
            <CheckIcon />
            Approve
          </Button>
        )}
        {proposedFix && (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => setConfirmFix(true)}>
            <SparklesIcon />
            Review fix
          </Button>
        )}
        {canRetry(action) && (
          <Button size="sm" variant="outline" disabled={busy} onClick={() => retry.mutate(action.id)}>
            <RotateCcwIcon />
            Retry
          </Button>
        )}
        {canComplete(action) && (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => setConfirmDone(true)}>
            Mark done
          </Button>
        )}
        <RowActions>
          <DropdownMenuItem onClick={() => router.push(`/apps/${action.app.app_id}`)}>
            <SquareArrowOutUpRightIcon />
            Open app
          </DropdownMenuItem>
          {action.person && (
            <DropdownMenuItem onClick={() => router.push(`/people/${action.person!.person_id}`)}>
              <UserIcon />
              Open person
            </DropdownMenuItem>
          )}
          {(canRetry(action) || activeFixes.length > 0 || proposedFix) && <DropdownMenuSeparator />}
          {canRetry(action) && (
            <DropdownMenuItem disabled={busy} onClick={() => byHand.mutate(action.id)}>
              <HandIcon />
              Do it by hand
            </DropdownMenuItem>
          )}
          {proposedFix && (
            <DropdownMenuItem disabled={busy} onClick={() => rejectFix.mutate(proposedFix.id)}>
              <XIcon />
              Reject AI fix
            </DropdownMenuItem>
          )}
          {activeFixes.map((fix) => (
            <DropdownMenuItem key={fix.id} disabled={busy} onClick={() => rejectFix.mutate(fix.id)}>
              <UndoIcon />
              Revert AI fix of “{fix.step_id}”
            </DropdownMenuItem>
          ))}
          {canCancel(action) && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" disabled={busy} onClick={() => cancel.mutate(action.id)}>
                <XIcon />
                Cancel action
              </DropdownMenuItem>
            </>
          )}
        </RowActions>
        <ConfirmDialog
          open={confirmDone}
          onOpenChange={setConfirmDone}
          title="Mark as done?"
          description={target(action)}
          confirmLabel="Mark done"
          pending={complete.isPending}
          onConfirm={() => complete.mutate(action.id, { onSuccess: () => setConfirmDone(false) })}
        />
        {proposedFix && (
          <ConfirmDialog
            open={confirmFix}
            onOpenChange={setConfirmFix}
            title="Use the AI's fix for an irreversible click?"
            description={`Step “${proposedFix.step_goal || proposedFix.step_id}” cannot be undone. ${proposedFix.note} After you approve, retry the action: it reads ${action.app.name} first and clicks only if the change is not there yet.`}
            confirmLabel="Approve fix"
            pending={approveFix.isPending}
            onConfirm={() => approveFix.mutate(proposedFix.id, { onSuccess: () => setConfirmFix(false) })}
          />
        )}
      </div>
      {inlineError && (
        <div role="alert" className="max-w-64 text-left text-xs whitespace-normal text-destructive">
          {errorMessage(inlineError)}
          {refused && (
            <TextLink href={`/apps/${action.app.app_id}?tab=connection`} className="mt-0.5 block w-fit">
              Connection settings
            </TextLink>
          )}
        </div>
      )}
    </div>
  );
}
