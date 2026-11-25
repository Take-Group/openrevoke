import { formatMoney } from "@/lib/format";
import type { MoneyAmount } from "@/lib/api/types";
import { cn } from "@/lib/utils";

/** Amounts in several currencies, one per line; no conversion between them. */
export function MoneyList({ amounts, className }: { amounts: MoneyAmount[]; className?: string }) {
  if (amounts.length === 0) return <span className="text-muted-foreground">—</span>;
  return (
    <span className={cn("inline-flex flex-col tabular-nums", className)}>
      {amounts.map((money) => (
        <span key={money.currency} className="whitespace-nowrap">
          {formatMoney(money)}
        </span>
      ))}
    </span>
  );
}

export function Money({ value, className }: { value: MoneyAmount | null | undefined; className?: string }) {
  if (!value) return <span className={cn("text-muted-foreground", className)}>—</span>;
  return <span className={cn("whitespace-nowrap tabular-nums", className)}>{formatMoney(value)}</span>;
}
