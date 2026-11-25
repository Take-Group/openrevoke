"use client";

import { SmartphoneIcon } from "lucide-react";
import { useState } from "react";

import { useHoldSignInPage } from "@/components/auth/auth-gate";
import { AuthCard } from "@/components/auth/auth-shell";
import { FormError } from "@/components/auth/form-parts";
import { CopyButton } from "@/components/common/copy-button";
import { FormField } from "@/components/common/form-field";
import { TextLink } from "@/components/common/links";
import { Panel } from "@/components/common/panel";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useSkipTotp, useVerifyTotp } from "@/hooks/use-auth";
import type { AuthStep, TotpEnrollment } from "@/lib/api/auth-types";

function formatSecret(secret: string): string {
  return secret.replace(/(.{4})/g, "$1 ").trim();
}

/** QR code and the key to type: a new authenticator (first-run setup and Settings). */
export function TotpEnrollmentPanel({ setup }: { setup: TotpEnrollment }) {
  return (
    <div className="flex flex-col items-center gap-3">
      {/* eslint-disable-next-line @next/next/no-img-element -- a data: URI from the API */}
      <img src={setup.qr_svg} alt="QR code for the authenticator app" className="size-44 rounded-lg bg-white p-1.5" />
      <Panel tone="muted" className="w-full" bodyClassName="flex flex-col gap-1 px-3 py-2">
        <p className="text-xs text-muted-foreground">Cannot scan? Enter this key:</p>
        <div className="flex items-center justify-between gap-2">
          <code className="font-mono text-[0.8125rem] break-all">{formatSecret(setup.secret)}</code>
          <CopyButton value={setup.secret} label="Copy the key" />
        </div>
      </Panel>
      <TextLink href={setup.otpauth_uri} className="flex items-center gap-1.5 text-xs md:hidden">
        <SmartphoneIcon className="size-3.5" />
        Open in the authenticator app
      </TextLink>
    </div>
  );
}

/** The 6-digit code field; `onComplete` fires when the sixth digit is typed or pasted. */
export function TotpCodeField({
  code,
  onCode,
  onComplete,
  autoFocus = true,
}: {
  code: string;
  onCode: (code: string) => void;
  onComplete?: (code: string) => void;
  autoFocus?: boolean;
}) {
  return (
    <FormField label="Code" htmlFor="totp-code">
      <Input
        id="totp-code"
        name="totp-code"
        inputMode="numeric"
        autoComplete="one-time-code"
        pattern="[0-9]{6}"
        maxLength={6}
        autoFocus={autoFocus}
        placeholder="123456"
        className="text-center font-mono text-base tracking-[0.4em]"
        value={code}
        onChange={(event) => {
          const value = event.target.value.replace(/\D/g, "").slice(0, 6);
          onCode(value);
          if (value.length === 6) onComplete?.(value);
        }}
      />
    </FormField>
  );
}

/** What wraps the step: `AuthCard`, with the first-run progress during setup. */
export interface TotpFrameProps {
  title: string;
  description: React.ReactNode;
  footer: React.ReactNode;
  children: React.ReactNode;
}
export type TotpFrame = React.ComponentType<TotpFrameProps>;

/**
 * Code step of a sign-in with 2FA: a 6-digit code. For `totp_setup` (first-run setup only) it first
 * shows the QR code to scan with Google Authenticator (or any TOTP app), and the admin may skip it.
 * `Frame` must be a stable component (module level), or the code field loses its value on every render.
 */
export function TotpStep({
  step,
  onRestart,
  Frame = AuthCard,
}: {
  step: AuthStep;
  onRestart: () => void;
  Frame?: TotpFrame;
}) {
  const [code, setCode] = useState("");
  const verify = useVerifyTotp();
  const skip = useSkipTotp();
  useHoldSignInPage();
  const enrolling = step.step === "totp_setup";
  const ticket = step.ticket ?? "";

  const submit = (value: string) => {
    if (value.length === 6 && !verify.isPending) verify.mutate({ ticket, code: value }, { onError: () => setCode("") });
  };

  return (
    <Frame
      title={enrolling ? "Set up two-factor authentication" : "Two-factor authentication"}
      description={
        enrolling
          ? "Scan the QR code with Google Authenticator (or another authenticator app), then enter the 6-digit code it shows."
          : "Enter the 6-digit code from your authenticator app."
      }
      footer={
        <Button type="button" variant="link-muted" onClick={onRestart}>
          Start over
        </Button>
      }
    >
      {enrolling && step.totp_setup && (
        <div className="mb-5">
          <TotpEnrollmentPanel setup={step.totp_setup} />
        </div>
      )}
      <form
        className="flex flex-col gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          submit(code);
        }}
      >
        <TotpCodeField code={code} onCode={setCode} onComplete={submit} />
        <FormError error={verify.error ?? skip.error} />
        <Button type="submit" size="lg" disabled={code.length !== 6 || verify.isPending || skip.isPending}>
          {enrolling ? "Turn on 2FA and continue" : "Verify"}
        </Button>
        {enrolling && (
          <div className="flex flex-col items-center gap-1 text-center">
            <Button
              type="button"
              variant="ghost"
              disabled={verify.isPending || skip.isPending}
              onClick={() => skip.mutate(ticket)}
            >
              Skip for now
            </Button>
            <p className="text-xs text-muted-foreground">
              Without 2FA a stolen password opens the panel. You can turn it on later in Settings.
            </p>
          </div>
        )}
      </form>
    </Frame>
  );
}
