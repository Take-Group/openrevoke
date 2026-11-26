"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2Icon } from "lucide-react";
import { toast } from "sonner";

import { LogoPicker, WebsiteCategoryFields, logoProblem } from "@/components/apps/app-identity-fields";
import { BillingNotice } from "@/components/apps/billing-notice";
import { IntegrationPicker } from "@/components/apps/integration-picker";
import { PriceFields, priceFormFrom, priceFromForm, type PriceForm } from "@/components/apps/price-fields";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { FormField } from "@/components/common/form-field";
import { Hint } from "@/components/common/info-tip";
import { SettingsSection } from "@/components/settings/settings-section";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { OptionSelect } from "@/components/common/option-select";
import { Textarea } from "@/components/ui/textarea";
import { useAppLogo, useDeleteApp, useUpdateApp } from "@/hooks/use-apps";
import { emptyToNull } from "@/lib/format";
import type { AppDetail, Integration, RequestPolicy } from "@/lib/api/types";

const REQUEST_POLICY_OPTIONS: { value: RequestPolicy; label: string }[] = [
  { value: "manager", label: "The person's manager approves" },
  { value: "manager_then_admin", label: "The manager, then an admin approve" },
  { value: "admin", label: "An admin approves" },
  { value: "automatic", label: "Granted automatically" },
  { value: "off", label: "Not available on request" },
];

function DeleteApp({ app }: { app: AppDetail }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const remove = useDeleteApp(app.id);
  const blocked = app.accounts_count > 0;
  const button = (
    <Button variant="destructive" disabled={blocked} onClick={() => setOpen(true)}>
      <Trash2Icon />
      Delete app
    </Button>
  );

  return (
    <SettingsSection title="Delete app" description="Removes it from Open Revoke only, not from the app.">
      {blocked ? (
        <Hint label={`Has ${app.accounts_count} account(s): only an app without accounts and actions can be deleted.`}>
          <span tabIndex={0} className="inline-block">
            {button}
          </span>
        </Hint>
      ) : (
        button
      )}
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={`Delete ${app.name}?`}
        description="This cannot be undone."
        confirmLabel="Delete"
        destructive
        pending={remove.isPending}
        onConfirm={() => remove.mutate(undefined, { onSuccess: () => router.push("/apps") })}
      />
    </SettingsSection>
  );
}

/** Saved at once on pick, outside the form's "Save changes": a file is not part of the PATCH. */
function AppLogoSection({ app }: { app: AppDetail }) {
  const logo = useAppLogo();
  const upload = (file: File | null) => {
    if (!file) return;
    const problem = logoProblem(file);
    if (problem) toast.error(problem);
    else logo.mutate({ id: app.id, file });
  };
  return (
    <SettingsSection title="Logo" description="Shown wherever the app appears; your own logo wins over the catalog's.">
      <LogoPicker
        name={app.name}
        current={app.logo_url}
        file={null}
        onFile={upload}
        onRemove={() => logo.mutate({ id: app.id, file: null })}
        pending={logo.isPending}
      />
    </SettingsSection>
  );
}

export function AppSettingsTab({ app }: { app: AppDetail }) {
  const [name, setName] = useState(app.name);
  const [slug, setSlug] = useState(app.slug);
  const [adminUrl, setAdminUrl] = useState(app.admin_url ?? "");
  const [integration, setIntegration] = useState<Integration>(app.integration);
  const [notes, setNotes] = useState(app.notes ?? "");
  const [website, setWebsite] = useState(app.website ?? "");
  const [category, setCategory] = useState(app.category ?? "");
  const [requestPolicy, setRequestPolicy] = useState<RequestPolicy>(app.request_policy);
  const [price, setPrice] = useState<PriceForm>(() => priceFormFrom(app.pricing_model, app.price));
  const update = useUpdateApp(app.id);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    update.mutate({
      name: name.trim(),
      slug: slug.trim(),
      admin_url: emptyToNull(adminUrl),
      integration,
      notes: emptyToNull(notes),
      website: emptyToNull(website),
      category: emptyToNull(category),
      request_policy: requestPolicy,
      pricing_model: price.pricing_model,
      price: priceFromForm(price),
    });
  };

  return (
    <div className="max-w-4xl pt-4">
      <form onSubmit={submit}>
        <AppLogoSection app={app} />
        <SettingsSection title="General" description="Name, slug, website, category and where its admin panel lives.">
          <div className="flex max-w-lg flex-col gap-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <FormField label="Name" htmlFor="set-name" required>
                <Input id="set-name" required value={name} onChange={(event) => setName(event.target.value)} />
              </FormField>
              <FormField label="Slug" htmlFor="set-slug" required info="Lowercase letters, digits and dashes.">
                <Input
                  id="set-slug"
                  required
                  pattern="^[a-z0-9]+(-[a-z0-9]+)*$"
                  value={slug}
                  onChange={(event) => setSlug(event.target.value)}
                />
              </FormField>
            </div>
            <FormField label="Admin URL" htmlFor="set-admin">
              <Input
                id="set-admin"
                type="url"
                placeholder="https://"
                value={adminUrl}
                onChange={(event) => setAdminUrl(event.target.value)}
              />
            </FormField>
            <WebsiteCategoryFields
              idPrefix="set"
              website={website}
              category={category}
              onWebsite={setWebsite}
              onCategory={setCategory}
            />
            <FormField label="Integration">
              <IntegrationPicker value={integration} onChange={setIntegration} />
            </FormField>
          </div>
        </SettingsSection>
        <SettingsSection title="Pricing" description="Monthly cost is the price times active seats, or the plan price.">
          <div className="flex max-w-lg flex-col gap-3">
            <BillingNotice app={app} onApplied={(next) => setPrice(priceFormFrom(next.pricing_model, next.price))} />
            <PriceFields idPrefix="set-price" value={price} onChange={setPrice} />
          </div>
        </SettingsSection>
        <SettingsSection
          title="Access requests"
          description="Who approves when someone asks for an account here, on My access or in Slack."
        >
          <div className="max-w-lg">
            <OptionSelect
              id="set-request-policy"
              aria-label="Access requests"
              value={requestPolicy}
              onChange={(next) => next && setRequestPolicy(next as RequestPolicy)}
              options={REQUEST_POLICY_OPTIONS}
            />
            <p className="mt-1.5 text-xs text-muted-foreground">
              Automatic still needs “Allow writes” on the connection; without a connector an admin gets a task.
            </p>
          </div>
        </SettingsSection>
        <SettingsSection title="Notes" description="Contract, owner, renewal date.">
          <Textarea
            id="set-notes"
            aria-label="Notes"
            rows={3}
            className="max-w-lg"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </SettingsSection>
        <div className="sticky bottom-0 z-10 mt-6 flex justify-end border-t bg-page/85 py-3 backdrop-blur">
          <Button type="submit" disabled={update.isPending}>
            {update.isPending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
      <DeleteApp app={app} />
    </div>
  );
}
