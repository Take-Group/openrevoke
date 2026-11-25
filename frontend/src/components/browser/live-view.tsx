"use client";

import { MonitorOffIcon } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { Panel } from "@/components/common/panel";
import { cn } from "@/lib/utils";
import type { BrowserState } from "@/lib/api/types";

/**
 * Address of the live view (docker/browser/live.html). `fit`: the browser display takes the size
 * of the view (resize=1), so pages are laid out to fill it; only one view on screen should do that.
 */
export function liveViewUrl(url: string, fit: boolean): string {
  if (!fit) return url;
  const address = new URL(url, "http://panel");
  address.searchParams.set("resize", "1");
  return url.startsWith("http") ? address.href : `${address.pathname}${address.search}`;
}

/**
 * Live view of the shared browser. Fills its box. Without `fit` the browser display keeps its
 * size and is scaled into the box (dark bars when the shapes differ); with `fit` the display
 * follows the box (`/browser`). `bare`: no frame, for an edge-to-edge page.
 */
export function LiveView({
  state,
  fit = false,
  bare = false,
}: {
  state: BrowserState;
  fit?: boolean;
  bare?: boolean;
}) {
  if (!state.available || !state.live_view_url) {
    return (
      <Panel className={cn("h-full w-full", bare && "rounded-none border-0 shadow-none")} bodyClassName="flex items-center justify-center">
        <EmptyState
          icon={MonitorOffIcon}
          title={state.available ? "No live view" : "Browser is offline"}
          description={state.available ? undefined : (state.error ?? "Start the browser container.")}
        />
      </Panel>
    );
  }
  const frame = (
    <iframe
      src={liveViewUrl(state.live_view_url, fit)}
      title="Live view of the shared browser"
      className="block h-full w-full"
      allow="clipboard-read; clipboard-write"
    />
  );
  if (bare) return <div className="h-full w-full bg-black">{frame}</div>;
  return <Panel className="h-full w-full bg-black">{frame}</Panel>;
}
