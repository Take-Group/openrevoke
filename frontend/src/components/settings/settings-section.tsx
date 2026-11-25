import { PanelFooter } from "@/components/common/panel";
import { cn } from "@/lib/utils";

interface SettingsSectionProps {
  title: React.ReactNode;
  /** One or two muted lines under the title. */
  description?: React.ReactNode;
  /** Grey bar at the bottom: a hint on the left, the action on the right. */
  footer?: React.ReactNode;
  className?: string;
  children?: React.ReactNode;
}

/**
 * A settings card (Vercel's team settings): title, description, the fields, and an optional grey
 * footer. Cards stack with a gap. A form whose submit button belongs in the footer ends with
 * `SettingsFooter` instead of passing `footer`, so the button stays inside the form.
 */
export function SettingsSection({ title, description, footer, className, children }: SettingsSectionProps) {
  return (
    <section className={cn("mt-6 overflow-hidden rounded-lg border border-frame bg-card shadow-card first:mt-0", className)}>
      <div className="p-5">
        <h2 className="text-xl font-semibold tracking-[-0.02em]">{title}</h2>
        {description && <p className="mt-2 text-sm text-muted-foreground">{description}</p>}
        {children && <div className="mt-5 min-w-0">{children}</div>}
      </div>
      {footer && <PanelFooter>{footer}</PanelFooter>}
    </section>
  );
}

/** The footer of a `SettingsSection`, drawn from inside its form (reaches the card's edges). */
export function SettingsFooter({ hint, children }: { hint?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <PanelFooter className="-mx-5 mt-5 -mb-5">
      <span>{hint}</span>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </PanelFooter>
  );
}
