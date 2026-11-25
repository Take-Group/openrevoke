import type { AppListItem, WriteMode } from "@/lib/api/types";

/** "Delete" or "Suspend" (Google Workspace suspends instead of deleting). */
export function removeVerb(app: Pick<AppListItem, "delete_suspends"> | undefined): "Suspend" | "Remove" {
  return app?.delete_suspends ? "Suspend" : "Remove";
}

export const WRITE_MODE_LABEL: Record<WriteMode, string> = {
  automatic: "Automatic",
  writes_disabled: "Writes off",
  manual: "Manual task",
};

/** One short sentence for a tooltip: what happens after approval. */
export function writeModeHint(mode: WriteMode, what: "create" | "remove" | "suspend"): string {
  const verb = what === "create" ? "creates" : what === "suspend" ? "suspends" : "removes";
  if (mode === "automatic") return `After approval the connector ${verb} the account and checks the result.`;
  if (mode === "writes_disabled") return `Writes are off for this app: turn on "Allow writes" in its connection first.`;
  return "After approval you do it in the app yourself and mark it done.";
}
