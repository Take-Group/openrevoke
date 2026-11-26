"use client";

import { useState } from "react";
import { DownloadIcon } from "lucide-react";

import { AccountImportPreview } from "@/components/apps/account-import-preview";
import { FileDrop } from "@/components/common/file-drop";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { LinkButton } from "@/components/common/links";
import { SwitchField } from "@/components/common/switch-field";
import { Button, buttonVariants } from "@/components/ui/button";
import { useImportAccounts } from "@/hooks/use-accounts";
import type { AccountImportResult } from "@/lib/api/inventory-types";

const COLUMNS = "app,email,username,display_name,role,status,kind";

// Fictional sample: two catalog apps and an internal one.
const SAMPLE_CSV = `${COLUMNS}
Notion,anna@example.com,,,member,active,person
Notion,jan@example.com,,,admin,,
Figma,anna@example.com,,,editor,invited,
Internal CRM,,crm-bot,CRM integration,,active,service
`;

const SAMPLE_HREF = `data:text/csv;charset=utf-8,${encodeURIComponent(SAMPLE_CSV)}`;

/** `/accounts/import`: accounts of manual apps from one CSV (several apps), Preview (dry run) then Import. */
export function ImportAccountsView() {
  const [file, setFile] = useState<File | null>(null);
  const [createApps, setCreateApps] = useState(false);
  const [result, setResult] = useState<AccountImportResult | null>(null);
  const importAccounts = useImportAccounts();

  const run = (dryRun: boolean) => {
    if (!file) return;
    importAccounts.mutate({ file, dryRun, createApps }, { onSuccess: setResult });
  };
  const changes = result ? result.created + result.updated : 0;
  const imported = result !== null && !result.dry_run;

  return (
    <FormPage
      title="Import accounts from CSV"
      backHref="/apps"
      backLabel="Apps"
      wide
      description={
        <>
          Columns: <code className="font-mono text-xs text-foreground">{COLUMNS}</code>
        </>
      }
      onSubmit={(event) => {
        event.preventDefault();
        run(false);
      }}
      submitLabel="Import"
      hint={
        <a href={SAMPLE_HREF} download="open-revoke-accounts.csv" className={buttonVariants({ variant: "link-muted", size: "sm" })}>
          <DownloadIcon />
          Sample file
        </a>
      }
      actions={
        imported ? (
          <LinkButton href="/apps">Back to apps</LinkButton>
        ) : (
          <>
            <Button type="button" variant="outline" onClick={() => run(true)} disabled={!file || importAccounts.isPending}>
              {importAccounts.isPending && !result ? "Checking…" : "Preview"}
            </Button>
            <Button type="submit" disabled={!result || changes === 0 || importAccounts.isPending}>
              {result ? `Import ${changes}` : "Import"}
            </Button>
          </>
        )
      }
    >
      <FormField
        label="CSV file"
        htmlFor="accounts-csv"
        info="app is the app's name or catalog slug; give an email, username or display_name. status: active, invited, suspended; kind: person, service. Accounts match people by e-mail. Nothing is deleted and empty cells keep existing values. Apps with a connector are skipped: their accounts come from the sync. UTF-8, up to 2 MB."
      >
        <FileDrop
          id="accounts-csv"
          accept=".csv,text/csv"
          what="the CSV file"
          fileName={file?.name}
          disabled={imported}
          onFile={(chosen) => {
            setFile(chosen ?? null);
            setResult(null);
          }}
        />
      </FormField>
      <SwitchField
        id="accounts-create-apps"
        label="Create missing apps"
        hint="An app the file names but Open Revoke lacks becomes a manual app (named from the catalog when it is there)."
        checked={createApps}
        disabled={imported}
        onChange={(checked) => {
          setCreateApps(checked);
          setResult(null);
        }}
      />
      {result && <AccountImportPreview result={result} showApp />}
    </FormPage>
  );
}
