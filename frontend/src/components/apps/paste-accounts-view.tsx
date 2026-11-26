"use client";

import { useState } from "react";
import { PenLineIcon } from "lucide-react";

import { AccountImportPreview } from "@/components/apps/account-import-preview";
import { EmptyState } from "@/components/common/empty-state";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { LinkButton } from "@/components/common/links";
import { Panel } from "@/components/common/panel";
import { QueryState } from "@/components/common/query-state";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { usePasteAccounts } from "@/hooks/use-accounts";
import { useApp } from "@/hooks/use-apps";
import type { AccountImportResult } from "@/lib/api/inventory-types";
import type { AppDetail } from "@/lib/api/types";

function PasteForm({ app }: { app: AppDetail }) {
  const [emails, setEmails] = useState("");
  const [result, setResult] = useState<AccountImportResult | null>(null);
  const paste = usePasteAccounts(app.id);
  const back = `/apps/${app.id}`;

  const run = (dryRun: boolean) => {
    if (!emails.trim()) return;
    paste.mutate({ emails, dryRun }, { onSuccess: setResult });
  };
  const changes = result ? result.created + result.updated : 0;
  const imported = result !== null && !result.dry_run;

  return (
    <FormPage
      title={`Paste e-mails into ${app.name}`}
      backHref={back}
      backLabel={app.name}
      wide
      onSubmit={(event) => {
        event.preventDefault();
        run(false);
      }}
      submitLabel="Add accounts"
      actions={
        imported ? (
          <LinkButton href={back}>Back to {app.name}</LinkButton>
        ) : (
          <>
            <LinkButton href={back} variant="outline">
              Cancel
            </LinkButton>
            <Button type="button" variant="outline" onClick={() => run(true)} disabled={!emails.trim() || paste.isPending}>
              {paste.isPending && !result ? "Checking…" : "Preview"}
            </Button>
            <Button type="submit" disabled={!result || changes === 0 || paste.isPending}>
              {result ? `Add ${changes}` : "Add accounts"}
            </Button>
          </>
        )
      }
    >
      <FormField
        label="E-mails"
        htmlFor="paste-emails"
        info="One per line, or separated with commas or semicolons; “Name <e-mail>” works too. Accounts match people by e-mail. Existing accounts stay as they are."
      >
        <Textarea
          id="paste-emails"
          rows={8}
          placeholder={"anna@example.com\njan@example.com"}
          value={emails}
          disabled={imported}
          onChange={(event) => {
            setEmails(event.target.value);
            setResult(null);
          }}
        />
      </FormField>
      {result && <AccountImportPreview result={result} />}
    </FormPage>
  );
}

/** `/apps/<id>/accounts/bulk`: pasted e-mails become accounts of a manual app (Preview, then Add). */
export function PasteAccountsView({ appId }: { appId: string }) {
  const query = useApp(appId);
  return (
    <QueryState query={query} rows={6}>
      {(app) =>
        app.integration === "manual" ? (
          <PasteForm app={app} />
        ) : (
          <Panel className="mx-auto max-w-xl">
            <EmptyState
              icon={PenLineIcon}
              title="Accounts of this app come from its connection"
              action={
                <LinkButton href={`/apps/${app.id}`} variant="outline">
                  Back to {app.name}
                </LinkButton>
              }
            />
          </Panel>
        )
      }
    </QueryState>
  );
}
