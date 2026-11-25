"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { FormError } from "@/components/auth/form-parts";
import { TotpCodeField, TotpEnrollmentPanel } from "@/components/auth/totp-step";
import { FormPage } from "@/components/common/form-page";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthState, useSetTwoFactor, useStartTwoFactor } from "@/hooks/use-auth";

/**
 * `/settings/two-factor`: turn 2FA (an authenticator app) on with the first code from a new QR
 * code, or off with a current code. With 2FA on, every sign-in asks for a code.
 */
export function TwoFactorView() {
  const router = useRouter();
  const user = useAuthState().data?.user;
  const start = useStartTwoFactor();
  const save = useSetTwoFactor();
  const [code, setCode] = useState("");
  const started = useRef(false);
  const enabled = user?.totp_enabled ?? false;

  useEffect(() => {
    // One secret per visit: a second call would replace the QR code the user is scanning.
    if (!user || enabled || started.current) return;
    started.current = true;
    start.mutate();
  }, [user, enabled, start]);

  if (!user) return null;
  const ticket = start.data?.ticket;

  const submit = (value: string) => {
    if (value.length !== 6 || save.isPending) return;
    const data = enabled ? { on: false as const, code: value } : { on: true as const, ticket: ticket ?? "", code: value };
    save.mutate(data, {
      onSuccess: () => {
        toast.success(enabled ? "Two-factor authentication is off" : "Two-factor authentication is on");
        router.push("/settings");
      },
      onError: () => setCode(""),
    });
  };

  return (
    <FormPage
      title="Two-factor authentication"
      backHref="/settings"
      backLabel="Settings"
      description={
        enabled
          ? "Enter a code from your authenticator app to turn two-factor authentication off."
          : "Scan the QR code with Google Authenticator (or another authenticator app), then enter the 6-digit code it shows."
      }
      submitLabel={enabled ? "Turn off" : "Turn on"}
      destructive={enabled}
      pending={save.isPending}
      submitDisabled={code.length !== 6 || (!enabled && !ticket)}
      hint={enabled ? "Without 2FA a stolen password opens the panel." : "Every next sign-in asks for a code."}
      onSubmit={(event) => {
        event.preventDefault();
        submit(code);
      }}
    >
      {!enabled &&
        (start.data ? (
          <TotpEnrollmentPanel setup={start.data.totp_setup} />
        ) : start.isError ? (
          <FormError error={start.error} />
        ) : (
          <Skeleton className="mx-auto size-44" />
        ))}
      <TotpCodeField code={code} onCode={setCode} onComplete={submit} autoFocus={enabled} />
      <FormError error={save.error} />
    </FormPage>
  );
}
