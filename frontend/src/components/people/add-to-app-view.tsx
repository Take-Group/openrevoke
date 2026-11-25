"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { OptionSelect } from "@/components/common/option-select";
import { WriteModeLine } from "@/components/common/write-mode-badge";
import { PersonQuery } from "@/components/people/person-query";
import { Input } from "@/components/ui/input";
import { useCreateAction } from "@/hooks/use-actions";
import { useApps } from "@/hooks/use-apps";
import { emptyToNull, fullName } from "@/lib/format";
import type { PersonDetail } from "@/lib/api/types";

/** Creates a create_account action (or a manual task) for the person. */
function AddToAppForm({ person }: { person: PersonDetail }) {
  const router = useRouter();
  const backHref = `/people/${person.id}`;
  const [appId, setAppId] = useState("");
  const [email, setEmail] = useState(person.primary_email);
  const [role, setRole] = useState("");
  const apps = useApps({ limit: 500 });
  const createAction = useCreateAction();

  // Apps where the person already has a live account are not offered.
  const taken = new Set(person.accounts.filter((a) => a.status !== "removed").map((a) => a.app.app_id));
  const options = (apps.data?.items ?? [])
    .filter((app) => !taken.has(app.id))
    .map((app) => ({ value: app.id, label: app.name }));
  const selected = apps.data?.items.find((app) => app.id === appId);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    createAction.mutate(
      { kind: "create_account", app_id: appId, person_id: person.id, email: emptyToNull(email), role: emptyToNull(role) },
      { onSuccess: () => router.push(backHref) },
    );
  };

  return (
    <FormPage
      title={`Add ${fullName(person)} to an app`}
      backHref={backHref}
      backLabel={fullName(person)}
      onSubmit={submit}
      submitLabel="Create action"
      pending={createAction.isPending}
      submitDisabled={!appId || person.status === "left"}
      hint={person.status === "left" ? "The person has left." : undefined}
    >
      <FormField label="App" htmlFor="ata-app" required>
        <OptionSelect
          id="ata-app"
          required
          placeholder={apps.isPending ? "Loading…" : "Choose an app"}
          options={options}
          value={appId}
          onChange={setAppId}
        />
      </FormField>
      {selected && <WriteModeLine mode={selected.create_mode} what="create" />}
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="E-mail" htmlFor="ata-email">
          <Input id="ata-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        </FormField>
        <FormField label="Role" htmlFor="ata-role">
          <Input id="ata-role" placeholder="member" value={role} onChange={(event) => setRole(event.target.value)} />
        </FormField>
      </div>
    </FormPage>
  );
}

/** `/people/<id>/add-to-app`. */
export function AddToAppView({ id }: { id: string }) {
  return <PersonQuery id={id}>{(person) => <AddToAppForm person={person} />}</PersonQuery>;
}
