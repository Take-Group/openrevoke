"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { FormPage } from "@/components/common/form-page";
import { EMPTY_PERSON, PersonFields, type PersonForm } from "@/components/people/person-fields";
import { useCreatePerson } from "@/hooks/use-people";
import { emptyToNull, parseEmailList } from "@/lib/format";

/** `/people/new`: creates the person, then opens their page. */
export function NewPersonView() {
  const router = useRouter();
  const [form, setForm] = useState<PersonForm>(EMPTY_PERSON);
  const create = useCreatePerson();

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    create.mutate(
      {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        primary_email: form.primary_email.trim(),
        employee_code: emptyToNull(form.employee_code),
        notes: emptyToNull(form.notes),
        aliases: parseEmailList(form.aliases),
      },
      { onSuccess: (person) => router.push(`/people/${person.id}`) },
    );
  };

  return (
    <FormPage
      title="Add person"
      backHref="/people"
      backLabel="People"
      onSubmit={submit}
      submitLabel="Add person"
      pending={create.isPending}
    >
      <PersonFields form={form} onChange={setForm} idPrefix="p" />
    </FormPage>
  );
}
