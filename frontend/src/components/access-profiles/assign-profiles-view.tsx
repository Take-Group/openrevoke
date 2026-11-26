"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AssignmentPreview } from "@/components/access-profiles/assignment-preview";
import { ProfileChoiceList } from "@/components/access-profiles/profile-choice-list";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { LinkButton } from "@/components/common/links";
import { LoadingRows, QueryState } from "@/components/common/query-state";
import { Button } from "@/components/ui/button";
import { useAccessProfiles, useAssignPersonProfiles, usePersonAccessProfiles } from "@/hooks/use-access-profiles";
import { usePerson } from "@/hooks/use-people";
import type { ProfileAssignResult } from "@/lib/api/access-profile-types";
import type { PersonDetail } from "@/lib/api/types";
import { fullName } from "@/lib/format";

function AssignForm({ person }: { person: PersonDetail }) {
  const router = useRouter();
  const profiles = useAccessProfiles();
  const current = usePersonAccessProfiles(person.id);
  const assign = useAssignPersonProfiles(person.id);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [preview, setPreview] = useState<ProfileAssignResult | null>(null);
  const back = `/people/${person.id}`;
  const left = person.status === "left";
  const assigned = new Map((current.data?.items ?? []).map((item) => [item.profile.profile_id, "Assigned"]));
  const ids = [...selected];

  const toggle = (id: string) => {
    setSelected((now) => {
      const next = new Set(now);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setPreview(null);
  };
  const runPreview = () => assign.mutate({ profile_ids: ids, dry_run: true }, { onSuccess: setPreview });
  const save = (event: React.FormEvent) => {
    event.preventDefault();
    assign.mutate(
      { profile_ids: ids },
      {
        onSuccess: (result) => {
          toast.success(`Assigned: ${result.actions.length} action(s) wait for approval`);
          router.push(result.batch_id ? `/actions?batch=${result.batch_id}` : back);
        },
      },
    );
  };

  return (
    <FormPage
      title={`Add access profiles to ${fullName(person)}`}
      backHref={back}
      backLabel={fullName(person)}
      description="The person gets the profiles and one batch of account creations for the apps they lack, with the profiles' roles. Nothing runs until you approve the batch in Actions."
      wide
      onSubmit={save}
      submitLabel="Assign"
      hint={left ? "The person has left." : `${selected.size} profile(s) chosen`}
      actions={
        <>
          <LinkButton href={back} variant="outline">
            Cancel
          </LinkButton>
          {preview ? (
            <Button type="submit" disabled={assign.isPending || left}>
              {assign.isPending ? "Saving…" : "Assign"}
            </Button>
          ) : (
            <Button type="button" onClick={runPreview} disabled={assign.isPending || ids.length === 0 || left}>
              {assign.isPending ? "Loading…" : "Preview"}
            </Button>
          )}
        </>
      }
    >
      <FormField label="Profiles">
        {profiles.isPending || current.isPending ? (
          <LoadingRows rows={3} />
        ) : (
          <ProfileChoiceList
            profiles={profiles.data?.items ?? []}
            selected={selected}
            onToggle={toggle}
            disabled={assigned}
          />
        )}
      </FormField>
      {preview && (
        <AssignmentPreview
          planned={preview.planned}
          skipped={preview.skipped}
          warnings={preview.warnings}
          monthlyCost={preview.monthly_cost}
          monthlyCostTotal={preview.monthly_cost_total}
        />
      )}
    </FormPage>
  );
}

/** `/people/<id>/access-profiles/add`. */
export function AssignProfilesView({ id }: { id: string }) {
  const query = usePerson(id);
  return <QueryState query={query}>{(person) => <AssignForm person={person} />}</QueryState>;
}
