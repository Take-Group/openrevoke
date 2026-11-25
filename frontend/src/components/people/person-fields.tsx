"use client";

import { FormField } from "@/components/common/form-field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export interface PersonForm {
  first_name: string;
  last_name: string;
  primary_email: string;
  employee_code: string;
  aliases: string;
  notes: string;
}

export const EMPTY_PERSON: PersonForm = {
  first_name: "",
  last_name: "",
  primary_email: "",
  employee_code: "",
  aliases: "",
  notes: "",
};

/** Fields shared by "Add person" and "Edit person". */
export function PersonFields({
  form,
  onChange,
  idPrefix,
}: {
  form: PersonForm;
  onChange: (form: PersonForm) => void;
  idPrefix: string;
}) {
  const set = (field: keyof PersonForm) => (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    onChange({ ...form, [field]: event.target.value });
  const id = (name: string) => `${idPrefix}-${name}`;

  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="First name" htmlFor={id("first")} required>
          <Input id={id("first")} required value={form.first_name} onChange={set("first_name")} />
        </FormField>
        <FormField label="Last name" htmlFor={id("last")} required>
          <Input id={id("last")} required value={form.last_name} onChange={set("last_name")} />
        </FormField>
      </div>
      <FormField label="E-mail" htmlFor={id("email")} required>
        <Input id={id("email")} type="email" required value={form.primary_email} onChange={set("primary_email")} />
      </FormField>
      <FormField label="Employee code" htmlFor={id("code")}>
        <Input id={id("code")} value={form.employee_code} onChange={set("employee_code")} />
      </FormField>
      <FormField
        label="Aliases"
        htmlFor={id("aliases")}
        info="Other e-mails of this person, one per line or separated by commas. Accounts with these e-mails match the person."
      >
        <Textarea id={id("aliases")} rows={2} value={form.aliases} onChange={set("aliases")} />
      </FormField>
      <FormField label="Notes" htmlFor={id("notes")}>
        <Textarea id={id("notes")} rows={3} value={form.notes} onChange={set("notes")} />
      </FormField>
    </>
  );
}
