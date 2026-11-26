"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { PencilIcon, Trash2Icon, UserPlusIcon, UsersIcon } from "lucide-react";

import { ProfileMembersTable } from "@/components/access-profiles/profile-members-table";
import { RoleTag } from "@/components/access-profiles/profile-parts";
import { AppAvatar } from "@/components/common/avatars";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { ConvertedMoney, ConvertedTotal } from "@/components/common/converted-money";
import { EmptyState } from "@/components/common/empty-state";
import { LinkButton } from "@/components/common/links";
import { Notice } from "@/components/common/notice";
import { PageHeader, SectionHeader } from "@/components/common/page-header";
import { DetailPageSkeleton, TableSkeleton } from "@/components/common/page-skeletons";
import { Panel } from "@/components/common/panel";
import { QueryState } from "@/components/common/query-state";
import { Stat, StatStrip } from "@/components/common/stat";
import { Button } from "@/components/ui/button";
import { useAccessProfile, useAccessProfileMembers, useDeleteAccessProfile } from "@/hooks/use-access-profiles";
import type { AccessProfileOut } from "@/lib/api/access-profile-types";

function DeleteProfileButton({ profile }: { profile: AccessProfileOut }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const remove = useDeleteAccessProfile(profile.id);
  return (
    <>
      <Button variant="destructive" onClick={() => setOpen(true)}>
        <Trash2Icon />
        <span className="max-md:sr-only">Delete</span>
      </Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={`Delete ${profile.name}?`}
        description={`${profile.member_count} people lose the profile. Their accounts in apps stay.`}
        confirmLabel="Delete profile"
        destructive
        pending={remove.isPending}
        onConfirm={() => remove.mutate(undefined, { onSuccess: () => router.push("/access-profiles") })}
      />
    </>
  );
}

function ProfileApps({ profile }: { profile: AccessProfileOut }) {
  return (
    <Panel title="Apps" meta={profile.apps.length} bodyClassName="flex flex-col divide-y text-sm">
      {profile.apps.length === 0 ? (
        <EmptyState title="No apps in this profile" className="py-6" />
      ) : (
        profile.apps.map((item) => (
          <div key={item.app.app_id} className="flex items-center gap-3 px-5 py-2">
            <AppAvatar name={item.app.name} slug={item.app.slug} size="sm" />
            <span className="min-w-0 flex-1 truncate font-medium">{item.app.name}</span>
            <RoleTag role={item.role} />
            <ConvertedMoney
              converted={item.seat_price_converted}
              original={item.seat_price}
              className="w-24 justify-end text-right text-muted-foreground"
            />
          </div>
        ))
      )}
    </Panel>
  );
}

function Members({ profile }: { profile: AccessProfileOut }) {
  const query = useAccessProfileMembers(profile.id);
  const addHref = `/access-profiles/${profile.id}/members/add`;
  return (
    <section>
      <SectionHeader
        title="Members"
        meta={profile.member_count}
        actions={
          <LinkButton href={addHref} variant="outline" size="sm">
            <UserPlusIcon />
            Add people
          </LinkButton>
        }
      />
      <QueryState query={query} loading={<TableSkeleton rows={3} />}>
        {(list) => (
          <ProfileMembersTable
            members={list.items}
            empty={<EmptyState icon={UsersIcon} title="Nobody has this profile yet" />}
          />
        )}
      </QueryState>
    </section>
  );
}

function ProfilePage({ profile }: { profile: AccessProfileOut }) {
  const base = `/access-profiles/${profile.id}`;
  const missing = profile.members_missing_access;
  return (
    <>
      <PageHeader
        title={profile.name}
        back={{ href: "/access-profiles", label: "Access profiles" }}
        actions={
          <>
            <LinkButton href={`${base}/edit`} variant="outline">
              <PencilIcon />
              Edit
            </LinkButton>
            <DeleteProfileButton profile={profile} />
          </>
        }
      />
      <div className="flex flex-col gap-5">
        <StatStrip className="mb-0">
          <Stat label="Apps">{profile.apps.length}</Stat>
          <Stat label="Members">{profile.member_count}</Stat>
          <Stat label="Per person / mo" info="Seat prices of the per-seat apps in this profile">
            <ConvertedTotal total={profile.cost_per_person_total} parts={profile.cost_per_person} />
          </Stat>
          <Stat label="Requests skip manager">{profile.auto_approve_requests ? "Yes" : "No"}</Stat>
        </StatStrip>
        {profile.description && <p className="text-sm text-muted-foreground">{profile.description}</p>}
        {missing > 0 && (
          <Notice
            tone="warning"
            title={`${missing} ${missing === 1 ? "member misses" : "members miss"} access from this profile`}
            action={
              <LinkButton href={`${base}/members/add?missing=1`} size="sm">
                Create actions for {missing} {missing === 1 ? "person" : "people"}
              </LinkButton>
            }
          >
            They lack an account in an app of the profile and no creation is open.
          </Notice>
        )}
        <ProfileApps profile={profile} />
        <Members profile={profile} />
      </div>
    </>
  );
}

/** `/access-profiles/<id>`. */
export function AccessProfileDetailView({ id }: { id: string }) {
  const query = useAccessProfile(id);
  return (
    <QueryState query={query} loading={<DetailPageSkeleton stats={4} tabs={0} />}>
      {(profile) => <ProfilePage profile={profile} />}
    </QueryState>
  );
}
