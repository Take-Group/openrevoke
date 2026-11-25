"use client";

import { PlayIcon } from "lucide-react";

import { LiveView } from "@/components/browser/live-view";
import { InlineError, Notice } from "@/components/common/notice";
import { Panel } from "@/components/common/panel";
import { Step, Steps, type StepState } from "@/components/common/steps";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useBrowserState } from "@/hooks/use-browser";
import { useGoogleCloudSetup, useStartGoogleCloudSetup } from "@/hooks/use-discovery";
import { errorMessage } from "@/lib/api/client";
import type { GoogleCloudSetupOut, GoogleCloudSetupStep } from "@/lib/api/discovery-types";

const STEP_STATE: Record<GoogleCloudSetupStep["state"], StepState> = {
  pending: "todo",
  active: "running",
  done: "done",
  failed: "failed",
};

/** What the admin has to do now, under the steps. */
function NextAction({ setup }: { setup: GoogleCloudSetupOut }) {
  if (setup.status === "needs_sign_in" || setup.status === null) {
    return (
      <p className="text-sm text-muted-foreground">
        Sign in to Google in the browser on the right with a Google Workspace super admin, then start. Open Revoke
        creates a project &quot;Open Revoke&quot; in your Google Cloud, sets up the consent screen as Internal and an
        OAuth client. You only click Allow at the end. Starting it accepts the Google API Services: User Data Policy
        on the consent screen setup for your company.
      </p>
    );
  }
  if (setup.status === "waiting_for_consent") {
    return (
      <Notice tone="warning">
        Your turn: in the browser on the right, choose your account, keep all permissions ticked and click Allow.
      </Notice>
    );
  }
  if (setup.status === "running") {
    return <p className="text-sm text-muted-foreground">Working in the browser on the right. Do not click there.</p>;
  }
  return null;
}

/** Automatic setup: Open Revoke clicks through the Google Cloud console in the shared browser. */
export function GoogleAutoSetup() {
  const setup = useGoogleCloudSetup();
  const start = useStartGoogleCloudSetup();
  const browser = useBrowserState();
  const data = setup.data;
  const busy = data?.status === "running" || data?.status === "waiting_for_consent";

  return (
    <div className="grid gap-6 lg:grid-cols-[20rem_minmax(0,1fr)]">
      <Panel className="self-start" bodyClassName="flex flex-col gap-4 p-5">
        {data ? (
          <>
            <Steps className="gap-3">
              {data.steps.map((step, index) => (
                <Step key={step.key} n={index + 1} title={step.label} state={STEP_STATE[step.state]} />
              ))}
            </Steps>
            {data.project_id && (
              <p className="text-xs text-muted-foreground">
                Project <span className="font-mono">{data.project_id}</span>
                {data.admin_email && <> · {data.admin_email}</>}
              </p>
            )}
            <NextAction setup={data} />
            {data.status === "failed" && data.error && <InlineError message={data.error} />}
            {start.error && <InlineError message={errorMessage(start.error)} />}
            <Button onClick={() => start.mutate({})} disabled={busy || start.isPending} className="self-start">
              <PlayIcon />
              {busy ? "Setting up…" : data.status ? "Start again" : "Set up automatically"}
            </Button>
          </>
        ) : (
          <Skeleton className="h-64" />
        )}
      </Panel>
      <div className="aspect-video min-h-[360px]">
        {browser.data ? <LiveView state={browser.data} /> : <Skeleton className="h-full w-full" />}
      </div>
    </div>
  );
}
