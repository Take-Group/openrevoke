"use client";

import { useState } from "react";

import { SCOPE_LABEL } from "@/components/api-tokens/scope";
import { McpSetupGuide } from "@/components/api-tokens/mcp-setup-guide";
import { TextField } from "@/components/auth/form-parts";
import { ChoiceCards } from "@/components/common/choice-cards";
import { CopyField } from "@/components/common/copy-button";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { LinkButton } from "@/components/common/links";
import { Notice } from "@/components/common/notice";
import { PageHeader } from "@/components/common/page-header";
import { PanelFooter } from "@/components/common/panel";
import { useCreateApiToken } from "@/hooks/use-api-tokens";
import type { ApiTokenCreated, ApiTokenScope } from "@/lib/api/api-token-types";

const SCOPES = [
  { value: "write" as const, label: SCOPE_LABEL.write, hint: "Everything your role allows: add people, connect apps, offboard." },
  { value: "read" as const, label: SCOPE_LABEL.read, hint: "Lists and details only. Every change is refused." },
];

/** The token once, with the setup snippets filled in. */
function CreatedToken({ created }: { created: ApiTokenCreated }) {
  return (
    <>
      <PageHeader title="Token created" back={{ href: "/settings/api", label: "API and MCP" }} />
      <section className="mx-auto w-full max-w-2xl overflow-hidden rounded-lg border border-frame bg-card shadow-card">
        <div className="flex flex-col gap-4 p-5">
          <Notice tone="warning" title="Copy the token now">
            It is not shown again. Lost it? Revoke it and create a new one.
          </Notice>
          <FormField label={`${created.token.name} (${SCOPE_LABEL[created.token.scope].toLowerCase()})`}>
            <CopyField value={created.secret} label="the token" />
          </FormField>
          <McpSetupGuide url={created.mcp_url} token={created.secret} />
        </div>
        <PanelFooter>
          <span>The assistant acts as you; changes show in the audit log.</span>
          <LinkButton href="/settings/api">Done</LinkButton>
        </PanelFooter>
      </section>
    </>
  );
}

/** `/settings/api/new`: name and access of a new token, then the token itself on the same page. */
export function NewApiTokenView() {
  const [name, setName] = useState("");
  const [scope, setScope] = useState<ApiTokenScope>("write");
  const [created, setCreated] = useState<ApiTokenCreated | null>(null);
  const create = useCreateApiToken();

  if (created) return <CreatedToken created={created} />;
  return (
    <FormPage
      title="Create API token"
      backHref="/settings/api"
      backLabel="API and MCP"
      submitLabel="Create token"
      pending={create.isPending}
      submitDisabled={!name.trim()}
      onSubmit={(event) => {
        event.preventDefault();
        create.mutate({ name: name.trim(), scope }, { onSuccess: setCreated });
      }}
    >
      <TextField
        id="token-name"
        label="Name"
        hint="Where you use it, to tell tokens apart later."
        placeholder="Claude Code on my laptop"
        required
        maxLength={100}
        value={name}
        onValue={setName}
      />
      <FormField label="Access">
        <ChoiceCards label="Access" options={SCOPES} value={scope} onChange={setScope} />
      </FormField>
    </FormPage>
  );
}
