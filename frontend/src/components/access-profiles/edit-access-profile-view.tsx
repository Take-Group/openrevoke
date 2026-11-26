"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { AccessProfileForm, toPayload, type ProfileDraft } from "@/components/access-profiles/access-profile-form";
import { QueryState } from "@/components/common/query-state";
import { useAccessProfile, useUpdateAccessProfile } from "@/hooks/use-access-profiles";
import type { AccessProfileOut } from "@/lib/api/access-profile-types";

function draftOf(profile: AccessProfileOut): ProfileDraft {
  return {
    name: profile.name,
    description: profile.description ?? "",
    autoApprove: profile.auto_approve_requests,
    apps: profile.apps.map((item) => ({ app: item.app, role: item.role ?? "" })),
  };
}

function EditForm({ profile }: { profile: AccessProfileOut }) {
  const router = useRouter();
  const update = useUpdateAccessProfile(profile.id);
  const href = `/access-profiles/${profile.id}`;
  return (
    <AccessProfileForm
      title={`Edit ${profile.name}`}
      backHref={href}
      backLabel={profile.name}
      submitLabel="Save"
      initial={draftOf(profile)}
      pending={update.isPending}
      onSubmit={(draft) =>
        update.mutate(toPayload(draft), {
          onSuccess: (saved) => {
            // A new app is not created for members by itself: the profile page offers it.
            if (saved.members_missing_access > 0) {
              toast.info(`${saved.members_missing_access} member(s) now miss access. Create the actions on the profile page.`);
            }
            router.push(href);
          },
        })
      }
    />
  );
}

/** `/access-profiles/<id>/edit`. */
export function EditAccessProfileView({ id }: { id: string }) {
  const query = useAccessProfile(id);
  return <QueryState query={query}>{(profile) => <EditForm profile={profile} />}</QueryState>;
}
