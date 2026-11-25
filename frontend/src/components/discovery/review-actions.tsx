"use client";

import Link from "next/link";
import { EyeOffIcon, PlusIcon, RotateCcwIcon, SquareArrowOutUpRightIcon } from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import { useTrackDiscoveredApp, useUpdateDiscoveredApp } from "@/hooks/use-discovery";
import type { DiscoveredAppOut } from "@/lib/api/discovery-types";

/**
 * What the admin does with a found app: track it as an app in Open Revoke (then connect it
 * to clean up accounts), ignore it, or undo the choice.
 */
export function ReviewActions({ app, size = "sm" }: { app: DiscoveredAppOut; size?: "sm" | "default" }) {
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
      <Button variant="outline" size={size} disabled={busy} onClick={() => track.mutate()}>
        <PlusIcon />
        Track
      </Button>
    </div>
  );
}
