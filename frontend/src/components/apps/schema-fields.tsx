"use client";

import { SlidersHorizontalIcon } from "lucide-react";

import { EmptyState } from "@/components/common/empty-state";
import { FormField } from "@/components/common/form-field";
import { StatusBadge } from "@/components/common/status-badge";
import { Input } from "@/components/ui/input";
import { OptionSelect } from "@/components/common/option-select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { FieldValue, SchemaField } from "@/lib/json-schema";

interface SchemaFieldsProps {
  fields: SchemaField[];
  values: Record<string, FieldValue>;
  onChange: (name: string, value: FieldValue) => void;
  /** Secret fields the backend already stores for this connection (`secret_fields_set`). */
  secretFieldsSet: string[];
}

function inputType(field: SchemaField): string {
  if (field.secret) return "password";
  if (field.type === "integer" || field.type === "number") return "number";
  if (field.format === "uri") return "url";
  if (field.format === "email") return "email";
  return "text";
}

interface FieldControlProps {
  field: SchemaField;
  value: FieldValue;
  onChange: (v: FieldValue) => void;
  /** This secret field has a stored value. */
  secretsSet: boolean;
}

function FieldControl({ field, value, onChange, secretsSet }: FieldControlProps) {
  const id = `cfg-${field.name}`;
  if (field.type === "boolean") {
    return <Switch id={id} checked={value === true} onCheckedChange={(checked) => onChange(checked)} />;
  }
  const text = typeof value === "string" ? value : "";
  if (field.type === "enum") {
    return (
      <OptionSelect
        id={id}
        required={field.required}
        placeholder={field.required ? undefined : "—"}
        options={field.options.map((option) => ({ value: option, label: option }))}
        value={text}
        onChange={onChange}
      />
    );
  }
  const secretPlaceholder = secretsSet ? "••••••••  (stored)" : "Not set";
  if (field.multiline || field.type === "string_list") {
    return (
      <Textarea
        id={id}
        rows={field.multiline ? 5 : 3}
        className={field.secret ? "font-mono text-xs [-webkit-text-security:disc]" : "font-mono text-xs"}
        required={field.required && !(field.secret && secretsSet)}
        placeholder={field.secret ? secretPlaceholder : (field.placeholder ?? (field.type === "string_list" ? "One per line" : undefined))}
        value={text}
        autoComplete="off"
        spellCheck={false}
        data-1p-ignore={field.secret || undefined}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }
  return (
    <Input
      id={id}
      type={inputType(field)}
      step={field.type === "number" ? "any" : undefined}
      required={field.required && !(field.secret && secretsSet)}
      pattern={field.secret ? undefined : (field.pattern ?? undefined)}
      placeholder={field.secret ? secretPlaceholder : (field.placeholder ?? undefined)}
      autoComplete={field.secret ? "new-password" : "off"}
      // Password managers must not offer to save connector tokens as logins.
      data-1p-ignore={field.secret || undefined}
      data-lpignore={field.secret || undefined}
      value={text}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

/** Connection form fields rendered from the connector's `config_schema`. */
export function SchemaFields({ fields, values, onChange, secretFieldsSet }: SchemaFieldsProps) {
  if (fields.length === 0) {
    return <EmptyState icon={SlidersHorizontalIcon} title="No settings needed" className="py-6" />;
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {fields.map((field) => {
        const secretsSet = field.secret && secretFieldsSet.includes(field.name);
        return (
        <FormField
          key={field.name}
          label={
            secretsSet ? (
              <span className="inline-flex items-center gap-2">
                {field.title}
                <StatusBadge status="ok" label="Set" className="h-5" />
              </span>
            ) : (
              field.title
            )
          }
          htmlFor={`cfg-${field.name}`}
          required={field.required && !(field.secret && secretsSet)}
          hint={field.description}
          info={
            field.secret
              ? secretsSet
                ? "A value is stored. Type a new one to replace it, or leave empty to keep it."
                : "Stored encrypted and never shown again."
              : undefined
          }
          className={field.multiline ? "sm:col-span-2" : undefined}
        >
          <FieldControl
            field={field}
            value={values[field.name] ?? ""}
            secretsSet={secretsSet}
            onChange={(value) => onChange(field.name, value)}
          />
        </FormField>
        );
      })}
    </div>
  );
}
