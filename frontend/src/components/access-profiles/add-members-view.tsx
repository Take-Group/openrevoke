"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { UsersIcon, XIcon } from "lucide-react";

import { AssignmentPreview } from "@/components/access-profiles/assignment-preview";
import { PersonAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { LinkButton } from "@/components/common/links";
import { Notice } from "@/components/common/notice";
import { Panel } from "@/components/common/panel";
import { PersonPicker } from "@/components/common/person-picker";
import { QueryState } from "@/components/common/query-state";
import { ConvertedTotal } from "@/components/common/converted-money";
import { Button } from "@/components/ui/button";
import { useAccessProfile, useAccessProfileMembers, useAssignProfileMembers } from "@/hooks/use-access-profiles";
import type { AccessProfileOut, MembersAssignResult } from "@/lib/api/access-profile-types";
import type { PersonRef } from "@/lib/api/types";
import { fullName } from "@/lib/format";

type Chosen = Pick<PersonRef, "person_id" | "first_name" | "last_name" | "primary_email">;

function ChosenPeople({ people, onRemove }: { people: Chosen[]; onRemove: (id: string) => void }) {
  return (
    <Panel bodyClassName="flex max-h-72 flex-col divide-y overflow-y-auto text-sm">
      {people.length === 0 ? (
        <EmptyState icon={UsersIcon} title="Nobody chosen yet" className="py-6" />
      ) : (
        people.map((person) => (
          <div key={person.person_id} className="flex items-center gap-3 px-3 py-2">
            <PersonAvatar firstName={person.first_name} lastName={person.last_name} email={person.primary_email} size="sm" />
            <span className="min-w-0 flex-1 leading-tight">
              <span className="block truncate font-medium">{fullName(person)}</span>
              <span className="block truncate text-xs text-muted-foreground">{person.primary_email}</span>
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label={`Remove ${fullName(person)}`}
              onClick={() => onRemove(person.person_id)}
            >
              <XIcon />
            </Button>
          </div>
        ))
      )}
    </Panel>
  );
}

function Preview({ result }: { result: MembersAssignResult }) {
  return (
    <div className="flex flex-col gap-3">
      {result.skipped_people.length > 0 && (
        <Notice tone="warning">
          Skipped: {result.skipped_people.map((item) => `${fullName(item.person)} (${item.reason.toLowerCase()})`).join(", ")}
        </Notice>
      )}
      {result.items.map((item) => (
        <AssignmentPreview
          key={item.person.person_id}
          title={fullName(item.person)}
          planned={item.planned}
          skipped={item.skipped}
          warnings={item.warnings}
          monthlyCost={item.monthly_cost}
          monthlyCostTotal={item.monthly_cost_total}
        />
      ))}
    </div>
  );
}

function AddMembersForm({ profile, initial }: { profile: AccessProfileOut; initial: Chosen[] }) {
  const router = useRouter();
  const [people, setPeople] = useState<Chosen[]>(initial);
  const [preview, setPreview] = useState<MembersAssignResult | null>(null);
  const assign = useAssignProfileMembers(profile.id);
  const base = `/access-profiles/${profile.id}`;
  const ids = people.map((person) => person.person_id);

  const change = (next: Chosen[]) => {
    setPeople(next);
    setPreview(null);
  };
  const runPreview = () => assign.mutate({ person_ids: ids, dry_run: true }, { onSuccess: setPreview });
  const save = (event: React.FormEvent) => {
    event.preventDefault();
    assign.mutate(
      { person_ids: ids },
      {
        onSuccess: (result) => {
          const actions = result.items.reduce((sum, item) => sum + item.actions.length, 0);
          toast.success(`${profile.name} assigned: ${actions} action(s) wait for approval`);
          router.push(actions > 0 ? "/actions?tab=pending" : base);
        },
      },
    );
  };

  return (
    <FormPage
      title={`Add people to ${profile.name}`}
      backHref={base}
      backLabel={profile.name}
      description="Each person gets the profile and one batch of account creations for the apps they lack, with the profile's roles. Nothing runs until you approve in Actions."
      wide
      onSubmit={save}
      submitLabel="Assign"
      hint={
        preview ? (
          <span className="flex items-center gap-1.5">
            Total per month <ConvertedTotal total={preview.monthly_cost_total} parts={preview.monthly_cost} className="font-medium text-foreground" />
          </span>
        ) : (
          `${people.length} chosen`
        )
      }
      actions={
        <>
          <LinkButton href={base} variant="outline">
            Cancel
          </LinkButton>
          {preview ? (
            <Button type="submit" disabled={assign.isPending || ids.length === 0}>
              {assign.isPending ? "Saving…" : "Assign"}
            </Button>
          ) : (
            <Button type="button" onClick={runPreview} disabled={assign.isPending || ids.length === 0}>
              {assign.isPending ? "Loading…" : "Preview"}
            </Button>
          )}
        </>
      }
    >
      <FormField label="People">
        <PersonPicker
          variant="field"
          value={null}
          placeholder="Add a person"
          onChange={(person) => {
            if (person && !ids.includes(person.id)) {
              change([
                ...people,
                {
                  person_id: person.id,
                  first_name: person.first_name,
                  last_name: person.last_name,
                  primary_email: person.primary_email,
                },
              ]);
            }
          }}
        />
      </FormField>
      <ChosenPeople people={people} onRemove={(id) => change(people.filter((person) => person.person_id !== id))} />
      {preview && <Preview result={preview} />}
    </FormPage>
  );
}

/** Members who miss access, for "Create actions for N people" (`?missing=1`). */
function WithMissing({ profile }: { profile: AccessProfileOut }) {
  const members = useAccessProfileMembers(profile.id);
  return (
    <QueryState query={members}>
      {(list) => (
        <AddMembersForm
          profile={profile}
          initial={list.items.filter((member) => member.missing.length > 0).map((member) => member.person)}
        />
      )}
    </QueryState>
  );
}

/** `/access-profiles/<id>/members/add`. */
export function AddMembersView({ id, missing }: { id: string; missing: boolean }) {
  const query = useAccessProfile(id);
  return (
    <QueryState query={query}>
      {(profile) => (missing ? <WithMissing profile={profile} /> : <AddMembersForm profile={profile} initial={[]} />)}
    </QueryState>
  );
}
