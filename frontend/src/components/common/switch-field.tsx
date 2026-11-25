import { InfoTip } from "@/components/common/info-tip";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";

interface SwitchFieldProps {
  id: string;
  label: React.ReactNode;
  /** Longer explanation behind an info icon next to the label. */
  info?: React.ReactNode;
  /** One short muted line under the label. */
  hint?: React.ReactNode;
  checked: boolean;
  disabled?: boolean;
  onChange: (checked: boolean) => void;
}

/** A yes/no setting in a form: label and hint on the left, the switch on the right. */
export function SwitchField({ id, label, info, hint, checked, disabled, onChange }: SwitchFieldProps) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex items-center gap-1.5">
          <Label htmlFor={id} className="text-[0.8125rem]">
            {label}
          </Label>
          {info && <InfoTip>{info}</InfoTip>}
        </div>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      <Switch id={id} className="mt-0.5" checked={checked} disabled={disabled} onCheckedChange={onChange} />
    </div>
  );
}
