"use client";

import { RefreshCwIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { FormError, NewPasswordFields, TextField, passwordProblem } from "@/components/auth/form-parts";
import { PageHeader, SETTINGS_COLUMN } from "@/components/common/page-header";
import { FormField } from "@/components/common/form-field";
import { CurrencySelect } from "@/components/common/currency-select";
import { DetailList } from "@/components/common/detail-list";
import { OptionSelect } from "@/components/common/option-select";
import { RatesSource } from "@/components/common/rates-source";
import { TimeZoneSelect } from "@/components/common/time-zone-select";
import { LinkButton } from "@/components/common/links";
import { StatusBadge } from "@/components/common/status-badge";
import { SettingsFooter, SettingsSection } from "@/components/settings/settings-section";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthState, useChangePassword } from "@/hooks/use-auth";
import { useCurrencies, useRefreshRates } from "@/hooks/use-currencies";
import { useOrganizationSettings, useUpdateOrganization } from "@/hooks/use-users";
import type { OrganizationCurrency, OrganizationOut } from "@/lib/api/auth-types";
import type { PasswordManager } from "@/lib/api/onboarding-types";

const PASSWORD_MANAGERS: { value: PasswordManager; label: string }[] = [
  { value: "1password", label: "1Password" },
  { value: "bitwarden", label: "Bitwarden" },
  { value: "other", label: "Another one (install it by hand)" },
  { value: "none", label: "None" },
];

function ChangePassword() {
  const [current, setCurrent] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const change = useChangePassword();
  const problem = passwordProblem(password, repeat);
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        change.mutate(
          { current_password: current, new_password: password },
          {
            onSuccess: () => {
              toast.success("Password changed. Other sessions were signed out.");
              setCurrent("");
              setPassword("");
              setRepeat("");
            },
          },
        );
      }}
    >
      <div className="flex max-w-sm flex-col gap-4">
      <TextField
        id="current-password"
        label="Current password"
        type="password"
        autoComplete="current-password"
        required
        value={current}
        onValue={setCurrent}
      />
      <NewPasswordFields label="New password" password={password} repeat={repeat} onPassword={setPassword} onRepeat={setRepeat} />
      <FormError error={change.error} />
      </div>
      <SettingsFooter hint="Changing it signs out your other sessions.">
        <Button type="submit" size="sm" disabled={change.isPending || !current || Boolean(problem) || password !== repeat}>
          Change password
        </Button>
      </SettingsFooter>
    </form>
  );
}

function OrganizationForm({ organization, canEdit }: { organization: OrganizationOut; canEdit: boolean }) {
  const [name, setName] = useState(organization.name);
  const [currency, setCurrency] = useState<OrganizationCurrency>(organization.currency);
  const [timezone, setTimezone] = useState(organization.timezone);
  const update = useUpdateOrganization();
  const changed =
    name.trim() !== organization.name || currency !== organization.currency || timezone !== organization.timezone;
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        update.mutate({ name: name.trim(), currency, timezone });
      }}
    >
      <div className="flex max-w-sm flex-col gap-4">
      <TextField id="organization-name" label="Name" required disabled={!canEdit} value={name} onValue={setName} />
      <FormField label="Currency" htmlFor="organization-currency" hint="Every cost in the panel is converted to it.">
        <CurrencySelect id="organization-currency" value={currency} onChange={setCurrency} disabled={!canEdit} />
      </FormField>
      <FormField label="Time zone" htmlFor="organization-timezone" hint="Dates and times in the panel use it.">
        <TimeZoneSelect id="organization-timezone" value={timezone} onChange={setTimezone} disabled={!canEdit} />
      </FormField>
      </div>
      <SettingsFooter hint={canEdit ? "Applies to everyone in the panel." : "Only an admin can change it."}>
        {canEdit && (
          <Button type="submit" size="sm" disabled={!changed || !name.trim() || update.isPending}>
            Save
          </Button>
        )}
      </SettingsFooter>
    </form>
  );
}

