"use client";

import { useState } from "react";
import { ScanSearchIcon } from "lucide-react";

import { CopyField } from "@/components/common/copy-button";
import { FormField } from "@/components/common/form-field";
import { InlineError } from "@/components/common/notice";
import { Panel } from "@/components/common/panel";
import { Step, Steps } from "@/components/common/steps";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useConnectDiscoverySource } from "@/hooks/use-discovery";
import { errorMessage } from "@/lib/api/client";
import type { DiscoveryConnector } from "@/lib/api/discovery-types";

/** Alternative to Connect with Google: a service account key with domain-wide delegation. */
export function ServiceAccountSetup({ connector }: { connector: DiscoveryConnector | undefined }) {
  const connect = useConnectDiscoverySource();
  const [adminEmail, setAdminEmail] = useState("");
  const [key, setKey] = useState("");
  const required = connector?.required_scopes ?? [];
  const optional = connector?.optional_scopes ?? [];

  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <Panel className="lg:col-span-3" bodyClassName="p-5">
        <Steps>
          <Step
            n={1}
            title="Create a service account"
            description="In Google Cloud Console, enable the Admin SDK API, create a service account without roles and add a JSON key. The key file is a secret: paste it here and delete the file. Google Cloud organizations created since May 2024 block key creation by default; use Connect with Google there."
          />
          <Step
            n={2}
            title="Allow domain-wide delegation"
            description={
              <>
                In admin.google.com go to Security, Access and data control, API controls, Domain-wide delegation. Add
                the service account&apos;s Client ID with these scopes:
              </>
            }
          >
            {required.map((scope) => (
              <CopyField key={scope} value={scope} label="scope" />
            ))}
            {optional.length > 0 && (
              <>
                <p className="text-[0.8125rem] text-muted-foreground">
                  Optional: the current token of every person, also for apps authorized more than 180 days ago. This
                  scope can also revoke tokens; Open Revoke only reads them.
                </p>
                {optional.map((scope) => (
                  <CopyField key={scope} value={scope} label="scope" />
                ))}
              </>
            )}
          </Step>
          <Step
            n={3}
            title="Connect and scan"
            description="Open Revoke checks both scopes before it saves anything, then imports people and runs the first scan."
          />
        </Steps>
      </Panel>
      <Panel className="self-start lg:col-span-2" bodyClassName="p-5">
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            connect.mutate({
              admin_email: adminEmail.trim(),
              service_account_json: key,
            });
          }}
        >
          <FormField
            label="Admin e-mail"
            htmlFor="discovery-admin"
            required
            hint="A super admin. The service account acts as this person."
          >
            <Input
              id="discovery-admin"
              type="email"
              autoComplete="off"
              placeholder="admin@yourcompany.com"
              value={adminEmail}
              onChange={(event) => setAdminEmail(event.target.value)}
              required
            />
          </FormField>
          <FormField label="Service account key (JSON)" htmlFor="discovery-key" required hint="Stored encrypted.">
            <Textarea
              id="discovery-key"
              className="max-h-48 min-h-28 font-mono text-xs"
              spellCheck={false}
              autoComplete="off"
              placeholder='{"type": "service_account", ...}'
              value={key}
              onChange={(event) => setKey(event.target.value)}
              required
            />
          </FormField>
          {connect.error && <InlineError message={errorMessage(connect.error)} />}
          <Button type="submit" disabled={connect.isPending || !adminEmail || !key} className="self-start">
            <ScanSearchIcon />
            {connect.isPending ? "Checking Google…" : "Connect and scan"}
          </Button>
        </form>
      </Panel>
    </div>
  );
}
