"use client";

import { useRouter } from "next/navigation";

import { FormPage } from "@/components/common/form-page";
import { WriteModeBadge } from "@/components/common/write-mode-badge";
import { AppChoiceList, AppChoiceRow } from "@/components/people/app-choice-list";
import { PersonQuery } from "@/components/people/person-query";
import { useActions } from "@/hooks/use-actions";
import { useApps } from "@/hooks/use-apps";
import { useOffboardPerson } from "@/hooks/use-people";
import { accountLabel, fullName } from "@/lib/format";
import { removeVerb } from "@/lib/write-mode";
import type { ActionStatus, AppListItem, PersonAccountOut, PersonDetail } from "@/lib/api/types";

const OPEN: ActionStatus[] = ["pending_approval", "approved", "running", "verifying"];

interface PlanItem {
  account: PersonAccountOut;
  app: AppListItem | undefined;
  skip: string | null;
}

/** Mirrors the backend rules so the operator sees the outcome before clicking. */
function usePlan(person: PersonDetail): PlanItem[] {
  const open = useActions({ person_id: person.id, status: OPEN, limit: 500 }, true);
  const apps = useApps({ limit: 500 });
  const busy = new Set(
    (open.data?.items ?? [])
      .filter((action) => action.kind !== "create_account" && action.account)
      .map((action) => action.account!.account_id),
  );
  return person.accounts
    .filter((account) => account.status !== "removed")
    .map((account) => ({
      account,
      app: apps.data?.items.find((app) => app.id === account.app.app_id),
      skip: account.kind === "service" ? "Service account" : busy.has(account.id) ? "Already open" : null,
    }));
}

function Plan({ items }: { items: PlanItem[] }) {
  return (
    <AppChoiceList emptyTitle="No live accounts">
      {items.map(({ account, app, skip }) => {
        const verb = removeVerb(app);
        return (
          <AppChoiceRow
            key={account.id}
            app={{ name: account.app.name, slug: account.app.slug, connectorKey: app?.connector_key }}
            detail={accountLabel(account)}
            aside={
              skip ? (
                <span className="text-xs text-muted-foreground">{skip} · skipped</span>
              ) : (
                <span className="grid shrink-0 grid-cols-[auto_6.5rem] items-center gap-3">
                  <span className="text-xs text-muted-foreground">{verb}</span>
                  {app && <WriteModeBadge mode={app.delete_mode} what={verb === "Suspend" ? "suspend" : "remove"} />}
                </span>
              )
            }
          />
        );
      })}
    </AppChoiceList>
  );
}

/** The person becomes Left and every live account gets a removal action waiting for approval. */
function OffboardForm({ person }: { person: PersonDetail }) {
  const router = useRouter();
  const offboard = useOffboardPerson(person.id);
  const plan = usePlan(person);
  const toRemove = plan.filter((item) => !item.skip).length;

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    // The batch waits for approval in Actions: continue there.
    offboard.mutate(undefined, { onSuccess: (result) => router.push(`/actions?batch=${result.batch_id}`) });
  };

  return (
    <FormPage
      title={`Offboard ${fullName(person)}`}
      backHref={`/people/${person.id}`}
      backLabel={fullName(person)}
      description={
        person.status === "left"
          ? "Already left: only missing removals are added. Nothing runs until you approve the batch in Actions."
          : "The person becomes Left and every live account gets a removal action. Nothing runs until you approve the batch in Actions."
      }
      onSubmit={submit}
      submitLabel="Offboard"
      destructive
      pending={offboard.isPending}
      hint={`${toRemove} account(s) to remove after approval`}
    >
      <Plan items={plan} />
    </FormPage>
  );
}

/** `/people/<id>/offboard`. */
export function OffboardView({ id }: { id: string }) {
  return <PersonQuery id={id}>{(person) => <OffboardForm person={person} />}</PersonQuery>;
}
