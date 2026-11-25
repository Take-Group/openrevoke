"use client";

import {
  ArrowLeftIcon,
  ArrowRightIcon,
  FileSpreadsheetIcon,
  KeyRoundIcon,
  MessageSquareOffIcon,
  ShieldOffIcon,
  UserPlusIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { FormError } from "@/components/auth/form-parts";
import { AuthCard } from "@/components/auth/auth-shell";
import { SetupProgress } from "@/components/auth/setup-progress";
import { AppAvatar, GlyphAvatar } from "@/components/common/avatars";
import { ChoiceCards, type ChoiceOption } from "@/components/common/choice-cards";
import { TextLink } from "@/components/common/links";
import { Button } from "@/components/ui/button";
import { useOnboarding, useSaveOnboardingChoices } from "@/hooks/use-onboarding";
import { useUrlTab } from "@/hooks/use-url-tab";
import type { ChatPlatform, PasswordManager, PeopleImport } from "@/lib/api/onboarding-types";

export type WelcomeStep = "people" | "chat" | "manager";

const PEOPLE: ChoiceOption<PeopleImport>[] = [
  { value: "google_workspace", label: "Google Workspace", icon: <AppAvatar name="Google Workspace" size="sm" /> },
  { value: "microsoft_365", label: "Microsoft 365", icon: <AppAvatar name="Microsoft 365" size="sm" /> },
  { value: "csv", label: "CSV file", icon: <GlyphAvatar icon={FileSpreadsheetIcon} size="sm" /> },
  { value: "manual", label: "I'll add them by hand", icon: <GlyphAvatar icon={UserPlusIcon} size="sm" /> },
];

const CHAT: ChoiceOption<ChatPlatform>[] = [
  { value: "slack", label: "Slack", icon: <AppAvatar name="Slack" size="sm" /> },
  { value: "teams", label: "Microsoft Teams", icon: <AppAvatar name="Microsoft Teams" size="sm" /> },
  { value: "none", label: "Neither", icon: <GlyphAvatar icon={MessageSquareOffIcon} size="sm" /> },
];

const MANAGER: ChoiceOption<PasswordManager>[] = [
  { value: "1password", label: "1Password", icon: <AppAvatar name="1Password" size="sm" /> },
  { value: "bitwarden", label: "Bitwarden", icon: <AppAvatar name="Bitwarden" size="sm" /> },
  {
    value: "other",
    label: "Another one",
    hint: "We'll tell you how to add its extension by hand",
    icon: <GlyphAvatar icon={KeyRoundIcon} size="sm" />,
  },
  { value: "none", label: "None", icon: <GlyphAvatar icon={ShieldOffIcon} size="sm" /> },
];

/**
 * Three questions right after the first-run setup. The first two pick the first steps of the
 * setup checklist on the dashboard (skills/backend/setup-checklist.md); the third sets which
 * password manager the shared browser force-installs (skills/backend/browser.md). Nothing
 * connects here.
 */
export function WelcomeView({ initialStep }: { initialStep?: WelcomeStep }) {
  const router = useRouter();
  const onboarding = useOnboarding();
  const save = useSaveOnboardingChoices();
  const [stage, setStage] = useUrlTab<WelcomeStep>(initialStep, "people", "step");
  const [people, setPeople] = useState<PeopleImport | null>(null);
  const [chat, setChat] = useState<ChatPlatform | null>(null);
  const [manager, setManager] = useState<PasswordManager | null>(null);
  const peopleValue = people ?? onboarding.data?.people_import ?? null;
  const chatValue = chat ?? onboarding.data?.chat_platform ?? null;
  const managerValue = manager ?? onboarding.data?.password_manager ?? null;
  const skip = (
    <TextLink href="/" tone="muted">
      Skip, go to the dashboard
    </TextLink>
  );

  if (stage === "people") {
    return (
      <AuthCard
        eyebrow={<SetupProgress current={3} />}
        title="Where do your people come from?"
        footer={skip}
      >
        <form
          className="flex flex-col gap-5"
          onSubmit={(event) => {
            event.preventDefault();
            if (peopleValue) save.mutate({ people_import: peopleValue }, { onSuccess: () => setStage("chat") });
          }}
        >
          <ChoiceCards label="People source" options={PEOPLE} value={peopleValue} onChange={setPeople} />
          <FormError error={save.error} />
          <Button type="submit" size="lg" disabled={!peopleValue || save.isPending}>
            Continue
            <ArrowRightIcon />
          </Button>
        </form>
      </AuthCard>
    );
  }

  if (stage === "chat") {
    return (
      <AuthCard eyebrow={<SetupProgress current={4} />} title="Where does your team talk?" footer={skip}>
        <form
          className="flex flex-col gap-5"
          onSubmit={(event) => {
            event.preventDefault();
            if (chatValue) save.mutate({ chat_platform: chatValue }, { onSuccess: () => setStage("manager") });
          }}
        >
          <ChoiceCards label="Chat" options={CHAT} value={chatValue} onChange={setChat} />
          <FormError error={save.error} />
          <div className="flex gap-2">
            <Button type="button" variant="outline" size="lg" onClick={() => setStage("people")} disabled={save.isPending}>
              <ArrowLeftIcon />
              Back
            </Button>
            <Button type="submit" size="lg" className="flex-1" disabled={!chatValue || save.isPending}>
              Continue
              <ArrowRightIcon />
            </Button>
          </div>
        </form>
      </AuthCard>
    );
  }

  return (
    <AuthCard
      eyebrow={<SetupProgress current={5} />}
      title="Which password manager does your admin use?"
      description="Its extension goes into the shared browser, so you sign in to apps by autofill. Change it later in Settings."
      footer={skip}
    >
      <form
        className="flex flex-col gap-5"
        onSubmit={(event) => {
          event.preventDefault();
          if (managerValue) save.mutate({ password_manager: managerValue }, { onSuccess: () => router.push("/") });
        }}
      >
        <ChoiceCards label="Password manager" options={MANAGER} value={managerValue} onChange={setManager} />
        <FormError error={save.error} />
        <div className="flex gap-2">
          <Button type="button" variant="outline" size="lg" onClick={() => setStage("chat")} disabled={save.isPending}>
            <ArrowLeftIcon />
            Back
          </Button>
          <Button type="submit" size="lg" className="flex-1" disabled={!managerValue || save.isPending}>
            Finish setup
            <ArrowRightIcon />
          </Button>
        </div>
      </form>
    </AuthCard>
  );
}
