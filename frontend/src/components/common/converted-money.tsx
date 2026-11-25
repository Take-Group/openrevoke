import { TriangleAlertIcon } from "lucide-react";

import { Hint } from "@/components/common/info-tip";
import { MoneyList } from "@/components/common/money-list";
import { formatMoney, formatPrice } from "@/lib/format";
import type { MoneyAmount, PriceOut } from "@/lib/api/types";
import { cn } from "@/lib/utils";

function NoRate({ currency }: { currency: string }) {
  return (
    <Hint label={`No exchange rate for ${currency}, so this amount is not converted.`}>
      <TriangleAlertIcon className="size-3.5 shrink-0 text-warning" aria-label="Not converted" />
    </Hint>
  );
}

interface ConvertedProps<T> {
  /** The amount in the organization currency (null without a rate). */
  converted: T | null | undefined;
  /** The amount in the app's own currency. */
  original: T | null | undefined;
  /**
   * Also show the original amount under the converted one when the app bills
   * in another currency. Only the app detail page does; tables and totals show
   * the organization currency alone.
   */
  showOriginal?: boolean;
  className?: string;
}

function Converted<T extends MoneyAmount>({
  converted,
  original,
  showOriginal = false,
  className,
  format,
}: ConvertedProps<T> & { format: (value: T) => string }) {
  if (!original) return <span className={cn("text-muted-foreground", className)}>—</span>;
  if (!converted) {
    return (
      <span className={cn("inline-flex items-center gap-1 whitespace-nowrap tabular-nums", className)}>
        <NoRate currency={original.currency} />
        {format(original)}
      </span>
    );
  }
  const foreign = showOriginal && converted.currency !== original.currency;
  if (!foreign) return <span className={cn("whitespace-nowrap tabular-nums", className)}>{format(converted)}</span>;
  return (
    <span className={cn("inline-flex flex-col tabular-nums", className)}>
      <span className="whitespace-nowrap">{format(converted)}</span>
      <Hint label={`Billed in ${original.currency}. Converted with the daily exchange rate.`}>
        <span className="text-xs font-normal whitespace-nowrap text-muted-foreground">{format(original)}</span>
      </Hint>
    </span>
  );
}

/**
 * An amount in the organization currency. Without a rate the original is shown
 * with a warning.
 */
export function ConvertedMoney(props: ConvertedProps<MoneyAmount>) {
  return <Converted {...props} format={formatMoney} />;
}

/** A price with its period ("72,50 PLN / mo") in the organization currency. */
export function ConvertedPrice(props: ConvertedProps<PriceOut>) {
  return <Converted {...props} format={formatPrice} />;
}

/**
 * A sum of several currencies, shown in the organization currency. Without a
 * total (a currency has no rate) the parts are listed with a warning.
 */
export function ConvertedTotal({
  total,
  parts,
  className,
}: {
  total: MoneyAmount | null | undefined;
  parts: MoneyAmount[];
  className?: string;
}) {
  if (parts.length === 0) return <span className={cn("text-muted-foreground", className)}>—</span>;
  if (!total) {
    return (
      <span className={cn("inline-flex items-start gap-1", className)}>
        <NoRate currency={parts.map((part) => part.currency).join(", ")} />
        <MoneyList amounts={parts} />
      </span>
    );
  }
  return <span className={cn("whitespace-nowrap tabular-nums", className)}>{formatMoney(total)}</span>;
}
