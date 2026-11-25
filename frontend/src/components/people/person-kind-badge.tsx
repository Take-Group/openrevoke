"use client";

import { ServerCogIcon } from "lucide-react";

import { Hint } from "@/components/common/info-tip";
import { Badge } from "@/components/ui/badge";
import type { PersonListItem } from "@/lib/api/types";

/** "Service account" with why: the import rule, or an admin's choice. Nothing for people. */
export function PersonKindBadge({ person }: { person: Pick<PersonListItem, "kind" | "kind_source" | "kind_reason"> }) {
  if (person.kind !== "service") return null;
  const why =
    person.kind_source === "manual"
      ? "Marked as a service account by an admin. Syncs keep it."
      : `Marked automatically: ${person.kind_reason ?? "import rules"}. Change it in the More menu.`;
  return (
    <Hint label={why}>
      <Badge variant="secondary" className="gap-1">
        <ServerCogIcon className="size-3" />
        Service account
      </Badge>
    </Hint>
  );
}