/** Which password manager the shared browser force-installs. Changing it restarts that browser. */
function PasswordManagerForm() {
  const settings = useOrganizationSettings();
  const update = useUpdateOrganization("Password manager saved");
  const [manager, setManager] = useState<PasswordManager | "">("");
  const current = settings.data?.password_manager ?? "";
  const value = manager || current;
  if (settings.isPending) return <Skeleton className="h-9 max-w-sm" />;
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (value) update.mutate({ password_manager: value });
      }}
    >
      <div className="max-w-sm">
        <FormField
          label="Password manager"
          htmlFor="password-manager"
          hint="Its extension goes into the shared browser so you sign in to apps by autofill."
        >
          <OptionSelect
            id="password-manager"
            value={value}
            onChange={setManager}
            options={PASSWORD_MANAGERS}
            placeholder="Choose a manager"
            required
          />
        </FormField>
      </div>
      <SettingsFooter hint="Changing it restarts the shared browser to swap the extension.">
        <Button type="submit" size="sm" disabled={!value || value === current || update.isPending}>
          Save
        </Button>
      </SettingsFooter>
    </form>
  );
}

/** Where the rates come from, and a manual download for admins (it also runs every day). */
function ExchangeRates({ canRefresh }: { canRefresh: boolean }) {
  const currencies = useCurrencies();
  const refresh = useRefreshRates();
  const info = currencies.data?.rates;
  return (
    <>
      <div className="text-sm">
        <RatesSource info={info} />
      </div>
      <SettingsFooter hint={info ? `${info.currencies} currencies, downloaded every day.` : undefined}>
        {canRefresh && (
          <Button variant="outline" size="sm" disabled={refresh.isPending} onClick={() => refresh.mutate()}>
            <RefreshCwIcon />
            Refresh rates
          </Button>
        )}
      </SettingsFooter>
    </>
  );
}

/** The signed-in user's account (password); admins also get the organization and exchange rates. */
export function SettingsView() {
  const state = useAuthState().data;
  const user = state?.user;
  if (!user) return null;
  return (
    <>
      <PageHeader title="Settings" />
      <div className={SETTINGS_COLUMN}>
        <SettingsSection title="Account" description="You, as signed in to this panel.">
          <DetailList
            framed={false}
            className="max-w-sm"
            rows={[
              ["Name", user.name],
              ["E-mail", user.email],
              ["Role", <span key="role" className="capitalize">{user.role}</span>],
            ]}
          />
        </SettingsSection>
        <SettingsSection
          title="Two-factor authentication"
          description="A code from an authenticator app (Google Authenticator, 1Password, Authy) at every sign-in, on top of the password."
          footer={
            <>
              <StatusBadge
                status={user.totp_enabled ? "on" : "off"}
                label={user.totp_enabled ? "On" : "Off"}
                tone={user.totp_enabled ? "success" : "warning"}
              />
              <LinkButton href="/settings/two-factor" size="sm" variant={user.totp_enabled ? "outline" : "default"}>
                {user.totp_enabled ? "Turn off" : "Set up"}
              </LinkButton>
            </>
          }
        />
        <SettingsSection title="Password" description="The password you sign in with. With two-factor authentication on, a code from your app too.">
          <ChangePassword />
        </SettingsSection>
        {state.organization && user.role === "admin" && (
          <>
            <SettingsSection
              title="Organization"
              description="Name, currency and time zone. Every cost is converted to the currency, every date shown in the time zone."
            >
              <OrganizationForm
                key={`${state.organization.name}-${state.organization.currency}-${state.organization.timezone}`}
                organization={state.organization}
                canEdit
              />
            </SettingsSection>
            <SettingsSection
              title="Password manager"
              description="The admin's password manager, force-installed in the shared browser so you sign in to apps by autofill."
            >
              <PasswordManagerForm />
            </SettingsSection>
            <SettingsSection title="Exchange rates" description="Prices in other currencies are converted with daily rates.">
              <ExchangeRates canRefresh />
            </SettingsSection>
          </>
        )}
      </div>
    </>
  );
}
