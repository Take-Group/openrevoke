"use client";

import Link from "next/link";
import { useState } from "react";

import { AuthCard } from "@/components/auth/auth-shell";
import { DevFillButton } from "@/components/auth/dev-fill";
import { FormError, NewPasswordFields, passwordProblem } from "@/components/auth/form-parts";
import { TextLink } from "@/components/common/links";
import { CopyField } from "@/components/common/copy-button";
import { Button, buttonVariants } from "@/components/ui/button";
import { useResetPassword } from "@/hooks/use-auth";

const BACK = (
  <TextLink href="/login" className="font-normal">
    Back to sign in
  </TextLink>
);

/** The two ways to a reset link: an admin's link, or the CLI on the server for an admin. */
function WithoutEmail() {
  return (
    <div className="flex flex-col gap-3 text-sm">
      <p>
        <span className="font-medium">Not an admin?</span> Ask an admin of your panel. In Settings → Users they create a one-time reset
        link and pass it to you.
      </p>
      <p>
        <span className="font-medium">An admin?</span> Run this on the server, then open the link it prints:
      </p>
      <CopyField value={RESET_LINK_COMMAND} label="the command" />
    </div>
  );
}

const RESET_LINK_COMMAND = "docker compose exec app /app/backend/.venv/bin/python -m app.cli reset-link you@company.com";

/** `/forgot-password`: the panel sends no e-mail, so it says where a reset link comes from. */
export function ForgotPasswordView() {
  return (
    <AuthCard title="Forgot password" description="A reset link comes from an admin, not by e-mail." footer={BACK}>
      <WithoutEmail />
    </AuthCard>
  );
}

export function ResetPasswordView({ token }: { token: string | null }) {
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const reset = useResetPassword();

  if (reset.isSuccess) {
    return (
      <AuthCard
        title="Password changed"
        description="Every session was signed out. Sign in with the new password (and a code from your authenticator app, if 2FA is on)."
      >
        <Link href="/login" className={buttonVariants({ size: "lg", className: "w-full" })}>
          Sign in
        </Link>
      </AuthCard>
    );
  }

  const problem = passwordProblem(password, repeat);
  return (
    <AuthCard title="Set a new password" footer={BACK}>
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (token) reset.mutate({ token, password });
        }}
      >
        {!token && <FormError error={new Error("The link has no token. Open the whole reset link again.")} />}
        <DevFillButton
          onFill={(prefill) => {
            setPassword(prefill.password);
            setRepeat(prefill.password);
          }}
        />
        <NewPasswordFields label="New password" password={password} repeat={repeat} onPassword={setPassword} onRepeat={setRepeat} />
        <FormError error={reset.error} />
        <Button type="submit" size="lg" disabled={!token || reset.isPending || Boolean(problem) || password !== repeat}>
          Set password
        </Button>
      </form>
    </AuthCard>
  );
}
