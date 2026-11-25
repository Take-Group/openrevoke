import Link from "next/link";

import { AddressWarning } from "@/components/layout/address-warning";
import { BrandWordmark } from "@/components/layout/brand-mark";
import { Strings } from "@/components/common/strings";
import { ThemeSwitch } from "@/components/layout/theme-toggle";
import { cn } from "@/lib/utils";

/**
 * Frame of the sign-in pages and the first run (Vercel's sign-up): the theme switch in the top
 * right corner, the wordmark above one card, both centred on the screen on the grey page.
 */
export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative isolate flex min-h-svh flex-col overflow-hidden bg-page">
      <Strings className="-z-10" />
      <ThemeSwitch className="absolute top-4 right-6 z-10" />
      {/* Logo and card centred in both directions; a taller form grows the page and scrolls. */}
      <main className="flex flex-1 flex-col items-center justify-center px-4 py-16">
        <Link href="/login" className="mb-6 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-link">
          <BrandWordmark height={30} />
        </Link>
        <AddressWarning className="mb-5 w-full max-w-[34.375rem]" />
        <div className="w-full max-w-[34.375rem]">{children}</div>
      </main>
    </div>
  );
}

interface AuthCardProps {
  title: string;
  description?: React.ReactNode;
  children: React.ReactNode;
  /** Small centred text at the bottom of the card (e.g. "Forgot password?"). */
  footer?: React.ReactNode;
  /** Along the top edge of the card: where the first run is (`SetupProgress`). */
  eyebrow?: React.ReactNode;
  className?: string;
}

/** The card of a sign-in step: a centred title, the form at 390 px, a footer line. */
export function AuthCard({ title, description, children, footer, eyebrow, className }: AuthCardProps) {
  return (
    <div
      className={cn(
        "relative animate-page-in overflow-hidden rounded-[12px] border border-frame bg-card px-6 pt-8 pb-7 shadow-card sm:px-20 sm:pt-10 sm:pb-8",
        className,
      )}
    >
      {eyebrow}
      <h1 className="text-center text-2xl leading-tight font-semibold tracking-[-0.03em] text-balance">{title}</h1>
      {description && (
        <p className="mx-auto mt-2 max-w-[24rem] text-center text-sm text-muted-foreground text-pretty">{description}</p>
      )}
      <div className="mt-7">{children}</div>
      {footer && <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>}
    </div>
  );
}
