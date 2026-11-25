"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { InlineError } from "@/components/common/notice";
import { OptionSelect } from "@/components/common/option-select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useMyAccess, useRequestAccess } from "@/hooks/use-me";
import type { MyAccessRequestResult } from "@/lib/api/me-types";
import { errorMessage } from "@/lib/api/client";

function resultText(result: MyAccessRequestResult): string {
  const app = result.app_name;
  switch (result.outcome) {
    case "in_progress":
      return `Approved: your ${app} account is being created.`;
    case "waiting_for_admin":
      return `Approved: an admin creates your ${app} account.`;
    case "waiting_for_approval":
      return `Request sent: an admin has to approve ${app}.`;
    case "already_has_account":
      return `You already have a ${app} account.`;
    case "already_requested":
      return `You already asked for ${app}.`;
    case "not_available":
      return `${app} is not available on request. Ask an admin.`;
  }
}

/** `/me/request?app=`: ask for an account in an app. The app's self-service policy decides who approves. */
export function RequestAccessView({ appId }: { appId: string | null }) {
  const router = useRouter();
  const access = useMyAccess();
  const request = useRequestAccess();
  const apps = access.data?.requestable_apps ?? [];
  const [chosen, setChosen] = useState(appId ?? "");
  const [message, setMessage] = useState("");
  const selected = apps.find((option) => option.app.app_id === chosen);

  return (
    <FormPage
      title="Request access"
      backHref="/me"
      backLabel="My access"
      description="Ask for an account in an app your company uses."
      submitLabel="Send request"
      pending={request.isPending}
      submitDisabled={!selected}
      onSubmit={(event) => {
        event.preventDefault();
        if (!selected) return;
        request.mutate(
          { app_id: selected.app.app_id, message: message.trim() || null },
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
      ) : apps.length === 0 ? (
        <InlineError message="There is no app to ask for: you have them all, already asked, or your e-mail is not on the people list." />
      ) : (
        <>
          <FormField
            label="App"
            htmlFor="request-app"
            required
            hint={
              selected
                ? selected.needs_approval
                  ? "An admin approves this request first."
                  : "No approval needed: the account is created right away."
                : undefined
            }
          >
            <OptionSelect
              id="request-app"
              value={chosen}
              onChange={setChosen}
              placeholder="Choose an app"
              options={apps.map((option) => ({ value: option.app.app_id, label: option.app.name }))}
            />
          </FormField>
          <FormField label="Why do you need it?" htmlFor="request-message" hint="Optional. The admin sees it next to the request.">
            <Textarea id="request-message" maxLength={2000} value={message} onChange={(event) => setMessage(event.target.value)} />
          </FormField>
        </>
      )}
    </FormPage>
  );
}
