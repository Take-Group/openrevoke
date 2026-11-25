import { cn } from "@/lib/utils";

/** The whole first run: /setup (organization, admin, 2FA), then the two questions of /welcome. */
const FIRST_RUN_STEPS = ["Organization", "Admin account", "Two-factor", "People", "Chat", "Password manager"];

/**
 * Where the first run is, for the `eyebrow` of `AuthCard`: one segment per step along the top edge
 * of the card (positioned against the card). No text: the bar is enough; screen readers get
 * "Step n of 5".
 */
export function SetupProgress({ current }: { current: number }) {
  return (
    <div
      className="absolute inset-x-0 top-0 flex gap-[3px]"
      role="progressbar"
      aria-valuemin={1}
      aria-valuemax={FIRST_RUN_STEPS.length}
      aria-valuenow={current + 1}
      aria-valuetext={`Step ${current + 1} of ${FIRST_RUN_STEPS.length}`}
      aria-label="First-run progress"
    >
      {FIRST_RUN_STEPS.map((label, index) => (
        <span key={label} className={cn("h-[3px] flex-1 bg-border", index <= current && "bg-foreground")} />
      ))}
    </div>
  );
}
