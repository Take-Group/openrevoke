"use client";

import { ArrowRightIcon, CheckIcon, XIcon } from "lucide-react";
import Link from "next/link";

import { STRINGS_BAND, Strings } from "@/components/common/strings";
import { Button, buttonVariants } from "@/components/ui/button";
import { useAuthState } from "@/hooks/use-auth";
import { useDismissOnboarding, useOnboarding } from "@/hooks/use-onboarding";
import type { ChecklistItem } from "@/lib/api/onboarding-types";
import { cn } from "@/lib/utils";

function Row({ item, index }: { item: ChecklistItem; index: number }) {
  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 py-3 first:pt-0 last:pb-0">
      <span
        className={cn(
          "flex size-5 shrink-0 items-center justify-center rounded-full border text-[0.65rem] font-medium text-muted-foreground",
          item.done && "border-brand bg-brand text-brand-foreground",
        )}
      >
        {item.done ? <CheckIcon className="size-3" /> : index + 1}
      </span>
      <div className="min-w-56 flex-1">
        <p className={cn("text-sm font-medium", item.done && "text-muted-foreground line-through")}>{item.title}</p>
        {!item.done && <p className="mt-0.5 text-sm text-muted-foreground">{item.description}</p>}
      </div>
      {!item.done && item.href && item.action && (
        <Link href={item.href} className={buttonVariants({ variant: item.supported ? "default" : "outline", size: "sm" })}>
          {item.action}
          <ArrowRightIcon />
        </Link>
      )}
    </li>
  );
}

/**
 * First steps of a new installation, from the /welcome answers. Admins only; gone when every
 * step is done or the admin closes it. Each step's state comes from the data, not from clicks.
 */
export function SetupChecklist() {
  const auth = useAuthState();
  const { data } = useOnboarding();
  const dismiss = useDismissOnboarding();
  if (auth.data?.user?.role !== "admin" || !data || data.dismissed_at) return null;
  const items: ChecklistItem[] = data.answered
    ? data.items
    : [
        {
          key: "people",
          title: "Tell Open Revoke where your people come from",
          description: "Two questions: the source of your people and the chat your team uses.",
          href: "/welcome",
          action: "Answer",
          done: false,
          supported: true,
        },
        ...data.items.filter((item) => item.key === "apps"),
      ];
  const done = items.filter((item) => item.done).length;
  if (data.answered && done === items.length) return null;

  return (
    <section className="relative isolate mb-6 overflow-hidden rounded-lg border border-frame bg-card px-5 py-4 shadow-card">
      <Strings shape={STRINGS_BAND} intensity={0.2} className="-z-10 mask-[linear-gradient(to_right,transparent_45%,black_90%)]" />
      <div className="mb-3 flex items-center gap-3">
        <p className="flex-1 text-sm font-medium">
          Set up Open Revoke <span className="font-normal text-muted-foreground">· {done} of {items.length} done</span>
        </p>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Hide the setup steps"
          title="Hide the setup steps"
          onClick={() => dismiss.mutate()}
          disabled={dismiss.isPending}
        >
          <XIcon />
        </Button>
      </div>
      <ol className="divide-y">
        {items.map((item, index) => (
          <Row key={item.key} item={item} index={index} />
        ))}
      </ol>
    </section>
  );
}
