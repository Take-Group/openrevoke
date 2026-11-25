"use client";

import { useEffect, useRef, useState } from "react";
import {
  ExternalLinkIcon,
  GlobeIcon,
  MaximizeIcon,
  PanelRightCloseIcon,
  PanelRightOpenIcon,
} from "lucide-react";

import { BrowserAppsList } from "@/components/browser/browser-apps-list";
import { LiveView, liveViewUrl } from "@/components/browser/live-view";
import { NotAvailable } from "@/components/common/empty-state";
import { InlineError } from "@/components/common/notice";
import { PageHeader, SectionHeader } from "@/components/common/page-header";
import { Panel } from "@/components/common/panel";
import { Skeleton } from "@/components/ui/skeleton";
import { Button, buttonVariants } from "@/components/ui/button";
import { useBrowserState } from "@/hooks/use-browser";
import { errorMessage, isNotImplemented } from "@/lib/api/client";
import type { BrowserState } from "@/lib/api/types";

function OpenTabs({ state }: { state: BrowserState }) {
  if (state.tabs.length === 0) return null;
  return (
    <section className="border-t px-2 pt-3">
      <SectionHeader title="Tabs" meta={state.tabs.length} className="px-2" />
      <ul className="flex flex-col">
        {state.tabs.map((tab) => (
          <li key={tab.id} className="rounded-md px-2 py-1.5 leading-tight">
            <span className="block truncate text-sm">{tab.title || "(no title)"}</span>
            <span className="block truncate text-xs text-muted-foreground">{tab.url}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

const SIDE_PANEL_KEY = "open-revoke:browser-side-panel";

/** Side panel with the log-in list: hidden by default so the live view gets the width; remembered. */
function useSidePanel() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage exists only in the browser
    setOpen(window.localStorage.getItem(SIDE_PANEL_KEY) === "open");
  }, []);
  const toggle = () =>
    setOpen((value) => {
      window.localStorage.setItem(SIDE_PANEL_KEY, value ? "closed" : "open");
      return !value;
    });
  return [open, toggle] as const;
}

export function BrowserView() {
  const browser = useBrowserState();
  const state = browser.data;
  const [sideOpen, toggleSide] = useSidePanel();
  const viewRef = useRef<HTMLDivElement>(null);

  return (
    <>
      <PageHeader
        icon={GlobeIcon}
        title="Browser"
        className="md:mb-0"
        actions={
          <>
            {state?.live_view_url && (
              <>
                <Button variant="outline" onClick={() => void viewRef.current?.requestFullscreen()}>
                  <MaximizeIcon />
                  Full screen
                </Button>
                <a
                  href={liveViewUrl(state.live_view_url, true)}
                  target="_blank"
                  rel="noreferrer"
                  className={buttonVariants({ variant: "outline" })}
                >
                  <ExternalLinkIcon />
                  New tab
                </a>
              </>
            )}
            <Button variant="outline" onClick={toggleSide} aria-pressed={sideOpen}>
              {sideOpen ? <PanelRightCloseIcon /> : <PanelRightOpenIcon />}
              Log in to apps
            </Button>
          </>
        }
      />
      {browser.isError &&
        (isNotImplemented(browser.error) ? (
          <NotAvailable what="The shared browser" />
        ) : (
          <InlineError message={errorMessage(browser.error)} />
        ))}
      {(browser.isPending || state) && (
        // Edge to edge under the page bar (3.5rem): the negative margins undo the content padding of
        // AdminLayout (full-width page). The browser display follows the size of the view (fit).
        <div className="flex flex-col gap-4 md:-mx-6 md:-mb-5 md:h-[calc(100svh-3.5rem)] md:flex-row md:gap-0">
          <div ref={viewRef} className="h-[75svh] min-h-[480px] min-w-0 flex-1 bg-black md:h-full md:min-h-0">
            {state ? <LiveView state={state} fit bare /> : <Skeleton className="h-full w-full rounded-none" />}
          </div>
          {sideOpen && (
            <Panel
              title="Log in"
              className="md:w-72 md:shrink-0 md:rounded-none md:border-0 md:border-l md:shadow-none"
              bodyClassName="overflow-y-auto py-2"
            >
              <p className="px-4 pb-2 text-xs text-muted-foreground">
                Your password manager is installed in this browser. Unlock it once in the view,
                then open an app below and let it fill the sign-in; finish any 2FA yourself.
              </p>
              <div className="px-2">
                {state ? (
                  <BrowserAppsList apps={state.apps} tabs={state.tabs} usable={state.available} />
                ) : (
                  <Skeleton className="mx-2 h-24" />
                )}
              </div>
              {state && <OpenTabs state={state} />}
            </Panel>
          )}
        </div>
      )}
    </>
  );
}
