"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { integrationOfConnector } from "@/components/apps/app-options";
import { IntegrationPicker } from "@/components/apps/integration-picker";
import { DEFAULT_CURRENCY, PriceFields, priceFromForm, type PriceForm } from "@/components/apps/price-fields";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { Input } from "@/components/ui/input";
import { OptionSelect } from "@/components/common/option-select";
import { Separator } from "@/components/ui/separator";
import { useCreateApp } from "@/hooks/use-apps";
import { useAuthState } from "@/hooks/use-auth";
import { useConnectors } from "@/hooks/use-connectors";
import { emptyToNull, slugify } from "@/lib/format";
import type { Integration } from "@/lib/api/types";

function emptyPrice(currency: string | undefined): PriceForm {
  return { pricing_model: "per_seat", amount: "", currency: currency ?? DEFAULT_CURRENCY, billing_period: "monthly" };
}

/** `/apps/new`: a new app, optionally from a connector; with one it continues to the connection form. */
export function NewAppView() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugEdited, setSlugEdited] = useState(false);
  const [adminUrl, setAdminUrl] = useState("");
  const [integration, setIntegration] = useState<Integration>("manual");
  const [connectorKey, setConnectorKey] = useState("");
  // New prices start in the organization currency.
  const organizationCurrency = useAuthState().data?.organization?.currency;
  const [price, setPrice] = useState<PriceForm>(() => emptyPrice(organizationCurrency));
  const connectors = useConnectors();
  const create = useCreateApp();

  const chooseConnector = (key: string) => {
    setConnectorKey(key);
    const connector = connectors.data?.items.find((item) => item.key === key);
    if (!connector) return;
    setIntegration(integrationOfConnector(connector));
    if (!adminUrl && connector.admin_url) setAdminUrl(connector.admin_url);
    if (!name) {
      setName(connector.display_name);
      if (!slugEdited) setSlug(slugify(connector.display_name));
    }
  };

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    create.mutate(
      {
        name: name.trim(),
        slug: emptyToNull(slug),
        admin_url: emptyToNull(adminUrl),
        integration,
        pricing_model: price.pricing_model,
        price: priceFromForm(price),
      },
      {
        onSuccess: (app) => {
          // The connection form needs the connector's fields: continue there.
          router.push(connectorKey ? `/apps/${app.id}/connection/edit?connector=${connectorKey}` : `/apps/${app.id}`);
        },
      },
    );
  };

  const connectorOptions = (connectors.data?.items ?? []).map((c) => ({ value: c.key, label: c.display_name }));

  return (
    <FormPage
      title="Add app"
      backHref="/apps"
      backLabel="Apps"
      onSubmit={submit}
      submitLabel="Add app"
      pending={create.isPending}
    >
      <FormField
        label="Connector"
        htmlFor="app-connector"
        info="Optional. With a connector, Open Revoke reads the accounts itself; you set up the connection on the next screen."
      >
        <OptionSelect
          id="app-connector"
          placeholder={connectorOptions.length === 0 ? "None available" : "None"}
          options={connectorOptions}
          value={connectorKey}
          disabled={connectorOptions.length === 0}
          onChange={chooseConnector}
        />
      </FormField>
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="Name" htmlFor="app-name" required>
          <Input
            id="app-name"
            required
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              if (!slugEdited) setSlug(slugify(event.target.value));
            }}
          />
        </FormField>
        <FormField label="Slug" htmlFor="app-slug" info="Lowercase letters, digits and dashes.">
          <Input
            id="app-slug"
            pattern="^[a-z0-9]+(-[a-z0-9]+)*$"
            value={slug}
            onChange={(event) => {
              setSlug(event.target.value);
              setSlugEdited(true);
            }}
          />
        </FormField>
      </div>
      <FormField label="Admin URL" htmlFor="app-admin-url">
        <Input
          id="app-admin-url"
          type="url"
          placeholder="https://"
          value={adminUrl}
          onChange={(event) => setAdminUrl(event.target.value)}
        />
      </FormField>
      <FormField label="Integration">
        <IntegrationPicker value={integration} onChange={setIntegration} />
      </FormField>
      <Separator />
      <PriceFields idPrefix="app-price" value={price} onChange={setPrice} />
    </FormPage>
  );
}
