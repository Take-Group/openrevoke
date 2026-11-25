"use client";

import { LinkButton } from "@/components/common/links";
import { PageHeader } from "@/components/common/page-header";
import { PanelFooter } from "@/components/common/panel";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FormPageProps {
  title: string;
  /** Where Back and Cancel lead: the list or the record the form belongs to. */
  backHref: string;
  /** Name of that page in the back link ("Apps", the person's name). */
  backLabel: string;
  /** One short line above the fields, only when the form needs it. */
  description?: React.ReactNode;
  onSubmit: (event: React.FormEvent) => void;
  submitLabel: string;
  pending?: boolean;
  submitDisabled?: boolean;
  /** Destructive submit (Offboard). */
  destructive?: boolean;
  wide?: boolean;
  /** Replaces Cancel and submit, for forms with more steps (Preview, Import). */
  actions?: React.ReactNode;
  /** Muted text on the left of the footer. */
  hint?: React.ReactNode;
  children: React.ReactNode;
}

/**
 * Every create and edit form is its own page with its own address (`/apps/new`,
 * `/people/<id>/edit`): a back link in the page bar, one centred card with the fields and a grey
 * footer with Cancel and the submit button. Use it instead of side panels and dialogs for forms;
 * a short yes/no question stays a `ConfirmDialog`.
 */
export function FormPage({
  title,
  backHref,
  backLabel,
  description,
  onSubmit,
  submitLabel,
  pending,
  submitDisabled,
  destructive,
  wide,
  actions,
  hint,
  children,
}: FormPageProps) {
  return (
    <>
      <PageHeader title={title} back={{ href: backHref, label: backLabel }} />
      <form
        onSubmit={onSubmit}
        aria-label={title}
        className={cn(
          "mx-auto w-full overflow-hidden rounded-lg border border-frame bg-card shadow-card",
          wide ? "max-w-2xl" : "max-w-xl",
        )}
      >
        {description && <p className="border-b px-5 py-3 text-sm text-muted-foreground">{description}</p>}
        <div className="flex flex-col gap-4 p-5">{children}</div>
        <PanelFooter>
          <span>{hint}</span>
          <div className="flex items-center gap-2">
            {actions ?? (
              <>
                <LinkButton href={backHref} variant="outline">
                  Cancel
                </LinkButton>
                <Button type="submit" variant={destructive ? "destructive" : "default"} disabled={pending || submitDisabled}>
                  {pending ? "Saving…" : submitLabel}
                </Button>
              </>
            )}
          </div>
        </PanelFooter>
      </form>
    </>
  );
}
