"use client";

import { AppAvatar } from "@/components/common/avatars";
import { Hint } from "@/components/common/info-tip";
import { TagBadge } from "@/components/common/status-badge";
import type { AppRef } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/** App logos side by side, the name in a tooltip; more than `max` become "+N". */
export function AppLogos({ apps, max = 6 }: { apps: { app: AppRef; role?: string | null }[]; max?: number }) {
  if (apps.length === 0) return <span className="text-muted-foreground">—</span>;
  const shown = apps.slice(0, max);
  return (
    <span className="inline-flex items-center gap-1">
      {shown.map(({ app, role }) => (
        <Hint key={app.app_id} label={role ? `${app.name}: ${role}` : app.name}>
          <span>
            <AppAvatar name={app.name} slug={app.slug} size="xs" />
          </span>
        </Hint>
      ))}
      {apps.length > max && <span className="text-xs text-muted-foreground">+{apps.length - max}</span>}
    </span>
  );
}

/** A role as a quiet tag; "Any role" when the profile does not set one. */
export function RoleTag({ role, className }: { role: string | null | undefined; className?: string }) {
  return <TagBadge className={cn(!role && "italic", className)}>{role || "any role"}</TagBadge>;
}

/** Short comma list of app names, for table cells. */
export function AppNames({ apps, empty = "—" }: { apps: AppRef[]; empty?: string }) {
  if (apps.length === 0) return <span className="text-muted-foreground">{empty}</span>;
  return <span className="truncate">{apps.map((app) => app.name).join(", ")}</span>;
}
