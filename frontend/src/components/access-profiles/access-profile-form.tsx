"use client";

import { useState } from "react";
import { AppWindowIcon, XIcon } from "lucide-react";

import { AppAvatar } from "@/components/common/avatars";
import { EmptyState } from "@/components/common/empty-state";
import { FormField } from "@/components/common/form-field";
import { FormPage } from "@/components/common/form-page";
import { Panel } from "@/components/common/panel";
import { SearchableSelect } from "@/components/common/searchable-select";
import { SuggestInput } from "@/components/common/suggest-input";
import { SwitchField } from "@/components/common/switch-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAppRoleSuggestions } from "@/hooks/use-access-profiles";
import { useApps } from "@/hooks/use-apps";
import type { AccessProfileCreate } from "@/lib/api/access-profile-types";
import type { AppRef } from "@/lib/api/types";
import { emptyToNull } from "@/lib/format";

export interface ProfileAppDraft {
  app: AppRef;
  role: string;
}

export interface ProfileDraft {
  name: string;
  description: string;
  autoApprove: boolean;
  apps: ProfileAppDraft[];
}

export const EMPTY_PROFILE: ProfileDraft = { name: "", description: "", autoApprove: false, apps: [] };

export function toPayload(draft: ProfileDraft): Required<AccessProfileCreate> {
  return {
    name: draft.name.trim(),
    description: emptyToNull(draft.description),
    auto_approve_requests: draft.autoApprove,
    apps: draft.apps.map((item) => ({ app_id: item.app.app_id, role: emptyToNull(item.role) })),
  };
}

function AppRow({
  item,
  roles,
  onRole,
  onRemove,
}: {
  item: ProfileAppDraft;
  roles: string[];
  onRole: (role: string) => void;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center gap-3 px-3 py-2">
      <AppAvatar name={item.app.name} slug={item.app.slug} size="sm" />
      <span className="min-w-0 flex-1 truncate font-medium">{item.app.name}</span>
      <div className="w-44">
        <SuggestInput value={item.role} onChange={onRole} suggestions={roles} placeholder="Any role" />
      </div>
      <Button type="button" variant="ghost" size="icon-sm" aria-label={`Remove ${item.app.name}`} onClick={onRemove}>
        <XIcon />
      </Button>
    </div>
  );
}

/** The apps of a profile with a role each, and a picker that adds one more. */
function ProfileApps({ apps, onChange }: { apps: ProfileAppDraft[]; onChange: (apps: ProfileAppDraft[]) => void }) {
  const allApps = useApps({ limit: 500 });
  const roles = useAppRoleSuggestions();
  const chosen = new Set(apps.map((item) => item.app.app_id));
  const options = (allApps.data?.items ?? [])
    .filter((app) => !chosen.has(app.id))
    .map((app) => ({ value: app.id, label: app.name }));

  const add = (appId: string) => {
    const app = allApps.data?.items.find((item) => item.id === appId);
    if (!app) return;
    const suggested = roles.data?.get(app.id)?.[0] ?? "";
    onChange([...apps, { app: { app_id: app.id, name: app.name, slug: app.slug }, role: suggested }]);
  };

  return (
    <FormField label="Apps" htmlFor="profile-add-app" hint="Role suggestions come from existing accounts. Empty: any role.">
      <Panel bodyClassName="flex max-h-96 flex-col divide-y overflow-y-auto text-sm">
        {apps.length === 0 ? (
          <EmptyState icon={AppWindowIcon} title="No apps yet" className="py-6" />
        ) : (
          apps.map((item, index) => (
            <AppRow
              key={item.app.app_id}
              item={item}
              roles={roles.data?.get(item.app.app_id) ?? []}
              onRole={(role) => onChange(apps.map((other, i) => (i === index ? { ...other, role } : other)))}
              onRemove={() => onChange(apps.filter((_, i) => i !== index))}
            />
          ))
        )}
      </Panel>
      <SearchableSelect
        id="profile-add-app"
        value=""
        onChange={add}
        groups={[{ options }]}
        placeholder={allApps.isPending ? "Loading apps…" : "Add an app"}
        searchPlaceholder="Search apps"
        emptyText="No more apps"
        disabled={allApps.isPending}
        className="mt-2"
      />
    </FormField>
  );
}

interface AccessProfileFormProps {
  title: string;
  backHref: string;
  backLabel: string;
  submitLabel: string;
  initial: ProfileDraft;
  pending: boolean;
  onSubmit: (draft: ProfileDraft) => void;
}

/** Name, description, apps with roles and the "skip the manager" switch; used by new and edit. */
export function AccessProfileForm({ title, backHref, backLabel, submitLabel, initial, pending, onSubmit }: AccessProfileFormProps) {
  const [draft, setDraft] = useState<ProfileDraft>(initial);
  const set = (patch: Partial<ProfileDraft>) => setDraft((current) => ({ ...current, ...patch }));

  return (
    <FormPage
      title={title}
      backHref={backHref}
      backLabel={backLabel}
      wide
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(draft);
      }}
      submitLabel={submitLabel}
      pending={pending}
      submitDisabled={!draft.name.trim()}
      hint={`${draft.apps.length} app(s)`}
    >
      <FormField label="Name" htmlFor="profile-name">
        <Input
          id="profile-name"
          value={draft.name}
          onChange={(event) => set({ name: event.target.value })}
          placeholder="Developer"
          maxLength={200}
          required
        />
      </FormField>
      <FormField label="Description" htmlFor="profile-description">
        <Textarea
          id="profile-description"
          value={draft.description}
          onChange={(event) => set({ description: event.target.value })}
          rows={2}
          maxLength={2000}
        />
      </FormField>
      <ProfileApps apps={draft.apps} onChange={(apps) => set({ apps })} />
      <SwitchField
        id="profile-auto-approve"
        label="Requests for these apps skip the manager"
        hint="A person with this profile who asks for one of its apps gets it without the manager's approval."
        checked={draft.autoApprove}
        onChange={(autoApprove) => set({ autoApprove })}
      />
    </FormPage>
  );
}
