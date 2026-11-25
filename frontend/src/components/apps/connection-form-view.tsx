"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { SchemaFields } from "@/components/apps/schema-fields";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { Notice } from "@/components/common/notice";
import { OptionSelect } from "@/components/common/option-select";
import { QueryState } from "@/components/common/query-state";
import { SwitchField } from "@/components/common/switch-field";
import { Separator } from "@/components/ui/separator";
import { useApp } from "@/hooks/use-apps";
import { useSaveConnection } from "@/hooks/use-connection";
import { useConnectors } from "@/hooks/use-connectors";
import { authKindLabel, humanize } from "@/lib/format";
import { buildPayload, initialValues, schemaFields, type FieldValue } from "@/lib/json-schema";
import type { AppDetail, ConnectorOut } from "@/lib/api/types";

function writesHint(canWrite: boolean, syncedOnce: boolean): string | null {
  if (!canWrite) return "Read-only connector: actions become manual tasks.";
  if (!syncedOnce) return "Available after the first successful sync.";
  return null;
}

interface ConnectionFormProps {
  app: AppDetail;
  connectors: ConnectorOut[];
  initialConnector?: string;
}

/** Connector, its JSON Schema fields and the two switches. */
function ConnectionForm({ app, connectors, initialConnector }: ConnectionFormProps) {
  const router = useRouter();
  const backHref = `/apps/${app.id}?tab=connection`;
  const connection = app.connection;
  const [connectorKey, setConnectorKey] = useState(
    connection?.connector_key ?? connectors.find((c) => c.key === initialConnector)?.key ?? "",
  );
  const connector = connectors.find((c) => c.key === connectorKey) ?? null;
  // Saved config and secrets belong to the saved connector only.
  const sameConnector = connection !== null && connection.connector_key === connectorKey;
  const fields = useMemo(
    () => (connector ? schemaFields(connector.config_schema, connector.secret_fields) : []),
    [connector],
  );
  const [values, setValues] = useState<Record<string, FieldValue>>(() =>
    initialValues(fields, sameConnector ? connection.config : {}),
  );
  const [peopleSource, setPeopleSource] = useState(connection?.is_people_source ?? false);
  const [writesEnabled, setWritesEnabled] = useState(connection?.writes_enabled ?? false);
  const save = useSaveConnection(app.id);

  const chooseConnector = (key: string) => {
    setConnectorKey(key);
    const next = connectors.find((c) => c.key === key);
    const nextFields = next ? schemaFields(next.config_schema, next.secret_fields) : [];
    setValues(initialValues(nextFields, connection?.connector_key === key ? connection.config : {}));
  };

  const canListPeople = connector?.capabilities.includes("list_people") ?? false;
  const canWrite = connector?.capabilities.some((c) => c === "create_account" || c === "delete_account") ?? false;
  const syncedOnce = sameConnector && connection.last_synced_at !== null;

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!connector) return;
    const { config, secrets } = buildPayload(fields, values);
    save.mutate(
      {
        connector_key: connector.key,
        config,
        // Null keeps the stored secrets; a new connector starts from what was typed.
        secrets: Object.keys(secrets).length > 0 ? secrets : sameConnector ? null : {},
        is_people_source: canListPeople && peopleSource,
        writes_enabled: canWrite && writesEnabled,
      },
      { onSuccess: () => router.push(backHref) },
    );
  };

  return (
    <FormPage
      title={connection ? `Edit connection of ${app.name}` : `Connect ${app.name}`}
      backHref={backHref}
      backLabel={app.name}
      onSubmit={submit}
      submitLabel="Save"
      pending={save.isPending}
      submitDisabled={!connector}
      wide
    >
      <FormField
        label="Connector"
        htmlFor="conn-connector"
        required
        hint={connector?.capabilities.map((capability) => humanize(capability)).join(" · ")}
      >
        <OptionSelect
          id="conn-connector"
          required
          placeholder="Choose a connector"
          options={connectors.map((c) => ({ value: c.key, label: `${c.display_name} · ${authKindLabel(c.auth_kind)}` }))}
          value={connectorKey}
          onChange={chooseConnector}
        />
      </FormField>
      {connector && (
        <>
          {connector.auth_kind === "browser_session" && (
            <Notice>After saving, log in to the app on the Browser page.</Notice>
          )}
          <SchemaFields
            fields={fields}
            values={values}
            secretFieldsSet={sameConnector ? connection.secret_fields_set : []}
            onChange={(name, value) => setValues((prev) => ({ ...prev, [name]: value }))}
          />
          <Separator />
          {canListPeople && (
            <SwitchField
              id="conn-people"
              label="Source of people"
              info="New users of this app become people in Open Revoke."
              checked={peopleSource}
              onChange={setPeopleSource}
            />
          )}
          <SwitchField
            id="conn-writes"
            label="Allow writes"
            info="Approved actions create and remove real accounts in the app. Each action still needs approval and is checked by a read afterwards. Off by default."
            hint={writesHint(canWrite, syncedOnce)}
            checked={writesEnabled}
            disabled={!canWrite || !syncedOnce}
            onChange={setWritesEnabled}
          />
          {writesEnabled && (
            <Notice tone="warning">Approved actions will change real accounts in {app.name}.</Notice>
          )}
        </>
      )}
    </FormPage>
  );
}

/** `/apps/<id>/connection/edit`; `?connector=` preselects a connector (after "Add app" with one). */
export function ConnectionFormView({ appId, initialConnector }: { appId: string; initialConnector?: string }) {
  const app = useApp(appId);
  const connectors = useConnectors();
  return (
    <QueryState query={app} rows={6}>
      {(detail) => (
        <QueryState query={connectors} feature="The connector catalog" rows={6}>
          {(page) => <ConnectionForm app={detail} connectors={page.items} initialConnector={initialConnector} />}
        </QueryState>
      )}
    </QueryState>
  );
}
