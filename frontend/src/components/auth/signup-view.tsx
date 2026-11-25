"use client";

import { CheckCircle2Icon, HourglassIcon } from "lucide-react";
import { useState } from "react";

import { AuthCard } from "@/components/auth/auth-shell";
import { DevFillButton, uniqueEmail } from "@/components/auth/dev-fill";
import { FormError, NewPasswordFields, TextField, passwordProblem } from "@/components/auth/form-parts";
import { LinkButton, TextLink } from "@/components/common/links";
import { InlineError } from "@/components/common/notice";
import { Button } from "@/components/ui/button";
import { useAuthState, useSignup } from "@/hooks/use-auth";

const SIGN_IN = (
  <TextLink href="/login" className="font-normal">
    Already have an account? Sign in
  </TextLink>
);

/** Self sign-up (`/signup`): name, e-mail, password. Active at once for an approved domain, otherwise waits for an admin. */
export function SignupView() {
  const state = useAuthState().data;
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const signup = useSignup();

  if (state && !state.registration_enabled) {
    return (
      <AuthCard title="Sign-up is closed" footer={SIGN_IN}>
        <InlineError message="This panel does not take sign-ups. Ask an admin of your organization for an invite." />
      </AuthCard>
    );
  }

  if (signup.data?.status === "active") {
    return (
      <AuthCard title="Your account is ready">
        <div className="flex flex-col gap-5">
          <div className="flex gap-3 text-sm">
            <CheckCircle2Icon className="mt-0.5 size-5 shrink-0 text-success" />
            <p>Your company domain is approved, so you can sign in right away.</p>
          </div>
          <LinkButton href="/login" size="lg">
            Sign in
          </LinkButton>
        </div>
      </AuthCard>
    );
  }
  if (signup.data?.status === "pending") {
    return (
      <AuthCard title="Waiting for approval" footer={SIGN_IN}>
        <div className="flex gap-3 text-sm">
          <HourglassIcon className="mt-0.5 size-5 shrink-0 text-muted-foreground" />
          <p>
            An admin of your organization has to approve <span className="font-medium">{email}</span>. Let them know you signed
            up; once they approve, sign in with your password.
          </p>
        </div>
      </AuthCard>
    );
  }

  const problem = passwordProblem(password, repeat);
  return (
    <AuthCard
      title="Create your account"
      description={state?.organization ? `Join ${state.organization.name} on Open Revoke.` : "Join Open Revoke."}
      footer={SIGN_IN}
    >
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          signup.mutate({ name, email, password });
        }}
      >
        <DevFillButton
          onFill={(prefill) => {
            setName(prefill.invitee_name);
            setEmail(uniqueEmail(prefill.signup_email));
            setPassword(prefill.password);
            setRepeat(prefill.password);
          }}
        />
        <TextField id="name" label="Your name" autoComplete="name" autoFocus required value={name} onValue={setName} />
        <TextField id="email" label="Work e-mail" type="email" autoComplete="username" required value={email} onValue={setEmail} />
        <NewPasswordFields password={password} repeat={repeat} onPassword={setPassword} onRepeat={setRepeat} />
        <FormError error={signup.error} />
        <Button type="submit" size="lg" disabled={signup.isPending || Boolean(problem) || password !== repeat}>
          Create account
        </Button>
      </form>
    </AuthCard>
  );
}
