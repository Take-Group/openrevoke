"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { LoadingRows } from "@/components/common/query-state";
import { WriteModeBadge } from "@/components/common/write-mode-badge";
import { AppChoiceList, AppChoiceRow } from "@/components/people/app-choice-list";
import { PersonQuery } from "@/components/people/person-query";
import { Input } from "@/components/ui/input";
import { useActions } from "@/hooks/use-actions";
import { useApps } from "@/hooks/use-apps";
import { useOnboardPerson } from "@/hooks/use-people";
import { emptyToNull, fullName } from "@/lib/format";
import type { ActionStatus, AppListItem, PersonDetail } from "@/lib/api/types";

const OPEN: ActionStatus[] = ["pending_approval", "approved", "running", "verifying"];

interface Choice {
  app: AppListItem;
  /** Why the backend would skip the app; such apps cannot be chosen. */
  skip: string | null;
}

/** Mirrors the backend rules (services/onboarding.py) so the operator sees the outcome before clicking. */
function useChoices(person: PersonDetail): { choices: Choice[]; loading: boolean } {
  const apps = useApps({ limit: 500 });
  const open = useActions({ person_id: person.id, status: OPEN, limit: 500 }, true);
  const hasAccount = new Set(person.accounts.filter((a) => a.status !== "removed").map((a) => a.app.app_id));
  const creating = new Set(
    (open.data?.items ?? [])
      .filter(
        (action) =>
          action.kind === "create_account" ||
          (action.kind === "manual_task" && action.payload.operation === "create_account"),
      )
      .map((action) => action.app.app_id),
  );
  const choices = (apps.data?.items ?? []).map((app) => ({
    app,
    skip: hasAccount.has(app.id) ? "Has an account" : creating.has(app.id) ? "Already open" : null,
  }));
  return { choices, loading: apps.isPending };
}

function AppChoices({
  choices,
  selected,
  onToggle,
}: {
  choices: Choice[];
  selected: Set<string>;
  onToggle: (appId: string) => void;
}) {
  return (
    <AppChoiceList emptyTitle="No apps yet">
      {choices.map(({ app, skip }) => (
        <AppChoiceRow
          key={app.id}
          app={{ name: app.name, slug: app.slug, connectorKey: app.connector_key }}
          choice={{ checked: selected.has(app.id), disabled: skip !== null, onToggle: () => onToggle(app.id) }}
          aside={
            skip ? (
              <span className="text-xs text-muted-foreground">{skip}</span>
            ) : (
              <WriteModeBadge mode={app.create_mode} what="create" />
            )
          }
        />
      ))}
    </AppChoiceList>
  );
}

/** Gives a person accounts in several apps at once: one batch of creations waiting for approval. */
function OnboardForm({ person }: { person: PersonDetail }) {
  const router = useRouter();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [email, setEmail] = useState(person.primary_email);
  const onboard = useOnboardPerson(person.id);
  const { choices, loading } = useChoices(person);
  const chosen = choices.filter((choice) => !choice.skip && selected.has(choice.app.id));

  const toggle = (appId: string) =>
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(appId)) next.delete(appId);
      else next.add(appId);
      return next;
    });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    onboard.mutate(
      { apps: chosen.map((choice) => ({ app_id: choice.app.id })), email: emptyToNull(email) },
      // The batch waits for approval in Actions: continue there.
      { onSuccess: (result) => router.push(`/actions?batch=${result.batch_id}`) },
    );
  };

  return (
    <FormPage
      title={`Onboard ${fullName(person)}`}
      backHref={`/people/${person.id}`}
      backLabel={fullName(person)}
      description="Every chosen app gets an account creation, or a manual task when its connector cannot create accounts. Nothing runs until you approve the batch in Actions."
      onSubmit={submit}
      submitLabel="Onboard"
      pending={onboard.isPending}
      submitDisabled={chosen.length === 0 || person.status === "left"}
      hint={person.status === "left" ? "The person has left." : `${chosen.length} app(s) chosen`}
    >
      {loading ? <LoadingRows rows={3} /> : <AppChoices choices={choices} selected={selected} onToggle={toggle} />}
      <FormField label="E-mail for the new accounts" htmlFor="onb-email">
        <Input id="onb-email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
      </FormField>
    </FormPage>
  );
}

/** `/people/<id>/onboard`. */
export function OnboardView({ id }: { id: string }) {
  return <PersonQuery id={id}>{(person) => <OnboardForm person={person} />}</PersonQuery>;
}
