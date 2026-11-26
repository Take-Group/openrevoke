"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { InlineError } from "@/components/common/notice";
import { OptionSelect } from "@/components/common/option-select";
import { SuggestInput } from "@/components/common/suggest-input";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useMyAccess, useMyTeam, useRequestAccess } from "@/hooks/use-me";
import type { MyAccessRequestResult, RequestableApp } from "@/lib/api/me-types";
import type { RequestPolicy } from "@/lib/api/types";
import { errorMessage } from "@/lib/api/client";
import { fullName } from "@/lib/format";

const SELF = "self";

const POLICY_HINT: Record<RequestPolicy, string> = {
  off: "Not available on request.",
  automatic: "No approval needed: the account is created right away.",
  manager: "The manager approves, then the account is created.",
  manager_then_admin: "The manager approves, then an admin.",
  admin: "An admin approves this request.",
};

function resultText(result: MyAccessRequestResult): string {
  const app = result.app_name;
  switch (result.outcome) {
    case "in_progress":
      return `Approved: the ${app} account is being created.`;
    case "waiting_for_admin":
      return `Approved: an admin creates the ${app} account.`;
    case "waiting_for_manager":
      return `Request sent: ${result.note ?? "the manager"} decides on ${app}.`;
    case "waiting_for_approval":
      return `Request sent: an admin has to approve ${app}.${result.note ? ` ${result.note}` : ""}`;
    case "already_has_account":
      return `There is already a ${app} account.`;
    case "already_requested":
      return `${app} was already asked for.`;
    case "not_available":
      return `${app} is not available on request. Ask an admin.`;
  }
}

/**
 * `/me/request?app=`: ask for an account in an app with a reason (required) and an optional role. A
 * manager can also ask for one of their reports. The app's policy decides who approves.
 */
export function RequestAccessView({ appId }: { appId: string | null }) {
  const router = useRouter();
  const access = useMyAccess();
  const team = useMyTeam();
  const request = useRequestAccess();
  const reports = team.data?.reports ?? [];
  const [forWhom, setForWhom] = useState<string>(SELF);
  const [chosen, setChosen] = useState(appId ?? "");
  const [justification, setJustification] = useState("");
  const [role, setRole] = useState("");
  const member = reports.find((report) => report.person.person_id === forWhom);
  const apps: RequestableApp[] = member ? member.requestable_apps : (access.data?.requestable_apps ?? []);
  const selected = apps.find((option) => option.app.app_id === chosen);

  return (
    <FormPage
      title="Request access"
      backHref="/me"
      backLabel="My access"
      description="Ask for an account in an app your company uses."
      submitLabel="Send request"
      pending={request.isPending}
      submitDisabled={!selected || !justification.trim()}
      onSubmit={(event) => {
        event.preventDefault();
        if (!selected || !justification.trim()) return;
        request.mutate(
          {
            app_id: selected.app.app_id,
            justification: justification.trim(),
            role: role.trim() || null,
            person_id: member ? member.person.person_id : null,
          },
          {
            onSuccess: (result) => {
              toast.success(resultText(result));
              router.push("/me");
            },
          },
        );
      }}
    >
      {access.isPending ? (
        <Skeleton className="h-28 w-full" />
      ) : access.isError ? (
        <InlineError message={errorMessage(access.error)} />
      ) : (
        <>
          {reports.length > 0 && (
            <FormField label="For" htmlFor="request-for" hint="As their manager you can ask for a member of your team.">
              <OptionSelect
                id="request-for"
                value={forWhom}
                onChange={(next) => {
                  setForWhom(next || SELF);
                  setChosen("");
                }}
                required
                options={[
                  { value: SELF, label: "Me" },
                  ...reports.map((report) => ({ value: report.person.person_id, label: fullName(report.person) })),
                ]}
              />
            </FormField>
          )}
          {apps.length === 0 ? (
            <InlineError message="There is no app to ask for: every app is already there or asked for, or the e-mail is not on the people list." />
          ) : (
            <>
              <FormField label="App" htmlFor="request-app" required hint={selected ? POLICY_HINT[selected.policy] : undefined}>
                <OptionSelect
                  id="request-app"
                  value={chosen}
                  onChange={setChosen}
                  placeholder="Choose an app"
                  options={apps.map((option) => ({ value: option.app.app_id, label: option.app.name }))}
                />
              </FormField>
              <FormField
                label="Why do you need it?"
                htmlFor="request-justification"
                required
                hint="The approver reads it next to the request."
              >
                <Textarea
                  id="request-justification"
                  maxLength={2000}
                  required
                  value={justification}
                  onChange={(event) => setJustification(event.target.value)}
                />
              </FormField>
              <FormField label="Role" htmlFor="request-role" hint="Optional. Leave empty for the app's default role.">
                <SuggestInput id="request-role" value={role} onChange={setRole} suggestions={selected?.roles ?? []} placeholder="e.g. member" />
              </FormField>
            </>
          )}
        </>
      )}
    </FormPage>
  );
}
