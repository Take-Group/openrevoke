"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PenLineIcon } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { LinkButton } from "@/components/common/links";
import { Panel } from "@/components/common/panel";
import { PersonPicker } from "@/components/common/person-picker";
import { QueryState } from "@/components/common/query-state";
import { Input } from "@/components/ui/input";
import { OptionSelect } from "@/components/common/option-select";
import { useCreateAccount } from "@/hooks/use-accounts";
import { useApp } from "@/hooks/use-apps";
import { emptyToNull } from "@/lib/format";
import type { AccountKind, AccountStatus, AppDetail, PersonListItem } from "@/lib/api/types";

const STATUS_OPTIONS: { value: AccountStatus; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "invited", label: "Invited" },
  { value: "suspended", label: "Suspended" },
];

const KIND_OPTIONS: { value: AccountKind; label: string }[] = [
  { value: "person", label: "Person" },
  { value: "service", label: "Service account" },
  { value: "unknown", label: "Unknown" },
];

const EMPTY = { email: "", username: "", display_name: "", role: "", status: "active" as AccountStatus, kind: "" };

/** Manual apps only: an account the operator knows about. */
function NewAccountForm({ app }: { app: AppDetail }) {
  const router = useRouter();
  const [form, setForm] = useState(EMPTY);
  const [person, setPerson] = useState<PersonListItem | null>(null);
  const create = useCreateAccount(app.id);

  const set = (field: keyof typeof EMPTY) => (event: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: event.target.value }));
  const choose = (field: "status" | "kind") => (value: string) => setForm((prev) => ({ ...prev, [field]: value }));

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    create.mutate(
      {
        email: emptyToNull(form.email),
        username: emptyToNull(form.username),
        display_name: emptyToNull(form.display_name),
        role: emptyToNull(form.role),
        status: form.status,
        kind: (form.kind || null) as AccountKind | null,
        person_id: person?.id ?? null,
      },
      { onSuccess: () => router.push(`/apps/${app.id}`) },
    );
  };

  const hasIdentity = Boolean(form.email.trim() || form.username.trim() || form.display_name.trim());

  return (
    <FormPage
      title={`Add account to ${app.name}`}
      backHref={`/apps/${app.id}`}
      backLabel={app.name}
      description="E-mail, username or name: at least one."
      onSubmit={submit}
      submitLabel="Add account"
      pending={create.isPending}
      submitDisabled={!hasIdentity}
    >
      <FormField label="E-mail" htmlFor="acc-email" info="An e-mail that belongs to a person matches them automatically.">
        <Input id="acc-email" type="email" value={form.email} onChange={set("email")} />
      </FormField>
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="Username" htmlFor="acc-username">
          <Input id="acc-username" value={form.username} onChange={set("username")} />
        </FormField>
        <FormField label="Display name" htmlFor="acc-name">
          <Input id="acc-name" value={form.display_name} onChange={set("display_name")} />
        </FormField>
        <FormField label="Role" htmlFor="acc-role">
          <Input id="acc-role" placeholder="member" value={form.role} onChange={set("role")} />
        </FormField>
        <FormField label="Status" htmlFor="acc-status">
          <OptionSelect id="acc-status" options={STATUS_OPTIONS} value={form.status} onChange={choose("status")} />
        </FormField>
      </div>
      <FormField label="Kind" htmlFor="acc-kind">
        <OptionSelect id="acc-kind" placeholder="Automatic" options={KIND_OPTIONS} value={form.kind} onChange={choose("kind")} />
      </FormField>
      <FormField label="Owner" info="Optional. Without it, matching by e-mail decides.">
        <PersonPicker value={person} allowClear onChange={setPerson} placeholder="Choose person" variant="field" />
      </FormField>
    </FormPage>
  );
}

/** `/apps/<id>/accounts/new`. Apps with a connection get their accounts from the sync instead. */
export function NewAccountView({ appId }: { appId: string }) {
  const query = useApp(appId);
  return (
    <QueryState query={query} rows={6}>
      {(app) =>
        app.integration === "manual" ? (
          <NewAccountForm app={app} />
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
