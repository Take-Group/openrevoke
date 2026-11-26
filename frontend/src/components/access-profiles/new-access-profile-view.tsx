"use client";

import { useRouter } from "next/navigation";

import { AccessProfileForm, EMPTY_PROFILE, toPayload } from "@/components/access-profiles/access-profile-form";
import { useCreateAccessProfile } from "@/hooks/use-access-profiles";

/** `/access-profiles/new`. */
export function NewAccessProfileView() {
  const router = useRouter();
  const create = useCreateAccessProfile();
  return (
    <AccessProfileForm
      title="New access profile"
      backHref="/access-profiles"
      backLabel="Access profiles"
      submitLabel="Create profile"
      initial={EMPTY_PROFILE}
      pending={create.isPending}
      onSubmit={(draft) =>
        create.mutate(toPayload(draft), { onSuccess: (profile) => router.push(`/access-profiles/${profile.id}`) })
      }
    />
  );
}
