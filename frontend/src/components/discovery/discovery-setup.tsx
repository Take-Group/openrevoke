"use client";

import { useState } from "react";

import { Panel } from "@/components/common/panel";
import { Segmented } from "@/components/common/segmented";
import { GoogleAutoSetup } from "@/components/discovery/google-auto-setup";
import { GoogleOAuthSetup } from "@/components/discovery/google-oauth-setup";
import { ServiceAccountSetup } from "@/components/discovery/service-account-setup";
import type { DiscoveryOverview } from "@/lib/api/discovery-types";

type Method = "auto" | "oauth" | "service_account";

/** First run: what the scan reads, then one of two ways to connect Google Workspace. */
export function DiscoverySetup({
  overview,
  callbackError,
}: {
  overview: DiscoveryOverview;
  callbackError: string | null;
}) {
  // A Google error after the guided redirect brings the admin back to the guided form.
  const [method, setMethod] = useState<Method>(callbackError ? "oauth" : "auto");
  const google = overview.connectors.find((connector) => connector.key === "google_workspace");

  return (
    <div className="flex flex-col gap-4">
      <Panel title="Connect Google Workspace" bodyClassName="flex flex-col gap-4 p-4">
        <p className="text-sm text-muted-foreground">
          Open Revoke imports your people (name, e-mail, aliases, status) and keeps them in sync. It also reads
          Google&apos;s audit log of &quot;Sign in with Google&quot; and the app access people granted: every app people
          signed in to, who uses it, and who left the company but still signed in there. Google keeps this log for 180
          days.
        </p>
        <Segmented
          label="How to connect"
          value={method}
          onChange={setMethod}
          options={[
            { value: "auto", label: "Automatic" },
            { value: "oauth", label: "Guided (links)" },
            { value: "service_account", label: "Service account key" },
          ]}
        />
      </Panel>
      {method === "auto" && <GoogleAutoSetup />}
      {method === "oauth" && (
        <GoogleOAuthSetup redirectUri={overview.google_oauth_redirect_uri} callbackError={callbackError} />
      )}
      {method === "service_account" && <ServiceAccountSetup connector={google} />}
    </div>
  );
}
