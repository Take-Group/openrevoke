import { cn } from "@/lib/utils";

interface PanelProps {
  /** Header row inside the frame; leave out for a bare frame. */
  title?: React.ReactNode;
  /** Muted text or a count after the title. */
  meta?: React.ReactNode;
  /** Small buttons or links on the right of the header. */
  actions?: React.ReactNode;
  /** "muted": a grey box for a side note or a secret shown once. */
  tone?: "default" | "muted";
  className?: string;
  /** Classes of the body (padding, dividers). */
  bodyClassName?: string;
  /** Grey bar under the body: a hint on the left, a button on the right. */
  footer?: React.ReactNode;
  children: React.ReactNode;
}

/**
 * A white block with a hairline frame and an optional header row: the one
 * container of the panel. Do not nest panels; split the page instead.
 */
export function Panel({ title, meta, actions, tone = "default", className, bodyClassName, footer, children }: PanelProps) {
  return (
    <section
      className={cn(
        "flex min-w-0 flex-col overflow-hidden rounded-lg border border-frame",
        tone === "muted" ? "bg-subtle" : "bg-card shadow-card",
        className,
      )}
    >
      {title !== undefined && (
        <header className="flex min-h-12 items-center justify-between gap-3 border-b px-5 py-2">
          <h2 className="flex min-w-0 items-center gap-1.5 text-sm font-medium tracking-[-0.02em]">
            {title}
            {meta !== undefined && meta !== null && (
              <span className="font-normal text-muted-foreground tabular-nums">{meta}</span>
            )}
          </h2>
          {actions && <div className="flex shrink-0 items-center gap-1.5">{actions}</div>}
        </header>
      )}
      <div className={cn("min-h-0 flex-1", bodyClassName)}>{children}</div>
      {footer && <PanelFooter>{footer}</PanelFooter>}
    </section>
  );
}

/**
 * The grey bar at the bottom of a card (Vercel settings): a muted hint on the left, the action on
 * the right. `Panel` draws it from `footer`; a form inside a card renders it last, so its submit
 * button stays inside the form.
 */
export function PanelFooter({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      className={cn(
        "flex min-h-14 flex-wrap items-center justify-between gap-3 border-t border-frame bg-subtle px-5 py-3 text-sm text-muted-foreground",
        className,
      )}
    >
      {children}
    </div>
  );
}
