import { CheckIcon, XIcon } from "lucide-react";

import { Spinner } from "@/components/common/spinner";
import { cn } from "@/lib/utils";

export type StepState = "todo" | "active" | "running" | "done" | "failed";

/** A numbered list of setup steps. Children are `Step`s. */
export function Steps({ children, className }: { children: React.ReactNode; className?: string }) {
  return <ol className={cn("flex flex-col gap-5", className)}>{children}</ol>;
}

const MARK: Record<StepState, string> = {
  todo: "border bg-background text-muted-foreground",
  active: "border border-brand bg-brand-soft text-brand-ink",
  running: "border bg-background text-muted-foreground",
  done: "bg-success/15 text-success",
  failed: "bg-destructive/12 text-destructive",
};

interface StepProps {
  n: number;
  title: React.ReactNode;
  state?: StepState;
  /** Muted line under the title. */
  description?: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
}

/** One step: number (or a check, cross or spinner), title, optional description and body. */
export function Step({ n, title, state = "todo", description, className, children }: StepProps) {
  return (
    <li className={cn("flex gap-3", className)}>
      <span
        className={cn(
          "mt-px flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-medium tabular-nums",
          MARK[state],
        )}
      >
        {state === "done" ? (
          <CheckIcon className="size-3.5" />
        ) : state === "failed" ? (
          <XIcon className="size-3.5" />
        ) : state === "running" ? (
          <Spinner className="size-3.5" />
        ) : (
          n
        )}
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-2.5 pt-0.5">
        <div className="flex flex-col gap-0.5">
          <h3 className={cn("text-sm font-medium", state === "todo" && "text-muted-foreground")}>{title}</h3>
          {description && <p className="text-[0.8125rem] text-muted-foreground">{description}</p>}
        </div>
        {children}
      </div>
    </li>
  );
}
