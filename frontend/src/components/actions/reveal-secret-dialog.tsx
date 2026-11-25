"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { KeyRoundIcon } from "lucide-react";

import { CopyField } from "@/components/common/copy-button";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useRevealSecret } from "@/hooks/use-actions";
import { accountLabel, humanize } from "@/lib/format";
import type { ActionOut, ActionSecret } from "@/lib/api/types";

/**
 * "Reveal password": the backend returns the one-time secret once and deletes it.
 * Render it for every create action: the button shows only with `has_secret_result`, the dialog
 * stays open after a refetch clears that flag.
 */
export function RevealSecretButton({ action }: { action: ActionOut }) {
  const [open, setOpen] = useState(false);
  const [secret, setSecret] = useState<ActionSecret | null>(null);
  const reveal = useRevealSecret();
  const queryClient = useQueryClient();
  const who = action.account ? accountLabel(action.account) : (action.payload.email ?? "the account");

  return (
    <>
      {action.has_secret_result && (
        <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
          <KeyRoundIcon />
          Password
        </Button>
      )}
      <Dialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next && secret) {
            setSecret(null);
            // Only now: the refreshed row has no secret any more and hides this button.
            void queryClient.invalidateQueries({ queryKey: ["actions"] });
          }
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{secret ? humanize(secret.kind) : "Reveal the temporary password?"}</DialogTitle>
            <DialogDescription>
              {secret ? `${who} · ${action.app.name}` : `Temporary password for ${who} in ${action.app.name}.`}
            </DialogDescription>
          </DialogHeader>
          {secret ? (
            <div className="flex flex-col gap-3">
              <CopyField value={secret.value} label={humanize(secret.kind).toLowerCase()} />
              <p className="text-xs text-muted-foreground">Shown only now. Send it over a safe channel.</p>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">It can be revealed only once.</p>
          )}
          <DialogFooter>
            {secret ? (
              <>
                <Button onClick={() => setOpen(false)}>Done</Button>
              </>
            ) : (
              <>
                <Button variant="outline" onClick={() => setOpen(false)}>
                  Cancel
                </Button>
                <Button disabled={reveal.isPending} onClick={() => reveal.mutate(action.id, { onSuccess: setSecret })}>
                  {reveal.isPending ? "Revealing…" : "Reveal once"}
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
