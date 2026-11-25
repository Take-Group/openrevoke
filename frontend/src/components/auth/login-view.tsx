"use client";

import { useState } from "react";

import { AuthCard } from "@/components/auth/auth-shell";
import { DevFillButton } from "@/components/auth/dev-fill";
import { FormError, TextField } from "@/components/auth/form-parts";
import { TotpStep } from "@/components/auth/totp-step";
import { TextLink } from "@/components/common/links";
import { Button } from "@/components/ui/button";
import { useAuthState, useLogin } from "@/hooks/use-auth";
import type { AuthStep } from "@/lib/api/auth-types";

export function LoginView() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [step, setStep] = useState<AuthStep | null>(null);
  const login = useLogin();
  const registrationEnabled = useAuthState().data?.registration_enabled ?? false;

  if (step) {
    return (
      <TotpStep
        step={step}
        onRestart={() => {
          setStep(null);
          setPassword("");
          login.reset();
        }}
      />
    );
  }

  return (
    <AuthCard
      title="Sign in"
      description="Sign in to Open Revoke."
      footer={
        registrationEnabled ? (
          <TextLink href="/signup" className="font-normal">
            No account? Create one
          </TextLink>
        ) : (
          <>No account? Ask an admin of your panel for an invite.</>
        )
      }
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          login.mutate({ email, password }, { onSuccess: (next) => next.step !== "done" && setStep(next) });
        }}
      >
        <DevFillButton
          onFill={(prefill) => {
            setEmail(prefill.email);
            setPassword(prefill.password);
          }}
        />
        <TextField
          id="email"
          label="E-mail"
          type="email"
          autoComplete="username"
          autoFocus
          required
          value={email}
          onValue={setEmail}
        />
        <div className="flex flex-col gap-1.5">
          <TextField
            id="password"
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onValue={setPassword}
          />
          <TextLink href="/forgot-password" className="self-end text-xs font-normal text-muted-foreground">
            Forgot password?
          </TextLink>
        </div>
        <FormError error={login.error} />
        <Button type="submit" size="lg" disabled={login.isPending}>
          Continue
        </Button>
      </form>
    </AuthCard>
  );
}
