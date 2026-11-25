import Link from "next/link";
import { ExternalLinkIcon, XIcon } from "lucide-react";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const TEXT_LINK = {
  default:
    "font-medium text-foreground underline decoration-brand/40 underline-offset-4 transition-colors hover:text-brand-ink hover:decoration-brand-ink",
  muted: "text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline",
};

interface TextLinkProps {
  href: string;
  /** Opens in a new tab; use for every address outside the panel. */
  external?: boolean;
  /** `muted`: a quiet way out ("Skip", "Back to sign-in"), grey until hovered. */
  tone?: keyof typeof TEXT_LINK;
  className?: string;
  children: React.ReactNode;
}

/** A link inside a sentence or a "See all" link. Same look for inner and outer links. */
export function TextLink({ href, external, tone = "default", className, children }: TextLinkProps) {
  if (external) {
    return (
      <a href={href} target="_blank" rel="noreferrer" className={cn(TEXT_LINK[tone], className)}>
        {children}
      </a>
    );
  }
  return (
    <Link href={href} className={cn(TEXT_LINK[tone], className)}>
      {children}
    </Link>
  );
}

/**
 * The name of a record (person, app) in a table or list that opens its page. Plain text until
 * hovered, then underlined. Layout classes only in `className`.
 */
export function RecordLink({ href, className, children }: { href: string; className?: string; children: React.ReactNode }) {
  return (
    <Link href={href} className={cn("decoration-brand/60 underline-offset-4 hover:underline", className)}>
      {children}
    </Link>
  );
}

/** A button that opens a page of another service (Slack, Google console) in a new tab. */
export function ExternalLinkButton({
  href,
  variant = "outline",
  className,
  children,
}: {
  href: string;
  variant?: "outline" | "default";
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className={cn(buttonVariants({ variant, size: "sm" }), "w-fit", className)}>
      {children}
      <ExternalLinkIcon />
    </a>
  );
}

/** An active filter set from another page (e.g. "Person: Ann"), with an x that removes it. */
export function FilterChip({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className={cn(buttonVariants({ variant: "outline", size: "sm" }), "gap-1 font-normal")}>
      {children}
      <XIcon className="text-muted-foreground" />
    </Link>
  );
}

type ButtonLook = NonNullable<Parameters<typeof buttonVariants>[0]>;

/**
 * A button that goes to another page of the panel (Add app, Edit, Onboard). A real link, so the
 * address changes and the page can be opened directly. `disabled` draws a disabled button instead.
 */
export function LinkButton({
  href,
  variant,
  size,
  disabled,
  title,
  className,
  children,
}: {
  href: string;
  variant?: ButtonLook["variant"];
  size?: ButtonLook["size"];
  disabled?: boolean;
  title?: string;
  className?: string;
  children: React.ReactNode;
}) {
  const classes = cn(buttonVariants({ variant, size }), className);
  if (disabled) {
    return (
      <span role="link" aria-disabled="true" title={title} className={cn(classes, "pointer-events-none opacity-50")}>
        {children}
      </span>
    );
  }
  return (
    <Link href={href} title={title} className={classes}>
      {children}
    </Link>
  );
}
