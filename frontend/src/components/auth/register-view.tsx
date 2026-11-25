"use client";

import { useState } from "react";

import { AuthCard } from "@/components/auth/auth-shell";
import { DevFillButton } from "@/components/auth/dev-fill";
import { FormError, NewPasswordFields, TextField, passwordProblem } from "@/components/auth/form-parts";
import { TextLink } from "@/components/common/links";
import { InlineError } from "@/components/common/notice";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useInviteInfo, useRegister } from "@/hooks/use-auth";
import { errorMessage } from "@/lib/api/client";

/** Registration from an invite link (`/register?token=...`); signs in at once (2FA is optional, in Settings). */
export function RegisterView({ token }: { token: string | null }) {
  const invite = useInviteInfo(token);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const register = useRegister();

  // Signed in: the auth gate moves on to the panel; the used invite must not flash as invalid meanwhile.
  if (register.isSuccess) return null;

  if (!token || invite.isError) {
    return (
      <AuthCard
        title="Invite link not valid"
        footer={<TextLink href="/login" className="font-normal">Back to sign in</TextLink>}
      >
        <InlineError
          message={token ? errorMessage(invite.error) : "Registration needs an invite. Ask an admin of the panel for one."}
        />
      </AuthCard>
    );
  }

  const problem = passwordProblem(password, repeat);
  return (
    <AuthCard
      title="Create your account"
      description={
        invite.data?.organization_name ? `You were invited to ${invite.data.organization_name}.` : "You were invited."
      }
      footer={<TextLink href="/login" className="font-normal">Already have an account? Sign in</TextLink>}
    >
      {invite.isPending ? (
        <Skeleton className="h-48 w-full" />
      ) : (
        <form
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            register.mutate({ token, name, password });
          }}
        >
          <DevFillButton
            onFill={(prefill) => {
              setName(prefill.invitee_name);
              setPassword(prefill.password);
              setRepeat(prefill.password);
            }}
          />
          <TextField id="email" label="E-mail" type="email" autoComplete="username" value={invite.data.email} readOnly disabled onValue={() => {}} />
          <TextField id="name" label="Your name" autoComplete="name" autoFocus required value={name} onValue={setName} />
          <NewPasswordFields password={password} repeat={repeat} onPassword={setPassword} onRepeat={setRepeat} />
          <FormError error={register.error} />
          <Button type="submit" size="lg" disabled={register.isPending || Boolean(problem) || password !== repeat}>
            Create account
          </Button>
        </form>
      )}
    </AuthCard>
  );
}
