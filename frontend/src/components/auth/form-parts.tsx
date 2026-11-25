"use client";

import { FormField } from "@/components/common/form-field";
import { InlineError } from "@/components/common/notice";
import { Input } from "@/components/ui/input";
import { errorMessage } from "@/lib/api/client";

export const MIN_PASSWORD = 12;

interface TextFieldProps extends Omit<React.ComponentProps<"input">, "onChange"> {
  id: string;
  label: string;
  hint?: React.ReactNode;
  onValue: (value: string) => void;
}

export function TextField({ id, label, hint, onValue, ...props }: TextFieldProps) {
  return (
    <FormField label={label} htmlFor={id} hint={hint}>
      <Input id={id} name={id} onChange={(event) => onValue(event.target.value)} {...props} />
    </FormField>
  );
}

/** New password twice. Returns a message while the two do not match or the first is too short. */
export function passwordProblem(password: string, repeat: string): string | null {
  if (password.length < MIN_PASSWORD) return `At least ${MIN_PASSWORD} characters.`;
  if (repeat && password !== repeat) return "The passwords differ.";
  return null;
}

export function NewPasswordFields({
  password,
  repeat,
  onPassword,
  onRepeat,
  label = "Password",
}: {
  password: string;
  repeat: string;
  onPassword: (value: string) => void;
  onRepeat: (value: string) => void;
  label?: string;
}) {
  const mismatch = repeat.length > 0 && password !== repeat;
  return (
    <>
      <TextField
        id="new-password"
        label={label}
        type="password"
        autoComplete="new-password"
        required
        minLength={MIN_PASSWORD}
        value={password}
        onValue={onPassword}
        hint={`At least ${MIN_PASSWORD} characters. A passphrase of a few words works well.`}
      />
      <TextField
        id="repeat-password"
        label="Repeat password"
        type="password"
        autoComplete="new-password"
        required
        value={repeat}
        onValue={onRepeat}
        aria-invalid={mismatch || undefined}
        hint={mismatch ? "The passwords differ." : undefined}
      />
    </>
  );
}

export function FormError({ error }: { error: unknown }) {
  if (!error) return null;
  return <InlineError message={errorMessage(error)} />;
}
