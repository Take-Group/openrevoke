"use client";

import { ShieldCheckIcon } from "lucide-react";

import { AppLogos } from "@/components/access-profiles/profile-parts";
import { EmptyState } from "@/components/common/empty-state";
import { LinkButton } from "@/components/common/links";
import { Panel } from "@/components/common/panel";
import { Checkbox } from "@/components/ui/checkbox";
import type { AccessProfileOut } from "@/lib/api/access-profile-types";
import { cn } from "@/lib/utils";

interface ProfileChoiceListProps {
  profiles: AccessProfileOut[];
  selected: Set<string>;
  onToggle: (profileId: string) => void;
  /** Profiles that cannot be chosen, with the reason shown on the right ("Assigned"). */
  disabled?: Map<string, string>;
}

/** Profiles with a checkbox each and their app logos; used by Onboard and "Add profile". */
export function ProfileChoiceList({ profiles, selected, onToggle, disabled }: ProfileChoiceListProps) {
  return (
    <Panel bodyClassName="flex max-h-72 flex-col divide-y overflow-y-auto text-sm">
      {profiles.length === 0 ? (
        <EmptyState
          icon={ShieldCheckIcon}
          title="No access profiles yet"
          className="py-6"
          action={
            <LinkButton href="/access-profiles/new" variant="outline" size="sm">
              New profile
            </LinkButton>
          }
        />
      ) : (
        profiles.map((profile) => {
          const reason = disabled?.get(profile.id);
          return (
            <label
              key={profile.id}
              className={cn("flex items-center gap-3 px-3 py-2", reason ? "opacity-60" : "cursor-pointer hover:bg-subtle")}
            >
              <Checkbox
                disabled={Boolean(reason)}
                checked={selected.has(profile.id)}
                onCheckedChange={() => onToggle(profile.id)}
              />
              <span className="min-w-0 flex-1 leading-tight">
                <span className="block truncate font-medium">{profile.name}</span>
                <span className="block truncate text-xs text-muted-foreground">
                  {reason ?? `${profile.apps.length} app(s)`}
                </span>
              </span>
              <AppLogos apps={profile.apps} max={5} />
            </label>
          );
        })
      )}
    </Panel>
  );
}
