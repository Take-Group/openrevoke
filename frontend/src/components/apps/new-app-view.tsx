"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { LogoPicker, WebsiteCategoryFields, logoProblem } from "@/components/apps/app-identity-fields";
import { integrationOfConnector } from "@/components/apps/app-options";
import { CatalogAppPicker } from "@/components/common/catalog-app-picker";
import { IntegrationPicker } from "@/components/apps/integration-picker";
import { DEFAULT_CURRENCY, PriceFields, priceFromForm, type PriceForm } from "@/components/apps/price-fields";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { LinkButton, TextLink } from "@/components/common/links";
import { Notice } from "@/components/common/notice";
import { OptionSelect } from "@/components/common/option-select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { useAppLogo, useCreateApp } from "@/hooks/use-apps";
import { useAuthState } from "@/hooks/use-auth";
import { useConnectors } from "@/hooks/use-connectors";
import type { CatalogSearchItem } from "@/lib/api/catalog-types";
import { emptyToNull, slugify } from "@/lib/format";
import type { AppDetail, Integration } from "@/lib/api/types";

// Free until a price is set: a fast inventory should not stop at a price the admin may not know yet.
function emptyPrice(currency: string | undefined): PriceForm {
  return { pricing_model: "free", amount: "", currency: currency ?? DEFAULT_CURRENCY, billing_period: "monthly" };
}

/**
 * `/apps/new`: first a search of the app catalog (it fills the name, website and connector), or
 * "Add your own app" for an app the catalog lacks, with website, category and logo. With a connector it
 * continues to the connection form; a manual app can go straight to pasting its accounts' e-mails.
 */
export function NewAppView() {
  const router = useRouter();
  const [picked, setPicked] = useState<CatalogSearchItem | null>(null);
  const [custom, setCustom] = useState(false);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [slugEdited, setSlugEdited] = useState(false);
  const [website, setWebsite] = useState("");
  const [category, setCategory] = useState("");
  const [logo, setLogo] = useState<File | null>(null);
  const [adminUrl, setAdminUrl] = useState("");
  const [integration, setIntegration] = useState<Integration>("manual");
  const [connectorKey, setConnectorKey] = useState("");
  // New prices start in the organization currency.
  const organizationCurrency = useAuthState().data?.organization?.currency;
  const [price, setPrice] = useState<PriceForm>(() => emptyPrice(organizationCurrency));
  const connectors = useConnectors();
  const create = useCreateApp();
  const uploadLogo = useAppLogo();

  const setNameAndSlug = (value: string) => {
    setName(value);
    if (!slugEdited) setSlug(slugify(value));
  };

  const chooseConnector = (key: string) => {
    setConnectorKey(key);
    const connector = connectors.data?.items.find((item) => item.key === key);
    if (!connector) return;
    setIntegration(integrationOfConnector(connector));
    if (!adminUrl && connector.admin_url) setAdminUrl(connector.admin_url);
    if (!name) setNameAndSlug(connector.display_name);
  };

  const pick = (item: CatalogSearchItem) => {
    setPicked(item);
    setCustom(false);
    setNameAndSlug(item.name);
    setWebsite(item.website);
    const connector = connectors.data?.items.find((entry) => entry.key === item.connector_key);
    if (connector) {
      setConnectorKey(connector.key);
      setIntegration(integrationOfConnector(connector));
      if (connector.admin_url) setAdminUrl(connector.admin_url);
    } else {
      setConnectorKey("");
      setIntegration("manual");
    }
  };

  const startCustom = () => {
    setPicked(null);
    setCustom(true);
    setNameAndSlug("");
    setWebsite("");
    setConnectorKey("");
    setIntegration("manual");
  };

  const save = (pasteNext: boolean) => {
    const problem = logo && logoProblem(logo);
    if (problem) {
      toast.error(problem);
      return;
    }
    create.mutate(
      {
        name: name.trim(),
        slug: emptyToNull(slug),
        catalog_key: picked?.slug ?? null,
        website: emptyToNull(website),
        category: emptyToNull(category),
        admin_url: emptyToNull(adminUrl),
        integration,
        pricing_model: price.pricing_model,
        price: priceFromForm(price),
      },
      {
        onSuccess: (app: AppDetail) => {
          if (logo) uploadLogo.mutate({ id: app.id, file: logo });
          // The connection form needs the connector's fields: continue there.
          if (connectorKey) router.push(`/apps/${app.id}/connection/edit?connector=${connectorKey}`);
          else router.push(pasteNext ? `/apps/${app.id}/accounts/bulk` : `/apps/${app.id}`);
        },
      },
    );
  };

  const connectorOptions = (connectors.data?.items ?? []).map((c) => ({ value: c.key, label: c.display_name }));
  const added = picked?.already_added ?? null;
  const showForm = Boolean(picked) || custom;
  const pending = create.isPending;

  return (
    <FormPage
      title="Add app"
      backHref="/apps"
      backLabel="Apps"
      onSubmit={(event) => {
        event.preventDefault();
        save(false);
      }}
      submitLabel="Add app"
      actions={
        <>
          <LinkButton href="/apps" variant="outline">
            Cancel
          </LinkButton>
          {!connectorKey && integration === "manual" && (
            <Button type="button" variant="outline" disabled={pending || !showForm || Boolean(added)} onClick={() => save(true)}>
              Add and paste e-mails
            </Button>
          )}
          <Button type="submit" disabled={pending || !showForm || Boolean(added)}>
            {pending ? "Saving…" : "Add app"}
          </Button>
        </>
      }
    >
      <FormField label="App" htmlFor="app-catalog" info="Known apps come with their logo, website and, when there is one, the connector.">
        <CatalogAppPicker id="app-catalog" value={picked} onChange={pick} autoFocus />
        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          {custom ? (
            "Your own app: fill in the fields below, or pick one from the catalog."
          ) : (
            <>
              Not in the catalog?
              <Button type="button" variant="link" size="xs" onClick={startCustom}>
                Add your own app
              </Button>
            </>
          )}
        </p>
      </FormField>
      {added && (
        <Notice tone="info">
          {picked?.name} is already in Open Revoke. <TextLink href={`/apps/${added}`}>Open it</TextLink>
        </Notice>
      )}
      {showForm && !added && (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Name" htmlFor="app-name" required>
              <Input id="app-name" required value={name} onChange={(event) => setNameAndSlug(event.target.value)} />
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
          <WebsiteCategoryFields
            idPrefix="app"
            website={website}
            category={category}
            onWebsite={setWebsite}
            onCategory={setCategory}
          />
          {custom && (
            <FormField label="Logo">
              <LogoPicker name={name} file={logo} onFile={setLogo} pending={pending} />
            </FormField>
          )}
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
        </>
      )}
    </FormPage>
  );
}
