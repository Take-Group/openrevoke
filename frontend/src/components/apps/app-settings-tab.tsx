"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2Icon } from "lucide-react";

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
import { useDeleteApp, useUpdateApp } from "@/hooks/use-apps";
import { emptyToNull } from "@/lib/format";
import type { AppDetail, Integration, SelfServicePolicy } from "@/lib/api/types";

const SELF_SERVICE_OPTIONS: { value: SelfServicePolicy; label: string }[] = [
  { value: "approval", label: "An admin approves" },
  { value: "automatic", label: "Granted automatically" },
  { value: "off", label: "Not available" },
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

export function AppSettingsTab({ app }: { app: AppDetail }) {
  const [name, setName] = useState(app.name);
  const [slug, setSlug] = useState(app.slug);
  const [adminUrl, setAdminUrl] = useState(app.admin_url ?? "");
  const [integration, setIntegration] = useState<Integration>(app.integration);
  const [notes, setNotes] = useState(app.notes ?? "");
  const [selfService, setSelfService] = useState<SelfServicePolicy>(app.self_service);
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
      self_service: selfService,
      pricing_model: price.pricing_model,
      price: priceFromForm(price),
    });
  };

  return (
    <div className="max-w-4xl pt-4">
      <form onSubmit={submit}>
        <SettingsSection title="General" description="Name, slug and where its admin panel lives.">
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
          title="Requests in Slack"
          description="What the Slack agent does when someone asks for an account here."
        >
          <div className="max-w-lg">
            <OptionSelect
              id="set-self-service"
              aria-label="Requests in Slack"
              value={selfService}
              onChange={(next) => next && setSelfService(next as SelfServicePolicy)}
              options={SELF_SERVICE_OPTIONS}
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
