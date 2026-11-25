import { InfoTip } from "@/components/common/info-tip";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface FormFieldProps {
  label: React.ReactNode;
  htmlFor?: string;
  /** One short muted line under the control. */
  hint?: React.ReactNode;
  /** Longer explanation behind an info icon next to the label. */
  info?: React.ReactNode;
  required?: boolean;
  className?: string;
  children: React.ReactNode;
}

/** Label, control and an optional hint under it. */
export function FormField({ label, htmlFor, hint, info, required, className, children }: FormFieldProps) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-center gap-1.5">
        <Label htmlFor={htmlFor} className="gap-0.5 text-[0.8125rem]">
          {label}
          {required && <span className="text-muted-foreground">*</span>}
        </Label>
        {info && <InfoTip>{info}</InfoTip>}
      </div>
      {children}
      {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}
