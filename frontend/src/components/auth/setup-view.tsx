"use client";

import { ArrowLeftIcon, ArrowRightIcon } from "lucide-react";
import { useState } from "react";

import { DevFillButton } from "@/components/auth/dev-fill";
import { FormError, NewPasswordFields, TextField, passwordProblem } from "@/components/auth/form-parts";
import { AuthCard } from "@/components/auth/auth-shell";
import { SetupProgress } from "@/components/auth/setup-progress";
import { TotpStep, type TotpFrameProps } from "@/components/auth/totp-step";
import { CopyField } from "@/components/common/copy-button";
import { CurrencySelect } from "@/components/common/currency-select";
import { FormField } from "@/components/common/form-field";
import { InlineError } from "@/components/common/notice";
import { TimeZoneSelect } from "@/components/common/time-zone-select";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useRestartAtLogin, useSetup, useSetupTokenCheck } from "@/hooks/use-auth";
import { errorMessage } from "@/lib/api/client";
import type { AuthStep } from "@/lib/api/auth-types";
import { detectTimeZone } from "@/lib/time-zones";

/** The 2FA step of the first run with its progress. Module level: `TotpStep` needs a stable frame. */
function TotpSetupFrame(props: TotpFrameProps) {
  return <AuthCard eyebrow={<SetupProgress current={2} />} {...props} />;
}

const SETUP_LINK_COMMAND = "open-revoke setup-link";
const SETUP_LINK_COMPOSE = "docker compose exec app python -m app.cli setup-link";

/** No token, or a stale one: the setup link comes only from the server, so a stranger cannot claim the panel. */
function SetupLinkNeeded({ error }: { error?: string }) {
  return (
    <AuthCard
      eyebrow={<SetupProgress current={0} />}
      title="Open the setup link"
      description="A new installation is set up from a link printed on its server. Only someone with access to the server can create the first admin."
    >
      <div className="flex flex-col gap-4">
        {error && <InlineError message={error} />}
        <FormField label="On the server, run" hint="It prints a new link; the old one stops working.">
          <CopyField value={SETUP_LINK_COMMAND} label="the command" />
        </FormField>
        <FormField label="Installed without the installer" hint="In the folder with compose.yaml.">
          <CopyField value={SETUP_LINK_COMPOSE} label="the command" />
        </FormField>
      </div>
    </AuthCard>
  );
}

interface OrganizationDraft {
  name: string;
  currency: string;
  timezone: string;
}

function OrganizationStep({ draft, onNext }: { draft: OrganizationDraft; onNext: (draft: OrganizationDraft) => void }) {
  const [name, setName] = useState(draft.name);
  const [currency, setCurrency] = useState(draft.currency);
  const [timezone, setTimezone] = useState(draft.timezone);
  return (
    <AuthCard
      eyebrow={<SetupProgress current={0} />}
      title="Set up your organization"
    >
      <form
        className="flex flex-col gap-5"
        onSubmit={(event) => {
          event.preventDefault();
          onNext({ name: name.trim(), currency, timezone });
        }}
      >
        <DevFillButton
          onFill={(prefill) => {
            setName(prefill.organization_name);
            setCurrency(prefill.currency);
          }}
        />
        <TextField
          id="organization"
          label="Organization name"
          autoComplete="organization"
          placeholder="Acme Inc."
          autoFocus
          required
          value={name}
          onValue={setName}
        />
        <FormField label="Currency" htmlFor="currency" hint="Prices in other currencies are converted with daily exchange rates.">
          <CurrencySelect id="currency" value={currency} onChange={setCurrency} />
        </FormField>
        <FormField label="Time zone" htmlFor="timezone" hint="Suggested from this computer.">
          <TimeZoneSelect id="timezone" value={timezone} onChange={setTimezone} />
        </FormField>
        <Button type="submit" size="lg" className="mt-1" disabled={!name.trim()}>
          Continue
          <ArrowRightIcon />
        </Button>
      </form>
    </AuthCard>
  );
}

/** First run, from the setup link: the organization, its first user (the admin), then 2FA. /welcome asks the rest. */
export function SetupView({ token }: { token: string | null }) {
  const check = useSetupTokenCheck(token);
  if (!token) return <SetupLinkNeeded />;
  if (check.isError) return <SetupLinkNeeded error={errorMessage(check.error)} />;
  if (check.isPending) {
    return (
      <AuthCard eyebrow={<SetupProgress current={0} />} title="Set up your organization">
        <Skeleton className="h-64 w-full" />
      </AuthCard>
    );
  }
  return <SetupForm token={token} />;
}

function SetupForm({ token }: { token: string }) {
  const [draft, setDraft] = useState<OrganizationDraft>(() => ({ name: "", currency: "EUR", timezone: detectTimeZone() }));
  const [stage, setStage] = useState<"organization" | "account">("organization");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [step, setStep] = useState<AuthStep | null>(null);
  const setup = useSetup();
  const restart = useRestartAtLogin();

  if (step) return <TotpStep step={step} onRestart={restart} Frame={TotpSetupFrame} />;

  if (stage === "organization") {
    return (
      <OrganizationStep
        draft={draft}
        onNext={(next) => {
          setDraft(next);
          setStage("account");
        }}
      />
    );
  }

  const problem = passwordProblem(password, repeat);
  return (
    <AuthCard
      eyebrow={<SetupProgress current={1} />}
      title="Create your admin account"
    >
      <form
        className="flex flex-col gap-5"
        onSubmit={(event) => {
          event.preventDefault();
          setup.mutate(
            { organization_name: draft.name, currency: draft.currency, timezone: draft.timezone, name, email, password, token },
            { onSuccess: setStep },
          );
        }}
      >
        <DevFillButton
          onFill={(prefill) => {
            setName(prefill.name);
            setEmail(prefill.email);
            setPassword(prefill.password);
            setRepeat(prefill.password);
          }}
        />
        <TextField id="name" label="Your name" autoComplete="name" autoFocus required value={name} onValue={setName} />
        <TextField
          id="email"
          label="Work e-mail"
          type="email"
          autoComplete="username"
          placeholder="you@company.com"
          required
          value={email}
          onValue={setEmail}
        />
        <NewPasswordFields password={password} repeat={repeat} onPassword={setPassword} onRepeat={setRepeat} />
        <FormError error={setup.error} />
        <div className="mt-1 flex gap-2">
          <Button type="button" variant="outline" size="lg" onClick={() => setStage("organization")} disabled={setup.isPending}>
            <ArrowLeftIcon />
            Back
          </Button>
          <Button type="submit" size="lg" className="flex-1" disabled={setup.isPending || Boolean(problem) || password !== repeat}>
            Create admin account
            <ArrowRightIcon />
          </Button>
        </div>
      </form>
    </AuthCard>
  );
}
