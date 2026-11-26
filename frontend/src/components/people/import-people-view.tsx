"use client";

import { useState } from "react";

import { FileDrop } from "@/components/common/file-drop";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { LinkButton } from "@/components/common/links";
import { ImportPreview } from "@/components/people/import-preview";
import { Button } from "@/components/ui/button";
import { useImportPeople } from "@/hooks/use-people";
import type { ImportResult } from "@/lib/api/types";

/** `/people/import`. Two steps: Preview (dry run) shows what would change, then the real import. */
export function ImportPeopleView() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const importPeople = useImportPeople();

  const run = (dryRun: boolean) => {
    if (!file) return;
    importPeople.mutate({ file, dryRun }, { onSuccess: setResult });
  };

  const changes = result ? result.created + result.updated : 0;
  const imported = result !== null && !result.dry_run;

  return (
    <FormPage
      title="Import people from CSV"
      backHref="/people"
      backLabel="People"
      wide
      description={
        <>
          Columns: <code className="font-mono text-xs text-foreground">email,first_name,last_name,employee_code,aliases,manager_email,department,job_title</code>
        </>
      }
      onSubmit={(event) => {
        event.preventDefault();
        run(false);
      }}
      submitLabel="Import"
      actions={
        imported ? (
          <LinkButton href="/people">Back to people</LinkButton>
        ) : (
          <>
            <Button type="button" variant="outline" onClick={() => run(true)} disabled={!file || importPeople.isPending}>
              {importPeople.isPending && !result ? "Checking…" : "Preview"}
            </Button>
            <Button type="submit" disabled={!result || changes === 0 || importPeople.isPending}>
              {result ? `Import ${changes}` : "Import"}
            </Button>
          </>
        )
      }
    >
      <FormField
        label="CSV file"
        htmlFor="csv-file"
        info="Only email is required; aliases are separated with “;”. Matching is by e-mail. manager_email must be a person already here or a row of the file; managers from the file are kept by syncs. Nobody is deleted and empty cells keep existing values. UTF-8, up to 2 MB."
      >
        <FileDrop
          id="csv-file"
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
      {result && <ImportPreview result={result} />}
    </FormPage>
  );
}
