"use client";

import { useState } from "react";
import Link from "next/link";
import { EyeOffIcon, PlusIcon, RotateCcwIcon, SquareArrowOutUpRightIcon } from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useTrackDiscoveredApp, useUpdateDiscoveredApp } from "@/hooks/use-discovery";
import type { DiscoveredAppOut } from "@/lib/api/discovery-types";

interface ReviewActionsProps {
  app: DiscoveredAppOut;
  size?: "sm" | "default";
  /**
   * People who signed in and are active in the directory. When given (the detail page), a switch
   * next to Track also adds a manual account for each of them.
   */
  activeSignIns?: number;
}

/**
 * What the admin does with a found app: track it as an app in Open Revoke (then connect it
 * to clean up accounts), ignore it, or undo the choice.
 */
export function ReviewActions({ app, size = "sm", activeSignIns }: ReviewActionsProps) {
  const [withAccounts, setWithAccounts] = useState(false);
  const track = useTrackDiscoveredApp(app.id);
  const update = useUpdateDiscoveredApp(app.id);
  const busy = track.isPending || update.isPending;

  if (app.status === "tracked" && app.app) {
    return (
      <div className="flex items-center justify-end gap-1.5" data-row-ignore>
        <Link href={`/apps/${app.app.id}`} className={buttonVariants({ variant: "outline", size })}>
          <SquareArrowOutUpRightIcon />
          Open app
        </Link>
      </div>
    );
  }
  if (app.status === "ignored") {
    return (
      <div className="flex items-center justify-end" data-row-ignore>
        <Button variant="ghost" size={size} disabled={busy} onClick={() => update.mutate({ status: "new" })}>
          <RotateCcwIcon />
          Restore
        </Button>
      </div>
    );
  }
  return (
    <div className="flex items-center justify-end gap-1.5" data-row-ignore>
      <Button
        variant="ghost"
        size={size}
        disabled={busy}
        title="Ignore"
        onClick={() => update.mutate({ status: "ignored" })}
      >
        <EyeOffIcon />
        {/* Phones show the icon only, so the row keeps Track on screen. */}
        <span className="max-md:sr-only">Ignore</span>
      </Button>
      {activeSignIns ? (
        <div className="mr-2 flex items-center gap-2">
          <Switch id={`accounts-${app.id}`} checked={withAccounts} disabled={busy} onCheckedChange={setWithAccounts} />
          <Label htmlFor={`accounts-${app.id}`} className="text-[0.8125rem] font-normal text-muted-foreground">
            Also add accounts for the {activeSignIns} {activeSignIns === 1 ? "person" : "people"} who signed in
          </Label>
        </div>
      ) : null}
      <Button
        variant="outline"
        size={size}
        disabled={busy}
        onClick={() => track.mutate(withAccounts ? { create_accounts: true } : undefined)}
      >
        <PlusIcon />
        Track
      </Button>
    </div>
  );
}
