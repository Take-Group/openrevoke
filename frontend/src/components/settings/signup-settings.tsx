"use client";

import { useState } from "react";

import { FormField } from "@/components/common/form-field";
import { InlineError } from "@/components/common/notice";
import { SwitchField } from "@/components/common/switch-field";
import { SettingsFooter } from "@/components/settings/settings-section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { useOrganizationSettings, useUpdateOrganization } from "@/hooks/use-users";
import { errorMessage } from "@/lib/api/client";
import type { OrganizationSettingsOut } from "@/lib/api/auth-types";

function parseDomains(text: string): string[] {
  return text
    .split(/[\s,;]+/)
    .map((part) => part.trim().toLowerCase().replace(/^@/, ""))
    .filter(Boolean);
}

function SignupForm({ settings }: { settings: OrganizationSettingsOut }) {
  const [enabled, setEnabled] = useState(settings.registration_enabled);
  const [autoApprove, setAutoApprove] = useState(settings.registration_auto_approve);
  const [domains, setDomains] = useState(settings.registration_domains.join(", "));
  const update = useUpdateOrganization("Sign-up settings saved");
  const parsed = parseDomains(domains);
  const changed =
    enabled !== settings.registration_enabled ||
    autoApprove !== settings.registration_auto_approve ||
    parsed.join(",") !== settings.registration_domains.join(",");
  const missingDomain = enabled && autoApprove && parsed.length === 0;

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        update.mutate({ registration_enabled: enabled, registration_auto_approve: autoApprove, registration_domains: parsed });
      }}
    >
      <div className="flex max-w-lg flex-col gap-5">
        <SwitchField
          id="signup-enabled"
          label="Allow sign-up"
          hint="The sign-in page offers “Create account”. New accounts get the User role and see only their own access."
          checked={enabled}
          onChange={setEnabled}
        />
        <SwitchField
          id="signup-auto"
          label="Approve automatically"
          hint="A sign-up with an e-mail in one of the domains below gets in at once. Everyone else still waits for an admin."
          checked={autoApprove}
          disabled={!enabled}
          onChange={setAutoApprove}
        />
        {enabled && autoApprove && (
          <FormField label="Company e-mail domains" htmlFor="signup-domains" hint="Separate with commas, e.g. example.com, example.pl">
            <Input id="signup-domains" value={domains} placeholder="example.com" onChange={(event) => setDomains(event.target.value)} />
          </FormField>
        )}
        {missingDomain && <InlineError message="Add at least one domain, or turn automatic approval off." />}
      </div>
      <SettingsFooter hint="Nothing checks that people own the e-mail they type: keep the panel inside your company network.">
        <Button type="submit" size="sm" disabled={!changed || missingDomain || update.isPending}>
          Save
        </Button>
      </SettingsFooter>
    </form>
  );
}

/** Who can join on their own: sign-up on or off, and the domains approved without an admin. */
export function SignupSettings() {
  const settings = useOrganizationSettings();
  if (settings.isError) return <InlineError message={errorMessage(settings.error)} />;
  if (!settings.data) return <Skeleton className="h-32 w-full" />;
  const data = settings.data;
  return (
    <SignupForm
      key={`${data.registration_enabled}-${data.registration_auto_approve}-${data.registration_domains.join(",")}`}
      settings={data}
    />
  );
}
