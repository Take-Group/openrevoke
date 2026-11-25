"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { Segmented } from "@/components/common/segmented";
import { PersonFields, type PersonForm } from "@/components/people/person-fields";
import { PersonQuery } from "@/components/people/person-query";
import { useUpdatePerson } from "@/hooks/use-people";
import { emptyToNull, fullName, parseEmailList } from "@/lib/format";
import type { PersonDetail, PersonStatus, PersonUpdate } from "@/lib/api/types";

function initialForm(person: PersonDetail): PersonForm {
  return {
    first_name: person.first_name,
    last_name: person.last_name,
    primary_email: person.primary_email,
    employee_code: person.employee_code ?? "",
    notes: person.notes ?? "",
    aliases: person.aliases.map((alias) => alias.email).join("\n"),
  };
}

function EditPersonForm({ person }: { person: PersonDetail }) {
  const router = useRouter();
  const backHref = `/people/${person.id}`;
  const [form, setForm] = useState<PersonForm>(() => initialForm(person));
  const [status, setStatus] = useState<PersonStatus>(person.status);
  const update = useUpdatePerson(person.id);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const data: PersonUpdate = {
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      primary_email: form.primary_email.trim(),
      employee_code: emptyToNull(form.employee_code),
      notes: emptyToNull(form.notes),
      aliases: parseEmailList(form.aliases),
    };
    if (status !== person.status) data.status = status;
    update.mutate(data, { onSuccess: () => router.push(backHref) });
  };

  return (
    <FormPage
      title={`Edit ${fullName(person)}`}
      backHref={backHref}
      backLabel={fullName(person)}
      onSubmit={submit}
      submitLabel="Save"
      pending={update.isPending}
    >
      <PersonFields form={form} onChange={setForm} idPrefix="e" />
      <FormField label="Status" info="Setting Left does not remove any account. Use Offboard for that.">
        <Segmented
          label="Status"
          value={status}
          onChange={setStatus}
          options={[
            { value: "active", label: "Active" },
            { value: "left", label: "Left" },
          ]}
        />
      </FormField>
    </FormPage>
  );
}

/** `/people/<id>/edit`, opened from the person's "More" menu. */
export function EditPersonView({ id }: { id: string }) {
  return <PersonQuery id={id}>{(person) => <EditPersonForm person={person} />}</PersonQuery>;
}
